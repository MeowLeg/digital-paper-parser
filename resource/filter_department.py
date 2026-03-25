# encoding=utf-8
import sqlite3


DEPARTMENT_SITE_MAP = {
    "时政要闻部": 3,
    "民生专题部": 4,
    "经济专题部": 5,
    "采访部": 8,
    "报媒事业部": 9,
    "混合部门": 6,
    "地方事业部": 10,
    # "通讯员": 7,
    "其他": 1,
}


class FilterDepartment:
    def __init__(self, db_path: str = "../daily.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def __get_site_id(self, usernames: [str]) -> int | None:
        # print(usernames)
        ret = []
        for username in usernames:
            rows = self.cursor.execute(
                "select department from reporter where name = ?", (username,)
            ).fetchall()
            if rows is None or len(rows) == 0:
                ret.append(None)
            else:
                ret.append(rows[0]["department"])
        # print(ret)
        unique_ret = list(set(ret))
        # print(unique_ret)
        if len(unique_ret) == 1:
            if unique_ret[0] in DEPARTMENT_SITE_MAP:
                return DEPARTMENT_SITE_MAP[unique_ret[0]]
        else:
            num = 0
            site_id = None
            for item in unique_ret:
                if item in DEPARTMENT_SITE_MAP:
                    num += 1
                    site_id = DEPARTMENT_SITE_MAP[item]
            if num == 1:
                return site_id
            elif num > 1:
                return DEPARTMENT_SITE_MAP["混合部门"]
        return DEPARTMENT_SITE_MAP["其他"]

    def job(self, date_str: str):
        for r in self.cursor.execute(
            "select id, title, author, photo from digital_paper where date = ?",
            (date_str,),
        ).fetchall():
            site_id = self.__get_site_id(r["author"].split(" ") + r["photo"].split(" "))
            # print(r["title"], site_id)
            self.cursor.execute(
                "update digital_paper set site_id = ? where id = ?", (site_id, r["id"])
            )
        self.conn.commit()


if __name__ == "__main__":
    filter_department = FilterDepartment()
    for i in range(1, 9):
        filter_department.job(f"2026-03-{i:02d}")
