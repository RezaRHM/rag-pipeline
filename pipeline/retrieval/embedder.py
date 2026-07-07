"""
retrieval/embedder.py
─────────────────────────────────────────────────────────
ساخت dense vector (BGE-M3 از طریق LiteLLM) و
sparse vector (BM25 از طریق fastembed) — برای hybrid search.

این ماژول هم موقع indexing استفاده میشه (embed کردن chunk ها)
هم موقع query (embed کردن سوال کاربر).
─────────────────────────────────────────────────────────
"""

import requests
from fastembed import SparseTextEmbedding

import config

# مدل BM25 رو یه بار load می‌کنیم — سنگینه، نباید هر بار بسازیمش
_sparse_model = None


def _get_sparse_model() -> SparseTextEmbedding:
    global _sparse_model
    if _sparse_model is None:
        print("Loading BM25 sparse model (first time only)...")
        _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _sparse_model


def embed_dense(text: str) -> list:
    """متن رو با BGE-M3 به یه dense vector با ۱۰۲۴ بعد تبدیل می‌کنه"""
    response = requests.post(
        f"{config.LITELLM_BASE_URL}/v1/embeddings",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LITELLM_API_KEY}"
        },
        json={"model": config.MODEL_EMBEDDING, "input": text},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def embed_sparse(text: str) -> dict:
    """
    متن رو با BM25 به sparse vector تبدیل می‌کنه — برای
    keyword matching دقیق (کدهای خطا، part number و...)
    """
    model = _get_sparse_model()
    result = list(model.embed([text]))[0]
    return {
        "indices": result.indices.tolist(),
        "values": result.values.tolist()
    }


def embed_hybrid(text: str) -> dict:
    """هر دو vector رو با هم می‌سازه"""
    return {
        "dense": embed_dense(text),
        "sparse": embed_sparse(text)
    }