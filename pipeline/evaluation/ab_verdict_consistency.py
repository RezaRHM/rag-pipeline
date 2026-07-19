"""A/B a verdict-consistency rule against the reproducible cases where the
8B model contradicts evidence it just cited.

Baseline is the frozen NEUTRAL_EVAL_PROMPT (the benchmarking instrument).
The variant appends one rule; the point is to measure whether it helps
before deciding to touch the instrument at all.

Usage: python evaluation/ab_verdict_consistency.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import prompts.prompts as P
from db.connection import get_postgres

EXTRA_RULE = (
    "7. Every excerpt is quoted from the documentation of the product named "
    "in its [Source: ...] label. A statement inside an excerpt IS a "
    "documented fact about that product; never dismiss it as belonging to a "
    "different product or document. Your conclusion must follow from the "
    "facts you cite: if an excerpt answers the question, do not also claim "
    "the information is missing, and if you list a fact for two products, "
    "do not then deny that they share it.\n"
)

CASES = [
    ("GPS-single", "RD965 GPS?", None,
     "should confirm the GPS module (RD965's own GPS section)"),
    ("GPS-thread", "Does it have GPS?",
     [("user", "What ingress protection rating does the RD965 have?"),
      ("assistant", "The RD965 has an IP67 degree of protection "
                    "(Source: RD965 Digital Repeater — Outdoor operation)")],
     "pronoun -> RD965; should confirm GPS"),
    ("E2-compare",
     "Do the RD962i and the HR652 use the same alarm code for a low battery?",
     None, "should answer yes - both use E2"),
    ("network-codes", "Which codes indicate a network problem?",
     [("user", "What does alarm code H5 mean on the HR652?"),
      ("assistant", "H5 means an invalid network IP alarm on the HR652 "
                    "Digital Repeater (Section 7.12.1).")],
     "sticky HR652; should include H5 (and H3)"),
]


def run(tag, prompt_text):
    P.BASE_SYSTEM_PROMPT = prompt_text
    import importlib
    import main
    importlib.reload(main)          # rebind the prompt into the pipeline
    pg = get_postgres(); cur = pg.cursor()
    cur.execute("DELETE FROM query_cache"); pg.commit(); pg.close()
    print(f"\n{'='*72}\n### {tag}\n{'='*72}", flush=True)
    for case_id, question, hist, expectation in CASES:
        history = ([{"role": r, "content": c} for r, c in hist]
                   if hist else [])
        try:
            r = main.ask(question, conversation_history=history)
            ans = (r.get("answer") or "").replace("\n", " ")
        except Exception as exc:
            ans = f"ERROR {exc}"
        print(f"\n-- {case_id}: {question}")
        print(f"   expect: {expectation}")
        print(f"   ANSWER: {ans[:340]}", flush=True)


BASELINE = P.NEUTRAL_EVAL_PROMPT
VARIANT = P.NEUTRAL_EVAL_PROMPT.rstrip()[:-3].rstrip() + "\n" + EXTRA_RULE + '"""'
VARIANT = P.NEUTRAL_EVAL_PROMPT.rstrip() + "\n" + EXTRA_RULE

run("BASELINE (frozen neutral prompt)", BASELINE)
run("VARIANT (+ rule 7: verdict consistency)", VARIANT)
