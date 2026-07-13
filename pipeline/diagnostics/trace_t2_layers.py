import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from retrieval.retriever import hybrid_search

# query هایی که باید Packing List رو پیدا کنن
queries = [
    "RD98XS packing list",           # دقیقاً عنوان بخش
    "RD98XS product packaging list", # expander version
    "What is included with the RD98XS",
    "packing list",                  # بدون محصول
]
target = "Packing List"
mf = {"product": "RD98XS Digital Repeater"}

for q in queries:
    res = hybrid_search(q, metadata_filter=mf, limit=15, level="child")
    hit = next(((i+1, round(float(p.score),3)) for i,p in enumerate(res)
                if target.lower() in p.payload.get("section","").lower()), None)
    print(f"{'FOUND '+str(hit) if hit else 'MISS':22} | {q}")
    if not hit:
        # چی به‌جاش اومد؟
        top3 = [p.payload.get("section","?")[:24] for p in res[:3]]
        print(f"{'':22} | top3: {top3}")
