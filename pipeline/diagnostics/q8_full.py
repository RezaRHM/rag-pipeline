import sys, os
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

q = "What are the exact steps to install the RD98XS repeater in a rack or cabinet?"
clear()
r = process_query(q)

for name, ptext in [("production", P.BASE_SYSTEM_PROMPT), ("neutral_6", NEUTRAL)]:
    orig = P.BASE_SYSTEM_PROMPT
    P.BASE_SYSTEM_PROMPT = ptext
    full = P.build_generation_prompt(q, r["chunks"], "en")
    a = call_llm(full)
    P.BASE_SYSTEM_PROMPT = orig
    print("=" * 72)
    print(name)
    print("=" * 72)
    print(a)
    print()

# متن واقعی 3.2.2 چیه؟
print("=" * 72)
print("WHAT 3.2.2 ACTUALLY SAYS")
print("=" * 72)
for c in r["chunks"]:
    if "3.2.2" in c.payload["section"] or "3.1" in c.payload["section"]:
        print(f"--- {c.payload['section']}")
        print(c.payload["text"][:700])
        print()
