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

# Over-fetch factor.
#
# RRF produces exact score ties (it is rank-based, not similarity-based).
# When a tie straddles the limit boundary, Qdrant's choice of which tied
# result to return is not deterministic. Measured: at limit=10, positions
# 1-9 were stable across runs while position 10 alternated between two
# chunks that both scored 0.14285715.
#
# Fetching more, applying our own deterministic tie-break, then truncating
# moves the cut inside a region we control.
OVERFETCH = 3


def hybrid_search(question: str,
                  metadata_filter: dict = None,
                  limit: int = 5,
                  broad_limit: int = 60,
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
        limit=limit * OVERFETCH,
        with_payload=True
    )

    points = results.points

    for p in points:
        quality = p.payload.get("quality_score", 1.0)
        p.score = p.score * quality

    # Deterministic tie-break by id.
    #
    # RRF scores are rank-based, not continuous similarity, so exact ties are
    # common. Measured (5 runs, identical query): embeddings deterministic,
    # scores identical, but id ordering varied. Qdrant does not guarantee an
    # order for ties, and Python's stable sort only preserves the input order,
    # which is itself non-deterministic. Without this, the variance propagates
    # into the assembled context and flips the final answer.
    points.sort(key=lambda p: (-float(p.score), str(p.id)))

    return points[:limit]


def multi_query_search(queries: list,
                       metadata_filter: dict = None,
                       limit_per_query: int = 10,
                       final_limit: int = 30,
                       per_query_guarantee: int = 1,
                       level: str = "child") -> list:
    """
    Multi-query search with coverage guarantee.

    از هر query، بهترین `per_query_guarantee` نتیجه یکتا تضمین می‌شه.

    دلیل: score های hybrid_search برای هر query جدا محاسبه می‌شن (RRF)،
    پس مقایسه score مطلق بین query های مختلف بی‌معنیه. بدون این تضمین،
    chunk ای که در یک reformulation خاص رتبه ۲ داره (مثل "operating
    voltage" برای "12-16.8 V DC") با sort سراسری حذف می‌شه.

    باقی ظرفیت با score مطلق پر می‌شه.
    پارامترها برای ablation باز (پیش‌فرض G1/L30).
    """
    seen_ids = set()
    guaranteed = []
    extras = []
    best_rank = {}   # chunk id -> best rank achieved across all queries
    for query in queries:
        try:
            results = hybrid_search(
                query,
                metadata_filter=metadata_filter,
                limit=limit_per_query,
                level=level
            )
        except Exception:
            continue
        for rank, point in enumerate(results, start=1):
            prev = best_rank.get(point.id)
            if prev is None or rank < prev:
                best_rank[point.id] = rank
        taken = 0
        for point in results:
            if point.id in seen_ids:
                continue
            seen_ids.add(point.id)
            if taken < per_query_guarantee:
                guaranteed.append(point)
                taken += 1
            else:
                extras.append(point)

    # A chunk that reached rank 1 in ANY query is strong evidence, flagged for
    # preservation against a rerank false-negative. Uses best rank across
    # queries (not top-1-per-query, which the seen_ids skip could steal from
    # a strong chunk already seen by an earlier, weaker query).
    for p in guaranteed + extras:
        if best_rank.get(p.id, 999) == 1:
            p.payload["_guaranteed_top1"] = True
    extras.sort(key=lambda p: (-float(p.score), str(p.id)))
    return (guaranteed + extras)[:final_limit]


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

def _parent_key(chunk):
    """Dedupe key at parent/section level."""
    return (chunk.payload.get("parent_id")
            or chunk.payload.get("section")
            or str(chunk.id))


def merge_with_preserved(reranked, candidates,
                         rerank_parent_budget=4,
                         final_parent_limit=5,
                         max_preserved=1,
                         detected_product=None):
    """Keep rerank winners, then rescue top-1-per-query hybrid hits that a
    rerank false-negative would otherwise drop.

    A chunk flagged _guaranteed_top1 in multi_query_search was rank 1 for some
    expanded query. Rerank may reorder it but must not silently eliminate it.
    Deterministic and parent-deduped.
    """
    final = []
    seen = set()

    def add(c):
        k = _parent_key(c)
        if k in seen:
            return False
        final.append(c)
        seen.add(k)
        return True

    # 1. rerank winners, up to the rerank budget
    for c in reranked:
        if len(final) >= rerank_parent_budget:
            break
        add(c)

    # 2. preserved candidates: chunks that reached rank 1 in some query but were
    #    NOT among the rerank winners we just added. A chunk already in `final`
    #    needs no rescue; a flagged chunk that rerank pushed below the budget is
    #    exactly what preservation is for. Rank preserved by best rerank
    #    position so the strongest survivor is rescued first, not an arbitrary
    #    id-sorted one (a poorly-expanded query can also flag junk).
    rerank_pos = {}
    for pos, c in enumerate(reranked):
        rerank_pos.setdefault(_parent_key(c), pos)

    preserved = [c for c in candidates
                 if c.payload.get("_guaranteed_top1")
                 and _parent_key(c) not in seen]
    if detected_product:
        preserved = [c for c in preserved
                     if detected_product.lower()
                     in c.payload.get("product", "").lower()]
    # best rerank position first (a flagged chunk rerank ranked 5 beats one it
    # ranked 20); ties broken by id for reproducibility
    preserved.sort(key=lambda c: (rerank_pos.get(_parent_key(c), 999), str(c.id)))

    added = 0
    for c in preserved:
        if len(final) >= final_parent_limit or added >= max_preserved:
            break
        if add(c):
            added += 1

    # 3. fill any remaining room from the rerank list
    for c in reranked:
        if len(final) >= final_parent_limit:
            break
        add(c)

    return final


def add_heading_parents(final_chunks, heading_hits, limit=5, min_score=0.30):
    """Merge parent-level heading hits into the final set, dropping boilerplate.

    Some sections (Packing List, Product Layout) have children that are only
    table rows; the title and prose live in the parent, so a parent-level search
    finds them where child search cannot. When child search returns mostly
    non-content sections (Preface, Disclaimer, ...), a strong heading hit should
    replace that filler rather than queue behind it.

    Product is already scoped by the caller's metadata filter. min_score guards
    against pulling an unrelated section into an otherwise-empty (unsupported)
    result.
    """
    BOILERPLATE = ("preface", "disclaimer", "copyright", "notational",
                   "notation conventions", "icon conventions", "fcc",
                   "regulatory", "radiation", "abbreviations",
                   "instruction conventions", "conformance", "compliance",
                   "operational instructions and training")

    def is_boilerplate(c):
        s = c.payload.get("section", "").lower()
        return any(b in s for b in BOILERPLATE)

    # good heading hits, product already scoped, above threshold, not boilerplate
    good_hits = []
    for h in heading_hits:
        if float(h.score) < min_score:
            continue
        if is_boilerplate(h):
            continue
        good_hits.append(h)

    seen = {_parent_key(c) for c in final_chunks}
    new_hits = [h for h in good_hits if _parent_key(h) not in seen]

    if not new_hits:
        return final_chunks

    # keep content chunks first, then drop trailing boilerplate to make room
    content = [c for c in final_chunks if not is_boilerplate(c)]
    filler = [c for c in final_chunks if is_boilerplate(c)]

    out = list(content)
    for h in new_hits:
        if len(out) >= limit:
            break
        out.append(h)
        seen.add(_parent_key(h))

    # if still room, restore filler (better than empty slots)
    for c in filler:
        if len(out) >= limit:
            break
        out.append(c)

    return out[:limit]
