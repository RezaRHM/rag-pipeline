"""
retrieval/reranker.py
─────────────────────────────────────────────────────────
BGE Reranker v2-m3 — cross-encoder.

نکته مهم: reranker با English query × English chunks
کار میکنه — نه با query اصلی اگه غیرانگلیسیه.
این یه architectural decision ـه:
  - retrieval: multilingual (BGE-M3)
  - reranking: monolingual English (BGE-Reranker)

نسخه Hierarchical: برای child chunks، heading به proposition
اضافه میشه تا cross-encoder context کافی داشته باشه.
─────────────────────────────────────────────────────────
"""

import torch
from sentence_transformers import CrossEncoder

import config

_reranker_model = None


def _get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _get_reranker() -> CrossEncoder:
    global _reranker_model
    if _reranker_model is None:
        device = _get_device()
        print(f"Loading BGE Reranker model on {device} "
              f"(first time only, ~600MB download)...")
        _reranker_model = CrossEncoder(
            config.RERANKER_MODEL,
            max_length=512,
            device=device
        )
    return _reranker_model


def _get_english_query(all_queries: list) -> str:
    """
    از لیست query ها، انگلیسی‌ترین رو برمیگردونه.
    اولین query که فقط ASCII داره رو انتخاب میکنه.
    """
    for q in all_queries:
        try:
            q.encode('ascii')
            return q
        except UnicodeEncodeError:
            continue
    return all_queries[0]



def _rerank_text(chunk) -> str:
    """
    متن enriched برای reranking می‌سازه.

    ChatGPT پیشنهاد داد: به جای proposition خام، متادیتای
    document/model/section رو هم شامل کن. این هم context
    starvation رو حل میکنه، هم entity (product) رو حفظ میکنه
    تا reranker محصول درست رو تشخیص بده (RD98XS vs HR652).

    خروجی نمونه:
    "RD98XS Digital Repeater | 3.1 Installation Requirements |
     ambient temperature -30°C to +60°C"
    """
    payload = chunk.payload
    text = payload.get("text", "")
    section = payload.get("section", "")
    product = payload.get("product", "")
    level = payload.get("chunk_level", "")

    # فقط برای child ها enrich کن (parent ها خودشون کامل‌ان)
    if level == "child":
        parts = []
        if product:
            parts.append(product)
        if section and section not in text:
            parts.append(section)
        parts.append(text)
        return " | ".join(parts)

    return text


def rerank(question: str,
           chunks: list,
           top_k: int = 5,
           all_queries: list = None) -> list:
    """
    chunk ها رو rerank میکنه.

    اگه all_queries داده بشه:
      - English query رو به عنوان primary reranker input استفاده میکنه
      - این باعث میشه cross-lingual reranking بهتر کار کنه
    """
    if not chunks:
        return []

    model = _get_reranker()

    if all_queries:
        primary_query = _get_english_query(all_queries)
        rerank_queries = [primary_query]

        if question not in rerank_queries:
            rerank_queries.append(question)

        rerank_queries = rerank_queries[:3]
    else:
        rerank_queries = [question]

    chunk_scores = {}

    for query in rerank_queries:
        pairs = [(query, _rerank_text(c)) for c in chunks]
        scores = model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            current_best = chunk_scores.get(chunk.id, float('-inf'))
            chunk_scores[chunk.id] = max(current_best, float(score))

    for chunk in chunks:
        chunk.payload["rerank_score"] = chunk_scores.get(chunk.id, 0.0)

    reranked = sorted(
        chunks,
        key=lambda c: c.payload["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]