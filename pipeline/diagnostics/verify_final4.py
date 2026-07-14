import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_qdrant, get_postgres
from main import process_query
import config

q = get_qdrant()
PTS, _ = q.scroll(collection_name=config.QDRANT_COLLECTION, limit=2000, with_payload=True)

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

def show_section(pkey, sub):
    for p in PTS:
        if p.payload.get("chunk_level") != "parent":
            continue
        if pkey.lower() in p.payload.get("product","").lower() and sub.lower() in p.payload.get("section","").lower():
            return p.payload.get("section",""), " ".join(p.payload.get("text","").split())[:300]
    return None, None

# --- بخش ۱: محتوای بخش‌های مرتبط را نشان بده (برای تأیید ادعا) ---
print("=" * 72); print("GROUND TRUTH — section contents"); print("=" * 72)
checks = [
    ("HR652 tools", "HR652", "4.1 Tools"),
    ("RD98XS tools", "RD98XS", "3.1 Installation Requirements"),
    ("HR652 alarm codes", "HR652", "6.2 Seven-Segment"),
    ("RD98XS post-install", "RD98XS", "3.3 Post-installation"),
    ("RD98XS duplexer", "RD98XS", "3.2.1"),
]
for label, pk, sub in checks:
    sec, txt = show_section(pk, sub)
    print(f"\n[{label}] {sec}")
    print(f"   {txt}")

# --- بخش ۲: هر سوال را retrieve کن و ببین بخش‌های لازم می‌آیند ---
print("\n" + "=" * 72); print("RETRIEVAL CHECK — do the needed sections arrive?"); print("=" * 72)
QS = [
    ("M3", "How do I install the RD98XS duplexer, and where do I connect the antenna afterward?",
     ["3.2.1", "Rear Panel"]),
    ("M4", "Before powering on the RD98XS, what should I connect and how do I check it started correctly?",
     ["3.2.2", "Post-installation"]),
    ("C3", "Which repeater needs a Phillips screwdriver for installation, RD98XS or HR652?",
     ["Tools", "Installation Requirements"]),
    ("C4", "Do both repeaters use the same alarm codes, or do they differ?",
     ["Alarm", "Seven-Segment", "6."]),
]
for qid, question, expect in QS:
    clear()
    r = process_query(question)
    secs = [c.payload.get("section","?") for c in r["chunks"]]
    found = {e: any(e.lower() in s.lower() for s in secs) for e in expect}
    print(f"\n{qid} [{r['query_type']}] product={r.get('detected_product')}")
    print(f"   sections: {[s[:24] for s in secs]}")
    print(f"   needed: {found}")
