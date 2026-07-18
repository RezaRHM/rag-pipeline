"""Evidence-driven product-scope ambiguity gate.

Decides, for a question that names NO product, whether the retrieved
evidence supports one shared answer or diverges per product:

    answer  -> the documented values agree (or only one product is involved)
    clarify -> the values differ, extraction is one-sided, or nothing aligns

Replaces the keyword topic gate (TOPIC_KEYWORDS / CLARIFICATION_TEMPLATES):
ambiguity is a property of the evidence, not of the question wording, so the
decision is computed from per-product fact extraction over the chunks the
main retrieval already fetched. No topic lists, no product names in code.

Safety rule (no majority voting anywhere): wording tolerance lives only
inside the value comparison, and only for long prose. Any surviving
difference in the judged rows is real and always clarifies — one divergent
critical value (alcohol allowed vs prohibited) must never be averaged away.
"""

import re

from comparison.extractor import extract_product_facts
from comparison.comparison_builder import _labels_align


def _tokens(text):
    return set(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def _norm_value(value):
    nums = re.findall(r"-?\d+(?:\.\d+)?", value)
    if nums:
        return ("nums", tuple(sorted(float(n) for n in nums)))
    return ("text", re.sub(r"[^a-z0-9]+", " ", value.lower()).strip())


def _values_match(set_a, set_b):
    """Tiered value comparison. Strict for numbers and short categorical
    values (a one-word difference there IS the product difference, and can
    be safety-critical). Tolerant ONLY for long prose values, where small
    wording variations between manuals are noise, not divergence.
    """
    if set_a == set_b:
        return True
    if len(set_a) == 1 and len(set_b) == 1:
        (type_a, val_a), = set_a
        (type_b, val_b), = set_b
        if type_a == type_b == "text":
            words_a, words_b = set(val_a.split()), set(val_b.split())
            if min(len(words_a), len(words_b)) >= 8:   # long prose only
                overlap = len(words_a & words_b) / len(words_a | words_b)
                return overlap >= 0.7
    return False


def _stem_match(token_set, query_token):
    return any(t[:4] == query_token[:4] for t in token_set if len(t) >= 4)


def assess_product_scope(question: str, chunks: list,
                         max_products: int = 4) -> dict:
    """Gate decision over the final (product-unfiltered) retrieval output.

    Returns {"verdict": "answer"|"clarify", "stage": str,
             "products": [...], "diverging": [labels...]}.
    """
    by_product = {}
    for chunk in chunks:
        product = chunk.payload.get("product", "?")
        by_product.setdefault(product, []).append(chunk)

    products = list(by_product)
    if len(products) <= 1:
        return {"verdict": "answer", "stage": "single-product",
                "products": products, "diverging": []}

    # extraction order follows evidence order (a rank proxy)
    extract_products = products[:max_products]
    facts = {}
    for product in extract_products:
        envelope = extract_product_facts(
            product, question, by_product[product])
        facts[product] = envelope["facts"] if envelope else None

    if any(v is None for v in facts.values()):
        return {"verdict": "clarify", "stage": "extract-failed",
                "products": products, "diverging": []}

    with_facts = [p for p in extract_products if facts[p]]
    if len(with_facts) <= 1:
        # several products had evidence but facts came from at most one:
        # that is uncertainty, not a single-product situation
        return {"verdict": "clarify", "stage": "one-sided-facts",
                "products": products, "diverging": []}

    # align fact rows across products by label meaning
    rows = []
    for product in with_facts:
        for fact in facts[product]:
            placed = False
            for row in rows:
                if _labels_align(row["label"], fact["label"]):
                    row["vals"].setdefault(product, set()).add(
                        _norm_value(fact["value"]))
                    placed = True
                    break
            if not placed:
                rows.append({"label": fact["label"],
                             "vals": {product: {_norm_value(fact["value"])}}})

    shared = [r for r in rows if len(r["vals"]) >= 2]
    if not shared:
        return {"verdict": "clarify", "stage": "nothing-aligns",
                "products": with_facts, "diverging": []}

    q_tokens = {t for t in _tokens(question) if len(t) >= 4}
    detail = []
    for row in shared:
        sets = list(row["vals"].values())
        same = all(_values_match(s, sets[0]) for s in sets[1:])
        relevant = any(_stem_match({lt}, qt)
                       for lt in _tokens(row["label"]) for qt in q_tokens)
        detail.append({"label": row["label"], "same": same,
                       "relevant": relevant, "row": row})

    # Row selection, most specific first: if the question names a concrete
    # term, judge ONLY the rows carrying that term — anchored on the RAREST
    # matching term, so a generic word cannot widen the judgment set past
    # the specific one.
    row_tokens = []
    for d in detail:
        value_text = " ".join(
            v for s in d["row"]["vals"].values()
            for (t, v) in s if t == "text")
        row_tokens.append(_tokens(d["label"]) | _tokens(value_text))

    anchor = None
    best_count = None
    for q_token in (t for t in _tokens(question) if len(t) >= 5):
        matches = [i for i, toks in enumerate(row_tokens)
                   if _stem_match(toks, q_token)]
        if matches and (best_count is None or len(matches) < best_count):
            best_count = len(matches)
            anchor = matches

    if anchor is not None:
        judged = [detail[i] for i in anchor]
    else:
        relevant_rows = [d for d in detail if d["relevant"]]
        judged = relevant_rows if relevant_rows else detail

    diverging = [d["label"] for d in judged if not d["same"]]
    return {
        "verdict": "clarify" if diverging else "answer",
        "stage": "value-compare",
        "products": with_facts,
        "diverging": diverging,
    }
