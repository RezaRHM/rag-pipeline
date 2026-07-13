"""Targeted retrieval regression. Run before and after each fix, in isolation.

Reports, per question, whether the target section reaches the model, and the
final query_type, so a retrieval fix that quietly breaks an unsupported case is
caught immediately.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_postgres
from main import ask

def clear():
    pg = get_postgres(); cur = pg.cursor()
    cur.execute('DELETE FROM query_cache'); pg.commit(); pg.close()

# (id, question, expected_section_or_None, must_refuse)
CASES = [
    # retrieval targets
    ("F5", "What is on the front panel of the HR652?", "Product Layout", False),
    ("T2", "RD98XS box contents?", "Packing List", False),
    # controls: answerable, must stay answerable
    ("Q1",  "RD98XS LEDs?", "LED Indications", False),
    ("Q10", "What voltage or power supply requirements are listed for the HR652 repeater?", None, False),
    # controls: unsupported, must keep refusing
    ("Q16", "How do I configure AES-256 encryption keys on the RD98XS using the CPS software?", None, True),
    ("Q17", "What is the alarm code E47 on the Hytera RD99XS repeater?", None, True),
    ("Q19", "What is the default admin password for the RD98XS web interface?", None, True),
]

REFUSE_MARKERS = ["does not", "no mention", "no information", "not documented",
                  "does not cover", "not contain", "no relevant information",
                  "does not appear"]

def refused(ans, qtype):
    if qtype in ("needs_clarification", "unsupported_product"):
        return True
    return any(m in ans.lower()[:200] for m in REFUSE_MARKERS)

for qid, q, expect, must_refuse in CASES:
    clear()
    r = ask(q)
    ans = r.get("answer", "")
    qtype = r.get("query_type", "?")
    chunks = r.get("chunks", [])
    secs = [c.payload.get("section", "?") for c in chunks] if chunks else []

    retrieved = (expect is None) or any(expect.lower() in s.lower() for s in secs)
    ref = refused(ans, qtype)

    flags = []
    if expect and not retrieved:
        flags.append("TARGET_MISSING")
    if must_refuse and not ref:
        flags.append("SHOULD_REFUSE")
    if not must_refuse and ref and expect:
        flags.append("WRONGLY_REFUSED")

    status = " ".join(flags) if flags else "ok"
    print(f"{qid:4} [{status:22}] type={qtype}")
    if expect:
        rank = next((i+1 for i,s in enumerate(secs) if expect.lower() in s.lower()), None)
        print(f"      target '{expect}': {'rank '+str(rank) if rank else 'ABSENT'}")
    print(f"      {ans[:90].strip()}")
    print()
