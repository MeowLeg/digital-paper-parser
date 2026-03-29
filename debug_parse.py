# encoding=utf-8
import sys
sys.path.insert(0, r'D:\github\digital-paper-parser\resource')

from kimi_cloud import PdfParser

# 初始化解析器
api_key = "sk-BSvteGexprXexqyk6O5RBSPJtcmBNzoZwHVnVAAmJTUPIZTE"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-k2.5"

parser = PdfParser(api_key, base_url, model)

# 解析第01版
pdf_path = r'D:\github\digital-paper-parser\resource\舟山日报\Z20260326PDF\B2026-03-26一版01.pdf'
print(f'开始解析: {pdf_path}', flush=True)

ret = parser.parse(pdf_path)
print(f'返回结果: {ret}', flush=True)
