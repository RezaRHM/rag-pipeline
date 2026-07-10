import sys, os, hashlib, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import process_query

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

q = ("Which alarm conditions can be triggered by abnormal voltage, "
     "overheating, or fan failure on the RD98XS?")
clear()
r = process_query(q)
live = "\n\n".join(f"[{c.payload['product']} — {c.payload['section']}]\n{c.payload['text']}"
                   for c in r["chunks"])

froz = json.load(open('diagnostics/frozen_v2.json'))["Q9"]["context"]

def h(s): return hashlib.sha256(s.encode()).hexdigest()[:8]

print(f"live   hash={h(live)}  {len(live)} chars, {len(r['chunks'])} chunks")
print(f"frozen hash={h(froz)}  {len(froz)} chars")
print(f"identical: {live == froz}\n")

print("live sections:")
for m in re.findall(r'\[([^\]]+)\]', live):
    print(f"  {m}")
print("\nfrozen sections:")
for m in re.findall(r'\[([^\]]+)\]', froz):
    print(f"  {m}")
