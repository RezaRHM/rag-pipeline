# Validation set v1 analysis — table-flattened generation context

Run date: 2026-07-19
Branch: `comparison-pipeline-refactor` @ 620db6c. Baseline for comparison:
the ambiguity-gate run (18/6/0, same branch @ 4448aa1).

## Summary

| Status | v3.1 | comparison | ambiguity | This run |
|---|---:|---:|---:|---:|
| Pass | 11 | 16 | 18 | **19** |
| Partial | 8 | 6 | 6 | **5** |
| Fail | 5 | 2 | 0 | **0** |

Zero route/intent changes against the previous run — the context transform
altered only answer content.

## Changed cases

| ID | Before | Now | Assessment |
|---|---|---|---|
| **F2** | **Partial** | **Pass** | All three packed items with quantities (Repeater, Documentation Kit, DC Power Cord); the false "no other items" claim is gone. The dropped-table-row failure had reproduced in three consecutive runs before this fix. |
| F5 | Partial | Partial | Changed flavor: the unsupported inference wording is gone and the answer scopes itself honestly to the HR652, but the component list shrank from five items to three. The Product Layout table does not explicitly mark which parts are front-panel, so the model now under-selects instead of over-inferring. Remaining work is data-shape (panel attribution), not prompt wording. |

## Remaining Partials

| ID | Category |
|---|---|
| F5 | Product Layout panel attribution (data/ingest shape) |
| T1, M4 | Short-question intent (known open item) |
| A4, C2 | Outdated validation expectations (revision task) |

## Main findings

1. Markdown tables are now rewritten as explicit per-row lines in the
   generation context. This closed F2 and removed F5's inference wording;
   generic transform, no domain knowledge.
2. U-series refusals intact; U1 gained a verbose-but-grounded addendum
   (quotes a related documented statement after the plain refusal) — worth
   watching, not an unsupported claim.
3. The validation set is now fail-free with every remaining Partial mapped
   to a named, separate work item.
