import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests, config
from db.connection import get_postgres
from main import process_query

CACHE = "diagnostics/frozen_contexts.json"

# Q2/Q3 are handled by the clarification path before retrieval; they never
# reach the generator, so there is no context to ablate a prompt against.
SUBSET = {
    "Q1":  "RD98XS LEDs?",
    "Q8":  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
    "Q10": "What voltage or power supply requirements are listed for the HR652 repeater?",
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

def freeze_contexts():
    """retrieval رو یک بار اجرا و context ها رو ذخیره می‌کنه."""
    if os.path.exists(CACHE):
        print(f"loading frozen contexts from {CACHE}")
        return json.load(open(CACHE))
    frozen = {}
    for qid, q in SUBSET.items():
        clear()
        t = time.time()
        r = process_query(q)
        ctx = "\n\n".join(
            f"[{c.payload['product']} — {c.payload['section']}]\n{c.payload['text'][:800]}"
            for c in r["chunks"])
        frozen[qid] = {"question": q, "context": ctx,
                       "product": r["detected_product"], "type": r["query_type"]}
        print(f"  {qid}: {len(r['chunks'])} chunks, {time.time()-t:.0f}s", flush=True)
    json.dump(frozen, open(CACHE, "w"), indent=1)
    print(f"saved to {CACHE}")
    return frozen

# ── prompt groups ──
MINIMAL = "Answer the question using only the context provided below."

A_GROUNDING = """
- Answer only from the provided context. Do not invent facts."""

B_NOTFOUND = """
- If the requested information is genuinely absent from the context, say it is not
  documented in the retrieved context. Do not claim absence merely because the
  question's wording differs from the documentation's wording."""

E_ANTIREFUSAL = """
- If directly relevant evidence exists, answer it using the documentation's own
  terminology. Do not refuse because the phrasing differs.
- You may combine directly compatible facts from multiple retrieved sections of the
  same product when the relationship is explicit and no unsupported assumption is needed."""

C_ATTRIBUTION = """
- Keep evidence for each product separate. Never transfer a detail from one product
  to another unless the context states it for both."""

D_DISTINCTION = """
- Preserve exact technical values. Do not assume equivalences such as
  water resistant = waterproof, or ambient temperature = storage temperature."""

VARIANTS = {
    "V0_minimal":        MINIMAL,
    "V1_+grounding":     MINIMAL + "\n\nRules:" + A_GROUNDING,
    "V2_+notfound":      MINIMAL + "\n\nRules:" + A_GROUNDING + B_NOTFOUND,
    "V3_+antirefusal":   MINIMAL + "\n\nRules:" + A_GROUNDING + B_NOTFOUND + E_ANTIREFUSAL,
    "V4_+attribution":   MINIMAL + "\n\nRules:" + A_GROUNDING + B_NOTFOUND + E_ANTIREFUSAL + C_ATTRIBUTION,
    "V5_+distinction":   MINIMAL + "\n\nRules:" + A_GROUNDING + B_NOTFOUND + E_ANTIREFUSAL + C_ATTRIBUTION + D_DISTINCTION,
}

def ask_llm(system, context, question):
    prompt = f"{system}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
        json={"model": config.DEFAULT_MODEL,
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0},
        timeout=config.LLM_TIMEOUT)
    return r.json()["choices"][0]["message"]["content"]

def is_refusal(a):
    low = a.lower()
    return ("does not contain" in low or "not documented" in low[:120]
            or "no relevant information" in low)

if __name__ == "__main__":
    frozen = freeze_contexts()
    print("\n" + "=" * 70)
    results = {}
    for vname, system in VARIANTS.items():
        print(f"\n{vname}", flush=True)
        row = {}
        for qid, data in frozen.items():
            ans = ask_llm(system, data["context"], data["question"])
            refused = is_refusal(ans)
            row[qid] = {"refused": refused, "answer": ans[:150]}
            mark = "REFUSE" if refused else "answer"
            print(f"  {qid}: {mark:7} | {ans[:60].strip()}", flush=True)
        results[vname] = row
    json.dump(results, open("diagnostics/prompt_ablation_results.json", "w"), indent=1)

    print("\n" + "=" * 70)
    print("REFUSAL MATRIX (expected: Q16/Q20 refuse, others answer)")
    print("=" * 70)
    qids = list(SUBSET.keys())
    print(f"{'variant':20} " + " ".join(f"{q:>4}" for q in qids))
    for vname, row in results.items():
        cells = ["REF" if row[q]["refused"] else " ok" for q in qids]
        print(f"{vname:20} " + " ".join(f"{c:>4}" for c in cells))
