from comparison.comparison_builder import _generic_query, _retrieve_product_chunks

question = "What are the main installation differences between the RD98XS and HR652 repeaters?"
generic = _generic_query(question)

targets = {
    "duplexer": lambda t: "duplexer" in t,
    "rear_housing": lambda t: "rear housing" in t or "rear cover" in t,
    "grounding": lambda t: "ground" in t,
}

for product in ["HR652 Digital Repeater", "RD98XS Digital Repeater"]:
    print(f"\n{'='*55}\n{product}\n{'='*55}")
    for k in [3, 5, 8]:
        chunks = _retrieve_product_chunks(product, generic, top_k=k)
        found = {}
        for name, check in targets.items():
            found[name] = any(check(c.payload.get("text","").lower()) for c in chunks)
        sections = [c.payload["section"][:30] for c in chunks]
        print(f"\n  k={k} ({len(chunks)} chunks):")
        print(f"    duplexer={found['duplexer']}, rear_housing={found['rear_housing']}, grounding={found['grounding']}")
        for s in sections:
            print(f"      - {s}")
