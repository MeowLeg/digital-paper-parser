# encoding=utf-8

import sqlite3
import requests


class ExportArticle:
    def __init__(self, db_path: str = "../daily.db", page_name: str = "舟山日报"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.svr_url = "https://develop.xinlantech.cn/zscmscore/"
        self.page_name = page_name

    def __post(self, data, postfix):
        resp = requests.post(self.svr_url + postfix, json=data)
        if resp.status_code != 200:
            print(f"POST失败, 状态码: {resp.status_code}, 响应: {resp.text}")
            return
        else:
            print(f"POST成功, 响应: {resp.text}")
            resp_data = resp.json()
            if resp_data["success"]:
                return resp_data

    def __filter_article(self, article):
        # 舟山关注是广告版
        # "舟山关注", "广告", "金融理财"里有通讯员的，还要给稿费
        for pn in ["国内", "国际", "全国"]:
            if pn in article["page_name"]:
                return False
        if article["title"].startswith("新华社"):
            return False
        if (
            article["author"] == ""
            and article["photo"] == ""
            and article["collaborator"] == ""
        ):
            return False
        if article["is_xinhua"] == 1:
            return False
        return True

    def __vectorize_title(self) -> None:
        # 向量化标题
        url = "https://develop.xinlantech.cn/zscmscore/vectorize_titles"
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"向量化新增标题失败, 状态码: {resp.status_code}, 响应: {resp.text}")
            return
        else:
            print(f"向量化新增标题成功, 响应: {resp.text}")
            resp_data = resp.json()
            if resp_data["success"]:
                return resp_data["data"]
            else:
                print(f"向量化新增标题失败, 响应: {resp.text}")
                return None

    def job(self):
        dump_article_ids = []
        for row in self.cursor.execute(
            "select * from digital_paper where is_dump = 0"
        ).fetchall():
            date_eles = [int(e) for e in row["date"].split("-")]
            page_meta_id = 0
            try:
                page_meta_id = int(row["page_no"])
            except Exception as _e:
                pass
            if not self.__filter_article(row):
                continue
            print(f"POST文章: {row['title']} ")
            resp_data = self.__post(
                {
                    "title": row["title"],
                    "tv_or_paper": row["site_id"],
                    "publish_year": date_eles[0],
                    "publish_month": date_eles[1],
                    "publish_day": date_eles[2],
                    "tv_url": "",
                    "page_meta_id": page_meta_id,
                    "page_name": row["page_name"],
                    "state": 1,
                    "content": row["content"],
                    "html_content": row["content"].replace("\n", "<br>"),
                    "ref_id": row["id"],
                    "duration": 0,
                    "character_count": len(row["content"]),
                    "is_collaboration": 1 if len(row["collaborator"]) > 0 else 0,
                },
                "article_from_dump",
            )
            if resp_data is not None:
                article_id = resp_data["data"]
                if article_id is None or article_id <= 0:
                    continue
                reporter_data = []
                for reporter in row["author"].split(" "):
                    if len(reporter) > 0:
                        reporter_data.append(
                            {
                                "reporter_name": reporter,
                                "reporter_category_id": 3,
                                "score": 0,
                            }
                        )
                for reporter in row["photo"].split(" "):
                    if len(reporter) > 0:
                        reporter_data.append(
                            {
                                "reporter_name": reporter,
                                "reporter_category_id": 4,
                                "score": 0,
                            }
                        )
                for reporter in row["collaborator"].split(" "):
                    if len(reporter) > 0:
                        reporter_data.append(
                            {
                                "reporter_name": reporter,
                                "reporter_category_id": 7,
                                "score": 0,
                            }
                        )
                if len(reporter_data):
                    self.__post(
                        {
                            "article_id": article_id,
                            "score_basic": 0,
                            "score_action": 0,
                            "reporter_scores": reporter_data,
                        },
                        "score_for_dump",
                    )
                dump_article_ids.append(f"{row['id']}")

        self.cursor.execute(
            f"update digital_paper set is_dump = 1 where id in ({','.join(dump_article_ids)})"
        )
        self.conn.commit()
        # 向量化标题
        self.__vectorize_title()


if __name__ == "__main__":
    export_article = ExportArticle()
    export_article.job()
