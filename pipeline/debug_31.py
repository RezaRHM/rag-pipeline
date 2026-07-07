from workflows.ingest import parse_pdf, split_by_headings, _is_low_value_section
import config

pdf = sorted(config.DOCUMENTS_DIR.glob("*RD982S*"))[0]
md = parse_pdf(pdf)

# split_by_headings رو دستی اجرا کن ولی قبل از فیلتر
import re
lines = md.split("\n")
sections = []
current_text = []
current_heading = "Introduction"
last_numbered = ""

def is_num(t):
    return bool(re.match(r"^\d+[\.\d]*\s+\w", t.strip()))

for line in lines:
    is_h = re.match(r"^#{1,3}\s+", line) and "...." not in line
    if is_h:
        if current_text:
            sections.append({"heading": current_heading, "text": "\n".join(current_text).strip()})
        ht = re.sub(r"^#{1,3}\s+", "", line).strip()
        if is_num(ht):
            last_numbered = ht
            current_heading = ht
        else:
            current_heading = f"{last_numbered} → {ht}" if last_numbered else ht
        current_text = []
    else:
        current_text.append(line)
if current_text:
    sections.append({"heading": current_heading, "text": "\n".join(current_text).strip()})

# پیدا کن 3.1 و چک کن چرا فیلتر شد
for s in sections:
    if '3.1 Installation' in s['heading']:
        print(f"HEADING: {s['heading']}")
        print(f"TEXT:\n{s['text'][:400]}")
        print(f"\nword count: {len(s['text'].split())}")
        print(f"dotted count: {s['text'].count('....')}")
        import re as r2
        stripped = r2.sub(r'<!--.*?-->', '', s['text']).strip()
        stripped = r2.sub(r'\s+', ' ', stripped)
        print(f"stripped word count: {len(stripped.split())}")
        print(f"IS LOW VALUE? {_is_low_value_section(s['heading'], s['text'])}")
