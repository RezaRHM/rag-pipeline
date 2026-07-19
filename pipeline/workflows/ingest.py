"""
workflows/ingest.py
─────────────────────────────────────────────────────────
فرآیند کامل ingestion — نسخه Hierarchical + Noise Cleanup.

تغییرات این نسخه (fix 1-4):
  ۱. skip فهرست مطالب + جدول‌های نقطه‌چین + section های فقط-تصویر
  ۲. exact dedupe در convert_tables_to_text
  ۳. حذف markdown artifacts (<!-- image -->)
  ۴. targeted orphan filtering (حذف "No.: 1"، نگه‌داری part names)
─────────────────────────────────────────────────────────
"""

import re
import json
import hashlib
import requests
from pathlib import Path
from docling.document_converter import DocumentConverter
from qdrant_client.models import PointStruct

import config
from db.connection import get_postgres, get_qdrant
from retrieval.embedder import embed_dense, embed_sparse


# ── مرحله ۱: Security Scan (placeholder) ─────────────────
def security_scan(text: str) -> dict:
    return {"safe": True}


# ── مرحله ۲: Metadata Auto-Extraction ────────────────────
def extract_metadata(text_sample: str, filename: str) -> dict:
    prompt = f"""You are analyzing a technical document for a radio
communications equipment knowledge base.

Filename: {filename}

Document excerpt:
---
{text_sample[:2000]}
---

Extract the following as JSON only, no other text:
{{
  "product": "the specific product model name/number, or 'general' if this document covers multiple products",
  "doc_type": "one of: manual, catalog, spec_sheet, release_note, guideline",
  "version": "version number if mentioned, otherwise 'unknown'"
}}"""

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
        timeout=60
    )
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"product": "unknown", "doc_type": "manual", "version": "unknown"}


def generate_chunk_questions(chunk_text: str, product: str) -> str:
    """سوالاتی که فقط این chunk جوابشونه (برای augmentation)."""
    prompt = f"""You are indexing technical documentation for {product}.

Given this chunk of text, write 3-5 specific questions that THIS chunk 
and ONLY this chunk can answer completely and precisely.

Rules:
- Questions must be answerable ONLY from the exact content below
- Do NOT write questions about topics that are only mentioned briefly
- Do NOT write questions whose complete answer requires other sections
- Be specific: include exact values, names, or steps from the text

Chunk:
{chunk_text[:600]}

Write ONLY the questions, one per line, no numbering:"""

    try:
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
            timeout=config.LLM_TIMEOUT
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def convert_tables_to_text(text: str) -> str:
    """
    جداول Markdown رو به جملات طبیعی تبدیل میکنه.
    fix 2: خطوط تکراری (exact) حذف میشن تا multiline cell ها
    باعث تکرار نشن.
    """
    lines = text.split('\n')
    result = []
    in_table = False
    table_headers = []
    seen_lines = set()   # fix 2: برای exact dedupe

    for line in lines:
        if '|' not in line:
            if in_table:
                in_table = False
                table_headers = []
            result.append(line)
            continue

        cells = [c.strip() for c in line.split('|') if c.strip()]

        if all(set(c) <= {'-', ':'} for c in cells):
            continue

        if not in_table:
            in_table = True
            table_headers = cells
            continue

        if len(cells) == len(table_headers):
            parts = [f"{table_headers[i]}: {cells[i]}"
                     for i in range(len(cells))
                     if cells[i] and cells[i] not in ('/', '-', '')]
            if parts:
                sentence = ". ".join(parts) + "."
                # fix 2: فقط اگه این جمله قبلاً نیومده اضافه کن
                norm = sentence.strip().lower()
                if norm not in seen_lines:
                    seen_lines.add(norm)
                    result.append(sentence)
        elif cells:
            joined = " | ".join(cells)
            norm = joined.strip().lower()
            if norm not in seen_lines:
                seen_lines.add(norm)
                result.append(joined)

    return '\n'.join(result)


def _is_low_value_section(heading: str, text: str) -> bool:
    """
    fix 1: تشخیص section های بی‌ارزش که باید skip بشن:
      - فهرست مطالب (Contents / Table of Contents)
      - جدول‌های نقطه‌چین (dotted leaders: "....")
      - section های فقط-تصویر (فقط <!-- image -->)
    """
    h = heading.lower().strip()

    # فهرست مطالب
    if h in ("contents", "table of contents", "index"):
        return True

    # نقطه‌چین طولانی (فهرست مطالب پنهان)
    if text.count("....") >= 3:
        return True

    # section فقط-تصویر: بعد از حذف <!-- image --> چیزی نمونه
    stripped = re.sub(r'<!--.*?-->', '', text).strip()
    stripped = re.sub(r'\s+', ' ', stripped)
    if len(stripped.split()) < 5:
        return True

    return False


def _clean_markdown(text: str) -> str:
    """fix 3: حذف artifacts مارک‌داون."""
    text = re.sub(r'<!--\s*image\s*-->', '', text)
    text = re.sub(r'<!--.*?-->', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    return text


def _is_orphan_fragment(prop: str) -> bool:
    """
    fix 4: تشخیص fragment های بی‌ارزش که باید حذف بشن.
    حذف: "No.: 1", "Item: 3" (فقط شماره)
    نگه‌داری: "Ground Screw", "Operating Voltage: 12-16.8 V DC"
    """
    p = prop.strip().lower()

    # الگوهای orphan: "no.: N" یا "item: N" که فقط عدد دارن
    if re.match(r'^(no\.?|item|index)\s*:?\s*\d+\.?$', p):
        return True

    # خیلی کوتاه و فقط عدد/علامت
    words = prop.split()
    if len(words) <= 2 and not any(c.isalpha() and len(w) > 2
                                   for w in words for c in w):
        return True

    return False


def split_into_propositions(text: str) -> list:
    """
    یک section رو به propositions اتمی می‌شکنه.
    شامل cleanup مارک‌داون (fix 3) و orphan filtering (fix 4).
    """
    MIN_PROP_WORDS = 6

    # اول جداول رو به متن طبیعی تبدیل کن
    text = convert_tables_to_text(text)

    # fix 3: پاکسازی markdown
    text = _clean_markdown(text)

    lines = text.split('\n')
    body_lines = [l for l in lines if not l.strip().startswith('##')]

    raw_units = []
    for line in body_lines:
        line = line.strip()
        if not line:
            continue

        is_list_item = bool(re.match(r'^[-*•]\s+', line) or
                            re.match(r'^\d+[\.\)]\s+', line))

        if is_list_item:
            clean = re.sub(r'^[-*•]\s+', '', line)
            clean = re.sub(r'^\d+[\.\)]\s+', '', clean)
            raw_units.append(clean)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', line)
            for s in sentences:
                s = s.strip()
                if s:
                    raw_units.append(s)

    propositions = []
    for unit in raw_units:
        # fix 3: پاکسازی نهایی هر unit
        unit = re.sub(r'<!--.*?-->', '', unit).strip()
        if not unit:
            continue
        # fix 4: حذف orphan fragments
        if _is_orphan_fragment(unit):
            continue

        if propositions and len(unit.split()) < MIN_PROP_WORDS:
            propositions[-1] = propositions[-1] + " " + unit
        else:
            propositions.append(unit)

    if not propositions:
        clean_text = " ".join(body_lines).strip()
        clean_text = _clean_markdown(clean_text).strip()
        if clean_text and len(clean_text.split()) >= 3:
            propositions = [clean_text]

    return propositions


# ── مرحله ۳: Parser ───────────────────────────────────────
def parse_pdf(pdf_path: Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    return result.document.export_to_markdown()


# ── مرحله ۴: Doc Hashing ──────────────────────────────────
def compute_doc_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── مرحله ۵: Content-Aware Chunking ──────────────────────
def split_by_headings(markdown_text: str) -> list:
    """متن رو بر اساس heading ها تقسیم می‌کنه (با numbered-heading hierarchy)."""
    lines = markdown_text.split("\n")
    sections = []
    current_text = []
    current_heading = "Introduction"
    last_numbered_heading = ""

    def is_numbered_heading(text: str) -> bool:
        return bool(re.match(r"^\d+[\.\d]*\s+\w", text.strip()))

    for line in lines:
        is_heading = re.match(r"^#{1,3}\s+", line) and "...." not in line

        if is_heading:
            if current_text:
                sections.append({
                    "heading": current_heading,
                    "text": "\n".join(current_text).strip()
                })

            heading_text = re.sub(r"^#{1,3}\s+", "", line).strip()

            if is_numbered_heading(heading_text):
                last_numbered_heading = heading_text
                current_heading = heading_text
            else:
                if last_numbered_heading:
                    current_heading = f"{last_numbered_heading} → {heading_text}"
                else:
                    current_heading = heading_text

            current_text = []
        else:
            current_text.append(line)

    if current_text:
        sections.append({
            "heading": current_heading,
            "text": "\n".join(current_text).strip()
        })

    # fix 1: section های بی‌ارزش رو skip کن
    filtered = []
    for s in sections:
        if len(s["text"].split()) <= 5:
            continue
        if _is_low_value_section(s["heading"], s["text"]):
            continue
        filtered.append(s)

    return filtered


def maybe_split_large_section(section: dict) -> list:
    """section ها رو به فرمت parent آماده میکنه."""
    words = section["text"].split()

    if len(words) <= config.MAX_SECTION_WORDS:
        return [{
            "heading": section["heading"],
            "text": section["text"]
        }]

    sub_chunks = []
    start = 0
    while start < len(words):
        end = start + config.SUB_CHUNK_WORDS
        chunk_words = words[start:end]
        sub_chunks.append({
            "heading": section["heading"],
            "text": " ".join(chunk_words)
        })
        start += config.SUB_CHUNK_WORDS - config.SUB_CHUNK_OVERLAP

    return sub_chunks


# ── مراحل ۶ تا ۸: Hierarchical Embedding + Indexing ──────
def ingest_document(pdf_path: Path, product_override: str = None) -> dict:
    """یه PDF رو با معماری hierarchical (parent + children) پردازش میکنه."""
    print(f"\n{'=' * 60}")
    print(f"Ingesting: {pdf_path.name}")
    print(f"{'=' * 60}")

    print("Parsing with Docling...")
    markdown_text = parse_pdf(pdf_path)

    scan_result = security_scan(markdown_text)
    if not scan_result["safe"]:
        print("⚠️  Document flagged by security scan. Skipping.")
        return {"status": "quarantined"}

    # When the caller already knows the canonical product name, skip the LLM
    # metadata call entirely: it only extracts product/doc_type/version, the
    # product is being overridden anyway, and the call is the first thing to
    # stall under load. doc_type defaults to manual (correct for these docs).
    if product_override:
        metadata = {"product": product_override,
                    "doc_type": "manual", "version": "unknown"}
        print(f"  [override] product={product_override} "
              f"(skipped LLM metadata)")
    else:
        print("Extracting metadata via LLM...")
        metadata = extract_metadata(markdown_text, pdf_path.name)
        # normalize product name — حذف توضیحات داخل پرانتز
        # تا mismatch بین ingestion و query filter پیش نیاد
        metadata["product"] = re.sub(
            r'\s*\(.*?\)', '', metadata["product"]).strip()
    print(f"  product={metadata['product']}, doc_type={metadata['doc_type']}, "
          f"version={metadata['version']}")

    doc_hash = compute_doc_hash(markdown_text)
    doc_id = f"doc_{doc_hash[:12]}"

    print("Chunking by section headings...")
    sections = split_by_headings(markdown_text)
    parent_sections = []
    for section in sections:
        parent_sections.extend(maybe_split_large_section(section))
    print(f"  {len(parent_sections)} parent sections created")

    qdrant = get_qdrant()
    pg = get_postgres()
    pg_cur = pg.cursor()

    pg_cur.execute("""
        INSERT INTO documents (doc_id, filename, product, doc_type,
                               version, is_latest, language, upload_date)
        VALUES (%s, %s, %s, %s, %s, TRUE, 'en', NOW())
        ON CONFLICT (doc_id) DO NOTHING
    """, (doc_id, pdf_path.name, metadata["product"],
          metadata["doc_type"], metadata["version"]))

    points = []
    parent_count = 0
    child_count = 0

    for p_idx, parent in enumerate(parent_sections):
        parent_id = f"{doc_id}_parent_{p_idx+1:04d}"
        heading = parent["heading"]
        parent_full_text = f"## {heading}\n{parent['text']}"

        parent_dense = embed_dense(parent_full_text)
        parent_sparse = embed_sparse(parent_full_text)

        parent_payload = {
            "doc_id": doc_id,
            "chunk_id": parent_id,
            "parent_id": None,
            "chunk_level": "parent",
            "chunk_index": p_idx + 1,
            "section": heading,
            "product": metadata["product"],
            "doc_type": metadata["doc_type"],
            "version": metadata["version"],
            "is_latest": True,
            "source_file": pdf_path.name,
            "text": parent_full_text,
            "augmented_text": parent_full_text,
            "quality_score": 1.0,
            "blacklisted": False
        }

        points.append(PointStruct(
            id=abs(hash(parent_id)) % (10 ** 12),
            vector={"dense": parent_dense, "sparse": parent_sparse},
            payload=parent_payload
        ))
        parent_count += 1

        pg_cur.execute("""
            INSERT INTO chunks (chunk_id, doc_id, chunk_index, section,
                                content_type, quality_score, blacklisted)
            VALUES (%s, %s, %s, %s, 'parent', 1.0, FALSE)
            ON CONFLICT (chunk_id) DO NOTHING
        """, (parent_id, doc_id, p_idx + 1, heading))

        propositions = split_into_propositions(parent_full_text)
        questions = generate_chunk_questions(parent["text"], metadata["product"])

        for c_idx, prop in enumerate(propositions):
            child_id = f"{parent_id}_child_{c_idx+1:03d}"

            child_embed_text = f"## {heading}\n{prop}"
            if questions:
                child_embed_text = f"{questions}\n\n{child_embed_text}"

            child_dense = embed_dense(child_embed_text)
            child_sparse = embed_sparse(child_embed_text)

            child_payload = {
                "doc_id": doc_id,
                "chunk_id": child_id,
                "parent_id": parent_id,
                "chunk_level": "child",
                "chunk_index": p_idx + 1,
                "section": heading,
                "product": metadata["product"],
                "doc_type": metadata["doc_type"],
                "version": metadata["version"],
                "is_latest": True,
                "source_file": pdf_path.name,
                "text": prop,
                "augmented_text": child_embed_text,
                "quality_score": 1.0,
                "blacklisted": False
            }

            points.append(PointStruct(
                id=abs(hash(child_id)) % (10 ** 12),
                vector={"dense": child_dense, "sparse": child_sparse},
                payload=child_payload
            ))
            child_count += 1

        if (p_idx + 1) % 5 == 0 or p_idx == len(parent_sections) - 1:
            print(f"  Progress: {p_idx + 1}/{len(parent_sections)} parents "
                  f"({child_count} children so far)")

    qdrant.upsert(collection_name=config.QDRANT_COLLECTION, points=points)
    pg.commit()
    pg_cur.close()
    pg.close()

    print(f"✓ Indexed {parent_count} parents + {child_count} children "
          f"for {pdf_path.name}")

    return {
        "status": "success",
        "doc_id": doc_id,
        "parents_indexed": parent_count,
        "children_indexed": child_count,
        "chunks_indexed": parent_count + child_count
    }


# ── اجرای مستقیم ──────────────────────────────────────────
if __name__ == "__main__":
    pdf_files = sorted(config.DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {config.DOCUMENTS_DIR}")
    else:
        print(f"Found {len(pdf_files)} PDF(s) to ingest:")
        for f in pdf_files:
            print(f"  - {f.name}")

        results = []
        for pdf_path in pdf_files:
            result = ingest_document(pdf_path)
            results.append(result)

        print(f"\n{'=' * 60}")
        print("Ingestion Summary")
        print(f"{'=' * 60}")
        for pdf_path, result in zip(pdf_files, results):
            print(f"  {pdf_path.name}: {result['status']} "
                  f"({result.get('chunks_indexed', 0)} chunks)")