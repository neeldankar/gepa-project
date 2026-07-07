# CC brief template — mandatory rules

Rules every CC brief and its downstream `plan.md` must satisfy before any paid/live work.

## CALIBRATION RULE

Before any `plan.md` cost/time projection for a live run, smoke exactly **5 units** (pairs / batches
/ events) and derive the projection as **measured-per-unit × N**, with the measured per-unit figures
quoted in the plan. No point-sample projections and no assumption-based projections. The `APPROVED`
file must not be created against an uncalibrated plan.

## PERSISTENCE RULE

Any run that generates children must persist **per-example score vectors for every child draw**
(`capture_traces=True` or equivalent), plus the child text. Batch sums alone are insufficient.

Rationale: batch-swap v2 discarded draw-level per-example child scores, making the 4B gate-size
analysis permanently infeasible (`analysis/verification_postswap.md` Task 4B).
