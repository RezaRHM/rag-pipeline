"""
cache/semantic_cache.py
─────────────────────────────────────────────────────────
اگه سوال جدید از نظر معنایی خیلی شبیه سوال قبلیه
(نه دقیقاً یکی)، همون جواب قبلی رو برمیگردونه.

مثلاً "توان ارسال RD982S چقدره؟" و
"حداکثر قدرت ارسال RD982S چیه؟" یه جواب دارن.
─────────────────────────────────────────────────────────
"""

from db.connection import get_postgres
from retrieval.embedder import embed_dense

SIMILARITY_THRESHOLD = 0.92


def get_semantic_cached_response(question: str) -> dict:
    """
    embedding سوال جدید رو با embedding سوالات cache‌شده
    مقایسه میکنه — اگه خیلی شبیه بود، جواب cache رو برمیگردونه.
    """
    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        SELECT cache_key, query, response
        FROM query_cache
        WHERE is_valid = TRUE
          AND expires_at > NOW()
    """)
    cached_items = cur.fetchall()
    pg.close()

    if not cached_items:
        return {"hit": False}

    new_vec = embed_dense(question)

    best_score = 0.0
    best_item = None

    for item in cached_items:
        cached_vec = embed_dense(item["query"])

        dot = sum(a * b for a, b in zip(new_vec, cached_vec))
        norm_a = sum(a * a for a in new_vec) ** 0.5
        norm_b = sum(b * b for b in cached_vec) ** 0.5
        similarity = dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

        if similarity > best_score:
            best_score = similarity
            best_item = item

    if best_score >= SIMILARITY_THRESHOLD and best_item:
        return {
            "hit": True,
            "answer": best_item["response"],
            "similarity": best_score,
            "matched_query": best_item["query"]
        }

    return {"hit": False}