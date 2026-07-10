import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from language.language_detector import detect_language
from query.query_expander import expand_query
from query.query_analyzer import analyze_query
from retrieval.retriever import multi_query_search, hybrid_search, fetch_parents
from retrieval.context_expander import expand_context
from retrieval.reranker import rerank
from generation.generator import generate_answer

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

QUESTIONS = [
    ("Q1",  "RD98XS LEDs?"),
    ("Q8",  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?"),
    ("Q10", "What voltage or power supply requirements are listed for the HR652 repeater?"),
    ("Q16", "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?"),
    ("Q7",  "What does each front-panel LED state mean on the HR652?"),
]

# warm-up (model loading خارج از اندازه‌گیری)
print("warming up...", flush=True)
clear(); expand_query("test warm", "en")
_ = hybrid_search("test warm", limit=3, level="child")
print("warm.\n", flush=True)

MF_BY_Q = {}
totals = {}

for qid, q in QUESTIONS:
    clear()
    t = {}
    t0 = time.time()

    lang = detect_language(q)
    t["lang"] = time.time() - t0

    s = time.time()
    qs = expand_query(q, lang["code"] if isinstance(lang, dict) else "en")
    t["expand"] = time.time() - s
    nq = len(qs)

    s = time.time()
    analysis = analyze_query(qs[0])
    t["analyze"] = time.time() - s

    mf = {"product": analysis["product"]} if analysis.get("product") else None

    s = time.time()
    cands = multi_query_search(qs, metadata_filter=mf, limit_per_query=10,
                               final_limit=30, level="child")
    t["retrieve"] = time.time() - s

    s = time.time()
    exp_c = expand_context(cands, confidence_threshold=0.70)
    t["ctx_expand"] = time.time() - s

    s = time.time()
    rr = rerank(qs[0], exp_c, top_k=10, all_queries=qs)
    t["rerank"] = time.time() - s

    s = time.time()
    parents = fetch_parents(rr)[:5]
    t["parents"] = time.time() - s

    s = time.time()
    _ = generate_answer(q, parents)
    t["generate"] = time.time() - s

    total = time.time() - t0
    totals[qid] = (t, total, nq)

    print(f"{qid}: total {total:5.1f}s   ({nq} queries)", flush=True)
    for k, v in sorted(t.items(), key=lambda x: -x[1]):
        pct = 100 * v / total
        bar = "█" * int(pct / 3)
        print(f"     {k:11} {v:6.1f}s  {pct:4.1f}%  {bar}", flush=True)
    print(flush=True)

print("=" * 60)
print("AVERAGE BREAKDOWN")
print("=" * 60)
keys = ["lang","expand","analyze","retrieve","ctx_expand","rerank","parents","generate"]
n = len(totals)
avg_total = sum(v[1] for v in totals.values()) / n
for k in keys:
    avg = sum(v[0][k] for v in totals.values()) / n
    print(f"  {k:11} {avg:6.1f}s   {100*avg/avg_total:4.1f}%")
print(f"  {'TOTAL':11} {avg_total:6.1f}s")
print(f"\n  avg expanded queries: {sum(v[2] for v in totals.values())/n:.1f}")
