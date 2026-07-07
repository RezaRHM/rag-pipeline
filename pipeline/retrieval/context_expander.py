"""
retrieval/context_expander.py
─────────────────────────────────────────────────────────
وقتی یه chunk score پایینی داره (یعنی شاید جواب وسط مرز دو
chunk افتاده باشه)، chunk های مجاورش (قبلی و بعدی) رو هم
اضافه می‌کنه تا context کامل‌تر بشه.

این دقیقاً همون راه‌حلیه که برای مشکل "chunk boundary"
(سناریو ۱۲) طراحی کردیم.
─────────────────────────────────────────────────────────
"""

from qdrant_client.models import Filter, FieldCondition, MatchValue

import config
from db.connection import get_qdrant


def _get_neighbor_chunk(doc_id: str, chunk_index: int):
    """یه chunk خاص رو بر اساس doc_id و chunk_index پیدا می‌کنه"""
    qdrant = get_qdrant()

    results, _ = qdrant.scroll(
        collection_name=config.QDRANT_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id)),
                FieldCondition(key="chunk_index", match=MatchValue(value=chunk_index))
            ]
        ),
        limit=1,
        with_payload=True
    )

    return results[0] if results else None


def expand_context(chunks: list, confidence_threshold: float = 0.70) -> list:
    """
    chunk هایی که score‌شون پایینه رو با neighbor هاشون
    (قبلی و بعدی) تکمیل می‌کنه.

    chunks: لیست از hybrid_search() یا rerank()
    """
    expanded = []
    seen_ids = set()

    for chunk in chunks:
        if chunk.id not in seen_ids:
            expanded.append(chunk)
            seen_ids.add(chunk.id)

        score = chunk.payload.get("rerank_score", chunk.score)

        if score >= confidence_threshold:
            continue

        doc_id = chunk.payload.get("doc_id")
        chunk_index = chunk.payload.get("chunk_index")

        if doc_id is None or chunk_index is None:
            continue

        prev_chunk = _get_neighbor_chunk(doc_id, chunk_index - 1)
        if prev_chunk and prev_chunk.id not in seen_ids:
            expanded.append(prev_chunk)
            seen_ids.add(prev_chunk.id)

        next_chunk = _get_neighbor_chunk(doc_id, chunk_index + 1)
        if next_chunk and next_chunk.id not in seen_ids:
            expanded.append(next_chunk)
            seen_ids.add(next_chunk.id)

    expanded.sort(key=lambda c: (
        c.payload.get("doc_id", ""),
        c.payload.get("chunk_index", 0)
    ))

    return expanded