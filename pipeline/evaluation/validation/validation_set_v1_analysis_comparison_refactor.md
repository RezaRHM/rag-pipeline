# Validation set v1 analysis — comparison refactor (router v3.2)

Run date: 2026-07-17
Branch: `comparison-pipeline-refactor` (cc07c88, 96beda2, b7c3ab5 on top of the
router hardening ba6d295). Baseline for comparison: router v3.1 run
(`validation_set_v1_analysis_router_v3_1.md`, same day, same 5-document corpus).

## Summary

| Status | v3.1 baseline | This run |
|---|---:|---:|
| Pass | 11 | **16** |
| Partial | 8 | **6** |
| Fail | 5 | **2** |
| Total | 24 | 24 |

Zero regressions: no case scored lower than in the baseline. All 24 completed
in-batch with no timeout (baseline F3 had timed out and needed an isolated
rerun).

## Per-question assessment

| ID | v3.1 | Now | Assessment |
|---|---|---|---|
| F1 | Pass | Pass | Correct 44/40/30 dBm; Specifications ranked first. |
| F2 | Partial | Partial | Packing List rank 1, but generation again omitted the DC Power Cord table row and wrongly asserted "no other items". Single-product generation issue, untouched by this branch. |
| F3 | Pass* | Pass | All nine rear-panel connectors, in-batch, 33.1s — the baseline timeout did not recur. |
| F4 | Pass | Pass | Correctly prohibited alcohol, cited 9.2 Product Cleaning. |
| F5 | Partial | Partial | Correct front-panel list from Product Layout, but again used inference wording ("can be inferred from the layout diagram"). |
| T1 | Partial | Partial | Correct 44/40/30 answer; intent still troubleshooting instead of standard (open short-question issue). |
| T2 | Pass | Pass | Complete packing list including DC Power Cord. |
| T3 | Pass | Pass | Complete rear-panel list with connector types. |
| T4 | Pass | Pass | Correct alcohol guidance ("not recommended" softening, as in baseline). |
| U1 | Pass | Pass | Correct refusal on RD98XS RF output power. |
| U2 | Pass | Pass | Correct refusal; VSWR trap avoided. |
| U3 | Pass | Pass | Correctly states the weight cannot be verified. |
| **U4** | **Fail** | **Pass** | IP68 no longer mistaken for a product (router v3.2 technical-standard layer + main.py backstop). Intent standard, route ready, correct "genuinely absent" refusal. |
| A1 | Pass | Pass | Grounded per-product cleaning instructions (HR106X 7.2, HR652 9.2, RD98XS 7.2); intent now procedural. |
| A2 | Fail | Fail | Still answers with a multi-product packing-list aggregation instead of requesting clarification. Ambiguity policy untouched — next work item. |
| A3 | Fail | Fail | Still asserts Type-N Female across products instead of requesting clarification. Ambiguity policy untouched. |
| A4 | Partial | Partial | Grounded three-product ground-screw answer, but no clarification and intent troubleshooting. Ambiguity policy untouched. |
| **M2** | **Partial** | **Pass** | Correct cleaning order and sections, and intent is now procedural (v3.2 retrain fixed the boundary case the baseline flagged). |
| M3 | Pass | Pass | Correct ordered installation and post-installation check from 3.2.2/3.3. |
| M4 | Partial | Partial | Correct multi-section answer (3.3, 5.2, 4.1); intent still troubleshooting. |
| **C1** | **Fail** | **Pass** | Both Packing Lists retrieved and compared with [section] citations; correct verdict (shared Documentation Kit, Power Cord vs DC Power Cord). Stages 1+2. |
| C2 | Partial | Partial | needs_clarification, as before. The old two-product expectation predates the 5-document corpus; validation-set revision item. |
| **C3** | **Fail** | **Pass** | Deterministic evidence table: both products document a Phillips screwdriver, each cited to its own manual (RD98XS 3.1 Installation Requirements; HR652 4.2 Procedure). The old expectation that only one product needs it was itself wrong. Stage 3. |
| **C4** | **Partial** | **Pass** | Full 15-code HR652 alarm table (E1–bP with meanings) vs RD98XS LCD-message system with sections. Stage 2. |

## Main findings

1. Every targeted fix landed: U4 (router v3.2 + backstop), C1 (unified
   comparison retrieval + synonym bridge + no intermediate summary), C3
   (question-conditioned extraction with deterministic rendering), C4
   (verbatim evidence to a single facts-first compare call).
2. Bonus flip: M2 intent corrected to procedural by the v3.2 retrain.
3. Reliability: no timeout in the batch. Comparison latency, however, is
   higher than other categories (C1 173s, C3 109s, C4 230s) because broad
   questions pay for per-product extraction before falling back to the
   free-form compare. Candidate optimization: skip or parallelize extraction,
   or cache expansions.
4. Both remaining Fails (A2, A3) and two Partials (A4, and C2's outdated
   expectation) are concentrated in the ambiguity-policy work item, which
   this branch deliberately did not touch. The other Partials are F2/F5
   (single-product generation wording/table-row issues) and T1/M4
   (short-question intent), all pre-existing.
5. The validation set still needs revision for the five-document corpus
   (C2's expectation; A-series scope).
