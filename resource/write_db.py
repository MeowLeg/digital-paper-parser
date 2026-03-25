# encoding=utf-8

import sqlite3


class WriteDb:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def write(self, data):
        if data["hot_zone"] is None or len(data["hot_zone"]) != 4:
            x1 = 0
            y1 = 0
            x2 = 0
            y2 = 0
            x3 = 0
            y3 = 0
            x4 = 0
            y4 = 0
        else:
            x1 = data["hot_zone"][0][0]
            y1 = data["hot_zone"][0][1]
            x2 = data["hot_zone"][1][0]
            y2 = data["hot_zone"][1][1]
            x3 = data["hot_zone"][2][0]
            y3 = data["hot_zone"][2][1]
            x4 = data["hot_zone"][3][0]
            y4 = data["hot_zone"][3][1]
        self.cursor.execute(
            """
            insert into digital_paper (date, title, author, collaborator, photo, content, page_no, left_top_x, left_top_y, left_bottom_x, left_bottom_y, right_bottom_x, right_bottom_y, right_top_x, right_top_y, pdf, page_name, is_xinhua, is_pic, next_page, has_previous)
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["date"],
                data["title"],
                data["author"],
                data["collaborator"],
                data["photo"],
                data["content"],
                data["page_no"],
                x1,
                y1,
                x2,
                y2,
                x3,
                y3,
                x4,
                y4,
                data["pdf"],
                data["page_name"],
                data.get("is_xinhua", 0),
                data.get("is_pic", 0),
                data.get("next_page", ""),
                data.get("has_previous", 0),
            ),
        )
        self.conn.commit()

    def get_articles_by_date(self, date):
        """获取指定日期的所有文章"""
        self.cursor.execute(
            """
            SELECT id, date, title, author, collaborator, photo, content, page_no, page_name, is_xinhua, next_page, has_previous, left_top_x, left_top_y, left_bottom_x, left_bottom_y, right_bottom_x, right_bottom_y, right_top_x, right_top_y, pdf
            FROM digital_paper 
            WHERE date = ?
            ORDER BY id ASC
            """,
            (date,),
        )
        rows = self.cursor.fetchall()
        result = []
        for row in rows:
            article = dict(row)
            # article["dump"] = True  # 默认都需要写入
            result.append(article)
        return result

    def update_article_content(self, article_id, content, has_previous=None):
        """更新文章内容"""
        if has_previous is not None:
            self.cursor.execute(
                """
                UPDATE digital_paper SET content = ?, has_previous = ? WHERE id = ?
                """,
                (content, has_previous, article_id),
            )
        else:
            self.cursor.execute(
                """
                UPDATE digital_paper SET content = ? WHERE id = ?
                """,
                (content, article_id),
            )
        self.conn.commit()

    def delete_article(self, article_id):
        """删除已经被合并的文章"""
        self.cursor.execute(
            """
            DELETE FROM digital_paper WHERE id = ?
            """,
            (article_id,),
        )
        self.conn.commit()
