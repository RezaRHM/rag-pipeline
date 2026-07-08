from retrieval.retriever import hybrid_search

product = "HR652 Digital Repeater"

queries = [
    "duplexer installation",
    "rear housing removal",
    "grounding",
    "wall mounting fixing plate fasteners",
]

for q in queries:
    children = hybrid_search(q, metadata_filter={"product": product}, limit=5, level="child")
    print(f"\nquery: '{q}' → {len(children)} children")
    for c in children[:4]:
        print(f"  [{c.score:.3f}] {c.payload['section'][:35]} | {c.payload['text'][:50]}")
