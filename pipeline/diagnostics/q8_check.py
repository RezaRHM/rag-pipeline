import sys, os, hashlib, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import process_query

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

q = "What are the exact steps to install the RD98XS repeater in a rack or cabinet?"
print("Q8 context across 3 runs:\n")
for i in range(3):
    clear()
    r = process_query(q)
    ctx = "\n\n".join(f"[{c.payload['product']} — {c.payload['section']}]\n{c.payload['text']}"
                      for c in r["chunks"])
    h = hashlib.sha256(ctx.encode()).hexdigest()[:8]
    secs = [c.payload['section'][:30] for c in r["chunks"]]
    has_322 = any("3.2.2" in s for s in secs)
    print(f"  {i+1}. hash={h} | 3.2.2 present: {has_322}")
    print(f"     {secs}")
