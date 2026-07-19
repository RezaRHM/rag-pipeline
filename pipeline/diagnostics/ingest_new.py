"""Ingest the files in new_docs/, with manual product names.

Does not touch data/documents/ — the three base products stay untouched.
Product names are set explicitly because the LLM detector mangled RD982i-S
(OCR spacing + multi-variant manual).

NOTE: ingest_document APPENDS (it does not delete a product's existing
chunks, and Qdrant point ids come from a randomized hash). Re-running a job
for a product already in the index duplicates its chunks. The two
previously-ingested manuals (HR106X, RD982i-S) are therefore commented out;
only the three genuinely new products are active.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
from workflows.ingest import ingest_document

NEW = Path(__file__).parent.parent / "new_docs"

JOBS = [
    # ── new products (2026-07-19): corpus 5 -> 8 ──
    ("Hytera-RD625-Digital-Wall-Mounted-Repeater-Owners-Manual.pdf",
     "RD625 Digital Repeater"),
    ("Hytera-RD962i-Digital-Portable-Repeater-Owners-Manual.pdf",
     "RD962i Digital Repeater"),
    ("Hytera-RD965-Outdoor-DMR-Repeater-Owners-Manual.pdf",
     "RD965 Digital Repeater"),

    # ── already indexed — DO NOT re-run (would duplicate chunks) ──
    # ("Hytera-HR106X-Digital-Repeater-User-Manual-R2.0_eng.pdf",
    #  "HR106X Digital Repeater"),
    # ("Hytera-RD982i-RD982i-S-RD982i-S-100W-Digital-Repeater-Owners-Manual.pdf",
    #  "RD982i-S Digital Repeater"),
]

for filename, product in JOBS:
    path = NEW / filename
    if not path.exists():
        print(f"✗ MISSING: {path}")
        continue
    result = ingest_document(path, product_override=product)
    print(f"\n>>> {product}: {result.get('status')} "
          f"({result.get('chunks_indexed', 0)} chunks)\n")
