"""
test_connection.py
─────────────────────────────────────────────────────────
اولین قدم: مطمئن شیم به همه سرویس‌ها وصل می‌شیم.

این اسکریپت سه چیز رو تست می‌کنه:
  1. آیا .env درست خونده می‌شه؟
  2. آیا به Qdrant وصل می‌شیم؟
  3. آیا از طریق LiteLLM می‌تونیم embedding بگیریم؟
─────────────────────────────────────────────────────────
"""

import os
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# ── قدم ۱: خواندن .env ──────────────────────────────────
load_dotenv()

LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_API_KEY  = os.getenv("LITELLM_API_KEY", "sk-dry-run-key")
QDRANT_HOST      = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT      = int(os.getenv("QDRANT_PORT", 6333))
MODEL_EMBEDDING  = os.getenv("MODEL_EMBEDDING", "bge-m3")

print("=" * 50)
print("Step 1: Environment variables loaded")
print("=" * 50)
print(f"LiteLLM URL:     {LITELLM_BASE_URL}")
print(f"Qdrant:          {QDRANT_HOST}:{QDRANT_PORT}")
print(f"Embedding model: {MODEL_EMBEDDING}")
print()


# ── قدم ۲: تست اتصال به Qdrant ──────────────────────────
print("=" * 50)
print("Step 2: Testing Qdrant connection")
print("=" * 50)

try:
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    collections = qdrant.get_collections()
    print(f"✓ Connected to Qdrant")
    print(f"  Existing collections: {[c.name for c in collections.collections]}")
except Exception as e:
    print(f"✗ Failed to connect to Qdrant: {e}")
print()


# ── قدم ۳: تست embedding از طریق LiteLLM ────────────────
print("=" * 50)
print("Step 3: Testing embedding via LiteLLM")
print("=" * 50)

try:
    response = requests.post(
        f"{LITELLM_BASE_URL}/v1/embeddings",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_API_KEY}"
        },
        json={
            "model": MODEL_EMBEDDING,
            "input": "TRB-1900 maximum transmit power"
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()
    vector = data["data"][0]["embedding"]

    print(f"✓ Embedding received")
    print(f"  Vector dimensions: {len(vector)}")
    print(f"  First 3 values: {vector[:3]}")
except Exception as e:
    print(f"✗ Failed to get embedding: {e}")
print()


print("=" * 50)
print("All connectivity tests complete.")
print("=" * 50)
