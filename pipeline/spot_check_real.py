from workflows.ingest import (
    parse_pdf, split_by_headings, convert_tables_to_text,
    split_into_propositions
)
import config

# یکی از PDF ها رو parse کن (RD982S — کوچیک‌تره)
pdf = sorted(config.DOCUMENTS_DIR.glob("*RD982S*"))[0]
print(f"Parsing {pdf.name}...")
md = parse_pdf(pdf)
sections = split_by_headings(md)

# فقط section هایی که جدول دارن (شامل | هستن)
table_sections = [s for s in sections if s['text'].count('|') > 4]
print(f"Found {len(table_sections)} sections with tables\n")

# ۴ تا جدول اول رو کامل نشون بده — هر ۴ لایه
for i, sec in enumerate(table_sections[:4]):
    print("=" * 70)
    print(f"SECTION: {sec['heading']}")
    print("=" * 70)

    print("\n--- LAYER 1: RAW MARKDOWN (Docling) ---")
    print(sec['text'][:400])

    print("\n--- LAYER 2: AFTER convert_tables_to_text ---")
    converted = convert_tables_to_text(sec['text'])
    print(converted[:400])

    print("\n--- LAYER 3: CHILD PROPOSITIONS ---")
    full = f"## {sec['heading']}\n{sec['text']}"
    props = split_into_propositions(full)
    for p in props[:6]:
        print(f"  • {p[:80]}")

    print("\n\n")
