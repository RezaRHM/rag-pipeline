from comparison.comparison_builder import _retrieve_schema_aware
from comparison.extractor import extract_structured
import config, requests
from comparison.schemas import build_schema_prompt_spec

product = "HR652 Digital Repeater"
question = "What are the main installation differences between the RD98XS and HR652 repeaters?"

chunks = _retrieve_schema_aware(product, "installation", question)

print("CONTEXT chunks given to extractor:")
for i, c in enumerate(chunks, 1):
    print(f"\n[E{i}] {c.payload['section']}")
    print(f"     {c.payload['text'][:200]}")

# چک کن آیا متن duplexer واقعاً توی context هست
full = " ".join(c.payload.get('text','').lower() for c in chunks)
print("\n\n=== duplexer mentions in context ===")
import re
for c in chunks:
    t = c.payload.get('text','')
    if 'duplexer' in t.lower():
        # جمله‌های حاوی duplexer
        for sent in re.split(r'(?<=[.!?])\s+', t):
            if 'duplexer' in sent.lower():
                print(f"  • {sent[:120]}")
