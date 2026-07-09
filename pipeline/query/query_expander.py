"""
query/query_expander.py
─────────────────────────────────────────────────────────
Query expansion سه مرحله‌ای:

برای انگلیسی:
  ۱. Synonym expansion (dictionary-based)
  ۲. LLM augmentation (اصطلاحات صنعتی استاندارد)

برای غیرانگلیسی:
  ۱. LLM translation به انگلیسی (1 call)
  ۲. Domain glossary normalization
  ۳. Synonym expansion روی ترجمه انگلیسی
  ۴. query اصلی هم نگه داشته میشه (برای retrieval)

خروجی: لیستی از query ها برای multi_query_search
─────────────────────────────────────────────────────────
"""

import re
import requests
import config
from query.synonyms import expand_with_synonyms

TRANSLATION_PROMPT = """Translate the following question to English.
The question is about radio communication equipment (repeaters, base stations, antennas).
Use standard technical terminology used in equipment manuals.
Output ONLY the translated question, nothing else.

Question: {question}

English translation:"""

LLM_EXPANSION_PROMPT = """Generate search queries for retrieving technical
manual chunks about radio communication equipment.

Requirements:
- Use standard industrial and technical terminology
- Include synonyms used in product manuals
- Preserve product names and model numbers exactly
- Generate queries that may match installation, environmental, operating,
  and specification sections
- Do NOT answer the question
- Output ONLY search queries, one per line, no numbering

User question: {question}

Generate 5 retrieval queries:"""

# اصطلاحات غیراستاندارد که LLM ممکنه در ترجمه استفاده کنه
# و معادل دقیق‌شون توی مانوال‌ها
DOMAIN_GLOSSARY = {
    "warning light": "alarm indicator",
    "alert light": "alarm indicator",
    "red light": "alarm indicator glows red",
    "error light": "alarm indicator",
    "warning indicator": "alarm indicator",
    "working temperature": "operating temperature",
    "work temperature": "operating temperature",
    "ambient temp": "ambient temperature",
    "power voltage": "supply voltage",
    "input power": "input voltage",
    "power indicator": "alarm indicator",
    "signal light": "LED indicator",
}


def _translate_to_english(question: str) -> str:
    """
    سوال رو با LLM به انگلیسی ترجمه میکنه.
    اگه ترجمه fail کرد، سوال اصلی رو برمیگردونه.
    """
    try:
        response = requests.post(
            f"{config.LITELLM_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LITELLM_API_KEY}"
            },
            json={
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content":
                              TRANSLATION_PROMPT.format(question=question)}],
                "temperature": 0
            },
            timeout=config.LLM_TIMEOUT
        )
        response.raise_for_status()
        translated = response.json()["choices"][0]["message"]["content"].strip()
        translated = translated.strip('"').strip("'")

        if translated and len(translated) > 3:
            return translated
    except Exception:
        pass

    return question


def _normalize_with_glossary(query: str) -> str:
    """
    اصطلاحات غیراستاندارد رو با معادل‌های دقیق مانوال جایگزین میکنه.
    این post-processing روی ترجمه LLM ـه.
    """
    query_lower = query.lower()
    normalized = query_lower
    for wrong, correct in DOMAIN_GLOSSARY.items():
        if wrong in normalized:
            normalized = normalized.replace(wrong, correct)
    return normalized


# خطوط مقدماتی/توضیحی مدل که query نیستن
_PREAMBLE_MARKERS = (
    "here are", "here's", "sure", "certainly", "the following",
    "search quer", "based on", "i've generated", "these quer",
)

# جملات محاوره‌ای/پایانی که query نیستن
_CONVERSATIONAL_MARKERS = (
    "let me know", "hope this", "feel free", "if you need",
    "note that", "please note", "i hope", "would you like",
)


def _clean_expansion_line(line: str) -> str:
    """
    یک خط از خروجی LLM expansion رو به query تمیز تبدیل می‌کنه،
    یا رشته خالی برمی‌گردونه اگه query معتبر نباشه.

    مدل جمله مقدماتی ("Here are five search queries...") و شماره‌گذاری
    اضافه می‌کنه. بدون فیلتر این‌ها به‌عنوان query به retrieval می‌رن
    و coverage guarantee مجبور می‌شه براشون chunk تضمین کنه.
    """
    line = line.strip()
    if not line:
        return ""
    line = re.sub(r'^[-*\u2022]\s*', '', line)
    line = re.sub(r'^\d+[.\)]\s*', '', line)
    line = line.strip().strip('"').strip("'").strip()
    if not line:
        return ""
    low = line.lower()
    if any(low.startswith(m) for m in _PREAMBLE_MARKERS):
        return ""
    if any(m in low for m in _CONVERSATIONAL_MARKERS):
        return ""
    # جمله‌ی محاوره‌ای معمولاً با ! یا ? تمام می‌شه (به‌جز خود سوال اصلی)
    if line.endswith("!"):
        return ""
    words = line.split()
    if len(words) < 2 or len(words) > 15:
        return ""
    if line.endswith(":"):
        return ""
    return line


def expand_query(question: str, language_code: str) -> list:
    """
    query expansion — خروجی لیستی از query هاست.
    اولین عنصر همیشه query اصلیه (برای display).
    English query برای reranking استفاده میشه.
    """
    queries = [question]  # همیشه original اول

    if language_code != "en":
        # مرحله ۱: ترجمه به انگلیسی
        english_query = _translate_to_english(question)

        if english_query != question:
            queries.append(english_query)

            # مرحله ۲: normalize با domain glossary
            normalized = _normalize_with_glossary(english_query)
            if normalized != english_query.lower() and normalized not in queries:
                queries.append(normalized)

            # مرحله ۳: synonym expansion روی ترجمه انگلیسی
            synonym_queries = expand_with_synonyms(english_query)
            for q in synonym_queries:
                if q not in queries:
                    queries.append(q)

        return queries

    # برای انگلیسی: synonym + LLM augmentation
    synonym_queries = expand_with_synonyms(question)
    for q in synonym_queries:
        if q not in queries:
            queries.append(q)

    try:
        response = requests.post(
            f"{config.LITELLM_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LITELLM_API_KEY}"
            },
            json={
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content":
                              LLM_EXPANSION_PROMPT.format(question=question)}],
                "temperature": 0
            },
            timeout=config.LLM_TIMEOUT
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]

        for line in raw.strip().split("\n"):
            line = _clean_expansion_line(line)
            if line and line not in queries:
                queries.append(line)
    except Exception:
        pass

    return queries