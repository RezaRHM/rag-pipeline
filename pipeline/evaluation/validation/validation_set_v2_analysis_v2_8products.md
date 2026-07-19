# Validation set v2 analysis — eight-product corpus

Run date: 2026-07-20
Branch: `comparison-pipeline-refactor` @ fd7e5dc (+ ingest of RD625 / RD962i /
RD965). Corpus: 8 products, 1819 chunks. Every expectation was read out of
the indexed sections before the question was written.

## Summary

| Status | Count |
|---|---:|
| Pass | 17 |
| Partial | 1 |
| Fail | 2 |
| Total | 20 |

Both failures share one root cause: the 8B generator lists correct retrieved
facts and then states a conclusion that contradicts them. Retrieval,
routing, product scoping and the ambiguity gate were correct in every case.

## Per-question

| ID | Status | Assessment |
|---|---|---|
| N1 | Pass | Electric drill + T10 torx, cited. (Intent read as procedural — defensible for an install question.) |
| N2 | Pass | Both supplies: DC 13.6V ±15% and AC 90–264V. |
| N3 | Pass | Below 12%, alarm indicator red, LED shows E2, plus auto power-off detail. |
| N4 | Pass | IP67, correctly cited. (MIL-STD-810 omitted, but that is not an ingress rating — the expectation was over-broad.) |
| N5 | Pass | 10 Ah. (Runtime figure omitted; the question asked capacity.) |
| T1 | Pass | Telegraphic form answered correctly, intent standard — router v3.3 holding. |
| **T2** | **Fail** | "RD965 GPS?" — retrieval returned the product's own GPS section, the answer cites it, then claims "no information about the RD965 having a GPS module … appears to be a separate product". Self-contradiction on correct evidence. |
| U1 | Pass | Output power correctly absent; lists what the document does cover. |
| U2 | Pass | **Key trap passed.** With two IP-documenting products now in the corpus (RD965 IP67, HP7 IP68), the RD962i answer stays "not mentioned" instead of borrowing. |
| U3 | Pass | Frequency range correctly absent. |
| C1 | Pass | Both tool sets listed and genuinely compared (shared T10 torx; RD962i additionally needs a cross-head). |
| C2 | Pass | RD965 IP67 vs RD98XS "not documented" — accurate, with honest absence. |
| **C3** | **Fail** | Facts extracted correctly (HR652 "E2 for Low battery alarm"; RD962i "E2" below 12%), then concludes **"No, they do not use the same alarm code"** — contradicting its own fact #1. The convergence case this question was designed to test. |
| C4 | Pass | RD98XS (Phillips + T-10 torx + spanner) vs RD625 (drill + T10 torx + ST4X16), both cited. |
| C5 | Pass | Clarifies, as designed for an unnamed-product comparison. See UX note below. |
| A1 | Pass | Clarifies naming RD625 / RD962i / RD98XS — tools genuinely differ. |
| A2 | Pass | Clarifies naming HR652 / RD625 / RD962i / RD98XS — voltage genuinely differs. |
| **A3** | **Partial** | "Is it waterproof?" clarifies correctly, but the product list (HP7, HR106X, RD962i) **omits RD965**, the one product documenting IP67. Safe outcome, wrong candidate set — a retrieval gap for the word "waterproof". |
| M1 | Pass | Three holes, wall anchors, three ST4X16 self-tapping screws, then mount. |
| M2 | Pass | Dealer sets Tx power High or Low, cited. |

## Findings

1. **The three new products are fully usable**: factual, telegraphic,
   procedural, comparison and absence questions all work against RD625,
   RD962i and RD965 with correct citations.
2. **The dangerous cross-product borrow did not happen (U2).** Adding two
   IP-documenting products did not corrupt an IP answer for a product that
   documents none — the failure mode that produced the wrong "Type-N Female"
   answer earlier in the project.
3. **Remaining failures are generation-quality, not pipeline.** T2 and C3
   both had correct, correctly-scoped evidence in context and then
   contradicted it. This is the same class as the earlier "There is no
   specific question…" waffle. Candidate mitigations: a verdict-consistency
   rule in the compare prompt ("your verdict must follow from the facts you
   listed"), or a larger model for generation.
4. **A3 retrieval gap**: "waterproof" does not reach RD965's
   "Outdoor operation and IP67 degree of protection" section. A vocabulary
   bridge (waterproof / weatherproof → ingress protection / IP rating)
   belongs in the existing synonym layer, which already maps
   protection rating → IP rating.
5. **UX note on C5**: "Which repeater documents a backup battery?" is a
   *discovery* question across the corpus, not a two-product comparison.
   The pipeline answers it with the comparison-slot clarification. Correct
   by current design, but corpus-wide discovery ("which products document
   X?") is genuinely unsupported and is worth a decision.
