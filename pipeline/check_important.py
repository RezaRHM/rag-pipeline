from workflows.ingest import parse_pdf, split_by_headings, convert_tables_to_text
import config

pdf = sorted(config.DOCUMENTS_DIR.glob("*HR652*"))[0]
md = parse_pdf(pdf)
sections = split_by_headings(md)

# جدول error code / alarm code رو پیدا کن
for sec in sections:
    if 'alarm code' in sec['heading'].lower() or 'seven' in sec['heading'].lower():
        print("=== IMPORTANT TABLE:", sec['heading'], "===")
        print("\n--- RAW ---")
        print(sec['text'][:500])
        print("\n--- CONVERTED ---")
        print(convert_tables_to_text(sec['text'])[:500])
        print()
