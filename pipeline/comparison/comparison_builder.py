"""
comparison/comparison_builder.py
─────────────────────────────────────────────────────────
Product comparison with three routes:

1. aspect detected + valid structured extraction
   → structured decomposition + deterministic Python table
2. aspect detected + structured extraction fails
   → free-form decomposition
3. aspect not detected
   → free-form decomposition

Catalog-aware reference layer:
- retrieved separately from product evidence
- never treated as product evidence by default
- product-specific catalog claims require explicit product mention
- general solution-level claims remain general reference only
- no merged single-pass comparison
─────────────────────────────────────────────────────────
"""

import re
import requests

import config

from comparison.extractor import extract_product_facts, extract_structured
from comparison.product_profile import (
    has_meaningful_topic, build_no_topic_response)
from comparison.schemas import (
    get_retrieval_queries,
)
from prompts.prompts import BASE_SYSTEM_PROMPT
from retrieval.context_expander import expand_context
from retrieval.embedder import embed_dense
from retrieval.reranker import rerank
from retrieval.retriever import (
    fetch_parents,
    hybrid_search,
    merge_with_preserved,
    multi_query_search,
    _is_boilerplate,
    _parent_key as _retriever_parent_key,
)


_CATALOG_LABEL_CACHE = None


def _catalog_product_label():
    """The catalog document's product label, from the registry (doc_type),
    not hardcoded. Falls back to the historical label only if the registry
    has no catalog-typed document."""
    global _CATALOG_LABEL_CACHE
    if _CATALOG_LABEL_CACHE is None:
        try:
            from db.connection import get_postgres
            pg = get_postgres()
            cur = pg.cursor()
            cur.execute(
                "SELECT DISTINCT product FROM documents "
                "WHERE doc_type = 'catalog' LIMIT 1"
            )
            row = cur.fetchone()
            pg.close()
            _CATALOG_LABEL_CACHE = row["product"] if row else "HP7 SERIES"
        except Exception:
            _CATALOG_LABEL_CACHE = "HP7 SERIES"
    return _CATALOG_LABEL_CACHE

KNOWN_PRODUCT_KEYS = [
    "RD98XS",
    "RD99XS",
    "RD982S",
    "HR652",
    "HR106X",
    "HP7",
    "HP5",
    "HP6",
    "PD9",
    "HM",
]


# ─────────────────────────────────────────────────────────
# Product detection
# ─────────────────────────────────────────────────────────

def _mentioned_products(
    question: str,
    all_products: list,
) -> list:
    q_upper = question.upper().replace(" ", "")
    matched = []

    for product in all_products:
        match = re.match(
            r"([A-Z]+\d+[A-Z]*)",
            product.strip(),
            re.IGNORECASE,
        )

        if not match:
            continue

        key = match.group(1).upper()

        # Exact key substring only. The former "X acts as a digit wildcard"
        # fallback (RD98XS -> RD98\dS) matched RD982S and confidently
        # answered about the wrong product when a user typed a near-name like
        # "RD982s" (meaning RD982i-S). A near-name should miss and fall
        # through to the unsupported-product gate, never silently bind to a
        # different model — X is a literal here (RD98XS, HR106X), not a
        # wildcard.
        if key in q_upper:
            matched.append(product)

    return matched


def _product_key(product: str) -> str:
    """
    Extract canonical model key from a DB product label.

    Examples:
      HR652 Digital Repeater → HR652
      RD98XS Digital Repeater → RD98XS
    """
    match = re.match(
        r"([A-Z]+\d+[A-Z]*)",
        product.strip(),
        re.IGNORECASE,
    )

    if not match:
        return product.upper().strip()

    return match.group(1).upper()


# ─────────────────────────────────────────────────────────
# Generic retrieval
# ─────────────────────────────────────────────────────────

def _generic_query(
    search_question: str,
    products: list = None,
) -> str:
    """Strip product references so retrieval isn't biased toward one model.

    Removes the actual product names and their model keys (from the given
    product list) rather than guessing with fixed patterns. The old fixed
    patterns broke on new names: "HR106X" left an "X", "RD982i-S" left an
    "i-S", turning the query into junk like "compare the X and i-S".
    """
    generic = search_question
    for product in (products or []):
        generic = re.sub(re.escape(product), "", generic, flags=re.IGNORECASE)
        key = _product_key(product)
        # remove the key plus any model suffix left attached (e.g. the "-S" in
        # "RD982i-S", which _product_key drops). Bounded to a short suffix so it
        # can't eat the real topic words that follow.
        generic = re.sub(
            re.escape(key) + r"[-\w]{0,4}", "", generic, flags=re.IGNORECASE
        )
    for pattern in [
        r"\bvs\b",
        r"compared?\s+to",
        r"difference\s+between",
        r"\bboth\b",
    ]:
        generic = re.sub(pattern, "", generic, flags=re.IGNORECASE)
    return " ".join(generic.split())


def _heading_candidates(
    queries: list,
    metadata_filter: dict,
    per_query_keep: int = 2,
    max_heading: int = 2,
    garbage_floor: float = 0.20,
) -> list:
    """Parent-level heading hits fused across all query reformulations.

    Boilerplate is dropped per query BEFORE fusion. Fusing first lets
    sections that weakly match every reformulation (Preface, FCC statements,
    Disclaimer, ...) drown the section that strongly matches one specific
    reformulation - which is exactly the hit this arm exists to catch
    (table-only sections such as Packing List, found via a synonym-expanded
    query, not via the original phrasing).
    """
    best = {}
    for q in queries:
        kept = 0
        for rank, hit in enumerate(hybrid_search(
                q, metadata_filter=metadata_filter,
                limit=6, level="parent")):
            if float(hit.score) < garbage_floor:
                continue
            if _is_boilerplate(hit):
                continue
            key = _retriever_parent_key(hit)
            if key not in best or rank < best[key][0]:
                best[key] = (rank, hit)
            kept += 1
            if kept >= per_query_keep:
                break
    fused = sorted(best.values(), key=lambda pair: pair[0])
    return [hit for _, hit in fused][:max_heading]


def _retrieve_product_chunks(
    product: str,
    queries: list,
    child_slots: int = 2,
    heading_slots: int = 2,
) -> list:
    """Free-form evidence retrieval, unified with the main pipeline path.

    Previously a bare single-query hybrid search on a product-stripped query;
    now the same primitives process_query uses: multi-query child search over
    all expansions, context expansion, rerank with candidate preservation,
    and a multi-query heading-parent arm. Heading hits get reserved slots so
    table-only sections cannot be crowded out by generic content parents.
    """
    metadata_filter = {"product": product}

    candidates = multi_query_search(
        queries,
        metadata_filter=metadata_filter,
        limit_per_query=10,
        final_limit=30,
        level="child",
    )
    if not candidates:
        return []

    expanded = expand_context(candidates, confidence_threshold=0.70)
    reranked = rerank(
        queries[0],
        expanded,
        top_k=max(child_slots * 3, 6),
        all_queries=queries,
    )
    merged = merge_with_preserved(
        reranked,
        expanded,
        rerank_parent_budget=child_slots,
        final_parent_limit=child_slots,
        max_preserved=1,
        detected_product=product,
    )
    finals = fetch_parents(merged)[:child_slots]

    seen = {_retriever_parent_key(c) for c in finals}
    for hit in _heading_candidates(
            queries, metadata_filter, max_heading=heading_slots):
        if _retriever_parent_key(hit) in seen:
            continue
        if len(finals) >= child_slots + heading_slots:
            break
        finals.append(hit)
        seen.add(_retriever_parent_key(hit))

    return finals


def _parent_key(parent):
    """
    Stable parent dedupe key with defensive fallbacks.
    """
    payload = parent.payload

    return (
        payload.get("chunk_id")
        or payload.get("parent_id")
        or getattr(parent, "id", None)
        or (
            payload.get("product"),
            payload.get("section"),
            payload.get("text"),
        )
    )


# ─────────────────────────────────────────────────────────
# Schema-aware product retrieval
# ─────────────────────────────────────────────────────────

def _retrieve_schema_aware(
    product: str,
    aspect: str,
    question: str,
    top_k_per_query: int = 3,
    final_limit: int = 12,
) -> list:
    """
    Schema-aware multi-query retrieval with coverage preservation.

    Each targeted query retrieves independently.
    Unique best parents are preserved first.
    Additional unique parents fill remaining capacity.
    """
    queries = get_retrieval_queries(
        aspect,
        question,
    )

    if not queries:
        return []

    guaranteed = []
    extras = []
    seen = set()

    for query in queries:
        children = hybrid_search(
            query,
            metadata_filter={
                "product": product,
            },
            limit=6,
            level="child",
        )

        if not children:
            continue

        reranked = rerank(
            query,
            children,
            top_k=min(
                top_k_per_query,
                len(children),
            ),
        )

        parents = fetch_parents(
            reranked
        )

        best_taken = False

        for parent in parents:
            key = _parent_key(
                parent
            )

            if key in seen:
                best_taken = True
                continue

            seen.add(key)

            if not best_taken:
                guaranteed.append(
                    parent
                )
                best_taken = True

            else:
                extras.append(
                    parent
                )

    result = (
        guaranteed
        + extras
    )

    return result[:final_limit]


# ─────────────────────────────────────────────────────────
# Catalog intent detection
# ─────────────────────────────────────────────────────────

def _needs_catalog_reference(
    question: str,
    aspect: str,
) -> bool:
    """
    Catalog layer is useful for:
    - suitability / compact / cabinet / indoor deployment comparisons
    - feature comparisons where general solution-level material may exist
    """
    q = question.lower()

    deployment_terms = [
        "compact",
        "indoor",
        "cabinet",
        "rack",
        "suitable",
        "suitability",
        "deployment",
        "deploy",
        "2u",
        "space",
    ]

    if aspect == "features":
        return True

    return any(
        term in q
        for term in deployment_terms
    )


def _catalog_queries(
    question: str,
    aspect: str,
) -> list:
    q = question.lower()

    if aspect == "features":
        return [
            "individual call group call broadcast call PSTN call",
            "DMR professional solution supported functions",
        ]

    queries = []

    if any(
        term in q
        for term in [
            "compact",
            "cabinet",
            "rack",
            "indoor",
            "deployment",
            "suitable",
            "suitability",
            "2u",
            "space",
        ]
    ):
        queries.extend([
            "compact repeater cabinet installation",
            "2U compact repeater deployment",
            "indoor coverage compact repeater",
        ])

    return queries


# ─────────────────────────────────────────────────────────
# Catalog retrieval
# ─────────────────────────────────────────────────────────

def _retrieve_catalog_reference(
    question: str,
    aspect: str,
    top_k_per_query: int = 4,
    final_limit: int = 8,
) -> list:
    """
    Retrieve catalog reference evidence separately.

    Important:
    catalog metadata may be broad/misleading, so product attribution
    must later be validated from text content itself.
    """
    queries = _catalog_queries(
        question,
        aspect,
    )

    if not queries:
        return []

    seen = set()
    parents_out = []

    for query in queries:
        children = hybrid_search(
            query,
            metadata_filter={
                "product": _catalog_product_label(),
            },
            limit=10,
            level="child",
        )

        if not children:
            continue

        reranked = rerank(
            query,
            children,
            top_k=min(
                top_k_per_query,
                len(children),
            ),
        )

        parents = fetch_parents(
            reranked
        )

        for parent in parents:
            key = _parent_key(
                parent
            )

            if key in seen:
                continue

            seen.add(key)
            parents_out.append(
                parent
            )

    return parents_out[:final_limit]


# ─────────────────────────────────────────────────────────
# Catalog text filtering
# ─────────────────────────────────────────────────────────

def _filter_catalog_for_products(
    chunks: list,
    mentioned_products: list,
) -> dict:
    """
    Separate catalog text into:

    1. product_specific:
       text blocks explicitly mentioning one of the compared products

    2. general:
       catalog text that does not explicitly tie a claim to a compared product

    Text mentioning unrelated known product models is excluded.
    """
    compared_keys = {
        _product_key(product)
        for product in mentioned_products
    }

    product_specific = {
        product: []
        for product in mentioned_products
    }

    general = []

    for chunk in chunks:
        text = chunk.payload.get(
            "text",
            "",
        )

        section = chunk.payload.get(
            "section",
            "",
        )

        upper = text.upper()

        mentioned_known = {
            key
            for key in KNOWN_PRODUCT_KEYS
            if key in upper
        }

        unrelated = (
            mentioned_known
            - compared_keys
        )

        if unrelated:
            continue

        matched_compared = []

        for product in mentioned_products:
            key = _product_key(
                product
            )

            if key in upper:
                matched_compared.append(
                    product
                )

        entry = {
            "section": section,
            "text": text,
        }

        if matched_compared:
            for product in matched_compared:
                product_specific[
                    product
                ].append(entry)

        else:
            general.append(entry)

    return {
        "product_specific": product_specific,
        "general": general,
    }


# ─────────────────────────────────────────────────────────
# Catalog note generation
# ─────────────────────────────────────────────────────────

def _contains_any(
    text: str,
    terms: list,
) -> bool:
    lowered = text.lower()

    return any(
        term.lower() in lowered
        for term in terms
    )


def _deployment_catalog_note(
    catalog_data: dict,
    mentioned_products: list,
) -> str:
    """
    Build deterministic deployment/suitability note.

    No LLM synthesis here.
    """
    lines = []

    product_specific = catalog_data.get(
        "product_specific",
        {},
    )

    compact_terms = [
        "compact",
        "2u",
        "cabinet",
        "small size",
        "slim",
    ]

    stronger_products = []

    for product in mentioned_products:
        entries = product_specific.get(
            product,
            [],
        )

        matching_entries = [
            entry
            for entry in entries
            if _contains_any(
                entry.get(
                    "text",
                    "",
                ),
                compact_terms,
            )
        ]

        if matching_entries:
            stronger_products.append(
                product
            )

    if stronger_products:
        names = ", ".join(
            stronger_products
        )

        lines.append(
            f"The retrieved catalog evidence explicitly provides "
            f"compact/cabinet-related deployment evidence for {names}."
        )

    for product in mentioned_products:
        if product not in stronger_products:
            lines.append(
                f"No equivalent product-specific compact/cabinet "
                f"catalog evidence was found for {product}."
            )

    if stronger_products:
        if len(stronger_products) == 1:
            lines.append(
                f"{stronger_products[0]} has stronger documented evidence "
                f"for compact or cabinet-oriented installation in the "
                f"retrieved materials."
            )

    lines.append(
        "No Netherlands-specific installation requirement was established "
        "from the retrieved evidence."
    )

    return "\n".join(
        lines
    )


def _feature_catalog_note(
    catalog_data: dict,
    mentioned_products: list,
) -> str:
    """
    Explain general solution-level feature evidence without promoting it
    to product-level support.
    """
    general_entries = catalog_data.get(
        "general",
        [],
    )

    product_specific = catalog_data.get(
        "product_specific",
        {},
    )

    feature_terms = [
        "individual call",
        "group call",
        "broadcast call",
        "pstn call",
    ]

    general_text = " ".join(
        entry.get(
            "text",
            "",
        )
        for entry in general_entries
    )

    general_feature_reference = any(
        term in general_text.lower()
        for term in feature_terms
    )

    if not general_feature_reference:
        return ""

    explicitly_linked = []

    for product in mentioned_products:
        entries = product_specific.get(
            product,
            [],
        )

        combined = " ".join(
            entry.get(
                "text",
                "",
            )
            for entry in entries
        ).lower()

        if any(
            term in combined
            for term in feature_terms
        ):
            explicitly_linked.append(
                product
            )

    if explicitly_linked:
        names = ", ".join(
            explicitly_linked
        )

        return (
            "The retrieved catalog contains feature-related text explicitly "
            f"mentioning {names}. Product-level support should still be "
            "interpreted only from the exact retrieved text."
        )

    return (
        "The retrieved catalog lists these call types at a general DMR "
        "solution level, but the retrieved catalog evidence does not "
        "explicitly associate them with the compared products. Therefore, "
        "equal support cannot be concluded."
    )


def _build_catalog_note(
    catalog_data: dict,
    mentioned_products: list,
    question: str,
    aspect: str,
) -> str:
    if aspect == "features":
        return _feature_catalog_note(
            catalog_data,
            mentioned_products,
        )

    return _deployment_catalog_note(
        catalog_data,
        mentioned_products,
    )


# ─────────────────────────────────────────────────────────
# Structured quality gate
# ─────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────
# Free-form decomposition fallback
# ─────────────────────────────────────────────────────────

def _evidence_block(chunks: list, char_budget: int = 6000) -> str:
    """Verbatim, section-labelled excerpts for one product.

    Extractive by design: the compare model must see the original wording.
    The earlier abstractive per-product summary was an information
    bottleneck — it dropped facts (packing-list items, named alarms) that
    the final comparison could never recover. Chunks arrive already ranked,
    so the budget cuts the least relevant section instead of rewriting
    content.
    """
    parts = []
    used = 0
    for chunk in chunks:
        section = chunk.payload.get("section", "?")
        text = chunk.payload.get("text", "")
        piece = f"[{section}]\n{text}"
        if used + len(piece) > char_budget:
            remaining = char_budget - used
            if remaining > 400:  # only keep a partial section if meaningful
                parts.append(piece[:remaining] + "\n[... section truncated]")
            break
        parts.append(piece)
        used += len(piece)
    return "\n\n".join(parts)


def _freeform_comparison(
    mentioned: list,
    question: str,
    queries: list,
    chunks_by_product: dict = None,
) -> dict:
    # No intermediate abstractive summary: the compare model reads the
    # retrieved sections verbatim. Facts survive because nothing rewrites
    # them between retrieval and comparison.
    evidence = {}

    for product in mentioned:
        if chunks_by_product is not None:
            chunks = chunks_by_product.get(product) or []
        else:
            chunks = _retrieve_product_chunks(
                product,
                queries,
            )

        if chunks:
            evidence[product] = _evidence_block(chunks)
        else:
            evidence[product] = (
                "[No relevant context retrieved "
                f"for {product}]"
            )

    evidence_block = "\n\n".join([
        (
            f"{'=' * 40}\n"
            f"{product} documentation excerpts:\n"
            f"{'=' * 40}\n"
            f"{text}"
        )
        for product, text
        in evidence.items()
    ])

    compare_prompt = (
        BASE_SYSTEM_PROMPT
        + f"""

Compare the products based ONLY on these per-product documentation excerpts.
Each excerpt is quoted verbatim from that product's own manual, under its
section name in [brackets].

CRITICAL:
- Keep each product's details strictly separate.
- If a detail appears in only one product's excerpts, do NOT attribute it
  to the other.
- If something is "not documented" for a product, say exactly:
  "not documented in the retrieved context".
- Never rephrase missing documentation as "not present", "absent",
  "unsupported", or "the product does not have it".
- Do not use "likely", "probably", or "can be inferred".
- Preserve exact values, item names, and code identifiers from the excerpts.

Structure your response in exactly this order:
1. For each product, list the facts from its own excerpts that are relevant
   to the question, quoting exact item names, values, and codes with their
   [section].
2. Then answer the question directly, based only on the facts you listed.

{evidence_block}

Question: {question}

Comparison:"""
    )

    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": (
                f"Bearer "
                f"{config.LITELLM_API_KEY}"
            ),
        },
        json={
            "model": config.DEFAULT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": compare_prompt,
                }
            ],
            "temperature": 0,
        },
        timeout=config.LLM_TIMEOUT,
    )

    response.raise_for_status()

    answer = (
        response
        .json()["choices"][0]["message"]["content"]
    )

    return {
        "answer": answer,
        "products_compared": mentioned,
        "status": "compared",
        "method": "freeform",
        "catalog_used": False,
    }


# ─────────────────────────────────────────────────────────
# Generic fact alignment + deterministic rendering
# ─────────────────────────────────────────────────────────

NOT_DOCUMENTED = "not documented in the retrieved context"


def _label_tokens(label: str) -> set:
    return set(re.sub(r"[^a-z0-9 ]+", " ", label.lower()).split())


def _labels_align(label_a: str, label_b: str) -> bool:
    """Same comparison criterion? Lexical tier first, then embeddings.

    Tier 1: token Jaccard on normalized labels (catches "packed item" vs
    "packed items"). Tier 2: dense-embedding cosine via the same BGE-M3
    model retrieval already uses — no wordlists, no new models. Any
    embedding failure degrades to "not aligned", which only means the fact
    is listed per product instead of side by side.
    """
    ta, tb = _label_tokens(label_a), _label_tokens(label_b)
    if not ta or not tb:
        return False
    jaccard = len(ta & tb) / len(ta | tb)
    if jaccard >= 0.5:
        return True
    try:
        va = embed_dense(label_a)
        vb = embed_dense(label_b)
        dot = sum(x * y for x, y in zip(va, vb))
        na = sum(x * x for x in va) ** 0.5
        nb = sum(x * x for x in vb) ** 0.5
        if na and nb:
            return dot / (na * nb) >= 0.78
    except Exception:
        pass
    return False


def _question_names_a_fact(question: str, facts_by_product: dict) -> bool:
    """Signal for choosing deterministic rendering over free-form compare.

    True when some verified fact's VALUE appears verbatim (normalized) in
    the question — i.e. the user already named the specific criterion
    ("Phillips screwdriver", "IP68") and extraction verified per product
    whether it is documented. Broad questions ("compare the alarm code
    systems") never satisfy this, and go to the free-form compare, which is
    empirically better at exhaustive enumeration than constrained per-fact
    extraction on an 8B model. No keyword lists: the signal is computed
    from the question and the verified facts themselves.
    """
    q_norm = re.sub(r"[^a-z0-9]+", "", question.lower())
    for envelope in facts_by_product.values():
        if not envelope:
            continue
        for fact in envelope["facts"]:
            v_norm = re.sub(r"[^a-z0-9]+", "", fact["value"].lower())
            if len(v_norm) >= 5 and v_norm in q_norm:
                return True
    return False


def _render_fact_comparison(
    question: str,
    mentioned: list,
    facts_by_product: dict,
) -> dict:
    """Deterministic comparison rendering from verified facts.

    The table structure is fixed; its ROWS come from the question-conditioned
    facts, not from a schema file. Facts are aligned across products by label
    meaning, never by section title. No LLM call: every cell traces to a
    verified fact with its source section.
    """
    # rows: [{label, cells: {product: [facts]}}] — greedy alignment
    rows = []
    for product in mentioned:
        for fact in facts_by_product[product]["facts"]:
            target = None
            for row in rows:
                if product in row["cells"]:
                    continue
                if _labels_align(row["label"], fact["label"]):
                    target = row
                    break
            if target is None:
                # same-label facts of one product stack in one row's cell
                own = next(
                    (r for r in rows
                     if product in r["cells"]
                     and _labels_align(r["label"], fact["label"])),
                    None,
                )
                if own is not None:
                    own["cells"][product].append(fact)
                    continue
                rows.append({
                    "label": fact["label"],
                    "cells": {product: [fact]},
                })
            else:
                target["cells"].setdefault(product, []).append(fact)

    def _cell(row, product):
        facts = row["cells"].get(product)
        if not facts:
            return NOT_DOCUMENTED
        parts = []
        for f in facts:
            sections = ", ".join(dict.fromkeys(f["evidence"]))
            parts.append(f"{f['value']} ({sections})")
        return "; ".join(parts)

    # deterministic direct answer from row symmetry
    asymmetric = [
        row for row in rows
        if any(p not in row["cells"] or not row["cells"][p]
               for p in mentioned)
    ]
    if not rows:
        answer_line = (
            "Nothing relevant to this question is documented in the "
            "retrieved context for the compared products."
        )
    elif asymmetric:
        first = asymmetric[0]
        have = [p for p in mentioned if first["cells"].get(p)]
        miss = [p for p in mentioned if not first["cells"].get(p)]
        answer_line = (
            f"Only {', '.join(have)} documents "
            f"\"{first['label']}\" ({_cell(first, have[0])}); "
            f"for {', '.join(miss)} this is {NOT_DOCUMENTED}."
        )
    else:
        answer_line = (
            "Both products document the compared items; the exact "
            "documented values are shown side by side below."
        )

    lines = [f"**Answer:** {answer_line}", ""]
    if rows:
        header = "| Compared item | " + " | ".join(mentioned) + " |"
        sep = "|---" * (len(mentioned) + 1) + "|"
        lines += [header, sep]
        for row in rows:
            cells = " | ".join(_cell(row, p) for p in mentioned)
            lines.append(f"| {row['label']} | {cells} |")
        lines += ["", "*Every value is quoted from that product's own "
                      "manual; sections in parentheses.*"]

    return {
        "answer": "\n".join(lines),
        "products_compared": mentioned,
        "status": "compared",
        "method": "structured",
        "catalog_used": False,
    }


# ─────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────

def build_comparison(
    original_question: str,
    search_question: str,
    products: list,
    top_k: int = 3,
    expanded_queries: list = None,
) -> dict:
    del top_k

    mentioned = _mentioned_products(
        original_question,
        products,
    )

    if len(mentioned) < 2:
        # example names come from the live registry, not from a template
        example_keys = [_product_key(p) for p in products[:2]]
        example = (f" (e.g. {example_keys[0]} and {example_keys[1]})"
                   if len(example_keys) >= 2 else "")
        return {
            "answer": (
                "This comparison needs at least two clearly specified "
                "products. Please specify which products you want to "
                f"compare{example}."
            ),
            "products_compared": mentioned,
            "status": "needs_clarification",
            "method": "none",
            "catalog_used": False,
        }

    generic_q = _generic_query(
        search_question,
        mentioned,
    )

    # use-case / recommendation path
    # (suitability/deployment questions keep their catalog-aware flow)
    if _needs_catalog_reference(
        original_question,
        None,
    ):
        use_case = _use_case_comparison(
            mentioned,
            original_question,
        )

        if use_case is not None:
            return use_case

    # No aspect matched and no meaningful topic remains after stripping
    # product names/connectives ("compare X and Y"): don't run a free-form
    # search on an empty query (which returns nothing and wrongly reports
    # "not documented"). Show each product's documented topics and ask which
    # aspect to compare.
    if not has_meaningful_topic(generic_q):
        return build_no_topic_response(mentioned)

    # Single evidence-first path. Retrieval works on the full natural
    # question plus all its expansions (synonym + LLM). Product names are
    # NOT stripped: retrieval is already scoped per product by metadata
    # filter, so stripping only breaks the sentence and loses intent-bearing
    # words. generic_q remains only as the no-topic gate above.
    queries = expanded_queries or [original_question]
    chunks_by_product = {
        product: _retrieve_product_chunks(product, queries)
        for product in mentioned
    }

    # Question-conditioned constrained extraction per product, then
    # deterministic alignment + rendering. The former aspect->schema route
    # forced every question into one of three fixed field lists (and its
    # fastener filter explicitly rejected tools, so "which needs a Phillips
    # screwdriver" could never be answered). Here the question itself is the
    # field spec. Extraction parse failure falls back to the free-form
    # compare over the same retrieved evidence.
    facts_by_product = {
        product: extract_product_facts(
            product, original_question, chunks_by_product[product])
        for product in mentioned
    }

    extraction_ok = all(
        env is not None for env in facts_by_product.values())
    any_facts = any(
        env["facts"] for env in facts_by_product.values()
        if env is not None)

    # Deterministic table only when the question itself names the criterion
    # (its exact term shows up as a verified fact value). Broad questions go
    # to the free-form compare, which enumerates far better than
    # constrained extraction on an 8B model.
    if (extraction_ok and any_facts
            and _question_names_a_fact(
                original_question, facts_by_product)):
        result = _render_fact_comparison(
            original_question, mentioned, facts_by_product)
    else:
        result = _freeform_comparison(
            mentioned,
            original_question,
            queries,
            chunks_by_product,
        )

    result["aspect_detected"] = None

    return result

# ─────────────────────────────────────────────────────────
# Use-case / recommendation comparison path
# ─────────────────────────────────────────────────────────

def _use_case_evidence_aspect(question: str) -> str:
    """
    برای سوالات use-case/recommendation، تعیین می‌کنه evidence
    از کدوم aspect باید استخراج شه.

    "compact indoor site" → installation evidence
    "high temperature"    → specifications evidence
    "DMR features"        → features evidence
    """
    q = question.lower()

    if any(t in q for t in ["compact", "indoor", "cabinet", "rack",
                            "wall", "site", "space", "2u", "mount"]):
        return "installation"

    if any(t in q for t in ["temperature", "voltage", "power", "frequency",
                            "weight", "dimension", "current"]):
        return "specifications"

    if any(t in q for t in ["call", "dmr", "feature", "function", "pstn"]):
        return "features"

    return None


def _use_case_evidence_lines(product: str, envelope: dict,
                             evidence_aspect: str) -> list:
    """
    از envelope ساختارمند، خطوط evidence مرتبط با use-case رو می‌سازه.
    فقط field هایی که status معنادار دارن (documented/confirmed).
    """
    if not envelope:
        return [f"No structured evidence extracted for {product}."]

    lines = []
    for fname, field in envelope.get("fields", {}).items():
        if not isinstance(field, dict):
            continue
        status = field.get("status")
        display = fname.replace("_", " ")

        if status in ("documented", "confirmed"):
            value = field.get("value")
            items = field.get("items")
            if value:
                lines.append(f"- {display}: {value} (documented)")
            elif items:
                lines.append(f"- {display}: {', '.join(items)} (documented)")
            else:
                lines.append(f"- {display}: documented")
        elif status == "not_documented":
            lines.append(f"- {display}: not documented in retrieved context")

    if not lines:
        lines.append("- No relevant documented evidence in retrieved context.")
    return lines


def _build_use_case_answer(mentioned: list, envelopes: dict,
                           catalog_data: dict, question: str,
                           evidence_aspect: str) -> str:
    """
    جواب use-case رو به‌صورت deterministic می‌سازه.
    هیچ LLM synthesis/opinion — فقط evidence و مقایسه‌ی قدرت شواهد.
    """
    parts = ["**Use-case evidence comparison**\n"]

    # evidence هر محصول (از structured extraction)
    for product in mentioned:
        parts.append(f"\n**{product}** (from product documentation):")
        parts.extend(_use_case_evidence_lines(
            product, envelopes.get(product), evidence_aspect))

    # catalog note (deterministic، از تابع موجود)
    if catalog_data:
        note = _deployment_catalog_note(catalog_data, mentioned)
        if note and note.strip():
            parts.append("\n**Catalog Reference**\n")
            parts.append(note)

    # محدودیت صریح
    parts.append(
        "\n*This comparison reflects the strength of documented evidence in "
        "the retrieved materials, not a general product recommendation. "
        "Absence of evidence is not evidence of absence.*"
    )
    return "\n".join(parts)


def _use_case_comparison(mentioned: list, question: str) -> dict:
    """
    مسیر recommendation/use-case:
      evidence aspect → structured extraction (موجود، validated)
      + catalog (موجود)
      + decision layer deterministic
    """
    evidence_aspect = _use_case_evidence_aspect(question)
    if not evidence_aspect:
        return None  # نمی‌دونیم چه evidence ای لازمه → freeform

    # extraction با همون مسیر validated موجود
    envelopes = {}
    for product in mentioned:
        chunks = _retrieve_schema_aware(product, evidence_aspect, question)
        env = extract_structured(product, evidence_aspect, question, chunks)
        envelopes[product] = env  # ممکنه None باشه — در evidence_lines هندل می‌شه

    # اگه هیچ envelope ای نداریم، این مسیر بی‌فایده‌ست
    if not any(envelopes.values()):
        return None

    # catalog (deterministic)
    catalog_used = False
    catalog_data = None
    if _needs_catalog_reference(question, None):
        catalog_chunks = _retrieve_catalog_reference(question, None)
        if catalog_chunks:
            catalog_data = _filter_catalog_for_products(catalog_chunks, mentioned)
            catalog_used = True

    answer = _build_use_case_answer(mentioned, envelopes, catalog_data,
                                     question, evidence_aspect)

    return {
        "answer": answer,
        "products_compared": mentioned,
        "status": "compared",
        "method": "use_case",
        "catalog_used": catalog_used,
        "evidence_aspect": evidence_aspect,
    }
