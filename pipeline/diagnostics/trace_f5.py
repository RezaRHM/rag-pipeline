import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query.query_expander import expand_query
from retrieval.retriever import hybrid_search, multi_query_search, fetch_parents
from retrieval.context_expander import expand_context
from retrieval.reranker import rerank

CASES = [
    ("F5", "What is on the front panel of the HR652?",
     "HR652 Digital Repeater", "Product Layout"),
    ("T2", "RD98XS box contents?",
     "RD98XS Digital Repeater", "Packing List"),
]

for qid, question, product, target in CASES:
    print("=" * 74)
    print(f"{qid}: {question}   [target: {target}]")
    print("=" * 74)

    qs = expand_query(question, "en")
    mf = {"product": product}

    print("\n[L2] per-query hybrid_search — does any query find the target?")
    for i, q in enumerate(qs):
        res = hybrid_search(q, metadata_filter=mf, limit=10, level="child")
        hit = next(((j+1, round(float(p.score), 3))
                    for j, p in enumerate(res)
                    if target.lower() in p.payload.get("section", "").lower()), None)
        mark = f"rank {hit[0]} score {hit[1]}" if hit else "—"
        print(f"   q{i}: {mark:22} {q[:48]}")

    print("\n[L3] after multi_query_search (30 candidates):")
    cands = multi_query_search(qs, metadata_filter=mf, limit_per_query=10,
                               final_limit=30, level="child")
    hit = next(((j+1, round(float(c.score), 3))
                for j, c in enumerate(cands)
                if target.lower() in c.payload.get("section", "").lower()), None)
    print(f"   target: {'rank ' + str(hit[0]) if hit else 'ABSENT'}")

    print("\n[L3b] after expand_context:")
    exp = expand_context(cands, confidence_threshold=0.70)
    hit = next((j+1 for j, c in enumerate(exp)
                if target.lower() in c.payload.get("section", "").lower()), None)
    print(f"   target: {'rank ' + str(hit) if hit else 'ABSENT'}   ({len(exp)} candidates)")

    print("\n[L3c] after rerank (top 10):")
    rr = rerank(qs[0], exp, top_k=10, all_queries=qs)
    for j, c in enumerate(rr):
        s = c.payload.get("section", "?")[:34]
        mark = "  <<< TARGET" if target.lower() in s.lower() else ""
        print(f"   {j+1:2}. [{c.payload.get('rerank_score', 0):.3f}] {s}{mark}")

    print("\n[L4] after fetch_parents (top 5):")
    parents = fetch_parents(rr)[:5]
    for p in parents:
        print(f"   {p.payload.get('section','?')[:44]}")
    print()
