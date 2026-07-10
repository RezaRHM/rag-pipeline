import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prompts.prompts as P
from db.connection import get_postgres
from main import process_query
from generation.generator import call_llm

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

BASE = P.NEUTRAL_EVAL_PROMPT.rstrip() + "\n"
R7 = BASE + ("7. Do not suggest that undocumented capabilities might exist, and do not refer\n"
             "   the user to documentation that has not been provided to you.\n")

QS = {
    "Q1":  "RD98XS LEDs?",
    "Q8":  "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
    "Q16": "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?",
    "Q20": "How do I waterproof the RD98XS for permanent outdoor pole mounting in heavy rain?",
}
store = {}
for qid, q in QS.items():
    clear()
    store[qid] = (q, process_query(q)["chunks"])

orig = P.BASE_SYSTEM_PROMPT
for name, ptext in [("benchmark_6", BASE), ("benchmark_7", R7)]:
    P.BASE_SYSTEM_PROMPT = ptext
    print("=" * 72); print(f"{name}  [{len(ptext)} chars]"); print("=" * 72)
    for qid, (q, chunks) in store.items():
        a = call_llm(P.build_generation_prompt(q, chunks, "en"))
        print(f"--- {qid}")
        print(a[:340].strip())
        print()
P.BASE_SYSTEM_PROMPT = orig
