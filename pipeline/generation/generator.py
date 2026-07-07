"""
generation/generator.py
─────────────────────────────────────────────────────────
prompt نهایی رو می‌سازه و از LiteLLM جواب می‌گیره.

اگه quality_assessor تشخیص بده اطلاعات کافی نیست، اصلاً
LLM رو صدا نمی‌زنه — مستقیم پیام «اطلاعات موجود نیست»
رو برمی‌گردونه. این از hallucination جلوگیری می‌کنه.
─────────────────────────────────────────────────────────
"""

import requests

import config
from prompts.prompts import build_generation_prompt, NO_RESULTS_PROMPT
from generation.quality_assessor import assess_retrieval_quality


def call_llm(prompt: str, model: str = None) -> str:
    """LiteLLM رو صدا می‌زنه و جواب رو برمی‌گردونه"""
    model = model or config.DEFAULT_MODEL

    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LITELLM_API_KEY}"
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=config.LLM_TIMEOUT
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_answer(question: str, chunks: list, model: str = None) -> dict:
    """
    جریان کامل generation:
      ۱. کیفیت retrieval رو چک کن
      ۲. اگه کافی نبود، بدون صدا زدن LLM جواب «نداریم» بده
      ۳. اگه کافی بود، prompt بساز و از LLM جواب بگیر
    """
    quality = assess_retrieval_quality(chunks)

    if quality["status"] in ("no_results", "low_confidence"):
        return {
            "answer": ("No relevant information was found in the "
                      "available documentation for this question. "
                      "Please contact Rohill technical support directly."),
            "source": "no_results",
            "confidence": quality["confidence"],
            "chunks_used": []
        }

    prompt = build_generation_prompt(question, chunks)
    answer = call_llm(prompt, model=model)

    return {
        "answer": answer,
        "source": "generated",
        "confidence": quality["confidence"],
        "chunks_used": [c.payload["chunk_id"] for c in chunks]
    }