import json, re, requests, config
from comparison.comparison_builder import _generic_query, _retrieve_product_chunks
from comparison.schemas import build_schema_prompt_spec, expected_field_names
from comparison.extractor import _extract_json, _validate, _resolve_evidence_ids

product = "HR652 Digital Repeater"
question = "What are the main installation differences between the RD98XS and HR652 repeaters?"
generic = _generic_query(question)

# همون top_k فعلی (3) — تا وضعیت فعلی رو ببینیم
chunks = _retrieve_product_chunks(product, generic, top_k=3)

section_by_id = {}
parts = []
for i, c in enumerate(chunks, 1):
    eid = f"E{i}"; sec = c.payload.get("section","")
    section_by_id[eid] = sec
    parts.append(f"[{eid}] Section: {sec}\n{c.payload.get('text','')}")
context = "\n\n".join(parts)
allowed_ids = set(section_by_id.keys())
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

# یک call، هم raw هم validated ازش
r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
    headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
    json={"model": config.DEFAULT_MODEL, "messages":[{"role":"user","content":prompt}]},
    timeout=config.LLM_TIMEOUT)
raw = r.json()["choices"][0]["message"]["content"]

parsed = _extract_json(raw)
validated = _validate(parsed, "installation", question, product, allowed_ids)
if validated:
    _resolve_evidence_ids(validated, section_by_id)

print("="*60); print("RAW (parsed from SAME call)"); print("="*60)
for k, v in parsed.get("fields", {}).items():
    print(f"  {k}: {v}")
print()
print("="*60); print("VALIDATED (SAME call)"); print("="*60)
for k, v in validated.get("fields", {}).items():
    print(f"  {k}: {v}")
