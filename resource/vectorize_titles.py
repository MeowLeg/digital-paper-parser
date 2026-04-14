# encoding=utf-8
"""
文章标题向量化工具
- 从 digital_paper 表读取标题
- 使用 scikit-learn 的 TF-IDF 生成向量
- 存储到新表 title_vector
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Optional, Dict
import hashlib


class TitleVectorizer:
    def __init__(self, db_path: str = "../daily.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_table()
        self.vocab: Dict[str, int] = {}
        self._load_or_build_vocab()

    def _init_table(self):
        """创建向量化表（如果不存在）"""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS title_vector (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                digital_paper_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                vector BLOB NOT NULL,
                vector_dim INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(digital_paper_id)
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_vocab (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                idx INTEGER NOT NULL UNIQUE
            )
            """
        )
        self.conn.commit()

    def _tokenize(self, text: str) -> List[str]:
        """简单的中文分词（按字符和常用词分割）"""
        text = re.sub(r"[^\w\u4e00-\u9fff]", " ", text)
        tokens = []
        n = len(text)
        i = 0
        while i < n:
            if text[i] == " ":
                i += 1
                continue
            if i + 1 < n and text[i:i+2] in ["的", "是", "在", "有", "和", "与", "及", "或", "但", "而", "也", "都", "就", "被", "把", "让", "给", "到", "从", "向", "对", "于", "等", "这", "那", "个", "些", "之", "为", "以", "因", "所", "可以", "能够", "已经", "正在", "将要", "不会", "没有", "不是", "就是", "还是", "或者", "并且", "但是", "然而", "因此", "所以", "因为", "由于", "虽然", "尽管", "即使", "就算", "只要", "只有", "除非", "无论", "不管", "凡是", "所有", "全部", "一切", "任何", "每个", "各个", "各种", "各类", "各项", "各种", "各位", "各位", "许多", "很多", "不少", "大量", "许多", "众多", "诸多", "若干", "一些", "一点", "少许", "稍微", "比较", "相当", "非常", "极其", "特别", "尤其", "更加", "越发", "最", "更", "较", "比", "像", "似", "如", "同", "跟", "和", "与", "及", "以及", "暨", "及于", "至于", "关于", "对于", "针对", "按照", "根据", "依据", "凭借", "通过", "经过", "经由", "由于", "因为", "鉴于", "出于", "由于", "多亏", "幸亏", "幸好", "好在", "可惜", "遗憾", "不幸", "幸运", "可喜", "可贺", "可悲", "可叹", "可怜", "可恨", "可恶", "可气", "可笑", "可悲", "可叹", "可怜", "可恨", "可恶", "可气", "可笑", "可喜", "可贺"]:
                tokens.append(text[i:i+2])
                i += 2
            else:
                tokens.append(text[i])
                i += 1
        return tokens

    def _load_or_build_vocab(self):
        """加载或构建词汇表"""
        row = self.cursor.execute("SELECT COUNT(*) as cnt FROM vector_vocab").fetchone()
        if row["cnt"] > 0:
            rows = self.cursor.execute("SELECT word, idx FROM vector_vocab ORDER BY idx").fetchall()
            self.vocab = {r["word"]: r["idx"] for r in rows}
        else:
            self._build_vocab()

    def _build_vocab(self):
        """从所有标题构建词汇表"""
        print("正在构建词汇表...")
        rows = self.cursor.execute("SELECT title FROM digital_paper").fetchall()
        word_count: Dict[str, int] = {}
        
        for row in rows:
            tokens = self._tokenize(row["title"])
            for token in tokens:
                word_count[token] = word_count.get(token, 0) + 1
        
        sorted_words = sorted(word_count.items(), key=lambda x: -x[1])[:10000]
        self.vocab = {word: i for i, (word, _) in enumerate(sorted_words)}
        
        for word, idx in self.vocab.items():
            self.cursor.execute(
                "INSERT INTO vector_vocab (word, idx) VALUES (?, ?)",
                (word, idx)
            )
        self.conn.commit()
        print(f"词汇表构建完成，共 {len(self.vocab)} 个词")

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本向量（基于词汇表的 one-hot + TF 向量）"""
        tokens = self._tokenize(text)
        dim = len(self.vocab)
        vector = [0.0] * dim
        
        token_count: Dict[str, int] = {}
        for token in tokens:
            token_count[token] = token_count.get(token, 0) + 1
        
        max_count = max(token_count.values()) if token_count else 1
        
        for token, count in token_count.items():
            if token in self.vocab:
                idx = self.vocab[token]
                vector[idx] = count / max_count
        
        return vector

    def vectorize_all(self, force: bool = False):
        """向量化所有标题"""
        query = """
            SELECT dp.id, dp.title
            FROM digital_paper dp
        """
        if not force:
            query += """
                LEFT JOIN title_vector tv ON dp.id = tv.digital_paper_id
                WHERE tv.id IS NULL
            """
        query += " ORDER BY dp.id"

        rows = self.cursor.execute(query).fetchall()
        print(f"需要向量化的标题数量: {len(rows)}")

        for i, row in enumerate(rows, 1):
            paper_id = row["id"]
            title = row["title"]
            if i % 100 == 0:
                print(f"[{i}/{len(rows)}] 处理: {paper_id} - {title[:30]}...")

            vector = self.get_embedding(title)
            if vector:
                vector_blob = json.dumps(vector).encode("utf-8")
                
                self.cursor.execute(
                    """
                    INSERT OR REPLACE INTO title_vector 
                    (digital_paper_id, title, vector, vector_dim, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (paper_id, title, vector_blob, len(vector)),
                )
                if i % 100 == 0:
                    self.conn.commit()
        
        self.conn.commit()
        print(f"向量化完成，共处理 {len(rows)} 条")

    def get_vector(self, paper_id: int) -> Optional[List[float]]:
        """获取指定文章的向量"""
        row = self.cursor.execute(
            "SELECT vector FROM title_vector WHERE digital_paper_id = ?",
            (paper_id,),
        ).fetchone()
        if row:
            return json.loads(row["vector"])
        return None

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


if __name__ == "__main__":
    db_path = Path(__file__).resolve().parent.parent / "daily.db"
    vectorizer = TitleVectorizer(str(db_path))
    
    try:
        vectorizer.vectorize_all(force=False)
    finally:
        vectorizer.close()
