"""
01_index_sample.py
─────────────────────────────────────────────────────────
قدم دوم: یه collection توی Qdrant بساز و چند تا
chunk نمونه رو embed و index کن.

این هنوز خیلی ساده‌ست — بدون chunking پیچیده،
بدون metadata کامل. فقط می‌خوایم ببینیم
end-to-end کار می‌کنه.
─────────────────────────────────────────────────────────
"""

import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

load_dotenv()

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_API_KEY  = os.getenv("LITELLM_API_KEY", "sk-dry-run-key")
QDRANT_HOST      = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT      = int(os.getenv("QDRANT_PORT", 6333))
MODEL_EMBEDDING  = os.getenv("MODEL_EMBEDDING", "bge-m3")

COLLECTION_NAME = "rohill_documents"
VECTOR_SIZE = 1024  # BGE-M3 output dimension


def get_embedding(text: str) -> list:
    """یه متن رو می‌گیره و vector برمی‌گردونه"""
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


# ── قدم ۱: ساخت Collection ──────────────────────────────
print("=" * 50)
print("Step 1: Creating Qdrant collection")
print("=" * 50)

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

if qdrant.collection_exists(COLLECTION_NAME):
    print(f"Collection '{COLLECTION_NAME}' already exists. Deleting it to start fresh.")
    qdrant.delete_collection(COLLECTION_NAME)

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
)
print(f"✓ Collection '{COLLECTION_NAME}' created")
print()


# ── قدم ۲: داده نمونه (شبیه یه مانوال فنی) ───────────────
# این متن‌ها رو فعلاً دستی نوشتیم — نه از یه PDF واقعی.
# هدف اینه که ببینیم pipeline به صورت end-to-end کار می‌کنه.

sample_chunks = [
    {
        "chunk_id": "chunk_001",
        "text": "The TRB-1900 base station supports the TETRA standard "
                "EN 300 392. Maximum transmit power is 40 watts per carrier.",
        "page_number": 12
    },
    {
        "chunk_id": "chunk_002",
        "text": "Operating temperature range for the TRB-1900 is from "
                "-20 degrees Celsius to +55 degrees Celsius.",
        "page_number": 23
    },
    {
        "chunk_id": "chunk_003",
        "text": "For cold weather environments below -20 degrees Celsius, "
                "the HK-400 Heating Kit accessory is required for proper operation.",
        "page_number": 45
    },
    {
        "chunk_id": "chunk_004",
        "text": "The TRB-1900 has an IP65 ingress protection rating, making "
                "it suitable for outdoor installation in most weather conditions.",
        "page_number": 18
    },
]


# ── قدم ۳: Embed و Index هر chunk ────────────────────────
print("=" * 50)
print("Step 2: Embedding and indexing chunks")
print("=" * 50)

points = []
for i, chunk in enumerate(sample_chunks):
    print(f"Embedding {chunk['chunk_id']}...")
    vector = get_embedding(chunk["text"])

    points.append(
        PointStruct(
            id=i + 1,
            vector=vector,
            payload={
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_number": chunk["page_number"],
                "product": "TRB-1900",
                "doc_type": "manual",
                "is_latest": True
            }
        )
    )

qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
print(f"✓ Indexed {len(points)} chunks")
print()


# ── قدم ۴: تأیید ─────────────────────────────────────────
print("=" * 50)
print("Step 3: Verification")
print("=" * 50)

info = qdrant.get_collection(COLLECTION_NAME)
print(f"Collection: {COLLECTION_NAME}")
print(f"Points count: {info.points_count}")
print(f"Vector size: {info.config.params.vectors.size}")
print()
print("Done. You can now run 02_query_test.py to test retrieval.")
