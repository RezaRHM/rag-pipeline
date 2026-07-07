"""
02_query_test.py
─────────────────────────────────────────────────────────
قدم سوم: یه سوال واقعی بپرس و ببین end-to-end RAG
loop کار می‌کنه یا نه.

جریان:
  1. سوال رو embed کن
  2. توی Qdrant نزدیک‌ترین chunk ها رو پیدا کن
  3. اون chunk ها رو به LLM بده
  4. جواب رو چاپ کن
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
MODEL_LLAMA      = os.getenv("MODEL_LLAMA", "llama3.2-3b")

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


def retrieve(question: str, top_k: int = 3) -> list:
    """سوال رو embed کن و نزدیک‌ترین chunk ها رو از Qdrant بگیر"""
    question_vector = get_embedding(question)

    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=question_vector,
        limit=top_k
    )
    return results


def build_prompt(question: str, chunks: list) -> str:
    """chunk های retrieve شده رو با سوال ترکیب کن"""
    context = "\n\n".join([
        f"[Source: {c.payload['section']}]\n{c.payload['text']}"
        for c in chunks
    ])

    return f"""You are a technical assistant for Rohill. Answer the question
using ONLY the context below. If the answer is not in the context,
say so clearly. Cite the page number when relevant.

Context:
{context}

Question: {question}

Answer:"""


def generate(prompt: str) -> str:
    """prompt رو به LLM بفرست و جواب بگیر"""
    response = requests.post(
        f"{LITELLM_BASE_URL}/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_API_KEY}"
        },
        json={
            "model": MODEL_LLAMA,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def ask(question: str):
    print("=" * 60)
    print(f"Question: {question}")
    print("=" * 60)

    # مرحله ۱: retrieval
    chunks = retrieve(question)
    print(f"\nRetrieved {len(chunks)} chunks:")
    for c in chunks:
        print(f"  [score={c.score:.3f}] {c.payload['chunk_id']}: "
              f"{c.payload['text'][:60]}...")

    # مرحله ۲: prompt building
    prompt = build_prompt(question, chunks)

    # مرحله ۳: generation
    print("\nGenerating answer...")
    answer = generate(prompt)

    print(f"\nAnswer:\n{answer}")
    print()


if __name__ == "__main__":
    # سوال‌هایی متناسب با مانوال واقعی RD982S Digital Repeater
    ask("How do I install the duplexer in the repeater?")
    ask("What should I check after installation is complete?")
    ask("What does the alarm indicator mean when it glows red?")
    ask("What is the price of the RD982S?")