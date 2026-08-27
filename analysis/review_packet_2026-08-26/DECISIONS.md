# DECISIONS

Load-bearing choices, so they do not get relitigated. The binding text is always the frozen design
doc; this file is the index and the reasoning.

## 2026-07-22: The endpoint is a 50-claim selection-split argmax, not a val-argmax (design §8b)

- Why: on the 8 Stage-1 runs the val score lattice (`|D_pareto| = 10`, per-example scores on
  {0, ⅓, ⅔, 1}) collapsed 10–14 candidates onto 4–7 distinct means, so the tie-break decided the
  endpoint on 4/8 seeds and the seed prompt was returned on 2/8 despite a dozen accepted candidates.
  A paired `T − C` of exactly 0 does not add noise — it deletes that seed from the exact sign-flip
  test and eats the n=8 power the whole design rests on.
- Rules out: reading any Stage-1 endpoint as comparable to a v2.1 endpoint; and the cheap version of
  the Stage-1 backfill — the MDE's margins must come from the same estimator the live runs use, so
  all 97 Stage-1 candidates get re-scored ($22.03) rather than just the 8 val-argmax winners ($5.45).

## 2026-07-22: The MDE is assigned before `results.md` is read, not before `APPROVED-liverun`

- Why: what protects the confirmatory-vs-estimation-only label is that it is fixed before anyone
  sees an outcome. Requiring it before launch additionally chained the launch to
  `APPROVED-testsplit` → `APPROVED-backfill` → `APPROVED-dose`, which buys nothing the read-order
  rule does not already buy.
- Rules out: treating the MDE as a launch gate, or re-labelling the framing after reading the grid.
  If the label is not on disk when `results.md` is first read, the run is estimation-only by default.

## 2026-07-22: `skip_perfect_scope = chosen3`; dose event set = 235

- Why: `chosen3` gives semantic parity with arm B — the skip gate reads the same 3 examples that
  become the reflection minibatch, so both arms decide "is there anything to learn here?" about the
  same object. 235 is the event set β was estimated on, so `D` and `β` share a frame inside the
  product `D × β/2`.
- Rules out: gating on all 6 (which unmatches the arms), and defining the dose on 243 events with 8
  undefined (which would put `D` and `β` on different frames).

## 2026-07-22: `.venv-armT` rebuilt from an explicit lockfile, with a donor precedence rule

- Why: the venv could not run the experiment — no `bm25s` or `PyStemmer`, which `probe.py` imports
  at module load — and had drifted from the Stage-1 LM client (litellm 1.91.1 vs 1.90.1), which is
  where cost accounting and retry behaviour live, while arm B is supposed to reproduce Stage-1 cost.
- Rules out: ad-hoc `pip install` patching. The rule is now written down: the probe donor wins the
  optimization / LM / retrieval path, the screen donor wins the embedding stack, and the embedding
  stack wins the `tokenizers` collision. Both $0 acceptance gates were re-run against the rebuilt
  venv and both passed — bitwise-identical embeddings, 235/235 byte-exact novelty — which is the
  evidence, not the version numbers.
