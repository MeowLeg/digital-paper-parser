# encoding=utf-8
"""
标题相似度搜索工具
- 接受输入标题
- 计算与数据库中所有标题的余弦相似度
- 返回超过阈值的结果
"""

import sqlite3
import json
import math
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from vectorize_titles import TitleVectorizer


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


class SimilarTitleSearcher:
    def __init__(self, db_path: str = "../daily.db"):
        self.db_path = db_path
        self.vectorizer = TitleVectorizer(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def search(self, query_title: str, threshold: float = 0.5, top_k: int = 10) -> List[Tuple]:
        """搜索相似标题"""
        query_vector = self.vectorizer.get_embedding(query_title)
        if not query_vector:
            return []
        
        cursor = self.conn.cursor()
        rows = cursor.execute(
            """
            SELECT tv.digital_paper_id, tv.title, tv.vector, dp.date, dp.page_name
            FROM title_vector tv
            JOIN digital_paper dp ON tv.digital_paper_id = dp.id
            """
        ).fetchall()
        
        results = []
        for row in rows:
            vector = json.loads(row["vector"])
            sim = cosine_similarity(query_vector, vector)
            if sim >= threshold:
                results.append((
                    sim,
                    row["digital_paper_id"],
                    row["title"],
                    row["date"],
                    row["page_name"]
                ))
        
        results.sort(key=lambda x: -x[0])
        return results[:top_k]

    def close(self):
        """关闭连接"""
        self.vectorizer.close()
        self.conn.close()


def main():
    if len(sys.argv) < 2:
        print("用法: python search_similar_titles.py <标题> [阈值] [top_k]")
        print("示例: python search_similar_titles.py '海岛发展' 0.6 5")
        return
    
    query_title = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    db_path = Path(__file__).resolve().parent.parent / "daily.db"
    searcher = SimilarTitleSearcher(str(db_path))
    
    try:
        print(f"搜索标题: {query_title}")
        print(f"相似度阈值: {threshold}")
        print(f"返回结果数: {top_k}")
        print("-" * 80)
        
        results = searcher.search(query_title, threshold, top_k)
        
        if not results:
            print("未找到相似标题")
        else:
            print(f"找到 {len(results)} 条相似标题:")
            print()
            for i, (sim, paper_id, title, date, page_name) in enumerate(results, 1):
                print(f"{i}. [相似度: {sim:.4f}]")
                print(f"   ID: {paper_id}")
                print(f"   标题: {title}")
                print(f"   日期: {date}  版面: {page_name}")
                print()
    finally:
        searcher.close()


if __name__ == "__main__":
    main()
