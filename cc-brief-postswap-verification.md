# CC Brief: batch-swap v2 post-run verification + gate-size probe (all $0, offline)

Four tasks on frozen data. NO API calls, NO live spend anywhere in this brief. Corpora are read-only: do not modify calls/pairing CSVs or any frozen corpus file. All outputs are numbers + CIs; do NOT write interpretation language anywhere. Where a task reproduces a Desktop number, report MATCH or MISMATCH against the reference value to 4 decimals. If MISMATCH, report your number, the reference, and the first point of divergence; do not reconcile silently.

## Task 1: Independent reproduction of the sibling-ranking probe

Reproduce from the repo's own batch-swap v2 outputs (not from any Desktop-provided file). Definitions, exactly:

- Arm-cell = (pair, arm). 382 pairs x 2 arms = 764 cells, 3 draws each.
- own-margin of a draw = margin on the reflected batch (margin_on_B for arm R_B, margin_on_Bp for arm R_Bp). other-margin = margin on the non-reflected batch.
- Accept (for this task) = own-margin > 0.
- Best-of-3 selection = within each cell, the draw(s) with max own-margin; ties averaged over tied draws.
- Selection lift = mean over cells of [mean other-margin of selected draw(s) minus mean other-margin of all 3 draws].
- Within-cell correlation = demean own- and other-margins within each cell, pool all 2292 demeaned points, Pearson.
- CI on selection lift: cluster bootstrap resampling the 8 runs with replacement (run = seed prefix of B_id), 4000 iterations, percentile 95%.

Reference values to verify against:
- single-draw accept rate 0.3443 (report to 4dp); best-of-3 accept rate 0.5641 (4dp) [references given at 3dp: 0.344, 0.564]
- E[own-margin] single +0.0043; best-of-3 selected +0.2298
- selection lift +0.0059, cluster CI [-0.0057, +0.0199]
- within-cell correlation +0.0010

Also report, new: the same selection lift computed with accept >= 0 (tie-tolerant) and with selection by max child_sum instead of max margin, as robustness rows. No reference values; just report.

## Task 2: Provenance of the 0.382 lottery figure

results.md reports within-arm accept disagreement across draws = 0.382. Locate the exact code path that produced this number and report:

1. The exact accept rule used (per-example pointwise comparison vs batch-sum margin; > vs >=; any tie or normalization handling).
2. The exact denominator (which cells, any exclusions).
3. Recompute the figure from that code path and confirm it returns 0.382.
4. For the record, also compute the same statistic under batch-sum margin > 0 and >= 0 (Desktop got 0.4149 and 0.3979; report MATCH/MISMATCH).

Then append a one-line provenance note under the Lottery section of results.md stating the rule, e.g.: "Accept rule for this figure: <rule>. Sum-margin variants: 0.415 (>0), 0.398 (>=0)."

## Task 3: results.md corrections

1. In the Overlap decomposition section, delete the parenthetical claim "(stays >0: example-level)" and the reliance on predicted@overlap=1. Replace the section body with: "specificity ~ type_jaccard OLS: intercept -0.0176, slope +0.0690. Decomposition uninformative: run-cluster bootstrap slope 95% CI [-0.0739, +0.1959]; extrapolated prediction at overlap=1 95% CI [-0.0476, +0.1368]; observed jaccard support max 0.83 (mean 0.335), so overlap=1 is out of support. No masking or example-level residual is supported."
2. Add a definitions line under the Headline table: "Pooled specificity = mean over pairs of ((margin_on_B | R_B) - (margin_on_B | R_Bp) + (margin_on_Bp | R_Bp) - (margin_on_Bp | R_B)) / 2, draws averaged within arm first. Pooled transfer = mean over pairs of mismatched-arm margins ((margin_on_B | R_Bp) + (margin_on_Bp | R_B)) / 2."  Verify these definitions against the harness code before adding; if the harness used different definitions, report the actual ones and flag MISMATCH.
3. Do not change any number in the file.

## Task 4: Gate-size probe (decision instability and sibling-ranking vs n)

Uses per-example (per-constraint) parent/child binary scores logged for the 382 batch-swap batches, plus the 2 logged b=1 baseline runs.

A. Decision instability vs gate size. For each cell, the realized gate decision uses b=3 examples. Recompute the accept decision under all subsampled gates b'=1 (3 subsets per batch) and b'=2 (3 subsets per batch), using the SAME accept rule as the harness (from Task 2). Report: P(subsampled decision differs from full b=3 decision) at b'=1 and b'=2, overall and per run. Also report within-b' disagreement (do the 3 possible b'=1 gates agree with each other), same for b'=2.

B. Sibling-ranking vs gate size. Within each arm-cell, rank the 3 sibling draws by own-margin computed on b'=1 and b'=2 subsets; report the mean Spearman correlation of those rankings with (i) the full b=3 own-margin ranking and (ii) the other-batch margin ranking (the held-out criterion). This extends the Task 1 correlation downward in n; note we cannot extend upward with this corpus.

C. Cross-check: from the 2 logged b=1 runs, report the accept rate and any same-input repeat-draw disagreement statistic that exists in those logs, for comparison against A.

Output all of Task 4 as a small table plus, if convenient, a CSV of the instability-vs-n points. No smoothing, no fitted curves, no interpretation.

## Output format

Single file analysis/verification_postswap.md containing: Task 1 table with MATCH/MISMATCH column; Task 2 provenance statement + recomputed values; Task 3 diff summary (what changed in results.md); Task 4 tables. Numbers and CIs only. End the file with a Provenance block listing script paths and seeds used. Do not write a summary, conclusion, or recommendation section.
