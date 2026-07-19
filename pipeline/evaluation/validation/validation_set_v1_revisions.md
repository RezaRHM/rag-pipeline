# Validation set v1 — expectation revisions for the five-document corpus

Date: 2026-07-19
The set was authored against the original three-document corpus
(RD98XS / HR652 / HP7). Several expectations no longer match what the
current five-document corpus actually contains. Per the calibration
principle adopted for the ambiguity work (ground truth must be
corpus-backed, recorded with evidence), the following expectations were
revised in `run_validation_set_v1.py`. No question text changed; IDs are
stable, so runs remain comparable — only grading criteria moved.

## Revised cases

### A1 — "Cleaning instructions?"
- **Old:** "Optional clarification; both nearly identical"
- **New:** Answer (per-product) or clarification both acceptable.
- **Corpus evidence:** cleaning sections are materially identical across
  manuals (HR106X 7.2, RD98XS 7.2, RD982i-S 7.1 verbatim-identical;
  HR652 9.2 same guidance, 9.1 Product Care differs slightly). A grounded
  combined or per-product answer is safe; clarifying is not a failure.

### A4 — "Ground screw location?"
- **Old:** "Clarification required"
- **New:** Answer acceptable — every documented manual places the ground
  screw on the rear panel; clarification optional.
- **Corpus evidence:** RD98XS 3.2.2 Installing the Repeater, RD982i-S
  3.2.2, HR106X 3.3 Installation Procedure all document the rear-panel
  ground screw. Value-level extraction across products agrees (verified
  live during the ambiguity-gate work); demanding a clarification here
  penalizes a factually correct, evidence-cited answer.

### C2 — "Which repeater documents its output power?"
- **Old:** "HR652 yes; RD98XS no"
- **New:** needs_clarification — no products are named in a five-product
  corpus.
- **Rationale:** the old expectation presumed the implicit two-product
  world. Comparison routing deliberately requires explicit products
  (slot validation is a route outcome, not an intent); with five
  candidates, answering for an arbitrary pair would be a guess.

## Deliberately NOT revised

- **A2 / A3** stay "clarification required": packed items and antenna
  connector types genuinely differ per product (A3's merged answer was
  factually wrong for the HR652 — UHF/SMA, not Type-N).
- **F-series / T-series / U-series / M-series** targets are unchanged;
  they encode section-level retrieval targets and exact documented
  values that remain valid.

## Grading impact

Under revised expectations, the current pipeline behavior grades:
A4 Partial→Pass, C2 Partial→Pass (both were penalized only by the outdated
criteria). Nothing else changes. The next full validation run should be
graded against these criteria.
