"""فقط metadata دو فایل جدید رو ببین — بدون ingest واقعی."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from workflows.ingest import parse_pdf, extract_metadata
import re

NEW = Path(__file__).parent.parent / "new_docs"
files = sorted(NEW.glob("*.pdf"))

for f in files:
    print("=" * 70)
    print(f"FILE: {f.name}")
    print("=" * 70)
    md = parse_pdf(f)
    print(f"  parsed length: {len(md)} chars")
    print(f"  first 200 chars: {md[:200].strip()!r}")
    meta = extract_metadata(md, f.name)
    meta["product"] = re.sub(r'\s*\(.*?\)', '', meta["product"]).strip()
    print(f"  >>> DETECTED product: {meta['product']!r}")
    print(f"  >>> doc_type: {meta['doc_type']!r}, version: {meta['version']!r}")
    print()
