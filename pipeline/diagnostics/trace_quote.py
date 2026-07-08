from comparison.comparison_builder import _retrieve_schema_aware
from comparison.extractor import _extract_json, _normalize_text
import config, requests
from comparison.schemas import build_schema_prompt_spec

product = "HR652 Digital Repeater"
question = "What are the main installation differences between the RD98XS and HR652 repeaters?"
chunks = _retrieve_schema_aware(product, "installation", question)

section_by_id_text = {}
parts = []
for i, c in enumerate(chunks, 1):
    eid = f"E{i}"
    section_by_id_text[eid] = c.payload.get('text','')
    parts.append(f"[{eid}] Section: {c.payload.get('section','')}\n{c.payload.get('text','')}")
context = "\n\n".join(parts)
schema = build_schema_prompt_spec("installation", question)

prompt = f'''Extract structured data about {product}. Output STRICT JSON only.
"supporting_quote" must be an EXACT sentence copied verbatim from the cited evidence.

{{
  "product": "{product}", "aspect": "installation",
  "fields": {{
{schema}
  }}
}}

Context:
{context}

JSON:'''

r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
    headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
    json={"model": config.DEFAULT_MODEL, "messages":[{"role":"user","content":prompt}], "temperature":0},
    timeout=config.LLM_TIMEOUT)
raw = r.json()["choices"][0]["message"]["content"]
parsed = _extract_json(raw)

# fasteners رو چک کن
fast = parsed["fields"].get("fasteners", {})
print("Fasteners raw from model:")
print(f"  status: {fast.get('status')}")
print(f"  items: {fast.get('items')}")
print(f"  evidence: {fast.get('evidence')}")
print(f"  quote: {fast.get('supporting_quote')!r}")
print()
# آیا quote توی متن هست؟
quote = fast.get('supporting_quote','')
for eid in fast.get('evidence',[]):
    txt = section_by_id_text.get(eid,'')
    in_text = _normalize_text(quote) in _normalize_text(txt) if quote else False
    print(f"  quote in {eid}? {in_text}")
    if not in_text and quote:
        print(f"    quote norm:  {_normalize_text(quote)[:80]}")
        print(f"    text has:    {'m3' in _normalize_text(txt)}, {'m4' in _normalize_text(txt)}")
