"""
04_index_docling.py
─────────────────────────────────────────────────────────
قدم پنجم: section-aware chunking با Docling.

به جای بریدن بر اساس تعداد کلمه، از heading های واقعی
سند (که Docling تشخیص داده) به عنوان مرز chunk استفاده
می‌کنیم. این مشکل chunk boundary رو ریشه‌ای حل می‌کنه.
─────────────────────────────────────────────────────────
"""

import os
import re
import requests
from pathlib import Path
from docling.document_converter import DocumentConverter
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

MAX_CHUNK_WORDS = 350   # اگه section از این بزرگ‌تر بود، می‌شکنیمش
SUB_CHUNK_WORDS = 200
SUB_CHUNK_OVERLAP = 30


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


def parse_with_docling(pdf_path: Path) -> str:
    """PDF رو با Docling به Markdown تبدیل می‌کنه"""
    print("Parsing PDF with Docling (may take a minute)...")
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()


def split_by_headings(markdown_text: str) -> list:
    """
    متن Markdown رو بر اساس heading ها (## ...) تقسیم می‌کنه.
    هر بخش شامل خود heading + متن زیرش تا heading بعدی می‌شه.
    """
    # خط‌هایی که با ## شروع می‌شن (و فهرست مطالب با نقطه‌چین رو حذف می‌کنیم)
    lines = markdown_text.split("\n")

    sections = []
    current_heading = "Introduction"
    current_text = []

    for line in lines:
        # تشخیص heading واقعی (نه خط فهرست مطالب که نقطه‌چین داره)
        is_heading = re.match(r"^#{1,3}\s+", line) and "...." not in line

        if is_heading:
            # section قبلی رو ذخیره کن
            if current_text:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_text).strip()
                })
            current_heading = line.lstrip("#").strip()
            current_text = []
        else:
            current_text.append(line)

    # آخرین section
    if current_text:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_text).strip()
        })

    # section های خالی یا خیلی کوتاه (مثل فهرست مطالب) رو فیلتر کن
    sections = [s for s in sections if len(s["text"].split()) > 5]

    return sections


def maybe_split_large_section(section: dict) -> list:
    """
    اگه section خیلی بزرگ بود، به sub-chunk های کوچیک‌تر می‌شکنه.
    عنوان heading رو به هر sub-chunk اضافه می‌کنه تا context حفظ بشه.
    """
    words = section["text"].split()

    if len(words) <= MAX_CHUNK_WORDS:
        return [{
            "heading": section["heading"],
            "text": f"## {section['heading']}\n{section['text']}"
        }]

    # section بزرگه — بشکنش، ولی heading رو به هر تیکه اضافه کن
    sub_chunks = []
    start = 0
    while start < len(words):
        end = start + SUB_CHUNK_WORDS
        chunk_words = words[start:end]
        sub_chunks.append({
            "heading": section["heading"],
            "text": f"## {section['heading']}\n" + " ".join(chunk_words)
        })
        start += SUB_CHUNK_WORDS - SUB_CHUNK_OVERLAP

    return sub_chunks


# ── قدم ۱: Parse با Docling ──────────────────────────────
print("=" * 50)
print("Step 1: Parsing PDF with Docling")
print("=" * 50)

markdown_text = parse_with_docling(PDF_PATH)
print(f"✓ Parsed. Total length: {len(markdown_text)} characters")
print()


# ── قدم ۲: تقسیم بر اساس heading ─────────────────────────
print("=" * 50)
print("Step 2: Splitting by document headings")
print("=" * 50)

sections = split_by_headings(markdown_text)
print(f"✓ Found {len(sections)} sections")
for s in sections[:10]:
    word_count = len(s["text"].split())
    print(f"  - {s['heading'][:50]:50s} ({word_count} words)")
if len(sections) > 10:
    print(f"  ... and {len(sections) - 10} more")
print()


# ── قدم ۳: شکستن section های بزرگ ────────────────────────
print("=" * 50)
print("Step 3: Splitting oversized sections")
print("=" * 50)

all_chunks = []
for section in sections:
    all_chunks.extend(maybe_split_large_section(section))

print(f"✓ Final chunk count: {len(all_chunks)}")
print()


# ── قدم ۴: ساخت Collection ───────────────────────────────
print("=" * 50)
print("Step 4: Setting up Qdrant collection")
print("=" * 50)

qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

if qdrant.collection_exists(COLLECTION_NAME):
    print(f"Collection '{COLLECTION_NAME}' exists. Deleting to start fresh.")
    qdrant.delete_collection(COLLECTION_NAME)

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
)
print(f"✓ Collection created")
print()


# ── قدم ۵: Embed و Index ─────────────────────────────────
print("=" * 50)
print(f"Step 5: Embedding and indexing {len(all_chunks)} chunks")
print("=" * 50)

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
                "section": chunk["heading"],
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

print("Done. Run 02_query_test.py again to compare results.")