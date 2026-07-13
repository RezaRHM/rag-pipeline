import re
"""
main.py
─────────────────────────────────────────────────────────
Orchestrator اصلی pipeline — نسخه Hierarchical.

جریان جدید:
  retrieval روی child chunks (precision) →
  rerank روی children →
  fetch_parents (context کامل) →
  generation با parent ها
─────────────────────────────────────────────────────────
"""

from language.language_detector import detect_language
from query.query_rewriter import rewrite_query
from query.query_expander import expand_query
from query.query_analyzer import analyze_query
from retrieval.retriever import (
    hybrid_search, multi_query_search, fetch_parents, merge_with_preserved, add_heading_parents
)
from retrieval.context_expander import expand_context
from retrieval.reranker import rerank
from generation.generator import generate_answer
from generation.answer_classifier import classify_answer_type
from generation.quality_assessor import assess_retrieval_quality
from comparison.comparison_builder import _mentioned_products
from db.connection import get_postgres



_PRODUCTS_CACHE = None


# ─────────────────────────────────────────────────────────
# Unknown-product detection
# ─────────────────────────────────────────────────────────
# A question can name a product that does not exist in the corpus, e.g.
# "alarm code E47 on the RD99XS". The lexical matcher correctly finds no
# known product, but "no known product matched" and "no product named" are
# different situations:
#
#   NO_PRODUCT                  -> ask which model (clarification)
#   KNOWN_PRODUCT               -> normal route
#   UNKNOWN_PRODUCT_LIKE_ENTITY -> state that it is not documented
#
# Conflating the last two makes the system reply "RD98XS or HR652?" to a
# question that clearly named RD99XS, implicitly accepting that it exists.

_PRODUCT_PATTERN = re.compile(
    r'\b(?:RD\d{2,3}[A-Z]{0,2}|HR\d{3}[A-Z]?|HP\d{1,3}[A-Z]?)\b', re.I)


def _model_like_tokens(question: str) -> list:
    """Tokens shaped like a Rohill/Hytera model name, whether known or not."""
    return _PRODUCT_PATTERN.findall(question)


def _unsupported_product_response(mentions: list) -> str:
    names = ", ".join(sorted({m.upper() for m in mentions}))
    available = ", ".join(sorted(_get_all_products()))
    return (f"The available documentation does not cover {names}. "
            f"Documentation is available for: {available}.")


def _get_all_products() -> list:
    """لیست محصولات از DB، یک بار کش می‌شه."""
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is None:
        pg = get_postgres()
        cur = pg.cursor()
        cur.execute(
            "SELECT DISTINCT product FROM documents WHERE product != 'unknown'"
        )
        _PRODUCTS_CACHE = [row["product"] for row in cur.fetchall()]
        pg.close()
    return _PRODUCTS_CACHE



# ─────────────────────────────────────────────────────────
# Product clarification (deterministic, not prompt-driven)
# ─────────────────────────────────────────────────────────
# جواب بعضی سوالات بین محصولات فرق می‌کنه. اگه سوال محصولی نام نبرده
# و موضوعش product-dependent ـه، به‌جای حدس زدن یا قاطی کردن شواهد دو
# محصول، clarification می‌خوایم.
#
# این تصمیم control-flow ـه، نه generation — پس در کد اعمال می‌شه نه
# در prompt. قاعده‌ی معادلش (rule 5) قبلاً در prompt بود و مدل 8B
# بیش‌ازحد اعمالش می‌کرد: حتی برای "RD98XS LEDs?" که اسم محصول اولین
# کلمه‌ست، clarification می‌خواست.

TOPIC_KEYWORDS = {
    "alarm":        ["alarm", "error code", "alarm code", "lcd message"],
    "power":        ["power", "voltage", "battery", "adapter"],
    "led":          ["led", "indicator", "light"],
    "installation": ["install", "mount", "rack", "cabinet", "wall"],
}

CLARIFICATION_TEMPLATES = {
    "alarm": (
        "Alarm meanings differ between repeater models. Please specify whether you "
        "are using the RD98XS or HR652, and provide the alarm code or LCD message."
    ),
    "power": (
        "Power issues can refer to different conditions depending on the model. "
        "Please specify RD98XS or HR652, and whether the issue is no power, an "
        "input-voltage alarm, low TX/forward power, or a battery/power-adapter problem."
    ),
    "led": (
        "LED meanings differ by repeater model. Please specify RD98XS or HR652 and, "
        "if relevant, the LED color or state."
    ),
    "installation": (
        "Installation procedures differ between models. Please specify whether you "
        "mean the RD98XS or HR652."
    ),
}


def _detect_clarification_topic(question: str):
    """موضوع سوال رو تشخیص می‌ده (برای clarification هدفمند)."""
    low = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            return topic
    return None


def _needs_product_clarification(question: str, explicit_products: list,
                                 query_type: str) -> bool:
    """محصول نام برده نشده + موضوع product-dependent → clarification."""
    if explicit_products:
        return False
    if query_type == "comparison":
        return False
    return _detect_clarification_topic(question) is not None


def _build_product_clarification(question: str) -> str:
    """clarification هدفمند (نه generic) بر اساس موضوع."""
    topic = _detect_clarification_topic(question)
    if topic in CLARIFICATION_TEMPLATES:
        return CLARIFICATION_TEMPLATES[topic]
    return ("This answer depends on the repeater model. Please specify whether you "
            "mean the RD98XS or HR652.")


def process_query(question: str,
                  conversation_history: list = None,
                  top_k: int = 5) -> dict:
    """
    جریان کامل query — retrieval روی children، بعد جایگزینی با parents.
    """
    conversation_history = conversation_history or []

    # [۵] Language detection
    lang = detect_language(question)

    # [۸-الف] Query rewriting — فقط اگه history داریم
    if conversation_history:
        rewritten = rewrite_query(question, conversation_history)
    else:
        rewritten = question

    # [۸-ب] Query expansion
    expanded_queries = expand_query(rewritten, lang["code"])
    expanded = expanded_queries[0]

    # [۸-ج] Query analysis (advisory only)
    analysis = analyze_query(expanded)

    # [۸-د] Deterministic routing guards
    #
    # analyzer با temperature=0 پایداره، ولی می‌تونه پایدارِ اشتباه باشه:
    #   "RD98XS LEDs?"         → product=None      (اسم محصول صریحاً در سواله)
    #   "Can the HR652...5G?"  → type=comparison   (فقط یک محصول ذکر شده)
    #
    # پس فیلدهای پرریسک (product scope, comparison routing) از شواهد لغویِ
    # سوال اصلی استخراج می‌شن، نه از استنتاج مدل. analyzer فقط مشورتیه.
    #
    # نکته: روی question (سوال اصلی) کار می‌کنیم نه expanded — چون expansion
    # برای retrieval ـه و حق ندارد نیت کاربر را بازنویسی کند.
    COMPARISON_SIGNALS = ["compare", "difference", "differences", "versus",
                          " vs ", "both", "which repeater", "which one",
                          "more suitable", "better for"]

    explicit_products = _mentioned_products(question, _get_all_products())
    comparison_signal = any(s in question.lower() for s in COMPARISON_SIGNALS)

    # product scope: شواهد لغوی بر استنتاج مدل اولویت دارد
    if len(explicit_products) == 1:
        analysis["product"] = explicit_products[0]
    elif len(explicit_products) >= 2:
        analysis["product"] = None   # comparison → فیلتر per-product جداگانه

    # comparison routing: نیاز به intent صریح + حداقل دو محصول
    if comparison_signal and len(explicit_products) >= 2:
        analysis["query_type"] = "comparison"
    elif analysis["query_type"] == "comparison" and len(explicit_products) < 2:
        analysis["query_type"] = "standard"   # analyzer اشتباه کرد

    # [8-d] A model-like name that is not in the corpus.
    #
    # "No known product matched" is not the same as "no product named".
    # A question naming RD99XS should be told that model is undocumented,
    # not asked to choose between RD98XS and HR652 - which would implicitly
    # accept that RD99XS exists. Checked per token, so a mixed question
    # ("compare RD98XS and RD99XS") is caught as well.
    _known = _get_all_products()
    unknown_models = [m for m in _model_like_tokens(question)
                      if not _mentioned_products(m, _known)]
    if unknown_models:
        return {
            "original_question": question,
            "language": lang,
            "rewritten_question": rewritten,
            "expanded_question": expanded,
            "expanded_queries": expanded_queries,
            "query_type": "unsupported_product",
            "detected_product": None,
            "answer_type": None,
            "chunks": [],
            "clarification": _unsupported_product_response(unknown_models),
        }

    # [8-e] Product clarification — before retrieval (saves time)
    if _needs_product_clarification(question, explicit_products,
                                    analysis["query_type"]):
        return {
            "original_question": question,
            "language": lang,
            "rewritten_question": rewritten,
            "expanded_question": expanded,
            "expanded_queries": expanded_queries,
            "query_type": "needs_clarification",
            "detected_product": None,
            "answer_type": None,
            "chunks": [],
            "clarification": _build_product_clarification(question),
        }

    # [۹] Retrieval — روی CHILD chunks (hierarchical)
    metadata_filter = None
    if analysis["product"]:
        metadata_filter = {"product": analysis["product"]}

    child_candidates = multi_query_search(
        expanded_queries,
        metadata_filter=metadata_filter,
        limit_per_query=10,
        final_limit=30,
        level="child"
    )

    # [۱۰] Context expansion روی children (همسایه‌های child)
    expanded_candidates = expand_context(child_candidates, confidence_threshold=0.70)

    # [۱۱] Reranking روی children — precision بالا
    reranked_children = rerank(expanded, expanded_candidates,
                               top_k=top_k * 2,  # بیشتر بگیر چون بعداً به parent جمع میشن
                               all_queries=expanded_queries)

    # [۱۱-ب] فیلتر accessory (روی children)
    accessory_signals = ["accessor", "accessories", "optional component",
                         "deploy", "deployment"]
    if any(sig in expanded.lower() for sig in accessory_signals):
        from retrieval.retriever import filter_repeater_accessories
        reranked_children = filter_repeater_accessories(reranked_children)

    # [۱۲] Fetch parents — جایگزینی children با parent های کامل (Small-to-Big)
    # [12-b] Candidate preservation: rescue top-1-per-query hybrid
    # hits that a rerank false-negative would otherwise drop.
    merged_children = merge_with_preserved(
        reranked_children, expanded_candidates,
        rerank_parent_budget=top_k - 1,
        final_parent_limit=top_k,
        max_preserved=1,
        detected_product=analysis["product"])
    final_chunks = fetch_parents(merged_children)[:top_k]
    # [12-c] Heading arm: a parent-level search catches sections whose
    # child chunks are only table rows (title and prose live in the
    # parent text, e.g. Packing List, Product Layout).
    if analysis["product"]:
        heading_hits = hybrid_search(
            expanded, metadata_filter=metadata_filter,
            limit=6, level="parent")
        final_chunks = add_heading_parents(
            final_chunks, heading_hits, limit=top_k)

    # [۱۳] Answer classification
    answer_type = None
    if analysis["query_type"] not in ("procedural", "comparison"):
        answer_type = classify_answer_type(expanded, final_chunks)

    return {
        "original_question": question,
        "language": lang,
        "rewritten_question": rewritten,
        "expanded_question": expanded,
        "expanded_queries": expanded_queries,
        "query_type": analysis["query_type"],
        "detected_product": analysis["product"],
        "answer_type": answer_type,
        "chunks": final_chunks
    }


def ask(question: str, conversation_history: list = None) -> dict:
    """کل pipeline از سوال خام تا جواب نهایی."""
    from comparison.comparison_builder import build_comparison
    from db.connection import get_postgres
    from prompts.prompts import build_generation_prompt
    from generation.generator import call_llm

    retrieval_result = process_query(question, conversation_history)

    # clarification — سوال محصول رو مشخص نکرده و موضوع product-dependent ـه
    if retrieval_result["query_type"] in ("needs_clarification",
                                          "unsupported_product"):
        return {
            **retrieval_result,
            "answer": retrieval_result["clarification"],
            "answer_source": retrieval_result["query_type"],
        }

    # comparison
    if retrieval_result["query_type"] == "comparison":
        pg = get_postgres()
        cur = pg.cursor()
        cur.execute(
            "SELECT DISTINCT product FROM documents WHERE product != 'unknown'"
        )
        all_products = [row["product"] for row in cur.fetchall()]
        pg.close()

        comp_result = build_comparison(
            original_question=retrieval_result["original_question"],
            search_question=retrieval_result["expanded_question"],
            products=all_products,
            top_k=3
        )
        return {
            **retrieval_result,
            "answer": comp_result["answer"],
            "answer_source": "comparison",
            "products_compared": comp_result.get("products_compared", []),
            "comparison_status": comp_result.get("status", "compared"),
            "method": comp_result.get("method", "?"),
            "catalog_used": comp_result.get("catalog_used", False),
            "evidence_aspect": comp_result.get("evidence_aspect", None)
        }
        
        
    chunks = retrieval_result["chunks"]
    expanded_queries = retrieval_result.get("expanded_queries", [question])

    quality = assess_retrieval_quality(chunks)

    if quality["status"] == "low_confidence" and len(expanded_queries) > 1:
        top_score = chunks[0].payload.get("rerank_score", 0) if chunks else 0
        if top_score >= 0.01:
            quality["status"] = "uncertain"

    if quality["status"] in ("uncertain", "confident"):
        prompt = build_generation_prompt(
            question, chunks,
            language_code=retrieval_result["language"]["code"]
        )
        answer = call_llm(prompt)
        answer_source = "generated"
    else:
        generation_result = generate_answer(question, chunks)
        answer = generation_result["answer"]
        answer_source = generation_result["source"]

    return {
        **retrieval_result,
        "expanded_queries": expanded_queries,
        "answer": answer,
        "answer_source": answer_source
    }


if __name__ == "__main__":
    result = ask("How do I install the duplexer on the RD982S?")

    print(f"Question: {result['original_question']}")
    print(f"Type:     {result['query_type']}")
    print(f"Product:  {result['detected_product']}")
    print(f"\nAnswer:\n{result['answer']}")