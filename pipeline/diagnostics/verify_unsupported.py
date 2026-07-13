"""Verify 'unsupported' ground truth before it becomes a benchmark answer.

A wrong unsupported label is worse than a wrong supported one: the model
answers correctly and the rubric marks it FAIL. Three layers:
  A. exact lexical search over all chunk text
  B. synonym / paraphrase search
  C. product-scoped semantic retrieval
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_qdrant
from retrieval.retriever import hybrid_search
import config

q = get_qdrant()
PTS, _ = q.scroll(collection_name=config.QDRANT_COLLECTION, limit=2000, with_payload=True)

def lexical(product_key, terms, exclude=()):
    """chunk هایی که محصولشون match می‌کنه و حداقل یکی از terms رو دارن."""
    hits = []
    for p in PTS:
        prod = p.payload.get("product", "")
        if product_key.lower() not in prod.lower():
            continue
        txt = p.payload.get("text", "")
        low = txt.lower()
        found = [t for t in terms if t.lower() in low]
        if found and not any(x.lower() in low for x in exclude):
            hits.append((p.payload.get("section", "?"), found, txt[:150]))
    return hits

def semantic(query, product):
    res = hybrid_search(query, metadata_filter={"product": product},
                        limit=5, level="parent")
    return [(r.payload.get("section", "?"), round(float(r.score), 3),
             r.payload.get("text", "")[:110]) for r in res]

CASES = [
    ("V13  RD98XS RF output power", "RD98XS",
     ["output power", "tx power", "transmit power", "transmitter power",
      "rated power", "dBm", "watt", " W "],
     [],
     "What is the RF output power of the RD98XS repeater?",
     "RD98XS Digital Repeater"),

    ("V14  HR652 weight", "HR652",
     ["weight", "net weight", "gross weight", " kg", " g)", "mass"],
     [],
     "What is the weight of the HR652 repeater?",
     "HR652 Digital Repeater"),

    ("V15  HR652 front panel", "HR652",
     ["front panel", "product layout", "indicator", "knob", "display",
      "part name", "seven-segment"],
     [],
     "What is on the front panel of the HR652?",
     "HR652 Digital Repeater"),

    ("V16  RD98XS warranty", "RD98XS",
     ["warranty", "guarantee", "warranty period", "limited warranty",
      "service period", "months", "years"],
     [],
     "What is the warranty period for the RD98XS?",
     "RD98XS Digital Repeater"),
]

for label, pkey, terms, exclude, sem_q, prod in CASES:
    print("=" * 74)
    print(label)
    print("=" * 74)

    hits = lexical(pkey, terms, exclude)
    print(f"[A] lexical: {len(hits)} chunk(s)")
    for sec, found, txt in hits[:6]:
        print(f"    {sec[:42]:44} terms={found}")
        print(f"      {txt[:120].strip()}")
    if not hits:
        print("    (none)")

    print(f"\n[C] semantic (product-scoped, parent level):")
    for sec, score, txt in semantic(sem_q, prod):
        print(f"    [{score}] {sec[:44]}")
        print(f"      {txt.strip()[:110]}")
    print()
