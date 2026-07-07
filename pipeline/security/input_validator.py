"""
security/input_validator.py
─────────────────────────────────────────────────────────
سوال کاربر رو قبل از ورود به pipeline چک میکنه —
prompt injection، دستورات مخرب، و محتوای نامرتبط.

این یه لایه سبک و سریعه — فقط pattern matching،
بدون LLM call.
─────────────────────────────────────────────────────────
"""

import re

INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions",
    r"you\s+are\s+now\s+(a|an)",
    r"act\s+as\s+(a|an)",
    r"forget\s+(everything|all|your)",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*instruction",
]

MAX_QUESTION_LENGTH = 1000


def validate_input(question: str) -> dict:
    """
    سوال رو چک میکنه.

    برمیگردونه:
      valid: True/False
      reason: توضیح اگه invalid بود
    """
    if not question or not question.strip():
        return {"valid": False, "reason": "empty_question"}

    if len(question) > MAX_QUESTION_LENGTH:
        return {"valid": False, "reason": "question_too_long"}

    question_lower = question.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, question_lower):
            return {"valid": False, "reason": "prompt_injection_detected"}

    return {"valid": True, "reason": None}