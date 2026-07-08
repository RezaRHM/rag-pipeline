import requests, config
from retrieval.retriever import hybrid_search, fetch_parents
from retrieval.reranker import rerank

def summarize_product(product, aspect_query):
    """خلاصه‌ی یک محصول به‌تنهایی — بدون محصول دیگر در context."""
    children = hybrid_search(aspect_query, metadata_filter={"product": product},
                             limit=8, level="child")
    reranked = rerank(aspect_query, children, top_k=3)
    parents = fetch_parents(reranked)
    context = "\n\n".join([f"[{c.payload['section']}]\n{c.payload['text']}"
                           for c in parents[:3]])
    prompt = f"""Summarize ONLY the installation steps for {product} from this context.
List concrete steps/details (screws, brackets, sections). Do not mention any other product.

Context:
{context}

Summary:"""
    r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
        json={"model": config.DEFAULT_MODEL, "messages":[{"role":"user","content":prompt}]},
        timeout=config.LLM_TIMEOUT)
    return r.json()["choices"][0]["message"]["content"]

aspect = "installation steps mounting bracket screws"
print("=== RD98XS summary (isolated) ===")
rd = summarize_product("RD98XS Digital Repeater", aspect)
print(rd)
print("\n=== HR652 summary (isolated) ===")
hr = summarize_product("HR652 Digital Repeater", aspect)
print(hr)

# مقایسه‌ی نهایی از دو خلاصه
compare_prompt = f"""Compare the installation of two repeaters based ONLY on these two summaries.
Keep each product's details strictly separate. If a detail is only in one summary, do not attribute it to the other.

RD98XS summary:
{rd}

HR652 summary:
{hr}

Comparison:"""
r = requests.post(f"{config.LITELLM_BASE_URL}/v1/chat/completions",
    headers={"Authorization": f"Bearer {config.LITELLM_API_KEY}"},
    json={"model": config.DEFAULT_MODEL, "messages":[{"role":"user","content":compare_prompt}]},
    timeout=config.LLM_TIMEOUT)
print("\n=== FINAL COMPARISON (from 2 summaries) ===")
print(r.json()["choices"][0]["message"]["content"])
