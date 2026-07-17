from comparison.comparison_builder import _generic_query, _retrieve_product_chunks
from comparison.extractor import extract_structured, _extract_json
from comparison.schemas import build_schema_prompt_spec
import config, requests

product = "HR652 Digital Repeater"
question = "What are the main installation differences between the RD98XS and HR652 repeaters?"
generic = _generic_query(question)

# لایه ۱: chunks
chunks = _retrieve_product_chunks(product, [generic])
print("="*60)
print("LAYER 1: RETRIEVED CHUNKS")
print("="*60)
for i, c in enumerate(chunks, 1):
    print(f"[E{i}] {c.payload['section']}")
    print(f"     {c.payload['text'][:100]}")
print()

# لایه ۲: raw JSON از مدل
section_by_id = {}
context_parts = []
for i, c in enumerate(chunks, 1):
    eid = f"E{i}"
    sec = c.payload.get("section","")
    section_by_id[eid] = sec
    context_parts.append(f"[{eid}] Section: {sec}\n{c.payload.get('text','')}")
context = "\n\n".join(context_parts)
schema_desc = build_schema_prompt_spec("installation", question)
prompt = f'''Extract structured data about {product}. Output STRICT JSON only.
"evidence" must be section IDs like ["E1"]. Any "documented" MUST have evidence.

{{
  "product": "{product}",
  "aspect": "installation",
  "fields": {{
{schema_desc}
  }}
}}

Context:
{context}

JSON:'''
r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
    headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
    json={"model": config.DEFAULT_MODEL, "messages":[{"role":"user","content":prompt}]},
    timeout=config.LLM_TIMEOUT)
raw = r.json()["choices"][0]["message"]["content"]
print("="*60)
print("LAYER 2: RAW MODEL JSON")
print("="*60)
print(raw[:800])
print()

# لایه ۳: validated envelope
env = extract_structured(product, "installation", question, chunks)
print("="*60)
print("LAYER 3: VALIDATED ENVELOPE")
print("="*60)
import json
print(json.dumps(env, indent=2, ensure_ascii=False)[:800])
