"""
comparison/comparison_builder.py
─────────────────────────────────────────────────────────
مقایسه دو محصول — نسخه Hierarchical.

برای هر محصول:
  جستجو روی child chunks (با query generic) →
  rerank children →
  fetch parents (context کامل) →
  کنار هم چیدن برای LLM
─────────────────────────────────────────────────────────
"""

import re
import requests

import config
from retrieval.retriever import hybrid_search, fetch_parents
from retrieval.reranker import rerank
from prompts.prompts import BASE_SYSTEM_PROMPT


COMPARISON_PROMPT = BASE_SYSTEM_PROMPT + """

You are comparing two products based on the context below.
Structure your answer as a clear comparison, highlighting
similarities and differences. Use a table if appropriate.
If evidence for one product is missing or weak, say so explicitly
instead of guessing.

Context:
{context}

Question: {question}

Answer:"""


def build_comparison(question: str,
                     products: list,
                     top_k: int = 3) -> dict:
    """
    از هر محصول جداگانه retrieve میکنه (روی children)، بعد parent ها
    رو fetch میکنه و کنار هم برای مقایسه می‌چینه.
    """
    # نام محصولات رو از query حذف کن تا برای هر محصول
    # جستجوی generic بشه (نه آلوده به نام محصول دیگه)
    generic_question = question
    for pattern in [r'RD9\d+X?S?', r'HR\d+', r'HP\d+', r'\bvs\b',
                    r'compared?\s+to', r'difference\s+between',
                    r'\bboth\b']:
        generic_question = re.sub(pattern, '', generic_question,
                                  flags=re.IGNORECASE)
    generic_question = ' '.join(generic_question.split())

    all_chunks = {}

    for product in products:
        # جستجو روی child chunks
        child_candidates = hybrid_search(
            generic_question,
            metadata_filter={"product": product},
            limit=8,
            level="child"
        )
        # rerank children
        reranked = rerank(generic_question, child_candidates,
                          top_k=min(top_k, 3))
        # fetch parents برای context کامل
        parents = fetch_parents(reranked)
        all_chunks[product] = parents[:min(top_k, 3)]

    context_blocks = []
    for product, chunks in all_chunks.items():
        if chunks:
            product_context = "\n\n".join([
                f"[{product} — {c.payload['section']}]\n{c.payload['text']}"
                for c in chunks
            ])
            context_blocks.append(product_context)

    full_context = "\n\n" + "=" * 40 + "\n\n".join(context_blocks)

    prompt = COMPARISON_PROMPT.format(
        context=full_context,
        question=question
    )

    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LITELLM_API_KEY}"
        },
        json={
            "model": config.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=config.LLM_TIMEOUT
    )
    response.raise_for_status()
    answer = response.json()["choices"][0]["message"]["content"]

    return {
        "answer": answer,
        "products_compared": products,
        "chunks_per_product": {p: len(c) for p, c in all_chunks.items()}
    }