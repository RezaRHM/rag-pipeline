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
    "Q1":  "RD98XS LEDs?",
    "Q6":  "What are the exact operating temperature and storage temperature ranges for the RD98XS?",
    "Q9":  "Which alarm conditions can be triggered by abnormal voltage, overheating, or fan failure on the RD98XS?",
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}

print("retrieving chunks once per question...", flush=True)
store = {}
for qid, q in QUESTIONS.items():
    clear()
    r = process_query(q)
    store[qid] = (q, r["chunks"])
    print(f"  {qid}: {len(r['chunks'])} chunks", flush=True)

ORIGINAL = P.BASE_SYSTEM_PROMPT
R12_OLD = [l for l in ORIGINAL.split("\n") if l.strip().startswith("12.")][0]
R12_NEW = ("12. State only what the documentation explicitly confirms. If it does not "
           "confirm a point, say so plainly rather than estimating or reasoning from a "
           "related fact.")

VARIANTS = {
    "production":       ORIGINAL,
    "r12_no_examples":  ORIGINAL.replace(R12_OLD, R12_NEW),
}
SPEC = ["can be inferred", "likely", "probably", "may have", "it is possible", "suggests that"]

print()
for vname, ptext in VARIANTS.items():
    P.BASE_SYSTEM_PROMPT = ptext
    print("=" * 72)
    print(vname)
    print("=" * 72)
    for qid, (q, chunks) in store.items():
        full = P.build_generation_prompt(q, chunks, "en")
        a = call_llm(full)
        flags = [w for w in SPEC if w in a.lower()]
        print(f"  {qid}: {str(flags) if flags else 'clean'}", flush=True)
        print(f"     {a[:110].strip()}", flush=True)
    print()
P.BASE_SYSTEM_PROMPT = ORIGINAL
