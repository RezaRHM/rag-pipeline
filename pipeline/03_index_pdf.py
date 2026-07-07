"""
03_index_pdf.py
─────────────────────────────────────────────────────────
قدم چهارم: یه PDF واقعی رو parse، chunk، embed و index کن.

این هنوز fixed-size chunking ساده‌ست (نه semantic chunking) —
طبق همون اصلی که گفتیم: اول ساده، بعد با RAGAS بسنجیم،
بعد پیچیده‌ترش کنیم.
─────────────────────────────────────────────────────────
"""

import os
import requests
from pathlib import Path
from pypdf import PdfReader
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
VECTOR_SIZE = 1024

PDF_PATH = Path(__file__).parent.parent / "data" / "documents" / \
           "Hytera_RD982S_Digital_Repeater_User_Manual_R8.5_eng.pdf"

CHUNK_SIZE_WORDS = 200   # هر chunk تقریباً ۲۰۰ کلمه
CHUNK_OVERLAP_WORDS = 30  # ۳۰ کلمه overlap بین chunk های مجاور


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


def extract_pages(pdf_path: Path) -> list:
    """هر صفحه PDF رو جداگانه متن استخراج می‌کنه"""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"page_number": i + 1, "text": text})
    return pages


def chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """متن رو به chunk های با اندازه ثابت (بر اساس تعداد کلمه) تقسیم می‌کنه"""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap
    return chunks


# ── قدم ۱: استخراج متن از PDF ────────────────────────────
print("=" * 50)
print("Step 1: Extracting text from PDF")
print("=" * 50)

pages = extract_pages(PDF_PATH)
print(f"✓ Extracted {len(pages)} pages with text")
total_words = sum(len(p["text"].split()) for p in pages)
print(f"  Total words: {total_words}")
print()


# ── قدم ۲: Chunking ──────────────────────────────────────
print("=" * 50)
print("Step 2: Chunking text")
print("=" * 50)

all_chunks = []
for page in pages:
    page_chunks = chunk_text(page["text"], CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS)
    for chunk_text_content in page_chunks:
        all_chunks.append({
            "text": chunk_text_content,
            "page_number": page["page_number"]
        })

print(f"✓ Created {len(all_chunks)} chunks")
print(f"  Average chunk size: ~{CHUNK_SIZE_WORDS} words")
print()


# ── قدم ۳: ساخت Collection ───────────────────────────────
print("=" * 50)
print("Step 3: Setting up Qdrant collection")
print("=" * 50)

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

if qdrant.collection_exists(COLLECTION_NAME):
    print(f"Collection '{COLLECTION_NAME}' already exists. Deleting to start fresh.")
    qdrant.delete_collection(COLLECTION_NAME)

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
)
print(f"✓ Collection '{COLLECTION_NAME}' created")
print()


# ── قدم ۴: Embed و Index هر chunk ────────────────────────
print("=" * 50)
print(f"Step 4: Embedding and indexing {len(all_chunks)} chunks")
print("=" * 50)
print("This may take a minute...")

points = []
for i, chunk in enumerate(all_chunks):
    if (i + 1) % 10 == 0 or i == len(all_chunks) - 1:
        print(f"  Progress: {i + 1}/{len(all_chunks)}")

    vector = get_embedding(chunk["text"])

    points.append(
        PointStruct(
            id=i + 1,
            vector=vector,
            payload={
                "chunk_id": f"chunk_{i+1:04d}",
                "text": chunk["text"],
                "page_number": chunk["page_number"],
                "product": "RD982S",
                "doc_type": "manual",
                "source_file": PDF_PATH.name,
                "is_latest": True
            }
        )
    )

qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
print(f"✓ Indexed {len(points)} chunks")
print()


# ── قدم ۵: تأیید ─────────────────────────────────────────
print("=" * 50)
print("Step 5: Verification")
print("=" * 50)

info = qdrant.get_collection(COLLECTION_NAME)
print(f"Collection: {COLLECTION_NAME}")
print(f"Points count: {info.points_count}")
print()
print("Done. You can now run 02_query_test.py to ask questions about this manual.")
