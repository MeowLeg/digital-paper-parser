# encoding=utf-8
import sys
sys.path.insert(0, r'D:\github\digital-paper-parser\resource')

from kimi_cloud import PdfParser
from write_db import WriteDb
import sqlite3

# 初始化解析器
api_key = "sk-BSvteGexprXexqyk6O5RBSPJtcmBNzoZwHVnVAAmJTUPIZTE"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-k2.5"

parser = PdfParser(api_key, base_url, model)

# 解析第01版
pdf_path = r'D:\github\digital-paper-parser\resource\舟山日报\Z20260326PDF\B2026-03-26一版01.pdf'
print(f'解析: {pdf_path}')

ret = parser.parse(pdf_path)
if ret and ret.get('success'):
    print(f'解析成功，文章数: {len(ret.get("data", []))}')
    
    # 写入数据库
    db = WriteDb(r'D:\github\digital-paper-parser\daily.db')
    for article in ret['data']:
        article['date'] = '2026-03-26'
        article['pdf'] = pdf_path
        db.write(article)
    print(f'写入数据库成功: {len(ret["data"])} 篇文章')
else:
    print(f'解析失败: {ret}')
