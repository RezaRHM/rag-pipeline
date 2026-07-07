"""
generation/detector.py
─────────────────────────────────────────────────────────
تشخیص می‌ده آیا سوال به اندازه کافی مشخصه که بشه جواب داد،
یا نیاز به clarification از کاربر داریم.

ANSWER:        سوال کافیه، جواب رو generate کن
CLARIFICATION: سوال مبهمه، باید از کاربر بپرسیم
─────────────────────────────────────────────────────────
"""

import re
import json
import requests

import config

VALID_DECISIONS = {"ANSWER", "CLARIFICATION"}

DETECTOR_PROMPT = """You are deciding whether a technical question is
specific enough to answer from documentation, or whether it needs
clarification first.

Available products in the system: {known_products}

Question: {question}

Decide:
- ANSWER: the question is specific enough to search documentation and
  answer directly (even if the answer might not be found)
- CLARIFICATION: the question is too ambiguous to answer without more
  context from the user (e.g. asks about "the device" without specifying
  which product, or is completely off-topic)

Return JSON only: {{"decision": "...", "reason": "..."}}"""


def detect_intent(question: str, known_products: list) -> dict:
    """
    برمی‌گردونه: {{"decision": "ANSWER"/"CLARIFICATION", "reason": "..."}}
    fallback: ANSWER (به جای block کردن، بهتره بریم جواب بدیم)
    """
    prompt = DETECTOR_PROMPT.format(
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
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"decision": "ANSWER", "reason": "fallback"}

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return {"decision": "ANSWER", "reason": "fallback"}

    decision = result.get("decision", "ANSWER")
    if decision not in VALID_DECISIONS:
        decision = "ANSWER"

    return {
        "decision": decision,
        "reason": result.get("reason", "")
    }