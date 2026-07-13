import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.query_expander import expand_query
from retrieval.retriever import hybrid_search, multi_query_search
from retrieval.context_expander import expand_context

question = "What is on the front panel of the HR652?"
qs = expand_query(question, "en")
mf = {"product": "HR652 Digital Repeater"}

cands = multi_query_search(qs, metadata_filter=mf, limit_per_query=10,
                           final_limit=30, level="child")
exp = expand_context(cands, confidence_threshold=0.70)

# پیدا کردن chunk هدف و دیدن اینکه reranker چه متنی ازش می‌سازه
for c in exp:
    if "product layout" in c.payload.get("section", "").lower():
        print("=" * 66)
        print("TARGET chunk that rerank must score against 'front panel':")
        print("=" * 66)
        print(f"section:  {c.payload.get('section')}")
        print(f"product:  {c.payload.get('product')}")
        print(f"payload keys: {list(c.payload.keys())}")
        print(f"\n--- text field (what may be embedded/reranked):")
        print(repr(c.payload.get("text", "")[:300]))
        for k in ("retrieval_text", "rerank_text", "contextual_text", "enriched_text"):
            if k in c.payload:
                print(f"\n--- {k}:")
                print(repr(c.payload[k][:300]))
        break
