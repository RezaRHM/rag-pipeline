"""Ingest ONLY the two new files in new_docs/, with manual product names.

Does not touch data/documents/ — the three existing products stay untouched.
Product names are set explicitly because the LLM detector mangled RD982i-S
(OCR spacing + multi-variant manual).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from workflows.ingest import ingest_document

NEW = Path(__file__).parent.parent / "new_docs"

JOBS = [
    ("Hytera-HR106X-Digital-Repeater-User-Manual-R2.0_eng.pdf",
     "HR106X Digital Repeater"),
    ("Hytera-RD982i-RD982i-S-RD982i-S-100W-Digital-Repeater-Owners-Manual.pdf",
     "RD982i-S Digital Repeater"),
]

for filename, product in JOBS:
    path = NEW / filename
    if not path.exists():
        print(f"✗ MISSING: {path}")
        continue
    result = ingest_document(path, product_override=product)
    print(f"\n>>> {product}: {result.get('status')} "
          f"({result.get('chunks_indexed', 0)} chunks)\n")
