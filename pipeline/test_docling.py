"""
test_docling.py
─────────────────────────────────────────────────────────
تست می‌کنیم Docling چطور ساختار سند رو نسبت به pypdf
حفظ می‌کنه — مخصوصاً heading ها و section ها.
─────────────────────────────────────────────────────────
"""

from pathlib import Path
from docling.document_converter import DocumentConverter

PDF_PATH = Path(__file__).parent.parent / "data" / "documents" / \
           "Hytera_RD982S_Digital_Repeater_User_Manual_R8.5_eng.pdf"

print("Converting PDF with Docling (this may take a minute on first run)...")

converter = DocumentConverter()
result = converter.convert(str(PDF_PATH))

# خروجی Markdown — heading ها باید با # مشخص شده باشن
markdown_output = result.document.export_to_markdown()

# فقط ۳۰۰۰ کاراکتر اول رو چاپ می‌کنیم تا ببینیم ساختار چطوره
print("=" * 60)
print("First 3000 characters of Markdown output:")
print("=" * 60)
print(markdown_output[:3000])

# ذخیره کامل برای بررسی بیشتر
output_path = Path(__file__).parent / "docling_output.md"
output_path.write_text(markdown_output)
print(f"\n\nFull output saved to: {output_path}")