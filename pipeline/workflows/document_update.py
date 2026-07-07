"""
workflows/document_update.py
─────────────────────────────────────────────────────────
وقتی یه نسخه جدید از سند میاد، این workflow:
  ۱. سند قدیمی رو archive میکنه
  ۲. سند جدید رو ingest میکنه
  ۳. cache های مرتبط رو invalidate میکنه
  ۴. تغییرات رو لاگ میکنه
─────────────────────────────────────────────────────────
"""

from pathlib import Path
from datetime import datetime

from db.connection import get_postgres
from workflows.ingest import ingest_document
from cache.cache_invalidator import invalidate_by_product


def update_document(new_pdf_path: Path,
                    old_doc_id: str = None,
                    updated_by: str = "system") -> dict:
    """
    یه سند موجود رو با نسخه جدید جایگزین میکنه.

    new_pdf_path: مسیر فایل PDF جدید
    old_doc_id: doc_id نسخه قبلی (اگه None بود، خودش پیدا میکنه)
    """
    pg = get_postgres()
    cur = pg.cursor()

    # پیدا کردن doc قدیمی بر اساس filename
    if not old_doc_id:
        cur.execute("""
            SELECT doc_id, product, version
            FROM documents
            WHERE filename = %s AND is_latest = TRUE
        """, (new_pdf_path.name,))
        old_doc = cur.fetchone()
        if old_doc:
            old_doc_id = old_doc["doc_id"]
            product = old_doc["product"]
            old_version = old_doc["version"]
        else:
            product = "unknown"
            old_version = "unknown"
    else:
        cur.execute(
            "SELECT product, version FROM documents WHERE doc_id = %s",
            (old_doc_id,)
        )
        old_doc = cur.fetchone()
        product = old_doc["product"] if old_doc else "unknown"
        old_version = old_doc["version"] if old_doc else "unknown"

    # archive کردن نسخه قدیمی
    if old_doc_id:
        cur.execute("""
            UPDATE documents SET is_latest = FALSE
            WHERE doc_id = %s
        """, (old_doc_id,))
        pg.commit()

    pg.close()

    # ingest کردن نسخه جدید
    result = ingest_document(new_pdf_path)

    # invalidate کردن cache های مرتبط
    invalidated = invalidate_by_product(product, reason="document_updated")

    # لاگ کردن update
    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("""
        INSERT INTO document_updates
            (old_doc_id, new_doc_id, product, old_version,
             new_version, updated_by, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        old_doc_id, result.get("doc_id"), product,
        old_version, result.get("version", "unknown"),
        updated_by, datetime.now()
    ))
    pg.commit()
    pg.close()

    return {
        "status": "updated",
        "old_doc_id": old_doc_id,
        "new_doc_id": result.get("doc_id"),
        "product": product,
        "cache_invalidated": invalidated
    }