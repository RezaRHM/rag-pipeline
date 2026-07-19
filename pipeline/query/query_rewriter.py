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
from db.connection import get_postgres


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
    # tokenize past punctuation: in "How do I install it?" the naive
    # whitespace split yields "it?" which never matched the pronoun set
    words = set(re.findall(r"[a-z]+", question.lower()))
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


_KNOWN_PRODUCTS_CACHE = None


def _get_known_products() -> list:
    """Registry product labels, cached for the process lifetime.

    Same reset-after-ingest caveat as main._PRODUCTS_CACHE. Memoized because
    the rewriter now runs deterministically on every history-bearing turn
    (and the server calls it once more for the cache key).
    """
    global _KNOWN_PRODUCTS_CACHE
    if _KNOWN_PRODUCTS_CACHE is None:
        pg = get_postgres()
        cur = pg.cursor()
        cur.execute(
            "SELECT DISTINCT product FROM documents WHERE product != 'unknown'")
        _KNOWN_PRODUCTS_CACHE = [row["product"] for row in cur.fetchall()]
        pg.close()
    return _KNOWN_PRODUCTS_CACHE


def _product_key(product: str) -> str:
    """Model key of a registry label: 'HR652 Digital Repeater' -> 'HR652'."""
    match = re.match(r"([A-Za-z]+[\w-]*\d[\w-]*)", product.strip())
    return match.group(1).upper() if match else product.upper().split()[0]


def _keys_in_text(text: str, known_products: list) -> list:
    """Products whose MODEL KEY appears in the text.

    Matching on the key only. The old any-word>3 matching accepted generic
    label words such as 'Digital' and 'Repeater', so any sentence containing
    'Digital Repeater' matched the first product in DB order — which is how
    'Does it have a fan?' once resolved to the wrong model entirely.
    """
    upper = text.upper()
    found = []
    for product in known_products:
        if re.search(r"\b" + re.escape(_product_key(product)), upper):
            found.append(product)
    return found


def _question_mentions_known_product(question: str, known_products: list) -> bool:
    return bool(_keys_in_text(question, known_products))


def _product_stack(conversation_history: list,
                   known_products: list) -> list:
    """Ordered distinct products from the history, most recent first.

    User turns are scanned before assistant turns: what the user named is
    the strongest signal of what "it" (stack[0]) or "the previous one"
    (stack[1]) means. Turns naming SEVERAL products are skipped —
    clarification answers enumerate every documented model and would
    otherwise poison the resolution.
    """
    stack = []
    for wanted_role in ("user", None):
        for turn in reversed(conversation_history):
            if wanted_role and turn.get("role") != wanted_role:
                continue
            keys = _keys_in_text(turn.get("content", ""), known_products)
            if len(keys) == 1 and keys[0] not in stack:
                stack.append(keys[0])
    return stack


# ── Topic carryover (product-switch ellipsis) ─────────────

FRAMING_WORDS = {
    "what", "about", "and", "how", "the", "for", "of", "on", "in", "is",
    "are", "it", "its", "one", "a", "an", "same", "then", "also", "too",
    "does", "do", "with",
}

_PREVIOUS_REF_RE = re.compile(
    r"\b(the previous|the other|previous one|other one|earlier one|"
    r"the first one)\b", re.IGNORECASE)

_COMPARE_WORDS = {"compare", "comparison", "versus", "vs", "both",
                  "difference", "differences"}


_CODE_TOKEN_RE = re.compile(r"\b[A-Za-z]{1,3}\d{1,3}\b")


def _codes_in_text(text: str, known_products: list) -> list:
    """Short letters+digits tokens (E3, H5, F12, IP68) that are not
    registry product keys. Letter-only codes (EH, bP) are consciously out
    of scope: two plain letters cannot be told apart from words safely."""
    keys = {_product_key(p) for p in known_products}
    return [c for c in _CODE_TOKEN_RE.findall(text)
            if c.upper() not in keys]


def _content_tokens(question: str, known_products: list) -> set:
    """Alpha tokens that carry topic: framing words, product keys and
    code-shaped tokens out."""
    keys = {_product_key(p).lower() for p in known_products}
    tokens = set(re.findall(r"[a-z][\w-]*", question.lower()))
    return {t for t in tokens
            if t not in FRAMING_WORDS and t not in keys
            and not re.fullmatch(r"[a-z]{1,3}\d{1,3}", t)}


def _is_product_switch_ellipsis(question: str,
                                known_products: list) -> bool:
    """"And the RD98XS?" — a product is named and NOTHING topical remains.

    Zero content tokens, strictly: a single leftover token is already a
    topic ("the weight of the RD98XS?" leaves {weight}) and must stand
    alone rather than inherit the previous turn's topic.
    """
    return len(_content_tokens(question, known_products)) == 0


def _last_topical_user_turn(conversation_history: list,
                            known_products: list) -> str:
    """The most recent user turn that actually carries a topic.

    Elliptical turns ("And the HR106X?") are skipped automatically because
    they have no content tokens, so a chain of product switches keeps
    inheriting the original topical question.
    """
    for turn in reversed(conversation_history):
        if turn.get("role") != "user":
            continue
        content = turn.get("content", "")
        if len(_content_tokens(content, known_products)) >= 2:
            return content
    return ""


def _is_code_switch_ellipsis(question: str,
                             known_products: list) -> bool:
    """"And E3?" — a code is named and nothing topical remains.

    Besides zero content tokens, the question must be genuinely elliptical:
    at most two alpha tokens or an explicit elliptical opener. This keeps
    a definitional "What is IP68?" standalone instead of inheriting an
    unrelated previous topic.
    """
    if _content_tokens(question, known_products):
        return False
    alpha_tokens = re.findall(r"[a-z][\w-]*", question.lower())
    return len(alpha_tokens) <= 2 or _is_elliptical(question)


def _swap_code(topic_question: str, new_code: str,
               known_products: list) -> str:
    """Carry the topic over to the newly named code, keeping everything
    else (including the product) intact. Empty result means the topical
    turn had no code to swap — caller falls back to leaving the question
    unchanged."""
    old_codes = set(_codes_in_text(topic_question, known_products))
    if not old_codes:
        return ""
    swapped = topic_question
    for old in old_codes:
        swapped = re.sub(r"\b" + re.escape(old) + r"\b", new_code,
                         swapped, flags=re.IGNORECASE)
    return swapped


def _swap_product(topic_question: str, new_product: str,
                  known_products: list) -> str:
    """Carry the topic over to the newly named product.

    Full labels are replaced before bare keys so "HR652 Digital Repeater"
    cannot degrade into "<new label> Digital Repeater". If the topical
    question named no product at all (it used a pronoun), the new product
    is appended the same way pronoun resolution does.
    """
    swapped = topic_question
    replaced = False
    for product in known_products:
        if product == new_product:
            continue
        new = re.subn(re.escape(product), new_product, swapped,
                      flags=re.IGNORECASE)
        if new[1]:
            swapped, replaced = new[0], True
        key_pattern = r"\b" + re.escape(_product_key(product)) + r"[\w-]*"
        new = re.subn(key_pattern, new_product, swapped, flags=re.IGNORECASE)
        if new[1]:
            swapped, replaced = new[0], True
    if replaced:
        return swapped
    return f"{topic_question} (the {new_product})"


def rewrite_query(question: str, conversation_history: list) -> str:
    """
    Gate-based rewriter:
    ۱. اگه history نیست → برگردون
    ۲. اگه سوال خودش محصول داره → برگردون
    ۳. امتیاز dependency رو حساب کن
    ۴. اگه standalone → برگردون (default محافظه‌کارانه)
    ۵. فقط اگه dependency قوی بود → مرجع رو قطعی الحاق کن

    The resolution itself is DETERMINISTIC: the resolved entity is appended
    in parentheses, the original wording untouched. An LLM rewrite was tried
    here first and was unreliable in both directions on the 8B model — at
    temperature=0 it deterministically echoed some phrasings unresolved
    ("How do I install it?"), and few-shot prompting made it answer with
    multi-paragraph reasoning essays instead of a query. Retrieval does not
    need grammar: hybrid search and query expansion handle the parenthetical
    fine, and downstream product detection reads the entity from it.
    """
    if not conversation_history:
        return question

    known_products = _get_known_products()

    # سوال خودش محصول صریح داره:
    #   - اگه موضوع هم داره → standalone، دست نزن
    #   - اگه فقط تعویض محصوله ("And the RD98XS?") → موضوعِ نوبتِ
    #     موضوع‌دارِ قبلی رو با محصول جدید به ارث ببر
    if _question_mentions_known_product(question, known_products):
        if _is_product_switch_ellipsis(question, known_products):
            topic = _last_topical_user_turn(
                conversation_history, known_products)
            if topic:
                new_product = _keys_in_text(question, known_products)[0]
                return _swap_product(topic, new_product, known_products)
        return question

    # تعویض کد ("And E3?" بعد از سوال درباره‌ی E2): موضوع و محصولِ نوبتِ
    # موضوع‌دارِ قبلی حفظ می‌شود، فقط کد عوض می‌شود
    codes_now = _codes_in_text(question, known_products)
    if codes_now and _is_code_switch_ellipsis(question, known_products):
        topic = _last_topical_user_turn(conversation_history, known_products)
        if topic:
            swapped = _swap_code(topic, codes_now[0], known_products)
            if swapped:
                return swapped

    # امتیاز dependency
    score = _context_dependency_score(question)

    # Default محافظه‌کارانه: اگه شک داری، rewrite نکن
    if score <= 0:
        return question

    stack = _product_stack(conversation_history, known_products)
    if not stack:
        return question

    # "the previous one" / "the other one" → stack[1]. با عبارت مقایسه‌ای
    # یا ضمیر همراهش ("compare it with the previous one") هر دو محصول
    # ضمیمه می‌شن تا مسیر مقایسه هر دو رو صریح ببینه.
    if _PREVIOUS_REF_RE.search(question) and len(stack) >= 2:
        wants_both = (_has_pronoun(question)
                      or bool(set(re.findall(r"[a-z]+", question.lower()))
                              & _COMPARE_WORDS))
        if wants_both:
            return f"{question} (the {stack[0]} and the {stack[1]})"
        return f"{question} (the {stack[1]})"

    return f"{question} (the {stack[0]})"