import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from query.query_expander import expand_query
from retrieval.retriever import hybrid_search

# سوالاتی که واژه‌شون با عنوان سند فرق داره
CASES = [
    ("RD98XS box contents?", "RD98XS Digital Repeater", "Packing List"),
    ("What is on the front panel of the HR652?", "HR652 Digital Repeater", "Product Layout"),
]

for question, product, target in CASES:
    print("=" * 70)
    print(f"{question}   [target: {target}]")
    print("=" * 70)
    qs = expand_query(question, "en")
    mf = {"product": product}
    any_hit = False
    for i, q in enumerate(qs):
        res = hybrid_search(q, metadata_filter=mf, limit=10, level="child")
        hit = next(((j+1, round(float(p.score),3)) for j,p in enumerate(res)
                    if target.lower() in p.payload.get("section","").lower()), None)
        mark = f"rank {hit[0]}" if hit else "MISS"
        if hit: any_hit = True
        print(f"  {mark:8} | {q}")
    print(f"  → best case: {'RECOVERABLE' if any_hit else 'LOST'}\n")
