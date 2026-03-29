import sqlite3
conn = sqlite3.connect(r'D:\github\digital-paper-parser\daily.db')
cursor = conn.cursor()
cursor.execute("SELECT page_no, page_name, title, is_xinhua FROM digital_paper WHERE date = '2026-03-26' ORDER BY page_no")
rows = cursor.fetchall()
print(f'今日文章数: {len(rows)}')
for row in rows:
    print(f'[{row[0]}版] {row[1]} - {row[2][:30]}... {"[新华社]" if row[3] == 1 else ""}')
conn.close()
