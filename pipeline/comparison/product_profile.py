"""Product profiles built from real section headings, for the no-topic
comparison path ("compare X and Y" with no aspect given).

A profile is the list of documented top-level topics in a product's manual,
derived from its non-boilerplate section headings. Catalogs (doc_type !=
'manual') are excluded: their headings are marketing slogans, not topics.
"""
import re
from db.connection import get_qdrant
import config
from retrieval.retriever import _is_boilerplate

_PROFILE_CACHE = None


def _is_top_level(section: str) -> bool:
    """Top-level heading: 'N. Title' (single number) or a short unnumbered
    title. Excludes deep subsections (N.M...) and arrow-joined fragments."""
    s = section.strip()
    if re.match(r'^\d+\.?\s+\S', s) and not re.match(r'^\d+\.\d', s):
        return True
    if not re.match(r'^\d', s) and '→' not in s and len(s) < 40:
        return True
    return False


def _clean_topic(section: str) -> str:
    """Strip a leading 'N. ' number so the topic reads as a plain label."""
    return re.sub(r'^\d+\.?\s+', '', section.strip())


def _looks_like_doc_title(section: str) -> bool:
    """A heading that is really the manual's title, not a section."""
    low = section.lower()
    return "user manual" in low or "owner's manual" in low or "owners manual" in low


def build_product_profiles() -> dict:
    """product -> ordered list of documented top-level topics. Cached."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE is not None:
        return _PROFILE_CACHE

    q = get_qdrant()
    pts, _ = q.scroll(
        collection_name=config.QDRANT_COLLECTION,
        limit=5000, with_payload=True,
    )

    # gather top-level, non-boilerplate headings per manual product
    raw = {}
    for p in pts:
        pl = p.payload
        if pl.get("chunk_level") != "parent":
            continue
        if pl.get("doc_type") != "manual":
            continue  # exclude catalogs (marketing headings)
        section = pl.get("section", "")
        if _is_boilerplate(p):
            continue
        if not _is_top_level(section):
            continue
        if _looks_like_doc_title(section):
            continue
        prod = pl.get("product", "?")
        idx = pl.get("chunk_index", 999)
        raw.setdefault(prod, []).append((idx, _clean_topic(section)))

    # dedupe by topic label, keep first-seen order (by chunk index)
    profiles = {}
    for prod, items in raw.items():
        items.sort()
        seen = set()
        topics = []
        for _, topic in items:
            key = topic.lower()
            if key in seen:
                continue
            seen.add(key)
            topics.append(topic)
        profiles[prod] = topics

    _PROFILE_CACHE = profiles
    return profiles


# stopwords left after product names and comparison connectives are stripped;
# if only these remain, the user gave no real topic
_TOPIC_STOPWORDS = {
    "compare", "comparison", "the", "and", "or", "a", "an", "of", "to",
    "between", "with", "for", "me", "please", "what", "whats", "what's",
    "is", "are", "do", "does", "which", "better", "difference", "differences",
    "these", "those", "two", "both", "repeaters", "repeater", "models",
    "model", "products", "product", "?", "vs",
}


def has_meaningful_topic(generic_q: str) -> bool:
    """True if a real comparison topic remains after stripping product names
    and connective words. 'compare the and' -> False; 'alarm codes' -> True."""
    words = re.findall(r"[a-zA-Z]+", generic_q.lower())
    real = [w for w in words if w not in _TOPIC_STOPWORDS]
    return len(real) > 0


def build_no_topic_response(mentioned: list) -> dict:
    """No aspect given: show each product's documented topics and ask which
    aspect to compare. Aspect suggestions are drawn from the products' own
    profiles, not a hardcoded list."""
    profiles = build_product_profiles()
    lines = [
        "I can compare these, but \"better\" or \"different\" depends on the "
        "aspect. Here is what each manual documents:",
        "",
    ]
    all_topics = []
    for prod in mentioned:
        topics = profiles.get(prod)
        if topics:
            lines.append("%s documents: %s." % (prod, ", ".join(topics)))
            all_topics.extend(topics)
        else:
            lines.append("%s: no documented topic profile available." % prod)
    # suggested aspects = topics common to (or present across) the products
    seen = []
    for t in all_topics:
        if t not in seen:
            seen.append(t)
    lines.append("")
    lines.append(
        "Which aspect should I compare: %s?" % ", ".join(seen[:8])
    )
    return {
        "answer": "\n".join(lines),
        "products_compared": mentioned,
        "status": "needs_topic",
        "method": "product_profile",
        "catalog_used": False,
    }
