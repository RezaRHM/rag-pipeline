# Validation set v1 analysis — intent router v3.1

Run date: 2026-07-17

Corpus at run time: 5 documents (the validation set was originally written for
the 3-document RD98XS/HR652/HP7 corpus).

## Summary

| Status | Count |
|---|---:|
| Pass | 11 |
| Partial | 8 |
| Fail | 5 |
| Total | 24 |

F3 timed out in the batch but passed completely on an immediate isolated rerun;
it is counted as Pass with a reliability warning.

## Per-question assessment

| ID | Status | Assessment |
|---|---|---|
| F1 | Pass | Correct 44/40/30 dBm; Specifications ranked first. |
| F2 | Partial | Omitted the DC Power Cord; T2 later proved the packing list has three items. |
| F3 | Pass* | Batch timeout; isolated rerun returned all nine rear-panel items correctly. |
| F4 | Pass | Correctly prohibited alcohol and cited Product Cleaning. |
| F5 | Partial | Product Layout reached rank 5; likely correct list, but used unsupported inference wording. |
| T1 | Partial | Correct output-power answer, but intent was misclassified as troubleshooting. |
| T2 | Pass | Complete packing list including DC Power Cord. |
| T3 | Pass | Complete rear-panel list with connector types. |
| T4 | Pass | Correct alcohol guidance; wording softened "do not use" to "not recommended." |
| U1 | Pass | Correctly refused to invent RD98XS RF output power. |
| U2 | Pass | Correctly refused to infer a frequency range from VSWR context. |
| U3 | Pass | Correctly stated that a numeric HR652 weight cannot be verified. |
| U4 | Fail | IP68 was mistaken for a product-like entity; router asked for a second comparison product. |
| A1 | Pass | Gave grounded per-product cleaning instructions; clarification was optional. |
| A2 | Fail | Required clarification, but produced a multi-product packing-list answer. |
| A3 | Fail | Required clarification; generalized Type-N Female beyond products with direct evidence. |
| A4 | Partial | Evidence supports three current products, but answer generalized beyond documented scope; wrong intent. |
| M2 | Partial | Correct cleaning answer and sections; intent should have been procedural, not standard. |
| M3 | Pass | Correct ordered installation and post-installation check from both target sections. |
| M4 | Partial | Correct multi-section answer; intent was misclassified as troubleshooting. |
| C1 | Fail | Comparison retrieval missed both Packing List sections and incorrectly claimed no accessory evidence. |
| C2 | Partial | Clarification is sensible for the current five-product corpus, but fails the old implicit two-product expectation. |
| C3 | Fail | Retrieved relevant tool sections but answered with a generic installation schema; omitted Phillips screwdriver. |
| C4 | Partial | Captured part of the distinction but omitted most named RD98XS alarms and HR652 E-codes. |

## Main findings

1. Factual and unsupported-answer behavior is generally strong. The system
   preserved exact values and resisted the deliberately planted unsupported
   traps.
2. Telegraphic questions retrieve well, but short intent classification is not
   yet reliable (T1).
3. Ambiguity policy is too narrow. It currently covers selected alarm, power,
   LED, and installation topics, but not packing lists, connectors, or ground
   locations.
4. Comparison routing is correct, but comparison retrieval and aspect/schema
   selection are the largest quality bottlenecks (C1, C3, C4).
5. Product-token normalization still confuses technical identifiers such as
   IP68 with model identifiers.
6. The 30-second answer-classifier timeout caused one transient failure. The
   isolated rerun succeeded in 29.1 seconds.
7. The validation set itself must be revised for the five-document corpus;
   notably A1, A4, and C2 no longer have exactly the assumptions under which
   they were authored.
