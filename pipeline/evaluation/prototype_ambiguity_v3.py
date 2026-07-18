"""Prototype v3 of the ambiguity gate: value-level convergence.

Decision cascade for product-less questions:
  1. rank-based product membership (no score floor)
  2. stage 1: near-identical evidence text across products -> answer
  3. stage 2: extract_product_facts per product, compare normalized values
       all agree -> answer | any differ -> clarify

Run offline against the probe set; reports verdict, stage, and latency.
"""
import itertools
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from query.query_expander import expand_query
from retrieval.retriever import multi_query_search, fetch_parents
from retrieval.reranker import rerank
from retrieval.context_expander import expand_context
from comparison.extractor import extract_product_facts
from comparison.comparison_builder import _labels_align


def _tokens(t):
    return set(re.sub(r"[^a-z0-9 ]+", " ", t.lower()).split())


def _lex(a, b):
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


def _best_match_lex(chunks_a, chunks_b):
    fwd = sum(max(_lex(x, y) for y in chunks_b) for x in chunks_a) / len(chunks_a)
    bwd = sum(max(_lex(y, x) for x in chunks_a) for y in chunks_b) / len(chunks_b)
    return min(fwd, bwd)


def _norm_value(v):
    nums = re.findall(r"-?\d+(?:\.\d+)?", v)
    if nums:
        return ("nums", tuple(sorted(float(n) for n in nums)))
    return ("text", re.sub(r"[^a-z0-9]+", " ", v.lower()).strip())


def _values_match(set_a, set_b):
    """Tiered value comparison. Strict for numbers and short categorical
    values (a one-word difference there IS the product difference, and can
    be safety-critical). Tolerant ONLY for long prose values, where small
    wording variations between manuals are noise, not divergence.
    """
    if set_a == set_b:
        return True
    if len(set_a) == 1 and len(set_b) == 1:
        (ta, va), = set_a
        (tb, vb), = set_b
        if ta == tb == "text":
            wa, wb = set(va.split()), set(vb.split())
            if min(len(wa), len(wb)) >= 8:      # long prose only
                return len(wa & wb) / len(wa | wb) >= 0.7
    return False


def gate(question, lex_hi=0.80, max_extract_products=4):
    t0 = time.time()
    eq = expand_query(question, "en")
    cands = multi_query_search(eq, metadata_filter=None,
                               limit_per_query=10, final_limit=30, level="child")
    ec = expand_context(cands, confidence_threshold=0.70)
    rr = rerank(eq[0], ec, top_k=10, all_queries=eq)
    parents = fetch_parents(rr)[:6]

    by_product = {}
    for c in parents:
        p = c.payload.get("product", "?")
        by_product.setdefault(p, []).append(c)
    prods = sorted(by_product)

    if len(prods) <= 1:
        return {"verdict": "answer", "stage": "single-product",
                "products": prods, "elapsed": time.time() - t0}

    # stage 1: near-identical evidence text
    texts = {p: [c.payload.get("text", "") for c in by_product[p]] for p in prods}
    lex_scores = [
        _best_match_lex(texts[a], texts[b])
        for a, b in itertools.combinations(prods, 2)
    ]
    if min(lex_scores) >= lex_hi:
        return {"verdict": "answer", "stage": "identical-text",
                "min_lex": round(min(lex_scores), 2),
                "products": prods, "elapsed": time.time() - t0}

    # stage 2: value-level comparison via constrained extraction
    # limit to the products with the best child ranks
    rank_of = {}
    for i, c in enumerate(rr):
        p = c.payload.get("product", "?")
        rank_of.setdefault(p, i)
    extract_prods = sorted(prods, key=lambda p: rank_of.get(p, 99))[:max_extract_products]

    facts = {}
    for p in extract_prods:
        env = extract_product_facts(p, question, by_product[p])
        facts[p] = env["facts"] if env else None

    if any(v is None for v in facts.values()):
        return {"verdict": "clarify", "stage": "extract-failed",
                "min_lex": round(min(lex_scores), 2),
                "products": prods, "elapsed": time.time() - t0}

    with_facts = [p for p in extract_prods if facts[p]]
    if len(with_facts) <= 1:
        # Multiple products had evidence but extraction yielded facts for at
        # most one: that is uncertainty, not a single-product situation.
        return {"verdict": "clarify", "stage": "one-sided-facts",
                "min_lex": round(min(lex_scores), 2),
                "products": with_facts, "elapsed": time.time() - t0}

    # align labels greedily across products, then compare value sets
    rows = []
    for p in with_facts:
        for f in facts[p]:
            placed = False
            for row in rows:
                if _labels_align(row["label"], f["label"]):
                    row["vals"].setdefault(p, set()).add(_norm_value(f["value"]))
                    placed = True
                    break
            if not placed:
                rows.append({"label": f["label"],
                             "vals": {p: {_norm_value(f["value"])}}})

    shared = [r for r in rows if len(r["vals"]) >= 2]
    detail = []
    q_tokens = {t for t in _tokens(question) if len(t) >= 4}

    def _related(label):
        # stem-prefix match so "cleaning"/"cleanser"/"clean" all relate
        for lt in _tokens(label):
            if len(lt) < 4:
                continue
            for qt in q_tokens:
                if lt[:4] == qt[:4]:
                    return True
        return False

    for r in shared:
        sets = list(r["vals"].values())
        same = all(_values_match(s, sets[0]) for s in sets[1:])
        relevant = _related(r["label"])
        detail.append((r["label"], "same" if same else "DIFF",
                       "rel" if relevant else "-"))

    # Row selection, most specific first. If the question names a concrete
    # term (alcohol, temperature, connector), judge ONLY the rows carrying
    # that term — anchored on the RAREST matching term, so a generic word
    # ("cleaning") cannot widen the judgment set past the specific one.
    # No majority vote anywhere: wording tolerance lives inside
    # _values_match, so any surviving difference in the judged rows is
    # treated as real — and a real difference is never averaged away. One
    # divergent critical value (alcohol allowed vs prohibited) always
    # clarifies.
    row_text = []
    for i, r in enumerate(shared):
        vals = " ".join(v for _, s in r["vals"].items()
                        for (t, v) in s if t == "text")
        row_text.append(_tokens(r["label"]) | _tokens(vals))

    anchor_rows = None
    best_count = None
    for qt in (t for t in _tokens(question) if len(t) >= 5):
        matches = [i for i, toks in enumerate(row_text)
                   if any(lt[:4] == qt[:4] for lt in toks if len(lt) >= 4)]
        if matches and (best_count is None or len(matches) < best_count):
            best_count = len(matches)
            anchor_rows = matches

    if anchor_rows is not None:
        judged = [detail[i] for i in anchor_rows]
    else:
        rel_rows = [d for d in detail if d[2] == "rel"]
        judged = rel_rows if rel_rows else detail

    if not shared:
        verdict = "clarify"   # facts on both sides but nothing aligns
    else:
        verdict = "clarify" if any(
            d[1] == "DIFF" for d in judged) else "answer"

    return {"verdict": verdict, "stage": "value-compare",
            "min_lex": round(min(lex_scores), 2),
            "shared": detail, "products": with_facts,
            "elapsed": time.time() - t0}


PROBES = [
    # A1's validation expectation is literally "Optional clarification":
    # under the no-hidden-difference principle, clarify is also acceptable.
    ("A1", "gray-ok", "Cleaning instructions?"),
    ("P1", "answer",  "Can alcohol be used for cleaning?"),
    ("A2", "clarify", "What's in the box?"),
    ("A3", "clarify", "Antenna connector type?"),
    ("A4", "clarify", "Ground screw location?"),
    ("P4", "clarify", "What alarm codes exist?"),
    ("P5", "clarify", "What LED indicators are there?"),
    ("P6", "clarify", "How do I install the repeater?"),
    ("P7", "clarify", "What is the output power?"),
    ("P8", "clarify", "Where is the power inlet located?"),
    ("P2", "gray-ok", "How should I care for the product surface?"),
    ("P9", "gray-ok", "What is the operating temperature range?"),
]

if __name__ == "__main__":
    hard_ok = hard_total = 0
    for pid, label, q in PROBES:
        r = gate(q)
        mark = ""
        if label in ("answer", "clarify"):
            hard_total += 1
            if r["verdict"] == label:
                hard_ok += 1
                mark = "OK"
            else:
                mark = "WRONG"
        print(f"{pid} [{label:7}] -> {r['verdict']:7} ({r['stage']}, "
              f"{r['elapsed']:.0f}s) {mark}", flush=True)
        if r.get("shared"):
            for lbl, st, rel in r["shared"]:
                print(f"      {st:4} {rel:3} | {lbl}", flush=True)
    print(f"\nHARD ACCURACY: {hard_ok}/{hard_total}", flush=True)
