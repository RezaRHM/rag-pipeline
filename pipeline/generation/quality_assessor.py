"""
generation/quality_assessor.py
─────────────────────────────────────────────────────────
قبل از اینکه از LLM جواب بخوایم، چک می‌کنیم آیا اصلاً
chunk های retrieve‌شده به اندازه کافی مرتبطن — این دقیقاً
سناریوی «جواب غایب» (سناریو ۹) رو حل می‌کنه.

این ماژول از rerank_score استفاده می‌کنه، نه LLM call
جدید — سریع و بدون هزینه اضافیه.
─────────────────────────────────────────────────────────
"""

CONFIDENCE_THRESHOLDS = {
    "no_results": 0.0,
    "low_confidence": 0.30,
    "uncertain": 0.55,
}


def assess_retrieval_quality(chunks: list) -> dict:
    """
    chunks: لیست نهایی بعد از rerank (دارای rerank_score)

    برمی‌گردونه:
      status: no_results / low_confidence / uncertain / confident
      confidence: امتیاز بهترین chunk
    """
    if not chunks:
        return {"status": "no_results", "confidence": 0.0}
    
    top_score = chunks[0].payload.get("rerank_score")
    if top_score is None:
        top_score = getattr(chunks[0], "score", 0.0)


    if top_score < CONFIDENCE_THRESHOLDS["low_confidence"]:
        status = "low_confidence"
    elif top_score < CONFIDENCE_THRESHOLDS["uncertain"]:
        status = "uncertain"
    else:
        status = "confident"

    return {"status": status, "confidence": top_score}