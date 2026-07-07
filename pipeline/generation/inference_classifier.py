"""
generation/inference_classifier.py
─────────────────────────────────────────────────────────
بعد از generation، تشخیص می‌ده جواب LLM چقدر مستقیم
از context اومده — برای سناریوهای نیاز به شفافیت بیشتر.

DIRECT:      جواب مستقیماً از context کپی/خلاصه شده
TECHNICAL:   جواب نیاز به استنتاج فنی داشته (مثل محاسبه)
SPECULATION: جواب فراتر از context رفته (خطرناک!)
─────────────────────────────────────────────────────────
"""

import re
import json
import requests

import config

VALID_INFERENCE_TYPES = {"DIRECT", "TECHNICAL", "SPECULATION"}

INFERENCE_PROMPT = """You evaluated a RAG system response. Given the
context used and the answer generated, classify HOW the answer was derived.

Context:
{context}

Question: {question}

Answer: {answer}

Choose exactly ONE label:
- DIRECT: the answer is a direct quote or straightforward summary of
  the context — no reasoning beyond what's stated
- TECHNICAL: the answer required technical inference or calculation
  beyond what's literally in the context (e.g. combining two facts,
  unit conversion, applying a rule to a situation)
- SPECULATION: the answer goes beyond what the context supports —
  contains guesses, assumptions, or outside knowledge

Return JSON only: {{"inference_type": "..."}}"""


def classify_inference_type(question: str,
                             answer: str,
                             chunks: list) -> str:
    """
    برمی‌گردونه: DIRECT / TECHNICAL / SPECULATION
    fallback: DIRECT (امن‌ترین حالت)
    """
    context = "\n\n".join([c.payload.get("text", "") for c in chunks])

    prompt = INFERENCE_PROMPT.format(
        context=context,
        question=question,
        answer=answer
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
        return "DIRECT"

    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return "DIRECT"

    inference_type = result.get("inference_type", "DIRECT")
    if inference_type not in VALID_INFERENCE_TYPES:
        inference_type = "DIRECT"

    return inference_type