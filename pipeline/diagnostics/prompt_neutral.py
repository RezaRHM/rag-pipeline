import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prompts.prompts as P
from db.connection import get_postgres
from main import process_query
from generation.generator import call_llm

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

QUESTIONS = {
    # answerable
    "Q1":  "RD98XS LEDs?",
    "Q6":  "What are the exact operating temperature and storage temperature ranges for the RD98XS?",
    "Q7":  "What does each front-panel LED state mean on the HR652?",
    "Q8":  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
    "Q9":  "Which alarm conditions can be triggered by abnormal voltage, overheating, or fan failure on the RD98XS?",
    "Q10": "What voltage or power supply requirements are listed for the HR652 repeater?",
    # unsupported (must still decline)
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q18": "Can the HR652 be used as a 5G base station backup link?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}

NEUTRAL = """You are a technical support assistant for Rohill.

Rules:
1. Answer only from the provided context.
2. If the requested information is genuinely absent from the context, say so plainly.
   Do not claim absence merely because the question's wording differs from the documentation's.
3. Cite the document, model, and section when stating a fact.
4. State only what the documentation confirms. If it does not confirm a point, say so
   rather than estimating it or reasoning from a related fact.
5. Keep evidence for each product separate. Never transfer a detail from one product to
   another unless the context states it for both.
6. Preserve exact technical values and distinctions.
"""

print("retrieving chunks once per question...", flush=True)
store = {}
for qid, q in QUESTIONS.items():
    clear()
    r = process_query(q)
    store[qid] = (q, r["chunks"])
    print(f"  {qid}: {len(r['chunks'])} chunks", flush=True)

ORIGINAL = P.BASE_SYSTEM_PROMPT
SPEC = ["can be inferred", "likely", "probably", "may have", "it is possible",
        "suggests that", "appears that"]
REFUSE = ["does not contain", "no mention of", "does not provide", "no information",
          "not documented", "does not cover"]

VARIANTS = {"production (14 rules)": ORIGINAL, "neutral (6 rules)": NEUTRAL}
results = {}

print()
for vname, ptext in VARIANTS.items():
    P.BASE_SYSTEM_PROMPT = ptext
    print("=" * 74)
    print(f"{vname}   [{len(ptext)} chars]")
    print("=" * 74)
    row = {}
    for qid, (q, chunks) in store.items():
        full = P.build_generation_prompt(q, chunks, "en")
        a = call_llm(full)
        spec = [w for w in SPEC if w in a.lower()]
        ref = any(w in a.lower()[:200] for w in REFUSE)
        row[qid] = {"answer": a, "spec": spec, "refused": ref}
        tag = []
        if ref: tag.append("REF")
        if spec: tag.append(f"SPEC{spec}")
        print(f"  {qid}: {' '.join(tag) if tag else 'ok'}", flush=True)
        print(f"     {a[:115].strip()}", flush=True)
    results[vname] = row
    print()

P.BASE_SYSTEM_PROMPT = ORIGINAL

print("=" * 74)
print("SUMMARY   (want: Q1/Q6-Q10 answer clean; Q16/Q18/Q20 refuse clean)")
print("=" * 74)
qids = list(QUESTIONS)
print(f"{'question':6} {'production':28} {'neutral':28}")
for q in qids:
    def cell(v):
        r = results[v][q]
        s = "REF" if r["refused"] else "ans"
        if r["spec"]: s += f" +SPEC({len(r['spec'])})"
        return s
    print(f"{q:6} {cell('production (14 rules)'):28} {cell('neutral (6 rules)'):28}")
