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

from comparison.extractor import extract_structured
from comparison.schemas import (
    detect_aspect,
    get_retrieval_queries,
)
from prompts.prompts import BASE_SYSTEM_PROMPT
from retrieval.reranker import rerank
from retrieval.retriever import (
    fetch_parents,
    hybrid_search,
)


CATALOG_PRODUCT_LABEL = "HP7 SERIES"

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

        if key in q_upper:
            matched.append(product)

        elif "X" in key and re.search(
            key.replace("X", r"\d"),
            q_upper,
        ):
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
) -> str:
    generic = search_question

    for pattern in [
        r"RD9\d+X?S?",
        r"HR\d+",
        r"HP\d+",
        r"\bvs\b",
        r"compared?\s+to",
        r"difference\s+between",
        r"\bboth\b",
    ]:
        generic = re.sub(
            pattern,
            "",
            generic,
            flags=re.IGNORECASE,
        )

    return " ".join(
        generic.split()
    )


def _retrieve_product_chunks(
    product: str,
    generic_q: str,
    top_k: int = 3,
) -> list:
    """
    Generic retrieval used only by free-form fallback.
    """
    children = hybrid_search(
        generic_q,
        metadata_filter={
            "product": product,
        },
        limit=max(
            top_k * 2,
            8,
        ),
        level="child",
    )

    if not children:
        return []

    reranked = rerank(
        generic_q,
        children,
        top_k=min(
            top_k,
            len(children),
        ),
    )

    parents = fetch_parents(
        reranked
    )

    return parents[:top_k]


# ─────────────────────────────────────────────────────────
# Structured table formatting
# ─────────────────────────────────────────────────────────

def _format_cell(
    field_name: str,
    field: dict,
) -> str:
    if not isinstance(field, dict):
        return "unclear"

    if field_name == "fasteners":
        status = field.get(
            "status",
            "unclear",
        )

        items = field.get(
            "items",
            [],
        )

        if (
            status == "documented"
            and items
        ):
            return ", ".join(items)

        if status == "not_documented":
            return "not documented in retrieved context"

        return "unclear"

    if "value" in field:
        status = field.get(
            "status",
            "",
        )

        value = field.get(
            "value"
        )

        if value:
            source_term = field.get(
                "source_term"
            )

            if (
                source_term
                and source_term.lower()
                not in str(value).lower()
            ):
                return (
                    f"{value} "
                    f"({source_term})"
                )

            return str(value)

        if status == "not_documented":
            return "not documented in retrieved context"

        return "unclear"

    status = field.get(
        "status",
        "unclear",
    )

    if status in (
        "documented",
        "confirmed",
    ):
        return "✓ documented"

    if status == "not_documented":
        return "not documented in retrieved context"

    return "unclear"


def _build_structured_table(
    envelopes: dict,
    aspect: str,
) -> str:
    products = list(
        envelopes.keys()
    )

    first = next(
        iter(envelopes.values())
    )

    field_names = list(
        first["fields"].keys()
    )

    lines = [
        f"**Comparison ({aspect})**\n"
    ]

    lines.append(
        "| Field | "
        + " | ".join(products)
        + " |"
    )

    lines.append(
        "|"
        + "---|" * (
            len(products) + 1
        )
    )

    for field_name in field_names:
        cells = [
            _format_cell(
                field_name,
                envelopes[product][
                    "fields"
                ].get(
                    field_name,
                    {},
                ),
            )
            for product in products
        ]

        display = (
            field_name
            .replace("_", " ")
            .title()
        )

        lines.append(
            f"| {display} | "
            + " | ".join(cells)
            + " |"
        )

    lines.append(
        "\n*Values extracted separately per product; "
        "no cross-product inference.*"
    )

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# Parent dedupe
# ─────────────────────────────────────────────────────────

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
                "product": CATALOG_PRODUCT_LABEL,
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

def _has_meaningful_extraction(
    envelope: dict,
) -> bool:
    """
    Reject envelopes that are syntactically valid but entirely unclear.
    """
    fields = envelope.get(
        "fields",
        {},
    )

    for field in fields.values():
        if not isinstance(
            field,
            dict,
        ):
            continue

        status = field.get(
            "status"
        )

        if status in (
            "documented",
            "confirmed",
            "not_documented",
        ):
            return True

    return False


# ─────────────────────────────────────────────────────────
# Structured comparison
# ─────────────────────────────────────────────────────────

def _structured_comparison(
    mentioned: list,
    question: str,
    generic_q: str,
    aspect: str,
):
    """
    Structured decomposition:

    per-product schema-aware retrieval
    → per-product extraction
    → deterministic table
    → optional catalog reference layer
    """
    del generic_q

    envelopes = {}

    for product in mentioned:
        chunks = _retrieve_schema_aware(
            product,
            aspect,
            question,
        )

        envelope = extract_structured(
            product,
            aspect,
            question,
            chunks,
        )

        if (
            envelope is None
            or not _has_meaningful_extraction(
                envelope
            )
        ):
            return None

        envelopes[
            product
        ] = envelope

    answer = _build_structured_table(
        envelopes,
        aspect,
    )

    catalog_used = False

    if _needs_catalog_reference(
        question,
        aspect,
    ):
        catalog_chunks = _retrieve_catalog_reference(
            question,
            aspect,
        )

        if catalog_chunks:
            catalog_data = _filter_catalog_for_products(
                catalog_chunks,
                mentioned,
            )

            catalog_note = _build_catalog_note(
                catalog_data,
                mentioned,
                question,
                aspect,
            )

            if catalog_note.strip():
                answer += (
                    "\n\n**Catalog Reference Note**\n\n"
                    + catalog_note
                )

                catalog_used = True

    return {
        "answer": answer,
        "products_compared": mentioned,
        "status": "compared",
        "method": "structured",
        "catalog_used": catalog_used,
        "envelopes": envelopes,
    }


# ─────────────────────────────────────────────────────────
# Free-form decomposition fallback
# ─────────────────────────────────────────────────────────

def _summarize_product(
    product: str,
    chunks: list,
    question: str,
) -> str:
    context = "\n\n".join([
        (
            f"[{chunk.payload['section']}]\n"
            f"{chunk.payload['text']}"
        )
        for chunk in chunks
    ])

    prompt = f"""Summarize ONLY the relevant information about {product} from the context,
to help answer: "{question}"

Rules:
- Use ONLY the context below.
- Do not mention any other product.
- Preserve exact terminology and values.
- Do not paraphrase technical values.
- If something is not in the context, do not invent it.

Context:
{context}

Summary for {product}:"""

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
                    "content": prompt,
                }
            ],
            "temperature": 0,
        },
        timeout=config.LLM_TIMEOUT,
    )

    response.raise_for_status()

    return (
        response
        .json()["choices"][0]["message"]["content"]
    )


def _freeform_comparison(
    mentioned: list,
    question: str,
    generic_q: str,
) -> dict:
    summaries = {}

    for product in mentioned:
        chunks = _retrieve_product_chunks(
            product,
            generic_q,
        )

        if chunks:
            summaries[
                product
            ] = _summarize_product(
                product,
                chunks,
                question,
            )

        else:
            summaries[
                product
            ] = (
                "[No relevant context retrieved "
                f"for {product}]"
            )

    summary_block = "\n\n".join([
        (
            f"{'=' * 40}\n"
            f"{product} summary:\n"
            f"{'=' * 40}\n"
            f"{summary}"
        )
        for product, summary
        in summaries.items()
    ])

    compare_prompt = (
        BASE_SYSTEM_PROMPT
        + f"""

Compare the products based ONLY on these per-product summaries.

CRITICAL:
- Keep each product's details strictly separate.
- If a detail appears in only one summary, do NOT attribute it to the other.
- If something is "not documented" for a product, say exactly:
  "not documented in the retrieved context".
- Never rephrase missing documentation as "not present", "absent",
  "unsupported", or "the product does not have it".
- Do not use "likely", "probably", or "can be inferred".

{summary_block}

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
# Public entry point
# ─────────────────────────────────────────────────────────

def build_comparison(
    original_question: str,
    search_question: str,
    products: list,
    top_k: int = 3,
) -> dict:
    del top_k

    mentioned = _mentioned_products(
        original_question,
        products,
    )

    if len(mentioned) < 2:
        return {
            "answer": (
                "This comparison needs at least two clearly specified "
                "products. Please specify which products you want to "
                "compare (e.g. RD98XS and HR652)."
            ),
            "products_compared": mentioned,
            "status": "needs_clarification",
            "method": "none",
            "catalog_used": False,
        }

    generic_q = _generic_query(
        search_question
    )

    aspect = detect_aspect(
        original_question
    )

    if aspect:
        structured = _structured_comparison(
            mentioned,
            original_question,
            generic_q,
            aspect,
        )

        if structured is not None:
            return structured

    result = _freeform_comparison(
        mentioned,
        original_question,
        generic_q,
    )

    result["aspect_detected"] = aspect

    return result