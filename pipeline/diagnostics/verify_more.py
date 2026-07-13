import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.connection import get_qdrant
from retrieval.retriever import hybrid_search
import config

q = get_qdrant()
PTS, _ = q.scroll(collection_name=config.QDRANT_COLLECTION, limit=2000, with_payload=True)

def lexical(pkey, terms):
    out = []
    for p in PTS:
        if pkey.lower() not in p.payload.get("product", "").lower():
            continue
        low = p.payload.get("text", "").lower()
        f = [t for t in terms if t.lower() in low]
        if f:
            out.append((p.payload.get("section", "?"), f, p.payload.get("text", "")[:130]))
    return out

CASES = [
    ("RD98XS frequency range", "RD98XS",
     ["400-470", "mhz", "frequency range", "uhf band", "vhf band"]),
    ("RD98XS IP rating", "RD98XS",
     ["ip54", "ip55", "ip67", "ip68", "ingress protection", "ip rating"]),
    ("HR652 duplexer included", "HR652",
     ["duplexer", "external duplexer"]),
    ("RD98XS ethernet port", "RD98XS",
     ["ethernet"]),
]

for label, pkey, terms in CASES:
    hits = lexical(pkey, terms)
    print("=" * 72)
    print(f"{label}   ->  {len(hits)} lexical hit(s)")
    print("=" * 72)
    for sec, f, txt in hits[:5]:
        print(f"  {sec[:44]:46} {f}")
        print(f"    {txt.strip()[:110]}")
    if not hits:
        print("  (none — candidate for unsupported)")
    print()
