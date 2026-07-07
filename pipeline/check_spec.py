from workflows.ingest import parse_pdf, split_by_headings, convert_tables_to_text
import config

# هر سه PDF رو بگرد دنبال spec/status/parameter table
for pdf in sorted(config.DOCUMENTS_DIR.glob("*.pdf")):
    md = parse_pdf(pdf)
    sections = split_by_headings(md)
    for sec in sections:
        h = sec['heading'].lower()
        t = sec['text'].lower()
        # spec / specification / parameter / status / indicator tables
        is_spec = (('spec' in h or 'parameter' in h or 'status' in h
                    or 'indicat' in h or 'output power' in t or 'frequency' in t)
                   and sec['text'].count('|') > 4)
        if is_spec:
            print("=" * 60)
            print(f"[{pdf.name[:20]}] {sec['heading']}")
            print("--- RAW (first 300) ---")
            print(sec['text'][:300])
            print("--- CONVERTED (first 300) ---")
            print(convert_tables_to_text(sec['text'])[:300])
            print()
