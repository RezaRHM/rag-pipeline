"""
benchmark_retrieval.py
─────────────────────────────────────────────────────────
مقایسه retrieval قبل (dense-only) و بعد (hybrid + rerank)
از تغییراتی که توی فاز ۱ دادیم.

این نسخه بر اساس محتوای واقعی chunk چک می‌کنه، نه فقط
عنوان heading — چون نسخه قبلی benchmark نشون داد که
matching بر اساس heading گمراه‌کننده‌ست.
─────────────────────────────────────────────────────────
"""

import config
from db.connection import get_qdrant
from retrieval.embedder import embed_dense
from retrieval.retriever import hybrid_search
from retrieval.reranker import rerank


TEST_CASES = [
    {
        "question": "How do I install the duplexer in the repeater?",
        "expected_keywords": ["duplexer", "install"],
    },
    {
        "question": "What should I check after installation is complete?",
        "expected_keywords": ["post-installation"],
    },
    {
        "question": "What does the alarm indicator mean when it glows red?",
        "expected_keywords": ["alarm indicator glows red"],
    },
    {
        "question": "What does the LED indicator show on the HR652?",
        "expected_keywords": ["LED"],
    },
    {
        "question": "What does error code H5 mean?",
        "expected_keywords": ["H5", "DHCP"],
    },
    {
        "question": "What is alarm E1?",
        "expected_keywords": ["E1", "battery"],
    },
]


def naive_dense_search(question: str, limit: int = 5) -> list:
    """جستجوی ساده dense-only — معادل نسخه اول pipeline"""
    qdrant = get_qdrant()
    vec = embed_dense(question)
    results = qdrant.query_points(
        collection_name=config.QDRANT_COLLECTION,
        query=vec,
        using="dense",
        limit=limit,
        with_payload=True
    )
    return results.points


def find_rank(results: list, expected_keywords: list):
    for i, r in enumerate(results, start=1):
        text = r.payload.get("text", "").lower()
        if all(kw.lower() in text for kw in expected_keywords):
            return i
    return None


def run_benchmark():
    print(f"{'Question':<52} {'Naive':<10} {'Improved':<10}")
    print("-" * 75)

    naive_hits = 0
    improved_hits = 0
    naive_ranks = []
    improved_ranks = []

    for case in TEST_CASES:
        q = case["question"]
        expected = case["expected_keywords"]

        naive_results = naive_dense_search(q, limit=5)
        naive_rank = find_rank(naive_results, expected)

        candidates = hybrid_search(q, limit=15)
        improved_results = rerank(q, candidates, top_k=5)
        improved_rank = find_rank(improved_results, expected)

        if naive_rank:
            naive_hits += 1
            naive_ranks.append(naive_rank)
        if improved_rank:
            improved_hits += 1
            improved_ranks.append(improved_rank)

        n_str = str(naive_rank) if naive_rank else "miss"
        i_str = str(improved_rank) if improved_rank else "miss"
        print(f"{q[:50]:<52} {n_str:<10} {i_str:<10}")

    print("-" * 75)
    print(f"\nHit rate (found in top-5):")
    print(f"  Naive:    {naive_hits}/{len(TEST_CASES)}")
    print(f"  Improved: {improved_hits}/{len(TEST_CASES)}")

    if naive_ranks:
        print(f"\nAverage rank (when found):")
        print(f"  Naive:    {sum(naive_ranks)/len(naive_ranks):.1f}")
    if improved_ranks:
        print(f"  Improved: {sum(improved_ranks)/len(improved_ranks):.1f}")


if __name__ == "__main__":
    run_benchmark()