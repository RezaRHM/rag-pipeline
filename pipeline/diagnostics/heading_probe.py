"""Before building a heading arm: does dense similarity map colloquial queries
to formal headings? If 'box contents' doesn't reach 'Packing List', a bare
heading index won't fix T2 and we need heading aliases."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieval.embedder import embed_dense
import numpy as np

def cos(a, b):
    a, b = np.array(a), np.array(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

# عنوان‌های واقعی سند
headings = [
    "RD98XS Digital Repeater — 1. Packing List",
    "RD98XS Digital Repeater — 2.2 Rear Panel",
    "RD98XS Digital Repeater — 8. Optional Accessories",
    "HR652 Digital Repeater — 2. Product Layout",
    "HR652 Digital Repeater — Specifications",
]
heading_vecs = {h: embed_dense(h) for h in headings}

# query های کاربر (عامیانه) و اینکه به کدوم عنوان باید برسن
probes = [
    ("RD98XS box contents?",              "Packing List"),
    ("what's in the RD98XS box",          "Packing List"),
    ("front panel of the HR652",          "Product Layout"),
    ("RD98XS rear connectors",            "Rear Panel"),
]

for q, want in probes:
    qv = embed_dense(q)
    ranked = sorted(headings, key=lambda h: -cos(qv, heading_vecs[h]))
    top = ranked[0]
    hit = want.lower() in top.lower()
    rank = next((i+1 for i,h in enumerate(ranked) if want.lower() in h.lower()), None)
    print(f"{'OK ' if hit else 'MISS':5} rank {rank} | {q}")
    print(f"      best: {top}  (cos {cos(qv, heading_vecs[top]):.3f})")
    want_h = next(h for h in headings if want.lower() in h.lower())
    print(f"      want: {want_h}  (cos {cos(qv, heading_vecs[want_h]):.3f})")
    print()
