# encoding=utf-8

import requests
import sqlite3
import json
from fetch_ftp import get_current_date
from urllib.parse import quote


class CheckSpecialReporter:
    def __init__(self, db_path: str = "../daily.db"):
        self.special_pagename_1 = ["海山观察", "海潮文艺"]
        self.special_pagename_2 = [
            "海潮理论",
            "海潮人文",
            "竞“拍”",
            "竞 “拍”",
            '竞"拍"',
            '竞 "拍"',
        ]
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def __get_reporter_info(self, name):
        resp = requests.get(
            "https://develop.xinlantech.cn/zscmscore/get_reporter_info_by_name?name="
            + quote(name)
            # verify=False
        )
        if resp.status_code == 200:
            ret = resp.json()
            if "success" in ret and ret["success"] and ret["data"] is not None:
                return ret["data"]
            else:
                return None

    def job(self, date_eles: list[str]):
        """
        检查指定日期的记者是否存在.
        """
        date_str = "-".join(date_eles) if len(date_eles) == 3 else get_current_date("-")
        for r in self.cursor.execute(
            "select id, title, author, collaborator, photo, page_name, is_pic, is_xinhua from digital_paper where date = ?",
            (date_str,),
        ).fetchall():
            row = dict(r)
            # if r["id"] != 896:
            #     continue
            # print(row)
            need_update = False
            if row["page_name"] in self.special_pagename_1:
                if row["author"] != "":
                    need_update = True
                    row["collaborator"] = " ".join(
                        row["collaborator"].split() + row["author"].split()
                    )
                    row["author"] = ""
                if row["photo"] != "":
                    need_update = True
                    row["collaborator"] = " ".join(
                        row["collaborator"].split() + row["photo"].split()
                    )
                    row["photo"] = ""
            elif row["page_name"] in self.special_pagename_2:
                # print("tth-1")
                authors = []
                collaborators = []
                photos = []
                if row["author"] != "":
                    for name in row["author"].split(" "):
                        reporter_info = self.__get_reporter_info(name)
                        if (
                            reporter_info is None
                            or reporter_info["reporter_category_id"] == 7
                        ):
                            need_update = True
                            collaborators.append(name)
                        else:
                            authors.append(name)
                if row["photo"] != "":
                    # print("rtj-2")
                    for name in row["photo"].split(" "):
                        reporter_info = self.__get_reporter_info(name)
                        # print(reporter_info)
                        if (
                            reporter_info is None
                            or reporter_info["reporter_category_id"] == 7
                        ):
                            need_update = True
                            # print("rth-3")
                            collaborators.append(name)
                        else:
                            photos.append(name)
                row["collaborator"] = " ".join(
                    list(set(row["collaborator"].split() + collaborators))
                ).strip()
                row["author"] = " ".join(list(set(authors))).strip()
                row["photo"] = " ".join(list(set(photos))).strip()
            elif row["is_pic"] == 1 and row["is_xinhua"] == 0:
                # for pn in ["国内", "国际", "全国", "舟山关注", "广告", "金融理财"]:
                for pn in ["国内", "国际", "全国"]:
                    if pn in row["page_name"]:
                        continue
                # 处理图片稿
                collaborators = []
                photos = []
                if row["photo"] != "":
                    phs = row["photo"].split()
                    for p in phs:
                        reporter_info = self.__get_reporter_info(p)
                        if (
                            reporter_info is None
                            or reporter_info["reporter_category_id"] == 7
                        ):
                            need_update = True
                            collaborators.append(p)
                        else:
                            photos.append(p)
                row["collaborator"] = " ".join(
                    list(set(row["collaborator"].split() + collaborators))
                ).strip()
                row["photo"] = " ".join(list(set(photos))).strip()
            if need_update:
                print(row)
                self.cursor.execute(
                    "update digital_paper set author = ?, collaborator = ?, photo = ? where id = ?",
                    (row["author"], row["collaborator"], row["photo"], row["id"]),
                )
        self.conn.commit()


if __name__ == "__main__":
    check = CheckSpecialReporter()
    # for i in range(1, 29):
    #     check.job(["2026", "02", f"{i:02d}"])
    check.job(["2026", "03", "21"])
