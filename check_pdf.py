import pdfplumber

pdf_path = r'D:\Github\digital-paper-parser\resource\舟山日报\Z20260316PDF\B2026-03-16一版01.pdf'
pdf = pdfplumber.open(pdf_path)
page = pdf.pages[0]
print(f'PDF page size: {page.width} x {page.height}')
pdf.close()
