"""Check that answerable questions actually retrieve their evidence.

A question whose ground-truth chunk never reaches the model tests retrieval,
not the model. Verify before freezing the set, not after grading it.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import process_query

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

# (question, expected section substring)
CASES = [
    ("F1", "What is the output power of the HR652 in high, middle, and low settings?", "Specifications"),
    ("F2", "What items are included in the RD98XS packing list?", "Packing List"),
    ("F3", "Which connectors are on the rear panel of the RD98XS?", "2.2 Rear Panel"),
    ("F4", "Can alcohol be used to clean the HR652?", "Product Cleaning"),
    ("F5", "What is on the front panel of the HR652?", "Product Layout"),
    ("T1", "HR652 output power?", "Specifications"),
    ("T2", "RD98XS box contents?", "Packing List"),
    ("T3", "RD98XS rear connectors?", "2.2 Rear Panel"),
    ("T4", "HR652 cleaning alcohol?", "Product Cleaning"),
]

for qid, q, expect in CASES:
    clear()
    r = process_query(q)
    secs = [c.payload.get("section", "?") for c in r["chunks"]]
    found = any(expect.lower() in s.lower() for s in secs)
    rank = next((i+1 for i, s in enumerate(secs) if expect.lower() in s.lower()), None)
    status = f"rank {rank}" if found else "NOT RETRIEVED"
    print(f"{qid:3} [{status:14}] {q[:52]}")
    print(f"     type={r['query_type']:20} product={r['detected_product']}")
    print(f"     {[s[:26] for s in secs]}")
    print()
