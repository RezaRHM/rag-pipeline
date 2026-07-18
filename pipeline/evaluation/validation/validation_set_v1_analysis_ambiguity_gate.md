# Validation set v1 analysis — evidence-driven ambiguity gate

Run date: 2026-07-19
Branch: `comparison-pipeline-refactor` @ 0a6df5e. Baseline for comparison:
the comparison-refactor run (16/6/2, same branch @ b16c7f1).

## Summary

| Status | router v3.1 | comparison refactor | This run |
|---|---:|---:|---:|
| Pass | 11 | 16 | **18** |
| Partial | 8 | 6 | **6** |
| Fail | 5 | 2 | **0** |

Surgical diff against the previous run: only A2 and A3 changed
(ready -> needs_clarification); every other case kept its route, intent,
and answer behavior. No timeouts.

## Changed cases

| ID | Before | Now | Assessment |
|---|---|---|---|
| **A2** | **Fail** | **Pass** | Clarifies with the diverging item named ("packed item" differs) and the real product list from the registry — instead of a merged four-product packing answer. |
| **A3** | **Fail** | **Pass** | Clarifies ("Antenna connector type" differs) — instead of asserting Type-N Female, which was factually wrong for HR652. |

## Notable unchanged cases

| ID | Status | Note |
|---|---|---|
| A1 | Pass | Grounded per-product cleaning instructions; gate correctly judged the evidence convergent enough to answer (expectation says clarification is optional). |
| A4 | Partial | Gate answers because every documented manual agrees (ground screw on the rear panel, cited per product). The old "clarification required" expectation predates the current corpus and is flagged for validation-set revision — the produced answer is factually correct and evidence-cited. |
| C2 | Partial | Comparison-slot clarification, unchanged; validation-set revision item. |
| F2/F5, T1/M4 | Partial | Pre-existing single-product generation and short-question-intent items, untouched by this change. |

## Main findings

1. The ambiguity cluster is closed: both remaining validation Fails are gone.
   The gate decides from evidence (per-product fact extraction + strict
   value comparison), covers topics the keyword gate never knew about, and
   its clarification message names what differs and which products have
   documentation — all registry-derived, no hardcoded topics or products.
2. Safety property: no majority voting anywhere. Wording tolerance exists
   only inside value comparison and only for long prose; any surviving
   relevant difference always clarifies.
3. Cost: product-less ambiguous questions now take ~95-160s (per-product
   extraction). Product-named questions are unaffected (7/7 regression).
4. All six remaining Partials map to known, separate work items:
   single-product generation table/wording issues (F2, F5), short-question
   intent (T1, M4), and validation-set revision (A4, C2).
