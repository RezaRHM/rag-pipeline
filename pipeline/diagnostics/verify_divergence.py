"""Does the answer materially differ by product? That, not the absence of a
product name, is what should decide clarification vs answer-both."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_qdrant
import config

q = get_qdrant()
PTS, _ = q.scroll(collection_name=config.QDRANT_COLLECTION, limit=2000, with_payload=True)

def parent_text(pkey, section_substrings):
    for p in PTS:
        if p.payload.get("chunk_level") != "parent":
            continue
        if pkey.lower() not in p.payload.get("product", "").lower():
            continue
        sec = p.payload.get("section", "")
        if any(s.lower() in sec.lower() for s in section_substrings):
            return sec, p.payload.get("text", "")
    return None, None

CASES = [
    ("V9  Cleaning instructions?",  ["Product Cleaning"]),
    ("V10 What's in the box?",      ["Packing List"]),
    ("V11 Antenna connector type?", ["Rear Panel", "Product Layout"]),
    ("V12 Ground screw location?",  ["Rear Panel", "Product Layout", "Installing the Repeater"]),
]

for label, secs in CASES:
    print("=" * 72)
    print(label)
    print("=" * 72)
    for pkey in ["RD98XS", "HR652"]:
        sec, txt = parent_text(pkey, secs)
        if txt:
            clean = " ".join(txt.split())[:260]
            print(f"  [{pkey}] {sec}")
            print(f"     {clean}")
        else:
            print(f"  [{pkey}] — no matching section")
    print()
