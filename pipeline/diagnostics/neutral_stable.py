import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import prompts.prompts as P
from db.connection import get_postgres
from main import process_query
from generation.generator import call_llm

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

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
print(f"neutral prompt: {len(NEUTRAL)} chars\n")

QS = {
    "Q1":  "RD98XS LEDs?",
    "Q6":  "What are the exact operating temperature and storage temperature ranges for the RD98XS?",
    "Q8":  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
    "Q9":  "Which alarm conditions can be triggered by abnormal voltage, overheating, or fan failure on the RD98XS?",
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}

store = {}
for qid, q in QS.items():
    clear()
    r = process_query(q)
    store[qid] = (q, r["chunks"])

ORIG = P.BASE_SYSTEM_PROMPT
P.BASE_SYSTEM_PROMPT = NEUTRAL

SPEC = ["can be inferred", "likely", "probably", "may have", "it is possible",
        "suggests that", "appears that"]
REFUSE = ["does not contain", "no mention of", "does not provide", "no information",
          "not documented", "does not cover"]

print("3 runs with identical prompt and cached chunks:\n")
for run in range(3):
    print(f"run {run+1}:")
    for qid, (q, chunks) in store.items():
        full = P.build_generation_prompt(q, chunks, "en")
        a = call_llm(full)
        h = hashlib.md5(a.encode()).hexdigest()[:6]
        spec = [w for w in SPEC if w in a.lower()]
        ref = any(w in a.lower()[:200] for w in REFUSE)
        tag = ("REF " if ref else "ans ") + (f"SPEC{spec}" if spec else "")
        print(f"  {qid}: hash={h} {tag}")
    print()

P.BASE_SYSTEM_PROMPT = ORIG
