from comparison.comparison_builder import _generic_query, _retrieve_product_chunks
from comparison.extractor import extract_structured

product = "HR652 Digital Repeater"
question = "What are the main installation differences between the RD98XS and HR652 repeaters?"
generic = _generic_query(question)
chunks = _retrieve_product_chunks(product, generic, top_k=3)  # همون context ثابت

print("Running extraction 5x with SAME context (temperature=0)...\n")
runs = []
for i in range(5):
    env = extract_structured(product, "installation", question, chunks)
    if env:
        statuses = {k: v.get("status") for k, v in env["fields"].items()}
        runs.append(statuses)
        print(f"Run {i+1}: duplexer={statuses.get('duplexer_procedure')}, "
              f"fixing_plate={statuses.get('fixing_plate')}, "
              f"grounding={statuses.get('grounding')}")
    else:
        print(f"Run {i+1}: extraction returned None")

# چک کن آیا همه‌ی run ها یکسانن
if runs and all(r == runs[0] for r in runs):
    print("\n✓ STABLE — all 5 runs identical")
else:
    print("\n⚠️ UNSTABLE — runs differ even at temperature=0")
