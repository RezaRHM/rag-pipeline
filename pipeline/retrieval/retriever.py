"""
retrieval/retriever.py
─────────────────────────────────────────────────────────
Hybrid search: dense (BGE-M3) + sparse (BM25) + RRF fusion.

نسخه Hierarchical:
  - جستجو فقط روی child chunks (chunk_level="child") — precision بالا
  - بعد از rerank، parent ها fetch میشن — context کامل
─────────────────────────────────────────────────────────
"""

from qdrant_client.models import (
    Prefetch, FusionQuery, Fusion, Filter,
    FieldCondition, MatchValue, MatchText
)

import config
from db.connection import get_qdrant
from retrieval.embedder import embed_dense, embed_sparse


def _extract_product_key(product_name: str) -> str:
    """
    کلیدواژه‌ی اصلی و پایدار محصول رو استخراج می‌کنه —
    مقاوم به واریاسیون‌های metadata extraction.

    "HR652 Digital Repeater" → "HR652"
    "RD98XS Digital Repeater" → "RD98XS"
    "HP7 SERIES"              → "HP7"

    این باعث میشه فیلتر product حتی وقتی نسخه‌ی کامل نام
    متفاوت باشه، درست کار کنه.
    """
    import re
    # الگوهای مدل محصول: حروف + اعداد در ابتدا
    match = re.match(r'([A-Z]+\d+[A-Z]*)', product_name.strip(), re.IGNORECASE)
    if match:
        return match.group(1)
    # اگه الگو پیدا نشد، اولین کلمه
    return product_name.split()[0] if product_name.split() else product_name

def hybrid_search(question: str,
                  metadata_filter: dict = None,
                  limit: int = 5,
                  broad_limit: int = 20,
                  level: str = "child") -> list:
    """
    سوال رو با dense + sparse جستجو می‌کنه و با RRF ترکیب می‌کنه.

    level: "child" (پیش‌فرض) فقط child chunks رو جستجو میکنه.
           "parent" یا None برای جستجوی بدون فیلتر سطح.
    """
    qdrant = get_qdrant()

    dense_vec = embed_dense(question)
    sparse_vec = embed_sparse(question)

    must_conditions = [
        FieldCondition(key="blacklisted", match=MatchValue(value=False))
    ]

    # فقط روی سطح مشخص‌شده جستجو کن (hierarchical retrieval)
    if level:
        must_conditions.append(
            FieldCondition(key="chunk_level", match=MatchValue(value=level))
        )

    if metadata_filter:
        for key, value in metadata_filter.items():
            if key == "product":
                # partial match برای product — مقاوم به non-determinism
                # در metadata extraction (مثلاً "HR652" vs "HR652 Digital Repeater")
                # کلیدواژه‌ی اصلی محصول رو استخراج و با MatchText جستجو کن
                product_key = _extract_product_key(value)
                must_conditions.append(
                    FieldCondition(key="product", match=MatchText(text=product_key))
                )
            else:
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
    
    qdrant_filter = Filter(must=must_conditions)

    results = qdrant.query_points(
        collection_name=config.QDRANT_COLLECTION,
        prefetch=[
            Prefetch(
                query=dense_vec,
                using="dense",
                filter=qdrant_filter,
                limit=broad_limit
            ),
            Prefetch(
                query=sparse_vec,
                using="sparse",
                filter=qdrant_filter,
                limit=broad_limit
            )
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True
    )

    points = results.points

    for p in points:
        quality = p.payload.get("quality_score", 1.0)
        p.score = p.score * quality

    points.sort(key=lambda p: p.score, reverse=True)

    return points


def multi_query_search(queries: list,
                       metadata_filter: dict = None,
                       limit_per_query: int = 10,
                       final_limit: int = 15,
                       level: str = "child") -> list:
    """
    چند query رو جستجو میکنه، union و dedupe میکنه.
    پیش‌فرض روی child chunks کار میکنه.
    """
    seen_ids = set()
    all_points = []

    for query in queries:
        try:
            results = hybrid_search(
                query,
                metadata_filter=metadata_filter,
                limit=limit_per_query,
                level=level
            )
            for point in results:
                if point.id not in seen_ids:
                    seen_ids.add(point.id)
                    all_points.append(point)
        except Exception:
            continue

    all_points.sort(key=lambda p: p.score, reverse=True)

    return all_points[:final_limit]


def fetch_parents(child_chunks: list) -> list:
    """
    برای لیستی از child chunks، parent هاشون رو از Qdrant می‌گیره.

    - هر parent فقط یک بار برگردونده میشه (dedupe)
    - ترتیب بر اساس بهترین rerank_score بین children یک parent
    - rerank_score از بهترین child به parent منتقل میشه
    - اگه child ای parent_id نداشت (سازگاری با داده قدیمی)، خودش نگه داشته میشه
    """
    qdrant = get_qdrant()

    # بهترین score هر parent رو از children جمع کن
    parent_best_score = {}
    orphan_chunks = []

    for c in child_chunks:
        parent_id = c.payload.get("parent_id")
        score = c.payload.get("rerank_score", c.score if hasattr(c, "score") else 0)

        if not parent_id:
            orphan_chunks.append(c)
            continue

        if parent_id not in parent_best_score or score > parent_best_score[parent_id]:
            parent_best_score[parent_id] = score

    if not parent_best_score:
        return orphan_chunks

    # parent ها رو با chunk_id (که parent_id ـه) از Qdrant بگیر
    parent_ids = list(parent_best_score.keys())

    scroll_filter = Filter(
        must=[
            FieldCondition(
                key="chunk_level",
                match=MatchValue(value="parent")
            )
        ]
    )

    # همه parent ها رو scroll کن و اونایی که میخوایم فیلتر کن
    fetched_parents = []
    offset = None
    wanted = set(parent_ids)

    while wanted:
        batch, offset = qdrant.scroll(
            collection_name=config.QDRANT_COLLECTION,
            scroll_filter=scroll_filter,
            limit=256,
            offset=offset,
            with_payload=True
        )
        if not batch:
            break

        for point in batch:
            pid = point.payload.get("chunk_id")
            if pid in wanted:
                # score بهترین child رو به parent منتقل کن
                point.payload["rerank_score"] = parent_best_score[pid]
                fetched_parents.append(point)
                wanted.discard(pid)

        if offset is None:
            break

    # اگه بعضی parent ها پیدا نشدن، آنها رو نادیده بگیر
    # مرتب‌سازی بر اساس score
    fetched_parents.sort(
        key=lambda p: p.payload.get("rerank_score", 0),
        reverse=True
    )

    # orphan ها (بدون parent) رو هم اضافه کن
    result = fetched_parents + orphan_chunks
    return result


def filter_repeater_accessories(chunks: list) -> list:
    """
    برای سوالات مربوط به repeater accessories، chunk هایی که
    مربوط به portable radio هستن رو کنار میذاره.
    """
    PORTABLE_SIGNALS = ["earpiece", "belt clip", "palm microphone",
                        "wireless remote speaker", "portable", "hp5",
                        "hp6", "hp7", "pocket", "lanyard"]
    REPEATER_SIGNALS = ["duplexer", "repeater", "feeder", "rack",
                        "external power supply", "antenna uhf"]

    filtered = []
    for c in chunks:
        text_lower = c.payload.get("text", "").lower()

        has_repeater = any(sig in text_lower for sig in REPEATER_SIGNALS)
        has_portable = any(sig in text_lower for sig in PORTABLE_SIGNALS)

        if has_portable and not has_repeater:
            continue

        filtered.append(c)

    return filtered if filtered else chunks