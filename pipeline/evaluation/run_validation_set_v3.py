"""Validation set v3: 50 questions over the eight-product corpus,
including multi-turn conversations.

30 single-turn questions + 5 conversation threads of 4 turns each. Threads
accumulate history exactly as the server does (each answer is appended
before the next turn), so they exercise reference resolution, topic
carryover, code switching, clarification answers and sticky product scope
end to end.

Every expectation was read out of the indexed sections before the question
was written, per the calibration rule adopted in
validation_set_v1_revisions.md.

Usage:  python evaluation/run_validation_set_v3.py [run_tag]
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import ask


# ── single-turn cases: (id, category, question, expected) ──
SINGLES = [
    # factual, spread across all eight products
    ("S01", "factual", "What tools are needed to install the RD625?",
     "Electric drill and a T10 torx screwdriver"),
    ("S02", "factual", "What happens on the RD962i when the battery runs low?",
     "Below 12% capacity: alarm indicator red, LED segment shows E2"),
    ("S03", "factual", "What ingress protection rating does the RD965 have?",
     "IP67"),
    ("S04", "factual", "Which tools are required to install the HR106X?",
     "Phillips screwdriver, T-10 torx screwdriver, spanner, anti-static gloves, multimeter"),
    ("S05", "factual", "What IP rating do the HP7 series radios have?",
     "IP68 dust and waterproof"),
    ("S06", "factual",
     "What is the output power of the HR652 in high, middle and low settings?",
     "44 / 40 / 30 dBm"),
    ("S07", "factual", "Which connectors are on the rear panel of the RD98XS?",
     "Nine: TX/RX antenna (Type-N female), optional interfaces, monitor/tuning, accessory jack, DC power inlet, ethernet, ground screw"),
    ("S08", "factual", "What are the installation requirements of the RD982i-S?",
     "Dry well-ventilated place, -30C to +60C, humidity 95%, listed tools, DC 13.6V +/-15%"),
    ("S09", "factual", "What is the operating voltage of the RD625?",
     "DC 13.6V +/-15%; AC 90V to 264V"),
    ("S10", "factual", "What is the capacity of the optional RD965 backup battery?",
     "10 Ah lithium-ion"),

    # telegraphic (short-question intent, router v3.3)
    ("S11", "telegraphic", "RD625 tools?",
     "Electric drill + T10 torx; intent standard"),
    ("S12", "telegraphic", "HR652 output power?",
     "44/40/30 dBm; intent standard"),
    ("S13", "telegraphic", "RD965 IP rating?", "IP67"),
    ("S14", "telegraphic", "RD962i battery alarm?",
     "Low battery below 12%, LED shows E2"),

    # unsupported / absence traps
    ("S15", "unsupported", "What is the output power of the RD625?",
     "Absent: the RD625 document covers installation only"),
    ("S16", "unsupported", "Is the RD962i IP68 rated?",
     "Absent; must not borrow IP67 from RD965 or IP68 from HP7"),
    ("S17", "unsupported", "What firmware version does the RD625 ship with?",
     "Absent from the RD625 document"),
    ("S18", "unsupported", "What is the RF output power of the RD98XS?",
     "Absent; avoid the low-TX-power trap"),
    ("S19", "unsupported", "What is the price of the HR652?",
     "Absent: manuals contain no pricing"),

    # comparison
    ("S20", "comparison",
     "Compare the installation tools of the RD625 and the RD962i.",
     "RD625: drill + T10 torx; RD962i: cross head + T10 torx"),
    ("S21", "comparison",
     "Compare the ingress protection of the RD965 and the HP7 series.",
     "RD965: IP67; HP7: IP68 - both documented, different values"),
    ("S22", "comparison",
     "Compare the installation tools of the HR106X and the RD625.",
     "HR106X: five tools incl. multimeter and anti-static gloves; RD625: drill + T10 torx"),
    ("S23", "comparison",
     "Do the RD962i and the HR652 use the same alarm code for a low battery?",
     "Yes - both use E2"),
    ("S24", "comparison",
     "Compare the packing lists of the RD98XS and the RD982i-S.",
     "Near-identical manuals; expect largely the same items"),
    ("S25", "comparison",
     "Compare the outdoor protection of the HR652 and the RD965.",
     "RD965: IP67 + MIL-STD-810; HR652: not documented"),

    # ambiguous (no product named, eight candidates)
    ("S26", "ambiguous", "What installation tools do I need?",
     "Clarification required: tools differ per product"),
    ("S27", "ambiguous", "Is it waterproof?",
     "Clarification required; RD965 and HP7 document IP ratings, others do not"),
    ("S28", "ambiguous", "What's in the box?",
     "Clarification required: packed items differ per product"),

    # procedural
    ("S29", "procedural", "How do I install the RD625 on a wall, step by step?",
     "Drill three holes, wall anchors, three ST4X16 self-tapping screws, then mount"),
    ("S30", "procedural",
     "How do I check the HR106X works after installation?",
     "Turn the repeater on and observe the LED indicators (3.4 Post-installation Check)"),
]


# ── conversation threads: (thread_id, [(turn_id, category, q, expected)]) ──
THREADS = [
    ("T1", [
        ("T1.1", "thread-anchor",
         "What tools are needed to install the RD625?",
         "Electric drill + T10 torx (anchors RD625)"),
        ("T1.2", "thread-topic-carry", "And the RD962i?",
         "Inherits the tools topic: cross head + T10 torx for RD962i"),
        ("T1.3", "thread-pronoun", "Does it need a spanner?",
         "Pronoun -> RD962i; a spanner is not among its listed tools"),
        ("T1.4", "thread-plural-compare", "Compare them.",
         "Plural -> both stacked products (RD962i and RD625) compared"),
    ]),
    ("T2", [
        ("T2.1", "thread-anchor",
         "What does alarm code E2 mean on the HR652?",
         "Low battery alarm"),
        ("T2.2", "thread-code-switch", "And E3?",
         "Same product, code swapped: external power under-voltage alarm"),
        ("T2.3", "thread-code-switch", "What about H5?",
         "Same product: invalid network IP / DHCP failure alarm"),
        ("T2.4", "thread-sticky", "Which codes indicate a network problem?",
         "Sticky HR652: H3 network IP conflict and H5 invalid network IP"),
    ]),
    ("T3", [
        ("T3.1", "thread-ambiguous", "What are the installation tools?",
         "Clarification required: tools differ per product"),
        ("T3.2", "thread-clarify-answer", "I mean the HR106X",
         "Clarification answer -> HR106X tools: Phillips, T-10 torx, spanner, anti-static gloves, multimeter"),
        ("T3.3", "thread-pronoun", "Does it need a multimeter?",
         "Pronoun -> HR106X; yes, a multimeter is listed"),
        ("T3.4", "thread-topic-carry", "And the RD625?",
         "Inherits the tools topic: RD625 drill + T10 torx"),
    ]),
    ("T4", [
        ("T4.1", "thread-anchor",
         "What ingress protection rating does the RD965 have?", "IP67"),
        ("T4.2", "thread-pronoun", "Does it have GPS?",
         "Pronoun -> RD965; yes, GPS module for real-time location monitoring"),
        ("T4.3", "thread-sticky",
         "What is the optional backup battery capacity?",
         "Sticky RD965 (no product, no pronoun): 10 Ah lithium-ion"),
        ("T4.4", "thread-pronoun", "Is it suitable for outdoor use?",
         "Pronoun -> RD965; MIL-STD-810 C/D/E/F/G and IP67"),
    ]),
    ("T5", [
        ("T5.1", "thread-unsupported",
         "What is the output power of the RD9999?",
         "Unsupported product: RD9999 is not documented"),
        ("T5.2", "thread-clarify-answer", "I mean the HR652",
         "Clarification answer -> HR652 output power 44/40/30 dBm"),
        ("T5.3", "thread-pronoun", "Is it waterproof?",
         "Pronoun -> HR652; no IP rating documented (honest absence)"),
        ("T5.4", "thread-topic-carry", "What about the RD965?",
         "Topic carry -> RD965 IP67 / outdoor protection"),
    ]),
]


OUTPUT_DIR = Path(__file__).parent / "validation"
RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "v3_50q"
JSON_OUTPUT = OUTPUT_DIR / f"validation_set_v3_run_{RUN_TAG}.json"
MD_OUTPUT = OUTPUT_DIR / f"validation_set_v3_run_{RUN_TAG}.md"

TOTAL = len(SINGLES) + sum(len(turns) for _, turns in THREADS)


def _row(case_id, category, question, expected, result, elapsed,
         thread=None, error=None):
    if error:
        return {"id": case_id, "category": category, "thread": thread,
                "question": question, "expected": expected,
                "error": error, "elapsed_seconds": elapsed}
    return {
        "id": case_id,
        "category": category,
        "thread": thread,
        "question": question,
        "expected": expected,
        "rewritten": result.get("rewritten_question"),
        "intent": result.get("query_type"),
        "route_status": result.get("route_status"),
        "detected_product": result.get("detected_product"),
        "method": result.get("method"),
        "sections": [c.payload.get("section", "?")
                     for c in result.get("chunks", [])],
        "answer": result.get("answer", ""),
        "elapsed_seconds": elapsed,
    }


def save(results):
    JSON_OUTPUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    lines = [f"# Validation set v3 (8 products, 50 questions) — run: {RUN_TAG}",
             "", f"Completed: {len(results)}/{TOTAL}", ""]
    for row in results:
        header = f"## {row['id']} — {row['category']}"
        if row.get("thread"):
            header += f"  *(thread {row['thread']})*"
        lines.extend([
            header, "",
            f"**Question:** {row['question']}", "",
            f"**Expected:** {row['expected']}", "",
            f"**Rewritten:** `{row.get('rewritten')}`", "",
            f"**Intent:** `{row.get('intent')}` — **Route:** "
            f"`{row.get('route_status')}` — **Product:** "
            f"`{row.get('detected_product')}` — **Time:** "
            f"`{row.get('elapsed_seconds')}s`", "",
            "**Answer:**", "",
            row.get("answer") or f"ERROR: {row.get('error')}", "",
            "---", "",
        ])
    MD_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


results = []
done = 0

# ── single-turn ──
for case_id, category, question, expected in SINGLES:
    done += 1
    started = time.time()
    print(f"[{done:02d}/{TOTAL}] {case_id}: {question}", flush=True)
    try:
        result = ask(question)
        row = _row(case_id, category, question, expected, result,
                   round(time.time() - started, 1))
    except Exception as exc:
        row = _row(case_id, category, question, expected, None,
                   round(time.time() - started, 1),
                   error=f"{type(exc).__name__}: {exc}")
    results.append(row)
    save(results)
    print(f"  intent={row.get('intent')} route={row.get('route_status')} "
          f"product={row.get('detected_product')} "
          f"time={row['elapsed_seconds']}s", flush=True)

# ── conversation threads ──
for thread_id, turns in THREADS:
    history = []
    print(f"\n===== THREAD {thread_id} =====", flush=True)
    for case_id, category, question, expected in turns:
        done += 1
        started = time.time()
        print(f"[{done:02d}/{TOTAL}] {case_id}: {question}", flush=True)
        try:
            result = ask(question, conversation_history=history)
            row = _row(case_id, category, question, expected, result,
                       round(time.time() - started, 1), thread=thread_id)
            answer = result.get("answer", "")
        except Exception as exc:
            row = _row(case_id, category, question, expected, None,
                       round(time.time() - started, 1), thread=thread_id,
                       error=f"{type(exc).__name__}: {exc}")
            answer = ""
        results.append(row)
        save(results)
        print(f"  rewritten={row.get('rewritten')!r}", flush=True)
        print(f"  intent={row.get('intent')} route={row.get('route_status')} "
              f"product={row.get('detected_product')} "
              f"time={row['elapsed_seconds']}s", flush=True)
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

print(f"\nSaved JSON: {JSON_OUTPUT}")
print(f"Saved Markdown: {MD_OUTPUT}")
