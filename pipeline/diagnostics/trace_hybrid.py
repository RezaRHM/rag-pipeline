import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.embedder import embed_dense, embed_sparse
from retrieval.retriever import hybrid_search

def h(s):
    return hashlib.sha256(str(s).encode()).hexdigest()[:10]

Q = "RD98XS LED indicators specifications"
MF = {"product": "RD98XS Digital Repeater"}

print("A) dense embedding determinism (5x):")
for i in range(5):
    v = embed_dense(Q)
    print(f"  {i+1}. hash={h([round(x,8) for x in v])}  first3={[round(x,6) for x in v[:3]]}")

print("\nB) sparse embedding determinism (5x):")
for i in range(5):
    s = embed_sparse(Q)
    print(f"  {i+1}. hash={h(str(sorted(s.items()) if isinstance(s, dict) else s))}")

print("\nC) hybrid_search ids + scores (5x):")
for i in range(5):
    res = hybrid_search(Q, metadata_filter=MF, limit=10, level="child")
    ids = [str(p.id) for p in res]
    scores = [round(float(p.score), 6) for p in res]
    print(f"  {i+1}. ids={h(ids)}  scores={h(scores)}")

print("\nD) same id SET across runs (order aside)?")
sets = []
for i in range(3):
    res = hybrid_search(Q, metadata_filter=MF, limit=10, level="child")
    sets.append(frozenset(str(p.id) for p in res))
print(f"  identical sets: {len(set(sets)) == 1}")
if len(set(sets)) > 1:
    print(f"  set sizes: {[len(s) for s in sets]}")
    print(f"  symmetric diff (run1 vs run2): {len(sets[0] ^ sets[1])} ids")
