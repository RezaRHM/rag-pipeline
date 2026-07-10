import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests, config
from db.connection import get_postgres
from main import process_query

CACHE = "diagnostics/frozen_v2.json"

# Q2/Q3/Q17 never reach the generator (clarification / unsupported-product path).
SUBSET = {
    "Q1":  "RD98XS LEDs?",
    "Q8":  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
    "Q9":  "Which alarm conditions can be triggered by abnormal voltage, overheating, or fan failure on the RD98XS?",
    "Q10": "What voltage or power supply requirements are listed for the HR652 repeater?",
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

def freeze():
    if os.path.exists(CACHE):
        print(f"loading {CACHE}")
        return json.load(open(CACHE))
    frozen = {}
    for qid, q in SUBSET.items():
        clear()
        t = time.time()
        r = process_query(q)
        ctx = "\n\n".join(
            f"[{c.payload['product']} — {c.payload['section']}]\n{c.payload['text']}"
            for c in r["chunks"])
        frozen[qid] = {"question": q, "context": ctx}
        print(f"  {qid}: {len(r['chunks'])} chunks, {time.time()-t:.0f}s", flush=True)
    json.dump(frozen, open(CACHE, "w"), indent=1)
    return frozen

# ── cumulative rule groups ──
P0 = "Answer the question using only the context provided below."

G = {
 "grounding":   "- Cite the document, model, and section when stating a fact.",
 "notfound":    ("- If the requested information is genuinely absent from the context, say so "
                 "plainly. Do not claim absence merely because the wording differs."),
 "attribution": ("- Keep evidence for each product separate. Never transfer a detail from one "
                 "product to another unless the context states it for both."),
 "precision":   ("- Preserve exact technical values. Do not assume equivalences such as "
                 "water resistant = waterproof, or ambient temperature = storage temperature."),
 "antispec":    ('- Do not use speculative wording such as "likely", "probably", '
                 '"can be inferred", or "may support". State only what the documentation confirms.'),
 "scope":       ("- If the documentation covers part of the question, answer that part and state "
                 "once, briefly, which aspect it does not cover."),
}

ORDER = ["grounding", "notfound", "attribution", "precision", "antispec", "scope"]

VARIANTS = {"P0_minimal": P0}
acc = []
for i, k in enumerate(ORDER, 1):
    acc.append(G[k])
    VARIANTS[f"P{i}_+{k}"] = P0 + "\n\nRules:\n" + "\n".join(acc)

def ask_llm(system, ctx, q):
    p = f"{system}\n\nContext:\n{ctx}\n\nQuestion: {q}\n\nAnswer:"
    r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
        json={"model": config.DEFAULT_MODEL,
              "messages": [{"role": "user", "content": p}], "temperature": 0},
        timeout=config.LLM_TIMEOUT)
    return r.json()["choices"][0]["message"]["content"]

REFUSAL = ["does not contain", "not documented", "does not mention", "does not specify",
           "not provided in", "no information", "does not explicitly", "unfortunately"]

def refused(a):
    return any(m in a.lower()[:220] for m in REFUSAL)

def hedged(a):
    low = a.lower()
    return sum(low.count(m) for m in ["does not", "not specifically", "general instal"]) >= 2

def speculates(a):
    return any(m in a.lower() for m in ["can be inferred", "likely", "probably", "may support"])

if __name__ == "__main__":
    frozen = freeze()
    print()
    results = {}
    for vname, sysmsg in VARIANTS.items():
        print(f"{vname}", flush=True)
        row = {}
        for qid, d in frozen.items():
            a = ask_llm(sysmsg, d["context"], d["question"])
            row[qid] = {"refused": refused(a), "hedged": hedged(a),
                        "spec": speculates(a), "answer": a[:200]}
            flags = []
            if row[qid]["refused"]: flags.append("REF")
            if row[qid]["hedged"]:  flags.append("hedge")
            if row[qid]["spec"]:    flags.append("SPEC")
            print(f"  {qid}: {','.join(flags) if flags else 'ok':16} {a[:52].strip()}", flush=True)
        results[vname] = row
        print(flush=True)

    json.dump(results, open("diagnostics/prompt_build_results.json", "w"), indent=1)

    qids = list(SUBSET)
    print("=" * 74)
    print("REFUSAL MATRIX   (want: Q1/Q8/Q9/Q10 ok, Q16/Q20 REF)")
    print("=" * 74)
    print(f"{'variant':22} " + " ".join(f"{q:>5}" for q in qids))
    for v, row in results.items():
        cells = ["REF" if row[q]["refused"] else "ok" for q in qids]
        print(f"{v:22} " + " ".join(f"{c:>5}" for c in cells))

    print("\nHEDGE (Q8) and SPECULATION (Q9)")
    print("-" * 40)
    for v, row in results.items():
        print(f"{v:22} Q8_hedge={str(row['Q8']['hedged']):5} Q9_spec={row['Q9']['spec']}")
