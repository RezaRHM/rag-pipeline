"""
query/query_analyzer.py
─────────────────────────────────────────────────────────
سوال کاربر رو تحلیل می‌کنه:
  ۱. نوع سوال چیه؟ (standard/procedural/specification/comparison)
  ۲. کدوم محصول/entity توی سوال اشاره شده؟
  ۳. آیا اون entity واقعاً توی اسناد ما هست؟ (validation + fuzzy match)

نتیجه این تحلیل مستقیماً به retriever.py داده می‌شه تا
metadata filter خودکار اعمال بشه — حل مشکل "قاطی شدن
جواب از چند محصول مختلف".
─────────────────────────────────────────────────────────
"""

import re
import json
import requests

import config
from db.connection import get_postgres


ANALYZER_PROMPT = """You are analyzing a question for a technical RAG
system about radio communication equipment (repeaters, base stations).

Known products in the system: {known_products}

Question: {question}

Determine:
1. query_type: one of [standard, procedural, specification, comparison]
   - procedural: asks "how to" do something (install, configure, replace)
   - specification: asks for technical specs/numbers (power, range, frequency)
   - comparison: compares two or more products
   - standard: anything else (general questions, troubleshooting, alarms)

2. product: which specific product is being asked about, if any.
   Use EXACTLY one of the known products listed above, or null if
   the question is general / doesn't mention a specific product.

Return JSON only, no other text:
{{"query_type": "...", "product": "..." or null}}"""
VALID_QUERY_TYPES = {"standard", "procedural", "specification", "comparison"}


def _get_known_products() -> list:
    """لیست محصولاتی که توی PostgreSQL ثبت شدن رو برمی‌گردونه"""
    pg = get_postgres()
    cur = pg.cursor()
    cur.execute("SELECT DISTINCT product FROM documents WHERE product != 'unknown'")
    products = [row["product"] for row in cur.fetchall()]
    pg.close()
    return products


def _fuzzy_match_product(suggested: str, known_products: list) -> str:
    """
    اگه LLM یه چیزی پیشنهاد بده که دقیق match نشه، چک می‌کنه
    آیا یه substring از یکی از محصولات شناخته‌شده‌ست.
    مثلاً "RD982S" باید با "RD98XS Digital Repeater" match بشه
    چون X می‌تونه جای هر رقمی بشینه.
    """
    if not suggested:
        return None

    suggested_clean = suggested.upper().replace(" ", "")

    for product in known_products:
        product_clean = product.upper().replace(" ", "")

        # تطابق مستقیم
        if suggested_clean == product_clean:
            return product

        # تطابق با الگوی X (مثل RD98XS که X جای رقم می‌شینه)
        if "X" in product_clean:
            pattern = product_clean.replace("X", r"\d")
            if re.match(pattern, suggested_clean):
                return product

        # تطابق substring ساده
        if suggested_clean in product_clean or product_clean in suggested_clean:
            return product

    return None


def analyze_query(question: str) -> dict:
    """
    سوال رو تحلیل می‌کنه و query_type + product رو برمی‌گردونه.

    اگه LLM یه محصولی رو پیشنهاد بده که دقیقاً توی اسناد ما نیست،
    اول fuzzy match رو امتحان می‌کنیم (validation) تا فیلتر
    اشتباه باعث miss شدن نتایج نشه.
    """
    known_products = _get_known_products()

    prompt = ANALYZER_PROMPT.format(
        known_products=", ".join(known_products) if known_products else "none",
        question=question
    )

    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LITELLM_API_KEY}"
        },
        json={
            "model": config.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        },
        timeout=config.LLM_TIMEOUT
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"query_type": "standard", "product": None}

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return {"query_type": "standard", "product": None}

    # validation — اول دقیق چک کن، بعد fuzzy match
    product = result.get("product")
    if product not in known_products:
        product = _fuzzy_match_product(product, known_products)

    query_type = result.get("query_type", "standard")
    if query_type not in VALID_QUERY_TYPES:
        query_type = "standard"

    return {
        "query_type": query_type,
        "product": product
    }