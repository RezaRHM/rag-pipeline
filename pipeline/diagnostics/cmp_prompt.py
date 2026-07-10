import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import process_query
from prompts.prompts import build_generation_prompt, BASE_SYSTEM_PROMPT

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

q = ("Which alarm conditions can be triggered by abnormal voltage, "
     "overheating, or fan failure on the RD98XS?")
clear()
r = process_query(q)

prod = build_generation_prompt(q, r["chunks"], "en")

manual_ctx = "\n\n".join(f"[{c.payload['product']} — {c.payload['section']}]\n{c.payload['text']}"
                         for c in r["chunks"])
manual = f"{BASE_SYSTEM_PROMPT}\n\nContext:\n{manual_ctx}\n\nQuestion: {q}\n\nAnswer:"

print(f"production: {len(prod)} chars")
print(f"manual:     {len(manual)} chars")
print(f"identical:  {prod == manual}\n")
print("=" * 70)
print("PRODUCTION, from 'Context:' onward (1000 chars):")
print("=" * 70)
i = prod.find("Context:")
print(prod[i:i+1000] if i >= 0 else prod[-1000:])
