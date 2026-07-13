import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_postgres
from main import process_query
from query.query_expander import expand_query
from retrieval.retriever import hybrid_search

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

q = "RD98XS box contents?"

# 1. ببین expanded (rewritten) چیست — همان که به heading arm می‌رود
clear()
r = process_query(q)
print(f"expanded (rewritten): {r.get('expanded_question')!r}")
print(f"detected product:     {r.get('detected_product')!r}")
print(f"final sections:       {[c.payload.get('section','?')[:24] for c in r['chunks']]}")

# 2. heading arm را دستی با همان expanded اجرا کن
expanded = r.get("expanded_question", q)
mf = {"product": "RD98XS Digital Repeater"}
print(f"\n--- heading search with expanded query, level=parent ---")
hits = hybrid_search(expanded, metadata_filter=mf, limit=5, level="parent")
for h in hits:
    sec = h.payload.get("section","?")[:30]
    mark = " <<< PACKING" if "packing" in sec.lower() else ""
    print(f"  [{float(h.score):.3f}] {sec}{mark}")
