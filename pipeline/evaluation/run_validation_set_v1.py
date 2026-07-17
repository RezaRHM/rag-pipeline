"""Run the 24 unique questions in validation_set_draft_v1 end to end."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import ask


CASES = [
    ("F1", "factual", "What is the output power of the HR652 in high, middle, and low settings?", "44/40/30 dBm"),
    ("F2", "factual", "What items are included in the RD98XS packing list?", "1. Packing List"),
    ("F3", "factual", "Which connectors are on the rear panel of the RD98XS?", "2.2 Rear Panel"),
    ("F4", "factual", "Can alcohol be used to clean the HR652?", "No; 9.2 Product Cleaning"),
    ("F5", "factual", "What is on the front panel of the HR652?", "2. Product Layout"),
    ("T1", "telegraphic", "HR652 output power?", "44/40/30 dBm"),
    ("T2", "telegraphic", "RD98XS box contents?", "1. Packing List"),
    ("T3", "telegraphic", "RD98XS rear connectors?", "2.2 Rear Panel"),
    ("T4", "telegraphic", "HR652 cleaning alcohol?", "No; 9.2 Product Cleaning"),
    ("U1", "unsupported", "What is the RF output power of the RD98XS?", "Absent; avoid low-TX/100W traps"),
    ("U2", "unsupported", "What is the frequency range of the RD98XS?", "Absent; avoid VSWR antenna-frequency trap"),
    ("U3", "unsupported", "What is the weight of the HR652?", "Mentioned without a numeric value"),
    ("U4", "unsupported", "Is the RD98XS IP68 rated?", "Absent; do not transfer HP7 IP68"),
    ("A1", "ambiguous", "Cleaning instructions?", "Optional clarification; both nearly identical"),
    ("A2", "ambiguous", "What's in the box?", "Clarification required"),
    ("A3", "ambiguous", "Antenna connector type?", "Clarification required"),
    ("A4", "ambiguous", "Ground screw location?", "Clarification required"),
    ("M2", "multi_section", "Before cleaning the RD98XS, what to do first and what to avoid?", "RD98XS section 7.2"),
    ("M3", "multi_section", "Steps to install the RD98XS and confirm it works afterward?", "Sections 3.2.2 and 3.3"),
    ("M4", "multi_section", "After installing the RD98XS, confirm power-on and what the LEDs mean?", "Sections 3.3 and 5.2"),
    ("C1", "comparison", "Do RD98XS and HR652 ship with the same accessories?", "Packing lists for both"),
    ("C2", "comparison", "Which repeater documents its output power?", "HR652 yes; RD98XS no"),
    ("C3", "comparison", "Which repeater needs a Phillips screwdriver, RD98XS or HR652?", "Evidence from both manuals"),
    ("C4", "comparison", "Compare the alarm code systems of the RD98XS and HR652.", "RD98XS named alarms vs HR652 E-codes"),
]


OUTPUT_DIR = Path(__file__).parent / "validation"
# Optional run tag (argv[1]) so a new run never overwrites a baseline record.
RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "router_v3_1"
JSON_OUTPUT = OUTPUT_DIR / f"validation_set_v1_run_{RUN_TAG}.json"
MD_OUTPUT = OUTPUT_DIR / f"validation_set_v1_run_{RUN_TAG}.md"


def save(results):
    JSON_OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Validation set v1 — live run: {RUN_TAG}",
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
            f"**Intent:** `{row.get('intent')}` — **Route:** `{row.get('route_status')}` — **Time:** `{row.get('elapsed_seconds')}s`",
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
            "intent_confidence": result.get("intent_confidence"),
            "answer_source": result.get("answer_source"),
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
        f"time={row['elapsed_seconds']}s",
        flush=True,
    )

print(f"Saved JSON: {JSON_OUTPUT}")
print(f"Saved Markdown: {MD_OUTPUT}")
