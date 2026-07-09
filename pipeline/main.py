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
    hybrid_search, multi_query_search, fetch_parents
)
from retrieval.context_expander import expand_context
from retrieval.reranker import rerank
from generation.generator import generate_answer
from generation.answer_classifier import classify_answer_type
from generation.quality_assessor import assess_retrieval_quality
from comparison.comparison_builder import _mentioned_products
from db.connection import get_postgres



_PRODUCTS_CACHE = None


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
    final_chunks = fetch_parents(reranked_children)
    final_chunks = final_chunks[:top_k]  # به top_k نهایی محدود کن

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