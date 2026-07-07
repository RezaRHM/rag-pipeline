"""
generation/answer_classifier.py
─────────────────────────────────────────────────────────
قبل از generation، تشخیص می‌ده context چه نوع جوابی به
سوال می‌ده — برای انتخاب system prompt مناسب (سناریو ۹).

این طبقه‌بندی روی متن chunk های نهایی انجام می‌شه، نه
روی جواب نهایی LLM — چون باید قبل از generation اجرا بشه.
─────────────────────────────────────────────────────────
"""

import re
import json
import requests

import config

VALID_ANSWER_TYPES = {
    "EXPLICIT_YES", "EXPLICIT_NO", "IMPLICIT_NO", "PARTIAL", "NOT_FOUND"
}

CLASSIFIER_PROMPT = """Based on the context below, classify how well it
answers the question.

Context:
{context}

Question: {question}

Choose exactly ONE of these labels:
- EXPLICIT_YES: context directly and clearly answers the question
- EXPLICIT_NO: context directly states a negative answer
  (e.g. "X is not supported")
- IMPLICIT_NO: context implies a negative answer without stating it
  directly (e.g. only lists supported things, and the asked-about
  thing is absent from that list)
- PARTIAL: context has some relevant information but doesn't fully
  answer the question
- NOT_FOUND: context has no relevant information for this question

Return JSON only: {{"answer_type": "..."}}"""


def classify_answer_type(question: str, chunks: list) -> str:
    """
    برمی‌گردونه یکی از پنج مقدار VALID_ANSWER_TYPES.
    اگه LLM چیزی خارج از این پنج‌تا برگردونه یا parse نشه،
    fallback به PARTIAL می‌زنیم (امن‌ترین حالت پیش‌فرض).
    """
    context = "\n\n".join([c.payload.get("text", "") for c in chunks])

    prompt = CLASSIFIER_PROMPT.format(context=context, question=question)

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
        return "PARTIAL"

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return "PARTIAL"

    answer_type = result.get("answer_type", "PARTIAL")
    if answer_type not in VALID_ANSWER_TYPES:
        answer_type = "PARTIAL"

    return answer_type
