"""
diagnose_retrieval.py
─────────────────────────────────────────────────────────
قبل از حدس زدن راه‌حل، بیا دقیق ببینیم چرا chunk درست
نیومد. این اسکریپت ۸ تا نزدیک‌ترین chunk رو با متن کامل
نشون می‌ده.
─────────────────────────────────────────────────────────
"""

import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_API_KEY  = os.getenv("LITELLM_API_KEY", "sk-dry-run-key")
QDRANT_HOST      = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT      = int(os.getenv("QDRANT_PORT", 6333))
MODEL_EMBEDDING  = os.getenv("MODEL_EMBEDDING", "bge-m3")

COLLECTION_NAME = "rohill_documents"

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def get_embedding(text: str) -> list:
    response = requests.post(
        f"{LITELLM_BASE_URL}/v1/embeddings",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_API_KEY}"
        },
        json={"model": MODEL_EMBEDDING, "input": text},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


question = "What should I check after installation is complete?"
vector = get_embedding(question)

results = qdrant.search(
    collection_name=COLLECTION_NAME,
    query_vector=vector,
    limit=8
)

print(f"Question: {question}\n")
for r in results:
    print(f"[score={r.score:.3f}] {r.payload['chunk_id']} (page {r.payload['page_number']})")
    print(f"  {r.payload['text']}")
    print()