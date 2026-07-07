"""
cache/exact_cache.py
─────────────────────────────────────────────────────────
اگه دقیقاً همین سوال قبلاً پرسیده شده، جواب آماده رو
برمیگردونه — بدون embedding، retrieval یا LLM call.

کلید cache: hash از سوال normalize‌شده
─────────────────────────────────────────────────────────
"""

import hashlib
import json
from datetime import datetime, timedelta

from db.connection import get_postgres

CACHE_TTL_HOURS = 24


def _make_cache_key(question: str) -> str:
    """سوال رو normalize میکنه و hash میگیره"""
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:64]


def get_cached_response(question: str) -> dict:
    """
    اگه cache hit بود، جواب رو برمیگردونه.
    اگه miss بود، None برمیگردونه.
    """
    cache_key = _make_cache_key(question)
    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        SELECT response, retrieved_chunk_ids, hit_count
        FROM query_cache
        WHERE cache_key = %s
          AND is_valid = TRUE
          AND expires_at > NOW()
    """, (cache_key,))

    row = cur.fetchone()

    if row:
        cur.execute("""
            UPDATE query_cache
            SET hit_count = hit_count + 1,
                last_hit_at = NOW()
            WHERE cache_key = %s
        """, (cache_key,))
        pg.commit()
        pg.close()

        return {
            "hit": True,
            "answer": row["response"],
            "chunk_ids": row["retrieved_chunk_ids"]
        }

    pg.close()
    return {"hit": False}


def cache_response(question: str, answer: str, chunk_ids: list):
    """جواب جدید رو توی cache ذخیره میکنه"""
    cache_key = _make_cache_key(question)
    expires_at = datetime.now() + timedelta(hours=CACHE_TTL_HOURS)

    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO query_cache
            (cache_key, query, response, retrieved_chunk_ids,
             hit_count, created_at, last_hit_at, expires_at, is_valid)
        VALUES (%s, %s, %s, %s, 1, NOW(), NOW(), %s, TRUE)
        ON CONFLICT (cache_key) DO UPDATE
            SET response = EXCLUDED.response,
                retrieved_chunk_ids = EXCLUDED.retrieved_chunk_ids,
                hit_count = query_cache.hit_count + 1,
                last_hit_at = NOW(),
                expires_at = EXCLUDED.expires_at,
                is_valid = TRUE
    """, (cache_key, question, answer, chunk_ids, expires_at))
    pg.commit()
    pg.close()