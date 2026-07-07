"""
query/query_rewriter.py
─────────────────────────────────────────────────────────
Context-resolution gate چندمرحله‌ای — طبق پیشنهاد معماری:

۱. Deterministic gate تصمیم میگیره آیا rewrite لازمه
۲. LLM فقط بعد از gate صدا زده میشه — نه برای تصمیم‌گیری
۳. Default: standalone — اگه شک داری، rewrite نکن

اصل طلایی: هیچوقت original query رو دور نریز.
─────────────────────────────────────────────────────────
"""

import re
import requests
import config
from db.connection import get_postgres


REWRITER_PROMPT = """You are a query rewriting module for technical documentation search.

Task: Rewrite the user's follow-up question into a standalone search query.

Rules:
- Only resolve explicit pronouns (it, this, that, they) or missing subjects
- Use only the provided active entity
- Do NOT add product names, model numbers, or error codes unless required to resolve a pronoun
- If the question is already standalone, return it UNCHANGED
- Output ONLY the rewritten query, nothing else

Active entity: {active_entity}
User question: {question}

Rewritten query:"""


# ── Deterministic Gate ────────────────────────────────────

PRONOUNS = {"it", "its", "this", "that", "these", "those", "they", "them"}

DEMONSTRATIVE_REFS = [
    "the same", "previous", "above", "that range", "this model",
    "the other", "you said", "as mentioned"
]

ELLIPTICAL_PATTERNS = [
    r"^what about\b",
    r"^how about\b",
    r"^and the\b",
    r"^and its\b",
    r"^what is its\b",
]

STANDALONE_ENTITY_PATTERNS = [
    r'\b[A-Z]\d+\b',                    # H5, E1, E9
    r'\berror\s+code\s+[A-Z0-9]+\b',    # error code H5
    r'\balarm\s+code\s+[A-Z0-9]+\b',    # alarm code E1
    r'\bfault\s+code\s+[A-Z0-9]+\b',    # fault code
    r'\bRD9\d+\b',                       # RD982S, RD985S
    r'\bHR\d+\b',                        # HR652
    r'\bHP\d+\b',                        # HP7
    r'\bIP\d+\b',                        # IP65, IP67
]


def _has_pronoun(question: str) -> bool:
    words = set(question.lower().split())
    return bool(words & PRONOUNS)


def _has_demonstrative_ref(question: str) -> bool:
    q_lower = question.lower()
    return any(ref in q_lower for ref in DEMONSTRATIVE_REFS)


def _is_elliptical(question: str) -> bool:
    q_lower = question.lower().strip()
    return any(re.match(p, q_lower) for p in ELLIPTICAL_PATTERNS)


def _has_standalone_entity(question: str) -> bool:
    for pattern in STANDALONE_ENTITY_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return True
    return False


def _context_dependency_score(question: str) -> int:
    """
    امتیاز وابستگی به context — مثبت یعنی نیاز به rewrite،
    منفی یعنی standalone ـه.
    """
    score = 0

    if _has_pronoun(question):
        score += 3
    if _has_demonstrative_ref(question):
        score += 2
    if _is_elliptical(question):
        score += 3
    if _has_standalone_entity(question):
        score -= 4

    # سوال کامل (با subject صریح) standalone‌تره
    if re.match(r'^(what|how|where|when|which|who|does|is|can|will)\s+\w+\s+\w+', 
                question.lower()):
        if not _has_pronoun(question):
            score -= 1

    return score


def _get_known_products() -> list:
    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("SELECT DISTINCT product FROM documents WHERE product != 'unknown'")
    products = [row["product"] for row in cur.fetchall()]
    pg.close()
    return products


def _question_mentions_known_product(question: str, known_products: list) -> bool:
    question_upper = question.upper()
    for product in known_products:
        for kw in product.upper().split():
            if len(kw) > 3 and kw in question_upper:
                return True
    return False


def _extract_active_entity(conversation_history: list,
                            known_products: list) -> str:
    """
    آخرین entity مهم رو از history استخراج میکنه.
    """
    for turn in reversed(conversation_history):
        content = turn.get("content", "")
        for product in known_products:
            for kw in product.split():
                if len(kw) > 3 and kw.upper() in content.upper():
                    return product
    return ""


def rewrite_query(question: str, conversation_history: list) -> str:
    """
    Gate-based rewriter:
    ۱. اگه history نیست → برگردون
    ۲. اگه سوال خودش محصول داره → برگردون
    ۳. امتیاز dependency رو حساب کن
    ۴. اگه standalone → برگردون (default محافظه‌کارانه)
    ۵. فقط اگه dependency قوی بود → LLM صدا بزن
    """
    if not conversation_history:
        return question

    known_products = _get_known_products()

    # اگه سوال خودش محصول صریح داره، نیازی به rewrite نیست
    if _question_mentions_known_product(question, known_products):
        return question

    # امتیاز dependency
    score = _context_dependency_score(question)

    # Default محافظه‌کارانه: اگه شک داری، rewrite نکن
    if score <= 0:
        return question

    # dependency قوی داره — active entity رو استخراج کن
    active_entity = _extract_active_entity(conversation_history, known_products)
    if not active_entity:
        return question

    # LLM فقط برای rewrite، نه تصمیم‌گیری
    prompt = REWRITER_PROMPT.format(
        active_entity=active_entity,
        question=question
    )

    try:
        response = requests.post(
            f"{config.LITELLM_BASE_URL}/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LITELLM_API_KEY}"
            },
            json={
                "model": config.DEFAULT_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=config.LLM_TIMEOUT
        )
        response.raise_for_status()
        rewritten = response.json()["choices"][0]["message"]["content"].strip()
        rewritten = rewritten.strip('"').strip("'")

        # اگه LLM چیز عجیبی برگردوند، original رو نگه دار
        if len(rewritten) > len(question) * 3 or not rewritten:
            return question

        return rewritten
    except Exception:
        return question