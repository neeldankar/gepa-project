# Handoff: GEPA-SI-CURRICULUM — "selection-closed" milestone (2026-07-05)

> Unique doc ID: `gepa-si-selection-closed-20260705`. Paste this into a fresh Claude context cold.

## What this is
Research project investigating whether GEPA's reflective prompt-optimization loop can be improved by a
**curriculum over side-information (SI)** — i.e. whether *choosing which examples to reflect on* (via a
per-example scorer) beats uniform sampling. The whole project is empirical work on a frozen **IFBench**
reflective-optimization corpus (10 runs, 487 events, 382 b=3 minibatches, 54 constraint ids), plus a
thin **HoVer** probe. Nearly all analysis is offline/$0; a few small paid experiments gated on approval.

## Current state — the per-example SELECTION direction is now CLOSED (causally)
As of 2026-07-05, the headline conclusion: **there is no per-example selection lever to exploit in the
IFBench verifiable-SI regime.** Evidence, strongest last:
- **Scorer screen (Phase 1 + correct-object rescreen):** of ~43 candidate selection scorers, only
  `constraint_tractability` survived residualization — and on the *correct* proposer object (the full
  `Inputs + Generated Outputs + Feedback` triple, byte-verified), **0/5 semantic scorers beat
  constraint-identity**; the Output channel adds ≤0.
- **Outcome ICC:** per-example revision-value ΔU has **ICC ≈ 0** (crossed random effects) → no
  per-example target for a learned selector to predict.
- **Feedback ablation (live, $7.74):** deleting/genericizing the Feedback channel doesn't move one-step
  accept (0.340/0.313/0.367, p≥0.63) → the channel is causally inert; proposer call-to-call **lottery**
  (32–38% accept-flip on repeat calls) dominates outcome variance.
- **Batch-swap v2 (live, $38.74, JUST COMPLETED):** the 2×2 (reflect × gate) causal test. Pooled
  **specificity +0.005 CI[−0.012,+0.024]** and **transfer −0.001 CI[−0.024,+0.023]**, both ≈0 within
  MDE 0.033 → example-selection channel **causally inert even for the same example**. This is the
  pre-registered "strongest Claim A" and causally confirms all the correlational nulls above.

Scope caveat carried on every result: **one-step accept/ΔU gate ≠ downstream valset U**; **IFBench
verifiable-SI regime only** (does not generalize to rich-prose SI); nulls are bounded by their MDE/CI,
not proof of zero. HoVer is a different regime (~97–100% retrieval-locus failures; leaning NO-GO on a
full build — no actionability signal beyond difficulty).

## Active hypothesis
No open pre-registration. The batch-swap v2 hypothesis (does example identity matter at the one-step
gate — specificity vs transfer) was **just tested and answered NO**. Pre-reg for it lived in
`analysis/ablation/batch_swap_v2/plan.md` + the locked interpretation map in
`scripts/batch_swap_v2_analysis.py:126-141`.

## In flight
- Branch `main`, **no git commits** (repo is uncommitted; everything is on disk, gitignored artifacts).
- **Nothing is running.** The batch-swap v2 run finished cleanly (382/382 pairs, 0 restarts) and was
  recorded. No background processes remain.
- Fresh artifacts from today: `analysis/ablation/batch_swap_v2/{results.md,calls.csv,pairing.csv}`,
  run-card `notes/runs/2026-07-05-batch-swap-v2.md`, PROJECT_STATE.md `2026-07-05` entry.
- Edited `scripts/batch_swap_v2_run.py` (added `timeout=180` to both LMs) and added
  `scripts/v2_supervisor.sh` (detached resume-supervisor). Approval gate `analysis/ablation/APPROVED_V2`
  exists (created after Neel's verbal approval).

## Next steps (pick one; nothing is forced)
1. **The one remaining live lever = the ACCEPTANCE GATE** (not selection). Logged rejects show a 6.7%
   flip-rate under aggregate accept rules (weighted-coverage R3 is the workhorse; R2 minimax needs a
   no-net-regression guard). To move it you need a **live paired-seed run with UN-gated valset eval**
   (the logged corpus can't prove flips improve U — acceptance gates the broad eval = collider). Design
   notes in `analysis/gate_fliprate_probe.md` + PROJECT_STATE.
2. **Write up the closed selection direction.** `analysis/findings_summary.md` is already a near-final
   synthesis; fold in the v2 causal result to make it the definitive "selection is closed" writeup.
3. **HoVer:** currently LEAN NO-GO. Only revisit if you want to test the rich-prose-SI regime the IFBench
   nulls explicitly don't cover; one untested retrieval-fixability scorer (13% prevalence) remains.

## Where to look
- Live project log: `analysis/PROJECT_STATE.md` (long; newest entries at the bottom).
- Synthesis: `analysis/findings_summary.md`.
- Auto-memory: `phase1-scorer-screening-result` and `batch-swap-v2-result` (+ MEMORY.md index).
- Ops lesson (long laptop runs): gepa's LM passes NO request timeout → sleep-severed sockets hang
  forever, and harness-launched background tasks get reaped on session drop. Fix = `timeout=180` on the
  LMs + a detached `nohup→launchd` supervisor that resumes from checkpoint. Captured in
  `batch-swap-v2-result` memory.
