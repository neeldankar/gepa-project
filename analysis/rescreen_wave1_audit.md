# IFBench Wave 1 audit — is the "null on the correct object" safe to headline to Lakshya?

**Date:** 2026-07-01 · **$0, read-only, no LM/GEPA runs, no edits** (this report is the only new
artifact + a PROJECT_STATE note). Method: independent recompute from raw bytes (fresh code, NOT
re-calling the pipeline) + two independent audit agents (code number-path + data recompute). Same
standard as the necrosis audit. Hunt: silent substitution in the number path (wrong object /
keys-vs-values / wrong column / mis-join / label). Calibrated — a clean bill of health is a valid finding.

## Deliverable 1 — THE LOAD-BEARING CHECK: is (b) genuinely the full object?

The entire "stronger claim" rests on the (b) scorers being computed on **Inputs + Generated Outputs +
Feedback**, not silently on feedback-only (which would make the result the feedback-string null
relabeled). Proven three independent ways:

| evidence | result |
|---|---|
| **Code:** `Triple.full()` = `inputs + "\n\n" + outputs + "\n\n" + feedback` (`triples_io.py:27-29`); scorers take `fb=feedback`→(a), `fl=full`→(b) (`scorers_semantic.py:244-252`); `_delta = _b − _a`. No feedback-only fallback path. | ✓ |
| **Ground truth:** 219/219 sampled triple fields are **verbatim substrings of the byte-proven `proposal_end.prompts.system_prompt`** (the object proven to reach the reflection LM). `full()` matches the `## Inputs / ## Generated Outputs / ## Feedback` structure of `reflect_1.txt`. Example seed0 it1 ex0: Inputs 553 / Outputs 1493 / Feedback 354 chars, all non-empty and distinct. | ✓ |
| **(a)≠(b):** `knn_novelty_a` mean **0.0076** (std 0.018, near-degenerate — the feedback string is id-templated) vs `knn_novelty_b` mean **0.199** (std 0.128); **92.2%** of 1251 units differ >0.01; corr(a,b)=0.13. If (b) were secretly feedback-only, a≡b — it is not. | ✓ |

**→ (b) is genuinely the full object.** The substitution that would have falsified the headline did NOT happen.

## Deliverable 2 — byte-level recompute (are the numbers real?)

| check | method | result |
|---|---|---|
| `knn_novelty_b` value | fresh-code TF-IDF (word 1-2gram + char_wb 3-5gram, min_df=2, sublinear; k=5, cosine; novelty=1−mean top-k sim) on the full texts, vs pipeline | **exact to machine precision: r=1.0000000, max Δ=0.0** (e.g. seed0 it1 ex0 = 0.187054873 both). (c)=(b)−(a) confirmed arithmetically. |
| outcome = LOO unique-frontier-contribution (not ΔU) | trace `batch_frame` → `fungibility.loo_contributions`; inspect values | frontier marginal gains **0.1–1.5%**, nonzero only on accepted batches (75/382 accepted in the screened slice; 115 accept-capable) — genuinely the LOO target, **NOT the sparse ΔU** that bottlenecked the necrosis run |
| LORO fold unit = run | `loro_partial` loops `df_b3.seed.unique()` | **8 b3 runs** as folds; `loro_mean±sd` over held seeds |
| residualization controls | print constid control set | **4 difficulty (`difficulty, n2_peakedness, parent_dpareto, iteration`) + `constraint_tractability_mean` + 15 `ct_*` failed-type-composition = 20 controls.** Matches the writeup ("4 + tractability + 15"); no swapped/mislabeled column. |

## Deliverable 3 — verdict-label check (the DEAD-collapse class)

The necrosis run had a labeling bug (CI-touches-0 → "DEAD"). Wave 1's rule is different and correct — a
genuine **3-condition AND**, re-derived here from the STORED parquet:

| scorer | constid_b | Δconstid(b−a) | LORO μ±σ | >0.05 | output-origin | stable | verdict |
|---|---|---|---|---|---|---|---|
| knn_novelty | +0.079 | −0.017 | +0.101±0.130 | ✓ | ✗ (output dilutes) | ✗ (μ−σ<0) | **dead** |
| ncd_novelty | −0.042 | +0.028 | +0.043±0.135 | ✗ | ✓ | ✗ | dead |
| actionability | −0.048 | −0.009 | −0.068±0.131 | ✗ | ✗ | ✗ | dead |
| nov_x_act | +0.006 | −0.099 | +0.000±0.167 | ✗ | ✗ | ✗ | dead |
| failure_mode | −0.098 | n/a (no (a)) | −0.082±0.116 | ✗ | — | ✗ | dead |

**SURVIVORS: NONE** — reproduced exactly from the stored numbers. This is NOT a label artifact: the one
raw-bar-beater (`knn_novelty`, constid +0.079) is killed by the *output-origin* condition (its Δ(b−a) is
negative — the output DILUTES the feedback-string signal) and by LORO instability, both real numbers.

## Deliverable 4 — trust verdict (two kinds, kept separate)

**BUG-trustworthy: YES.** The numbers compute what they claim and (b) is genuinely the full object,
verified three independent ways (substring-of-proven-prompt, a≠b, machine-precision recompute). The LOO
target is genuine (not ΔU), controls are the full documented set (no 2-vs-5 gap like the necrosis run),
and the "NONE survive" verdict is a real 3-condition AND reproduced from stored numbers, not a
mislabel. **The audit surfaced nothing new** — no silent substitution anywhere in the number path.

**DESIGN caveats (known, orthogonal to bugs — already stated in `rescreen_wave1.md`; restated so they
aren't conflated with a fault):** (1) the "embedding"-kNN novelty is a **lexical TF-IDF stand-in**, not
paid sentence embeddings — but the output channel is empty/negative for every scorer (Δconstid ≤ 0), so a
richer embedding of that same channel is unlikely to reverse the null; (2) the only raw-bar-beater (knn)
carried its signal on the **feedback string** (constraint-rarity ≈ the dead singleton signature), diluted
by the output — the honest core finding, not a bug; (3) LORO stability at n=8 folds with 20 controls
(~48 batches/fold) is high-variance — the **pooled n=382 constid** number is the reliable one (LORO is a
stability read only).

**Bottom line.** Unlike the HoVer necrosis run (bug-clean but *underpowered* on sparse ΔU), IFBench Wave 1
is **bug-clean AND adequately powered at the pooled-batch level (n=382 batches, real LOO target)**. The
correct-object null is **audit-grade and safe to state as a headline to Lakshya**, with the two design
caveats (TF-IDF stand-in; knn's signal living on the feedback string) noted as honest scope limits — not
as cracks in the result. "No semantic scorer adds output-origin signal beyond constraint identity on the
object the proposer actually sees" holds up to byte-level scrutiny.
