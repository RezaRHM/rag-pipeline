"""
cache/cache_invalidator.py
─────────────────────────────────────────────────────────
وقتی یه سند جدید آپلود میشه یا یه chunk blacklist میشه،
cache های مرتبط رو invalidate میکنه.
─────────────────────────────────────────────────────────
"""

from db.connection import get_postgres


def invalidate_by_chunk_ids(chunk_ids: list, reason: str = "chunk_updated"):
    """cache هایی که از این chunk ها استفاده کردن رو invalid میکنه"""
    if not chunk_ids:
        return 0

    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        UPDATE query_cache
        SET is_valid = FALSE,
            invalidated_at = NOW(),
            invalidation_reason = %s
        WHERE is_valid = TRUE
          AND retrieved_chunk_ids && %s::varchar[]
    """, (reason, chunk_ids))

    count = cur.rowcount
    pg.commit()
    pg.close()
    return count


def invalidate_by_product(product: str, reason: str = "document_updated"):
    """همه cache های مرتبط با یه محصول رو invalid میکنه"""
    pg = get_postgres()
    cur = pg.cursor()

    cur.execute("""
        UPDATE query_cache
        SET is_valid = FALSE,
            invalidated_at = NOW(),
            invalidation_reason = %s
        WHERE is_valid = TRUE
          AND query ILIKE %s
    """, (reason, f"%{product}%"))

    count = cur.rowcount
    pg.commit()
    pg.close()
    return count


def invalidate_expired():
    """cache های منقضی‌شده رو پاک میکنه"""
    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("DELETE FROM query_cache WHERE expires_at < NOW()")
    count = cur.rowcount
    pg.commit()
    pg.close()
    return count