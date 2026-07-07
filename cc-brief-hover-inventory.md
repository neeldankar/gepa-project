# CC Brief: HoVer batch-swap feasibility inventory + post-v2 hygiene (all $0, offline)

Three tasks. NO API calls, NO live spend, NO network anywhere in this brief (run with HF_DATASETS_OFFLINE=1; if any step would require a live call or a download, STOP on that step, record the blocker, and continue with the rest). Frozen corpora are read-only: the HoVer necrosis capture, GATE-1, the IFBench logs, and all batch-swap v2 outputs must not be modified. Output is facts, counts, and file paths; no recommendation or interpretation sections anywhere.

Purpose, so the inventory is aimed correctly: we are assessing whether the frozen HoVer logs can support a port of the batch-swap v2 experiment (the IFBench version that just completed). The v2 design, as built in scripts/batch_swap_v2_run.py and batch_swap_v2_analysis.py: pair logged reflection contexts within-run; for each pair, run the proposer twice per context (reflect on batch B vs on batch B'), K=3 draws per arm; evaluate every child on BOTH batches; compute specificity and transfer with run-clustered inference. The inventory's job is to determine, for HoVer, which ingredients of that design exist in the logs, which are absent, and what the eval path would require, WITHOUT running anything live.

## Task 1: HoVer corpus inventory (the main task)

### 1a. Locate and enumerate

Find every frozen HoVer artifact in the repo (the necrosis capture and the GATE-1 corpus, plus anything else HoVer-tagged). For each: path, format, size, date, and a one-line description of what it contains. If any HoVer artifact referenced in analysis/PROJECT_STATE.md or prior analysis docs is missing from disk, list it as MISSING with the referencing document.

### 1b. Reflection-event census

For each HoVer run log found, count and tabulate:
- number of reflection events (proposer invocations), per run and total
- for each event, presence/absence of: parent program text (all modules), minibatch example ids, minibatch example CONTENT (inputs), generated outputs, SI / reflective-dataset text (the Feedback strings), per-example parent scores on the minibatch, per-example child scores post-mutation, child program text, accept decision, valset scores
- report this as a presence matrix: rows = fields above, columns = runs, entries = present-for-all-events / partial (with %) / absent
- minibatch size b used in these runs, and whether it is constant

### 1c. Pairability

Using the v2 pairing logic as the reference (scripts/batch_swap_v2_run.py pairing stage; state the actual criteria it used, read from the code): count how many valid within-run pairs the HoVer events would yield under the same criteria. Report per run and total. If the v2 criteria depend on fields absent from HoVer logs (e.g. constraint-type composition for jaccard), report which criteria are unportable, and additionally report the pair count under the weakest sane criterion (same run, distinct minibatches, parent text available). Do not invent a new pairing scheme; report counts under stated criteria only.

### 1d. Evaluation-path requirements (static analysis only)

Read the HoVer program and metric code (the ChainOfThought multi-hop program used in these runs) and report, without executing anything:
- what one child evaluation on one example requires: which LM calls (model names from config), how many calls per example (trace the module chain), whether retrieval is involved and against what (local index? remote API? which), and whether that retrieval dependency is available offline in the repo
- whether the dataset splits used by the logged runs are present on disk (paths), and whether the specific minibatch example ids in the logs resolve against them (spot-check 20 ids per run, report resolve rate)
- whether the metric is deterministic given a child output, or itself involves an LM judge
- from the logged runs, if timing/cost metadata exists per eval or per event, report per-example eval latency and any cost figures actually logged; if absent, say absent (do NOT estimate)

### 1e. Score statistics from the logs (for later MDE sizing, computed offline)

Where per-example scores exist in the HoVer logs: report the score distribution (mean, sd, min/max, fraction at floor/ceiling) for parent scores, and where child per-example scores exist, the distribution of child-minus-parent per-example deltas and per-batch sum margins. Per run and pooled. If per-example child scores are absent (as they were for IFBench v2 draws), state exactly which of these statistics are computable and report only those.

### 1f. Blockers list

End Task 1 with a flat list titled BLOCKERS: every ingredient of the v2 design that is absent or unportable for HoVer, one line each, stated as a fact (e.g. "SI text absent from runs X,Y" or "retrieval requires live API Z"). No severity ranking, no workaround proposals.

## Task 2: Cite-safe ledger correction (lottery figure)

In analysis/findings_summary.md (and its traceability map, if separate):
1. Add the batch-swap v2 verified headline numbers with provenance: pooled specificity +0.0054, run-cluster 95% CI [-0.0116, +0.0242], MDE 0.033; pooled transfer -0.0011, CI [-0.0243, +0.0228]; 382/382 pairs, 8 runs, dual-path verified (analysis/verification_postswap.md).
2. Add the lottery correction: the citable same-input accept-disagreement figure is 0.415 (own-gate batch-sum margin, strict > 0, n=764 cells). The previously reported 0.382 is a mixed estimand (margin_on_B applied to both arms, per scripts/batch_swap_v2_analysis.py:73-77) and is deprecated for external use. The prior 0.32 figure is from a different corpus/rule and is not directly comparable; note this.
3. Add the gate-instability numbers: P(decision flip vs b=3) = 0.203 at b'=1, 0.104 at b'=2; within-b' disagreement 0.372 / 0.309 (analysis/verification_postswap.md Task 4A).
4. Do not remove or alter any existing ledger entry; additions only, each with a pointer to its source file.

## Task 3: Brief-template and plan.md hygiene

1. Locate the CC brief template (or the closest thing to it; if none exists as a file, create docs/cc-brief-template-rules.md) and add two mandatory rules:
   - CALIBRATION RULE: before any plan.md cost/time projection for a live run, smoke exactly 5 units (pairs/batches/events), and the projection must be measured-per-unit x N, with the measured figures quoted. No point-sample or assumption-based projections. The APPROVED file must not be created against an uncalibrated plan.
   - PERSISTENCE RULE: any run that generates children must persist per-example score vectors for every child draw (capture_traces=True or equivalent), plus child text. Batch sums alone are insufficient. Rationale pointer: batch-swap v2 discarded draw-level per-example scores, making the 4B gate-size analysis permanently infeasible (analysis/verification_postswap.md Task 4B).
2. In the batch-swap v2 plan.md, verify the cost/time overrun note exists (projected $29 / ~8h vs actual $38.74 / ~14h, cause: point-sample calibration). If absent, add it. Do not alter the original projections.

## Output format

Single file analysis/hover_swap_inventory.md containing Task 1 (sections 1a-1f), then a short Task 2/Task 3 change log (files touched, lines added). Tables preferred over prose. Every count must carry its source path. End with a Provenance block: scripts written (paths), inputs read, confirmation that no network calls were made and no frozen file was modified. Do not write a summary, conclusion, feasibility verdict, or recommendation; the go/no-go is decided elsewhere.
