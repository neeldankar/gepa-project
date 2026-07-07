# HoVer GATE 2 — full-screen corpus cost estimate

**Date:** 2026-06-30 · **Spend: $0** (no GEPA runs, no LM calls — pure extrapolation from measured
anchors). Purpose: put a dollar figure with error bars on the GATE 2 scorer-screen corpus so the
run-directly vs run-the-~$2-kill-switch-first decision is informed.

## Anchors (both measured)

| anchor | value | source |
|---|---|---|
| GATE 1 HoVer probe | $0.142 / 24 metric calls = **$0.00592 / metric call**; 147 LM calls (144 task = 6/rollout + 3 reflection); reflection ~6% of spend, ~1 per 8 metric calls; reflection LM = gpt-4.1-mini | `capture/equality.json`, `gate1_capture.md` |
| IFBench corpus (sanity) | **$31.73** = 10 runs × mm=2500, valset=150, ~487 cycles; task gpt-4.1-mini + reflection gpt-4.1; **$0.00127 / metric call**, ~$3.17/run | `logs/baseline_*.config.json` (`results.total_usd`), `PROJECT_STATE.md`, `scripts/run_corpus.py` |

**HoVer per-metric-call ≈ 4.7–7.9× IFBench (exp 5.9×)** — because each HoVer rollout is 6 LM calls
(3 hops × 2 predictors) with the 10-full-passage `append_notes` context, vs IFBench's single Predict.

## Corpus design being priced (all parameters stated)

- **Runs (LORO folds):** 5 / 8 / 10 (proposition expected "closer to 5 than 3").
- **Per-run budget mm (dominant lever):** 1000 / 1500 / 2500. Default **2500** matches IFBench's
  cycle yield (~40–60 cycles/run at valset=150 → 5–8 runs ≈ 250–400 cycles vs IFBench 487).
- **valset = 150** (IFBench-matched). valset-eval calls ARE metric calls, so at fixed mm the $/run
  is fixed; valset size trades cycles-per-dollar, not dollars-per-mm.
- **Reflection LM:** default gpt-4.1-mini (captured object is model-independent). gpt-4.1 (IFBench
  style) adds ~$0.0013/metric call → folded into the HIGH band.

## Per-metric-call bands (all-in)

| band | $/metric call | basis |
|---|---|---|
| LOW | $0.0060 | GATE 1 measured ($0.00592), short-run, mini reflection |
| EXPECTED | $0.0075 | + ~1.25× for evolved-instruction growth over a mature run |
| HIGH | $0.0100 | + heavier growth (~1.5×) + gpt-4.1 reflection |

## Cost table — total ≈ runs × mm × $/metric-call

**EXPECTED ($0.0075/call):**

| runs \ mm | 1000 | 1500 | 2500 |
|---|---|---|---|
| **5** | $38 | $56 | **$94** |
| **8** | $60 | $90 | **$150** |
| **10** | $75 | $112 | **$188** |

**LOW–HIGH range on representative designs:**

| design | LOW | EXPECTED | HIGH | note |
|---|---|---|---|---|
| 10 × 2500 (IFBench-matched) | $150 | $188 | $250 | 4.7–7.9× IFBench's $31.73 |
| 8 × 2500 | $120 | $150 | $200 | powered |
| 5 × 2500 | $75 | $94 | $125 | powered, fewer folds |
| 8 × 1500 | $72 | $90 | $120 | powered-ish |
| 5 × 1000 | $30 | $38 | $50 | lean / underpowered LORO |
| **1 × ~300 (kill-switch)** | — | **~$2.25** | — | single-run signal check |

## Caveats

1. **Context growth is the dominant error source and biases the estimate DOWNWARD.** GATE 1's 24
   metric calls ran mostly the SHORT seed instructions; a mature run prepends evolved instructions
   (GATE 1's proposals were already ~2k chars) to every task call, on top of the 10 passages +
   accumulating notes. Hence the ×1.25–1.5 multiplier — trust EXPECTED/HIGH over LOW.
2. **valset-eval calls** dominate mm at valset=150 (baseline 150 + ~150 per accepted candidate) and
   cost the same per call as minibatch rollouts — already inside the per-call anchor.
3. **Sanity vs IFBench $31.73:** HoVer at the identical 10×2500 design ≈ $150–250, i.e. ABOVE
   IFBench by ~5–8× in the expected direction (6 calls/rollout + heavy passage context). Consistent.

## Bottom line

**GATE 2 corpus ≈ $90–190 for a properly-powered screen (low-hundreds); ~$30–50 for a
lean/underpowered one (low-tens).** Because a powered screen lands in low-hundreds AND GATE 1's
usefulness signal was genuinely mixed (variance ≠ usefulness, n≈handful), **run the ~$2 kill-switch
(1 lean run, mm≈300) first** to check the signal survives before funding the full corpus.

**$0 spent — no GEPA runs, no LM calls; arithmetic on existing measured anchors only.**
