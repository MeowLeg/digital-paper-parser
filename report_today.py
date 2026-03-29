import sqlite3
import sys

conn = sqlite3.connect(r'D:\github\digital-paper-parser\daily.db')
cursor = conn.cursor()
cursor.execute("SELECT page_no, page_name, title, author, is_xinhua FROM digital_paper WHERE date = '2026-03-26' ORDER BY page_no")
rows = cursor.fetchall()

# 写入文件
with open(r'D:\github\digital-paper-parser\report_2026-03-26.txt', 'w', encoding='utf-8') as f:
    f.write('=== 舟山日报 2026-03-26 解析简报 ===\n')
    f.write(f'总文章数: {len(rows)} 篇\n\n')
    
    current_page = None
    page_count = {}
    
    for row in rows:
        page_no, page_name, title, author, is_xinhua = row
        if page_no not in page_count:
            page_count[page_no] = 0
        page_count[page_no] += 1
    
    for page_no in sorted(page_count.keys()):
        f.write(f'\n【第 {page_no} 版】共 {page_count[page_no]} 篇文章\n')
        for row in rows:
            p_no, p_name, title, author, is_xinhua = row
            if p_no == page_no:
                xinhua_mark = '[新华社] ' if is_xinhua == 1 else ''
                f.write(f'  - {xinhua_mark}{title}\n')

conn.close()
print('简报已保存到 report_2026-03-26.txt')
