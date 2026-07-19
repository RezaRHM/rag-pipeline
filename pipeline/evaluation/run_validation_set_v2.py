"""Run validation set v2: 20 questions for the eight-document corpus.

Written after RD625 / RD962i / RD965 were ingested (corpus 5 -> 8). Every
expectation is corpus-backed: the facts were read out of the indexed
sections before the question was written, per the calibration rule adopted
during the ambiguity work (see validation_set_v1_revisions.md).

Usage:  python evaluation/run_validation_set_v2.py [run_tag]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import ask


CASES = [
    # ── factual, new products ────────────────────────────
    ("N1", "factual", "What tools are needed to install the RD625?",
     "An electric drill and a T10 torx screwdriver"),
    ("N2", "factual", "What is the operating voltage of the RD625?",
     "DC 13.6V +/-15%; AC 90V to 264V"),
    ("N3", "factual", "What happens on the RD962i when the battery is low?",
     "Below 12% threshold: alarm indicator red, LED segment shows E2"),
    ("N4", "factual", "What ingress protection rating does the RD965 have?",
     "IP67, and MIL-STD-810 C/D/E/F/G"),
    ("N5", "factual", "What is the capacity of the optional RD965 backup battery?",
     "10 Ah lithium-ion, at least 8 hours at 50% duty cycle"),

    # ── telegraphic (short-question intent, router v3.3) ──
    ("T1", "telegraphic", "RD625 installation tools?",
     "Electric drill + T10 torx; intent should be standard"),
    ("T2", "telegraphic", "RD965 GPS?",
     "GPS module enables real-time location monitoring"),

    # ── unsupported / absence traps ──────────────────────
    ("U1", "unsupported", "What is the output power of the RD625?",
     "Absent: the RD625 document covers installation only"),
    ("U2", "unsupported", "Is the RD962i IP68 rated?",
     "Absent; must not borrow IP67/IP68 from RD965 or HP7"),
    ("U3", "unsupported", "What is the frequency range of the RD625?",
     "Absent: no specifications section in the RD625 document"),

    # ── comparison (new x new, new x old) ────────────────
    ("C1", "comparison",
     "Compare the installation tools of the RD625 and the RD962i.",
     "RD625: drill + T10 torx; RD962i: cross head + T10 torx"),
    ("C2", "comparison",
     "Compare the ingress protection of the RD965 and the RD98XS.",
     "RD965: IP67; RD98XS: not documented"),
    ("C3", "comparison",
     "Do the RD962i and HR652 use the same alarm code for low battery?",
     "Yes - both use E2 for the low-battery alarm"),
    ("C4", "comparison",
     "Compare the installation tools of the RD98XS and the RD625.",
     "RD98XS: Phillips + T-10 torx + spanner; RD625: drill + T10 torx"),
    ("C5", "comparison", "Which repeater documents a backup battery?",
     "No products named in an eight-product corpus -> needs_clarification"),

    # ── ambiguous (no product named, 8 candidates) ───────
    ("A1", "ambiguous", "What installation tools do I need?",
     "Clarification required: tools differ per product"),
    ("A2", "ambiguous", "What is the operating voltage?",
     "Clarification required: voltage differs per product"),
    ("A3", "ambiguous", "Is it waterproof?",
     "Clarification required: only some products document IP ratings"),

    # ── procedural / multi-step ──────────────────────────
    ("M1", "procedural",
     "How do I install the RD625 on a wall, step by step?",
     "Drill three holes, wall anchors, three ST4X16 self-tapping screws, then mount"),
    ("M2", "procedural",
     "How is the transmit power level set on the RD962i?",
     "Dealer sets Tx power to High or Low"),
]


OUTPUT_DIR = Path(__file__).parent / "validation"
RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "v2_8products"
JSON_OUTPUT = OUTPUT_DIR / f"validation_set_v2_run_{RUN_TAG}.json"
MD_OUTPUT = OUTPUT_DIR / f"validation_set_v2_run_{RUN_TAG}.md"


def save(results):
    JSON_OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Validation set v2 (8-product corpus) — run: {RUN_TAG}",
        "",
        f"Completed: {len(results)}/{len(CASES)}",
        "",
    ]
    for row in results:
        lines.extend([
            f"## {row['id']} — {row['category']}",
            "",
            f"**Question:** {row['question']}",
            "",
            f"**Expected:** {row['expected']}",
            "",
            f"**Intent:** `{row.get('intent')}` — **Route:** "
            f"`{row.get('route_status')}` — **Product:** "
            f"`{row.get('detected_product')}` — **Time:** "
            f"`{row.get('elapsed_seconds')}s`",
            "",
            "**Retrieved sections:**",
            "",
            *[f"- {section}" for section in row.get("sections", [])],
            "",
            "**Answer:**",
            "",
            row.get("answer") or f"ERROR: {row.get('error')}",
            "",
            "---",
            "",
        ])
    MD_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


results = []
for index, (case_id, category, question, expected) in enumerate(CASES, 1):
    started = time.time()
    print(f"[{index:02d}/{len(CASES)}] {case_id}: {question}", flush=True)
    try:
        result = ask(question)
        row = {
            "id": case_id,
            "category": category,
            "question": question,
            "expected": expected,
            "intent": result.get("query_type"),
            "route_status": result.get("route_status"),
            "detected_product": result.get("detected_product"),
            "intent_confidence": result.get("intent_confidence"),
            "answer_source": result.get("answer_source"),
            "method": result.get("method"),
            "sections": [
                chunk.payload.get("section", "?")
                for chunk in result.get("chunks", [])
            ],
            "answer": result.get("answer", ""),
            "elapsed_seconds": round(time.time() - started, 1),
        }
    except Exception as exc:
        row = {
            "id": case_id,
            "category": category,
            "question": question,
            "expected": expected,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.time() - started, 1),
        }
    results.append(row)
    save(results)
    print(
        f"  intent={row.get('intent')} route={row.get('route_status')} "
        f"product={row.get('detected_product')} time={row['elapsed_seconds']}s",
        flush=True,
    )

print(f"Saved JSON: {JSON_OUTPUT}")
print(f"Saved Markdown: {MD_OUTPUT}")
