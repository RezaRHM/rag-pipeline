import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.query_expander import expand_query
from retrieval.retriever import multi_query_search, hybrid_search

q = "What is on the front panel of the HR652?"
qs = expand_query(q, "en")
mf = {"product": "HR652 Digital Repeater"}

print("=== per-query hybrid_search, level=child, limit=10 ===")
for i, query in enumerate(qs):
    res = hybrid_search(query, metadata_filter=mf, limit=10, level="child")
    pl_rank = next((j+1 for j,p in enumerate(res)
                    if "product layout" in p.payload.get("section","").lower()), None)
    print(f"  q{i} PL_rank={pl_rank}  | {query[:50]}")

print("\n=== multi_query_search (exactly as main.py calls it) ===")
cands = multi_query_search(qs, metadata_filter=mf,
                           limit_per_query=10, final_limit=30, level="child")
pl = [(i, c.payload.get("_guaranteed_top1", False))
      for i,c in enumerate(cands)
      if "product layout" in c.payload.get("section","").lower()]
print(f"  candidates: {len(cands)}")
print(f"  Product Layout positions & flags: {pl}")
flagged = [c.payload.get("section","?")[:30] for c in cands if c.payload.get("_guaranteed_top1")]
print(f"  all flagged sections: {flagged}")
