# encoding=utf-8

import sqlite3

# from openai import OpenAI
import json
import requests


class FindDeplicate:
    # def __init__(self, db_path: str = "../daily.db", threshold: float = 0.5, model: str = "qwen3:0.6b", api_key: str = "ollama-local", base_url: str = "http://localhost:11434/v1"):
    def __init__(
        self,
        db_path: str = "../daily.db",
        threshold: float = 0.5,
        model: str = "qwen3:0.6b",
        api_key: str = "ollama-local",
        base_url: str = "http://localhost:11434",
    ):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.base_url = base_url
        # self.client = OpenAI(
        #     api_key=api_key,
        #     base_url=base_url,
        # )
        self.model = model
        self.threshold = threshold

    def job(self, date: str):
        rows_before = [
            dict(r)
            for r in self.cursor.execute(
                "select id, title from digital_paper where date < ? and ((author is not null and author != '') or (collaborator is not null and collaborator != '') or (photo is not null and photo != ''))",
                (date,),
            ).fetchall()
        ]
        rows = self.cursor.execute(
            "select id, title from digital_paper where date = ?", (date,)
        ).fetchall()
        sim_rows = []
        for row in rows[1:]:
            for i, r in enumerate(rows_before):
                print(i, r)
                similarity = compare_title(
                    self.base_url, self.model, [r["title"], row["title"]]
                )
                if similarity is not None and similarity > self.threshold:
                    sim_rows.append(
                        {
                            "digital_paper_id": row["id"],
                            "similary_id": r["id"],
                            "similarity": ret_json["similarity"],
                        }
                    )
        for r in sim_rows:
            self.cursor.execute(
                "insert into duplicate (digital_paper_id, similary_id, similarity) values (?, ?, ?)",
                (r["digital_paper_id"], r["similary_id"], r["similarity"]),
            )
        self.conn.commit()


def compare_title(base_url: str, model: str, titles: [str]) -> float | None:
    try:
        response = requests.post(
            base_url + "/api/generate",
            json={
                "model": model,
                "prompt": f"""
                        你是一个专业的标题比较器，能够判断两个标题的相似性。
                        严格返回json格式为： {{
                            "success": true,
                            "errMsg": "比较完成",
                            "similarity": 0.8,
                        }},
                        比较以下两个标题的相似性，"{titles[0]}", "{titles[1]}"
                """,
                "format": "json",
                "stream": False,
                "think": False,
            },
            timeout=10,
        )
    except Exception as e:
        print(e)
        return
        # print(response.status_code)
    if response is not None and response.status_code == 200:
        resp = response.json()
        ret_str = resp["response"]
        if ret_str.startswith("```json"):
            ret_str = ret_str[7:]
        ret_str = ret_str.split("```")[0]
        ret_str = ret_str.strip()
        ret_json = None
        try:
            ret_json = json.loads(ret_str)
        except Exception as e:
            print("error: -------------------------")
            print("titles compare:", titles[0], titles[1])
            print(resp)
            print(e)
            return
        print(f"《{titles[0]}》 similarity: ", ret_json["similarity"])
        return float(ret_json["similarity"])


if __name__ == "__main__":
    # model = "qwen3.5:4b" # kimi-k2.5:cloud # maternion/fara:7b qwen3:4b
    # model = "maternion/fara:7b" # kimi-k2.5:cloud # maternion/fara:7b qwen3:4b
    # find_deplicate = FindDeplicate(model=model)
    # find_deplicate.job("2026-03-04")

    compare_title(
        "http://localhost:11434",
        "qwen3.5:4b",
        [
            "“国家一切权力属于人民”——习近平总书记全过程人民民主重大理念的生动实践",
            "国家一切权力属于人民——习近平总书记全过程人民民主重大理念的生动实践",
        ],
    )
