"""
security/guard.py
─────────────────────────────────────────────────────────
چک میکنه سوال اصلاً مرتبط با حوزه کاریمونه —
radio equipment, repeaters, base stations.

یه LLM call سبک — فقط بله/خیر.
─────────────────────────────────────────────────────────
"""

import re
import json
import requests

import config

GUARD_PROMPT = """You are a topic guard for a radio communication
equipment support system (repeaters, base stations, antennas,
DMR/TETRA protocols, RF equipment).

Question: {question}

Is this question related to radio communication equipment, technical
support, or the products in our system?

Return JSON only: {{"on_topic": true/false, "reason": "..."}}"""


def check_topic(question: str) -> dict:
    """
    برمیگردونه: {{"on_topic": True/False, "reason": "..."}}
    fallback: on_topic=True (بهتره اشتباه قبول کنیم تا اشتباه رد کنیم)
    """
    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LITELLM_API_KEY}"
        },
        json={
            "model": config.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": GUARD_PROMPT.format(
                question=question
            )}]
        },
        timeout=30
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"on_topic": True, "reason": "fallback"}

    try:
        result = json.loads(match.group())
        return {
            "on_topic": bool(result.get("on_topic", True)),
            "reason": result.get("reason", "")
        }
    except json.JSONDecodeError:
        return {"on_topic": True, "reason": "fallback"}