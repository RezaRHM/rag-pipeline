from query.query_expander import expand_query
from query.query_analyzer import analyze_query
from retrieval.retriever import hybrid_search, multi_query_search

CASES = {
    "Q1 (LED)": {
        "question": "RD98XS LEDs?",
        "marker": lambda t: "timeslot" in t.lower() and "indicator" in t.lower(),
        "desc": "LED indicator table",
    },
    "Q8 (rack)": {
        "question": "What are the exact steps to install the RD98XS repeater in a rack or cabinet?",
        "marker": lambda t: "rack" in t.lower() or "cabinet" in t.lower(),
        "desc": "rack/cabinet text",
    },
    "Q10 (voltage)": {
        "question": "What voltage or power supply requirements are listed for the HR652 repeater?",
        "marker": lambda t: "16.8" in t,
        "desc": "12-16.8 V DC",
    },
}

for name, case in CASES.items():
    print("=" * 60)
    print(f"{name}: {case['desc']}")
    print("=" * 60)

    q = case["question"]
    marker = case["marker"]
    queries = expand_query(q, "en")
    analysis = analyze_query(queries[0])
    mf = {"product": analysis["product"]} if analysis["product"] else None
    print(f"  product filter: {analysis['product']}")
    print(f"  expanded queries: {len(queries)}")

    # آیا کدوم query پیداش می‌کنه؟
    found_in = []
    for i, eq in enumerate(queries, 1):
        children = hybrid_search(eq, metadata_filter=mf, limit=10, level="child")
        for r, c in enumerate(children, 1):
            if marker(c.payload.get("text", "")):
                found_in.append((i, r))
                break
    if found_in:
        print(f"  ✓ found in {len(found_in)} queries: " +
              ", ".join(f"q{i}@rank{r}" for i, r in found_in[:5]))
    else:
        print("  ✗ NOT found in any expanded query (deeper problem)")
        continue

    # survival بعد از final_limit=20 و 100
    for fl in [20, 100]:
        cands = multi_query_search(queries, metadata_filter=mf,
                                   limit_per_query=10, final_limit=fl, level="child")
        pos = None
        for i, c in enumerate(cands, 1):
            if marker(c.payload.get("text", "")):
                pos = i
                break
        status = f"position {pos}" if pos else "REMOVED"
        print(f"  final_limit={fl:3} ({len(cands)} cands) → {status}")
    print()
