from main import process_query

print("=" * 60)
print("Q1: RD98XS LEDs?  — does the LED chunk reach the LLM?")
print("=" * 60)
r = process_query("RD98XS LEDs?")
print(f"detected_product: {r['detected_product']}")
print(f"final chunks ({len(r['chunks'])}):")
for c in r["chunks"]:
    t = c.payload.get("text", "")
    mark = " ← LED TABLE" if ("timeslot" in t.lower() and "indicator" in t.lower()) else ""
    print(f"  [{c.payload.get('rerank_score',0):.3f}] {c.payload['product'][:20]} | {c.payload['section'][:32]}{mark}")

print("\n" + "=" * 60)
print("Q8: rack install — does the rack chunk reach the LLM?")
print("=" * 60)
r = process_query("What are the exact steps to install the RD98XS repeater in a rack or cabinet?")
print(f"detected_product: {r['detected_product']}")
print(f"final chunks ({len(r['chunks'])}):")
for c in r["chunks"]:
    t = c.payload.get("text", "")
    mark = " ← RACK" if ("rack" in t.lower() or "cabinet" in t.lower()) else ""
    print(f"  [{c.payload.get('rerank_score',0):.3f}] {c.payload['section'][:38]}{mark}")
