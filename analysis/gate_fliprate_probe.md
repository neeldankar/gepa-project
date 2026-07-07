# Gate flip-rate probe — does an aggregate accept rule behave differently from the pointwise gate?

**Date:** 2026-07-02 · **$0, read-only, no runs** (frozen IFBench corpus untouched: baseline logs
2026-06-26). Script: `scripts/run_gate_fliprate_probe.py`. **IFBench only** — HoVer's necrosis dumps
log only per-example scalar recall (no per-gold-doc parent-vs-child binary), so the constraint-level
flip rules are not computable there (noted, not leaned on).

**Purpose.** The selection direction is closing (offline batch checks: IFBench outcome ~90%
unpredictable; HoVer failures ~90% retrieval-only). The **gate** direction is the live candidate. This
probe pre-qualifies it: on logged data, does an aggregate accept rule flip any REJECTED children to
accept — i.e. does it behave differently from the pointwise gate at all?

## HONESTY GUARD (read first)
The corpus **cannot** say whether a flipped-accept would improve U. Rejected children never received a
valset eval — acceptance gates the broad eval; that is the collider. This probe answers **only** "does
the aggregate gate behave differently from pointwise at all." Flip-rate ≈ 0 → kill the live gate idea.
Meaningful flip-rate → the live experiment is worth designing, and **only a live paired-seed run proves
it helps**. **The flip-rate is NOT evidence the gate works.**

## Setup
267 logged-REJECTED b3 children (of 382 cycles = 115 accept + 267 reject), each with aligned
parent/child per-constraint binary scores (full coverage). Ground truth = the logged accept flag (the
pointwise proxy `child_mean>parent_mean` reconciles 99% of rejects / 90% of accepts; the ~10% gap is
GEPA weighting per-example, not flat per-constraint). No committed gate-pivot doc exists, so the three
rules are implemented from the brief with stated parameters:
- **R1 majority-fix** — flip iff the child satisfies a MAJORITY (>50%) of the constraints the parent
  failed (ignores regressions).
- **R2 minimax-lineage** — worst-case: flip iff the child STRICTLY improves the constraint TYPE the
  lineage persistently fails most. History window = all prior cycles in the same run (expanding);
  fallback to corpus type fail-rate if unseen.
- **R3 weighted-coverage** — boosting: weight each constraint by corpus difficulty (global type
  fail-rate `type_failrate()`); flip iff weighted child score > weighted parent score.

## Flip-rate table

| rule | flips / 267 | flip rate | median (fix, lost) | fixed-difficulty vs lost-difficulty |
|---|---|---|---|---|
| R1 majority-fix | 1 | **0.4%** | (1, 1) | 0.67 vs 0.56 |
| R2 minimax-lineage | 7 | **2.6%** | (1, 1) | **0.73 vs 0.45** |
| R3 weighted-coverage | 16 | **6.0%** | (1, 1) | 0.57 vs 0.37 |
| **any rule** | **18** | **6.7%** | — | — |

## Trade distribution of flips (fixed vs lost constraints per flip)
`(#fixed, #lost) → count`:
- R1: `{(1,1): 1}`
- R2: `{(1,1): 4, (1,2): 1, (2,1): 1, (1,3): 1}`
- R3: `{(1,1): 12, (2,1): 2, (1,2): 1, (2,2): 1}`

The **target texture** ("fix ≥2 stubborn, lose ≤1 easier", fixed-difficulty ≥ lost-difficulty) is
**rare: R1 0/1, R2 1/7, R3 2/16** (3 flips total). Most flips are 1-fix-1-loss washes. But the
*direction* is right: across flips, fixes land on **harder** constraints than losses (R2 0.73 vs 0.45;
R3 0.57 vs 0.37) — the aggregate rules do preferentially admit "fix-the-hard-thing" trades, just not
often, and not always cleanly.

## Overlap between rules
- R1 ∩ R2 = 1 (Jaccard 0.14) · R1 ∩ R3 = 1 (0.06) · R2 ∩ R3 = 5 (0.28)
- flipped by ALL 3 = 1 · flipped by ANY = 18/267 (6.7%)

The rules mostly flip **different** children — they are genuinely distinct behaviors, not three names
for one rule. R1 (majority-fix) is essentially inert; R3 (weighted-coverage) is the most active; R2
(minimax) picks the highest-difficulty fixes.

## Verbatim flipped events (parent vs child per-constraint; why it flips)

```
[seed7 it37]  flips under R3_weighted_coverage   — the target texture
  ex0 FIX  keywords:frequency              parent=0 child=1  (difficulty 0.42)
  ex1 FIX  count:count_increment_word      parent=0 child=1  (difficulty 0.86)  <- stubborn
  ex2 LOSS change_case:english_lowercase   parent=1 child=0  (difficulty 0.32)  <- easy
  -> fixes 2 (incl a very hard count constraint), loses 1 easy case-constraint; weighted score rises,
     so R3 accepts what pointwise rejected.

[seed5 it47]  flips under R2_minimax_lineage + R3
  ex1 LOSS detectable_format:square_brackets    parent=1 child=0  (0.45)
  ex2 FIX  detectable_format:multiple_sections  parent=0 child=1  (0.45)
  ex2 FIX  letters:letter_counting2             parent=0 child=1  (0.56)
  -> 2 fixes / 1 loss; the lineage's worst-persistent type improves -> R2 flips.

[seed5 it41]  flips under R3_weighted_coverage   — a wash, shown for honesty
  ex0 FIX  last_word:last_word_answer     parent=0 child=1 (0.43) ; FIX first_word:first_word_answer (0.67)
  ex0 LOSS punctuation:no_comma           parent=1 child=0 (0.31) ; ex2 LOSS keywords:no_adjacent_consecutive (0.42)
  -> 2 fixes / 2 losses; weighted score barely tips positive -> a marginal, debatable flip.

[seed5 it59]  flips under R2_minimax_lineage     — a BAD trade the rule still admits
  ex0 FIX  copy:repeat_phrase             parent=0 child=1  (0.96)  <- fixes the single hardest type
  ex0 LOSS punctuation:no_comma (0.31) ; ex1 LOSS detectable_format:bigram_wrapping (0.45) ; ex2 LOSS first_word:first_word_answer (0.67)
  -> 1 fix / 3 losses; R2 flips because it only checks the worst-persistent bucket (copy) — a caution
     that the minimax rule can admit net-negative trades.
```

## Verdict — LEAN GO (small), with rule pruning
Flip-rate is **not ≈ 0** (kill threshold not met): **6.7% of rejects flip under ≥1 aggregate rule**
(R3 6.0%, R2 2.6%, R1 0.4%). The aggregate gate genuinely behaves differently from pointwise on ~1-in-15
rejected children (~2-3 extra accepts per run), and preferentially on fix-the-hard-constraint trades —
so **the live gate experiment is worth designing.** Caveats for the design: (1) the effect is **small**
— a live paired-seed run must be powered to detect a ~7%-of-rejects behavioral delta; (2) **drop R1**
(inert at 0.4%); **R3 is the workhorse, R2 the aggressive minimax** (which can admit net-negative
1-fix-3-loss trades — seed5 it59 — so it needs a no-net-regression guard); (3) the clean "fix stubborn,
lose easy" texture is real but rare (3 flips). **This says nothing about U** — only a live run with the
valset eval un-gated (score realized SI regardless of accept) can show whether these flips help. Go/no-go:
**GO on designing the live gate experiment; NO to reading any of this as the gate working.**
