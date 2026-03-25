# encoding=utf-8

from fetch_ftp import FetchFtp, get_current_date
from kimi_cloud import PdfParser
from write_db import WriteDb
from filter_department import FilterDepartment
from check_reporter import CheckSpecialReporter
from export_article import ExportArticle
from find_duplicate import FindDeplicate, compare_title

from pathlib import Path
import json
import os


def __convert_page_no(page_no: str) -> int | str:
    try:
        return int(page_no)
    except Exception as _e:
        return page_no


THRESHOLD = 0.9


def __update_article(ra, d):
    ra["content"] += d["content"]
    # 合并作者、通讯员、照片
    if ra["author"] == "" and d["author"]:
        ra["author"] = d["author"]
    if ra["collaborator"] == "" and d["collaborator"]:
        ra["collaborator"] = d["collaborator"]
    if ra["photo"] == "" and d["photo"]:
        ra["photo"] = d["photo"]
    d["dump"] = False
    if ra["is_xinhua"] == 0 and d["is_xinhua"] == 1:
        ra["is_xinhua"] = 1
    d["has_previous"] = False


def __merge_content(ra, rest_datas, title, db):
    title = ra["title"]
    page_no = __convert_page_no(ra["next_page"])
    # target_page_articles = [a for a in datas[i+1] if __convert_page_no(a["page_no"]) == page_no]
    # for d in datas[i+1:]:
    for idx, d in enumerate(rest_datas):
        pn = __convert_page_no(d["page_no"])
        # 采用qwen3.5检测转版的题目相似度
        if pn == page_no:
            compare_title_result = compare_title(
                "http://localhost:11434", "qwen3.5:4b", [d["title"], title]
            )
            if len(d["title"]) > 0 and (
                (compare_title_result is not None and compare_title_result >= THRESHOLD)
                or d["title"] in title
            ):
                print(idx, d["title"])
                __update_article(ra, d)
                # 更新数据库中原文章的内容
                db.update_article_content(ra["id"], ra["content"])
                # 删除已经被合并的文章
                db.delete_article(d["id"])
                if len(d["next_page"]) > 0:
                    __merge_content(ra, rest_datas[idx + 1 :], title, db)
                return
    # for idx, d in enumerate(rest_datas):
    #     pn = __convert_page_no(d["page_no"])
    #     if pn == page_no and d["has_previous"]:
    #         __update_article(ra, d)
    #         # 更新数据库中原文章的内容
    #         db.update_article_content(ra["id"], ra["content"])
    #         # 删除已经被合并的文章
    #         db.delete_article(d["id"])
    #         if len(d["next_page"]) > 0:
    #             __merge_content(ra, rest_datas[idx + 1 :], title, db)


def merge_content(datas, db):
    """
    转版内容合并.
    """
    datas.sort(key=lambda x: __convert_page_no(x["page_no"]))
    for idx, data in enumerate(datas):
        # if data["dump"] and len(data["next_page"]) > 0:
        if len(data["next_page"]) > 0:
            print("开始比对：", data["title"])
            __merge_content(datas[idx], datas[idx + 1 :], data["title"], db)


def load_parsed_record(record_file: str) -> set:
    """加载已解析的PDF记录"""
    if os.path.exists(record_file):
        with open(record_file, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_parsed_record(record_file: str, parsed_pdfs: set):
    """保存已解析的PDF记录"""
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(list(parsed_pdfs), f, ensure_ascii=False, indent=2)


def main(date_eles: list[str] = []):
    # 0. 准备记录文件
    current_date = "-".join(date_eles) if len(date_eles) else get_current_date("-")
    record_file = f"../parsed_record_{current_date}.json"
    parsed_pdfs = load_parsed_record(record_file)
    print(f"已解析的PDF: {parsed_pdfs}")

    # 确保使用绝对路径
    script_dir = Path(__file__).parent.resolve()
    db_path = script_dir.parent / "daily.db"
    print(f"数据库路径: {db_path}")

    # 1. 从FTP服务器下载文件
    ftp_host = "47.105.52.63"
    ftp_port = 21
    ftp_user = "zsftp"
    ftp_pass = "zsftp^Psa99Epaper"
    target_dir = "舟山日报"
    ftpObj = FetchFtp(ftp_host, ftp_port, ftp_user, ftp_pass, target_dir)
    target_down_dir = ftpObj.ftp_job("".join(date_eles) if len(date_eles) else None)
    if target_down_dir is None:
        print("FTP操作失败")
        return

    # 2. 从Kimi Cloud解析文件
    api_key = "sk-BSvteGexprXexqyk6O5RBSPJtcmBNzoZwHVnVAAmJTUPIZTE"
    base_url = "https://api.moonshot.cn/v1"
    model = "kimi-k2.5"
    if not Path(target_down_dir).exists() or not Path(target_down_dir).is_dir():
        print("目标目录不存在")
        return

    # 初始化数据库连接（只连接一次）
    db = WriteDb(str(db_path))

    parser = PdfParser(api_key, base_url, model)
    except_files = []

    pdf_files = sorted(Path(target_down_dir).glob("*.pdf"))
    total = len(pdf_files)

    # 先将所有解析的文章写入数据库
    total_insert = 0
    for idx, pdf_path in enumerate(pdf_files, 1):
        pdf_path_str = str(pdf_path).replace("\\", "/")
        pdf_name = pdf_path.name

        # 检查是否已解析
        if pdf_name in parsed_pdfs:
            print(f"[{idx}/{total}] 跳过已解析: {pdf_name}")
            continue

        # 检查是否在排除列表
        to_parse = True
        for f in except_files:
            if f is not None and len(f) > 0 and f in f"{pdf_path}":
                to_parse = False
                break
        if not to_parse:
            continue

        print(f"[{idx}/{total}] 解析文件: {pdf_path}")

        try:
            ret = parser.parse(f"{pdf_path}")

            # 处理 high risk 情况
            if ret and ret.get("high_risk"):
                print(f"[{idx}/{total}] Kimi返回 high risk，跳过并记录: {pdf_name}")
                parsed_pdfs.add(pdf_name)
                save_parsed_record(record_file, parsed_pdfs)
                print(f"[{idx}/{total}] 已记录为已解析(高风险): {pdf_name}")
                continue

            if ret is None or not ret["success"]:
                print(f"[{idx}/{total}] 解析失败或返回空: {pdf_name}")
                continue

            # 立即写入数据库
            count = 0
            for d in ret["data"]:
                d["date"] = current_date
                d["pdf"] = f"{pdf_path_str}"
                db.write(d)
                count += 1
                total_insert += 1

            print(f"[{idx}/{total}] 写入数据库成功: {count} 篇文章")

            # 标记为已解析
            parsed_pdfs.add(pdf_name)
            save_parsed_record(record_file, parsed_pdfs)
            print(f"[{idx}/{total}] 已记录: {pdf_name}")

        except Exception as e:
            print(f"[{idx}/{total}] 解析异常: {pdf_name}, 错误: {e}")
            import traceback

            traceback.print_exc()
            continue

    print(f"\n所有PDF解析完成，共写入 {total_insert} 篇文章")

    # # 从数据库读取当天所有文章进行合并处理
    print("开始读取数据库中的文章...")
    all_articles = db.get_articles_by_date(current_date)
    print(f"读取到 {len(all_articles)} 篇文章，开始合并转版内容...")

    # # 在所有版面都写入数据库后进行合并
    merge_content(all_articles, db)
    print("转版内容合并完成")

    # 3. 过滤部门
    print("开始过滤部门...")
    filter_department = FilterDepartment()
    filter_department.job(current_date)
    print("过滤部门成功")

    # 4. 检查特殊版面的记者
    print("开始检查记者...")
    check_reporter = CheckSpecialReporter()
    check_reporter.job(date_eles)
    print("检查记者成功")

    print("\n任务完成!")


if __name__ == "__main__":
    main([])
