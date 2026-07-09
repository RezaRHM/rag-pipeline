import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from query.query_expander import expand_query
from retrieval.retriever import multi_query_search, fetch_parents, hybrid_search
from retrieval.context_expander import expand_context
from retrieval.reranker import rerank

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

def h(s):
    return hashlib.sha256(str(s).encode()).hexdigest()[:10]

QUESTION = "RD98XS LEDs?"
MF = {"product": "RD98XS Digital Repeater"}
N = 5

print(f"Layer-by-layer determinism, {N} runs\n")
rows = []
for run in range(N):
    clear()
    L = {}

    qs = expand_query(QUESTION, "en")
    L["L1_queries"] = h(qs)

    per_query = []
    for q in qs:
        res = hybrid_search(q, metadata_filter=MF, limit=10, level="child")
        per_query.append([(str(p.id), round(float(p.score), 6)) for p in res])
    L["L2_perquery"] = h(per_query)

    cands = multi_query_search(qs, metadata_filter=MF, limit_per_query=10,
                               final_limit=30, level="child")
    L["L3_cands"] = h([str(c.id) for c in cands])

    exp_c = expand_context(cands, confidence_threshold=0.70)
    L["L3b_ctxexp"] = h([str(c.id) for c in exp_c])

    rr = rerank(qs[0], exp_c, top_k=10, all_queries=qs)
    L["L3c_rerank"] = h([str(c.id) for c in rr])

    parents = fetch_parents(rr)[:5]
    ctx = "\n\n".join(f"[{p.payload['product']} — {p.payload['section']}]\n{p.payload['text']}"
                      for p in parents)
    L["L4_context"] = h(ctx)

    rows.append(L)
    print(f"run {run+1}: " + "  ".join(f"{k}={v}" for k, v in L.items()), flush=True)

print("\n" + "=" * 72)
print("FIRST DIVERGING LAYER")
print("=" * 72)
for layer in rows[0]:
    vals = set(r[layer] for r in rows)
    print(f"  {layer:14} {'STABLE' if len(vals)==1 else f'VARIES ({len(vals)} distinct)'}")
