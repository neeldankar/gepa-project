# state-dependent — §15-12 degeneracy and §15-4 monitored descriptives

Numbers only. No interpretation, no verdicts, no grid-cell assignment.
Emitted by `emit_descriptives.py` from `dose.json` (235 events) and 24 `run_summary.json`.

---

## §15-12 — selection-pressure degeneracy

### The criterion, verbatim (design v2 §15, item 12)

> 12. **Selection-pressure degeneracy.** If realized novelty scores are near-constant across the
>     6 (nothing to select on), T ≈ C by construction and the experiment measures nothing.
>     Monitored: per-event novelty spread and T-vs-C choice overlap (§8). §11-0 converts this from
>     monitor-only into a **pre-spend estimate**. A (null,null) read must check this descriptive
>     before concluding "signal doesn't transfer".

**§15-12 states no numeric threshold.** It says "near-constant" and names the statistics to
monitor; it does not define a cutoff separating degenerate from non-degenerate events. No
threshold is invented here. The distributions below are reported in full; the only counts
given are exact zeros, which require no threshold.

Statistics are those §11-0 (`:740-742`) names as the degeneracy pre-estimate: per-event
novelty spread as **max−min** and **SD of the 6**, plus the **top-3 − bottom-3 mean gap**.
`*_norm` divides by that seed's within-run SD (`dose_compute.py:74-77`), the unit β is
expressed in (§11-1).

### Across all 235 events

| statistic | n | mean | SD | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|---|---|
| SD of the 6 | 235 | 0.041718 | 0.019122 | 0.009070 | 0.026553 | 0.039240 | 0.053986 | 0.099093 |
| range (max−min) | 235 | 0.111916 | 0.053113 | 0.019604 | 0.069448 | 0.100014 | 0.147389 | 0.281178 |
| top3 − bottom3 mean | 235 | 0.059437 | 0.026932 | 0.013339 | 0.038506 | 0.058594 | 0.074774 | 0.149801 |
| SD / within-run SD | 235 | 1.655675 | 0.776979 | 0.351328 | 1.037291 | 1.553828 | 2.142307 | 3.850752 |
| range / within-run SD | 235 | 4.444318 | 2.155840 | 0.845162 | 2.676116 | 4.028318 | 5.925279 | 10.595353 |
| (top3 − bottom3) / within-run SD | 235 | 2.357535 | 1.094513 | 0.533328 | 1.534253 | 2.282464 | 3.008203 | 5.650293 |

### Exact-zero counts (threshold-free)

| quantity | events | of | fraction |
|---|---|---|---|
| range (max−min) == 0 exactly | 0 | 235 | 0.000000 |
| top3 − bottom3 == 0 exactly | 0 | 235 | 0.000000 |

### Per seed

**range (max−min)**

| seed | n | mean | SD | min | median | max |
|---|---|---|---|---|---|---|
| 0 | 31 | 0.113377 | 0.049917 | 0.037457 | 0.114414 | 0.196291 |
| 1 | 33 | 0.102025 | 0.047286 | 0.030045 | 0.079740 | 0.239006 |
| 2 | 27 | 0.106204 | 0.040503 | 0.035147 | 0.100370 | 0.194696 |
| 3 | 32 | 0.107196 | 0.062082 | 0.019604 | 0.093940 | 0.245583 |
| 4 | 26 | 0.114573 | 0.061331 | 0.026184 | 0.096024 | 0.278075 |
| 5 | 33 | 0.112478 | 0.051370 | 0.030808 | 0.095310 | 0.224569 |
| 6 | 27 | 0.121720 | 0.050091 | 0.023999 | 0.105068 | 0.210471 |
| 7 | 26 | 0.120920 | 0.062663 | 0.032007 | 0.112807 | 0.281178 |

**top3 − bottom3 mean**

| seed | n | mean | SD | min | median | max |
|---|---|---|---|---|---|---|
| 0 | 31 | 0.058776 | 0.024259 | 0.020445 | 0.061316 | 0.108252 |
| 1 | 33 | 0.053404 | 0.023932 | 0.016840 | 0.046534 | 0.133037 |
| 2 | 27 | 0.060107 | 0.019313 | 0.018826 | 0.062487 | 0.094437 |
| 3 | 32 | 0.057112 | 0.032634 | 0.016161 | 0.055769 | 0.131063 |
| 4 | 26 | 0.059912 | 0.028028 | 0.016188 | 0.065432 | 0.114826 |
| 5 | 33 | 0.059804 | 0.027201 | 0.014978 | 0.057971 | 0.140457 |
| 6 | 27 | 0.065635 | 0.029493 | 0.013339 | 0.061312 | 0.135982 |
| 7 | 26 | 0.062667 | 0.029918 | 0.016485 | 0.060501 | 0.149801 |

**(top3 − bottom3) / within-run SD**

| seed | n | mean | SD | min | median | max |
|---|---|---|---|---|---|---|
| 0 | 31 | 2.687551 | 1.109225 | 0.934864 | 2.803678 | 4.949804 |
| 1 | 33 | 2.185743 | 0.979485 | 0.689236 | 1.904563 | 5.444978 |
| 2 | 27 | 2.040257 | 0.655567 | 0.639024 | 2.121070 | 3.205569 |
| 3 | 32 | 2.462157 | 1.406901 | 0.696720 | 2.404263 | 5.650293 |
| 4 | 26 | 2.086561 | 0.976137 | 0.563801 | 2.278819 | 3.999063 |
| 5 | 33 | 2.369614 | 1.077790 | 0.593487 | 2.296981 | 5.565321 |
| 6 | 27 | 2.624303 | 1.179213 | 0.533328 | 2.451441 | 5.436991 |
| 7 | 26 | 2.361431 | 1.127375 | 0.621183 | 2.279786 | 5.644792 |

### T-vs-C choice overlap (structural constant, not measured)

| quantity | value |
|---|---|
| E[ \|top-3 ∩ random-3\| ] over all C(6,3)=20 subsets | 1.500000 |
| hypergeometric mean 3·3/6 | 1.500000 |
| implied expected disjoint picks per event | 1.500000 of 3 |

This is a property of pick-3-of-6, identical in every arm and event; it does not depend on
the novelty scores and is reported because §11-0 lists it as an output.

---

## §15-4 — monitored descriptives (no tests)

`accept_rate` = `accepts` / `reflection_events` from each run's `run_summary.json`.

### Per-arm means over the 8 seeds

| arm | accept rate | reflection events | candidates (incl. seed) | accepts | total evals |
|---|---|---|---|---|---|
| B | 0.345631 | 31.2500 | 11.5000 | 10.5000 | 303.2500 |
| C | 0.255815 | 26.0000 | 7.5000 | 6.5000 | 309.0000 |
| T | 0.383817 | 23.3750 | 9.8750 | 8.8750 | 309.1250 |

### Per-arm SD over the 8 seeds

| arm | accept rate | reflection events | candidates (incl. seed) |
|---|---|---|---|
| B | 0.102666 | 3.3700 | 2.0000 |
| C | 0.085197 | 2.0702 | 1.7728 |
| T | 0.081259 | 1.4079 | 1.4577 |

### Per seed, per arm

| arm | seed | reflection events | child-bearing events | accepts | accept rate | candidates (incl. seed) | total evals |
|---|---|---|---|---|---|---|---|
| B | 0 | 32 | 32 | 10 | 0.312500 | 11 | 302 |
| B | 1 | 32 | 32 | 10 | 0.312500 | 11 | 302 |
| B | 2 | 35 | 35 | 8 | 0.228571 | 9 | 300 |
| B | 3 | 32 | 32 | 10 | 0.312500 | 11 | 302 |
| B | 4 | 27 | 27 | 13 | 0.481481 | 14 | 302 |
| B | 5 | 36 | 36 | 8 | 0.222222 | 9 | 309 |
| B | 6 | 29 | 29 | 12 | 0.413793 | 13 | 304 |
| B | 7 | 27 | 27 | 13 | 0.481481 | 14 | 305 |
| C | 0 | 27 | 27 | 6 | 0.222222 | 7 | 313 |
| C | 1 | 30 | 30 | 3 | 0.100000 | 4 | 310 |
| C | 2 | 27 | 27 | 6 | 0.222222 | 7 | 313 |
| C | 3 | 25 | 25 | 8 | 0.320000 | 9 | 315 |
| C | 4 | 23 | 23 | 9 | 0.391304 | 10 | 307 |
| C | 5 | 26 | 26 | 6 | 0.230769 | 7 | 304 |
| C | 6 | 25 | 25 | 7 | 0.280000 | 8 | 305 |
| C | 7 | 25 | 25 | 7 | 0.280000 | 8 | 305 |
| T | 0 | 23 | 23 | 9 | 0.391304 | 10 | 307 |
| T | 1 | 22 | 22 | 10 | 0.454545 | 11 | 308 |
| T | 2 | 23 | 23 | 9 | 0.391304 | 10 | 307 |
| T | 3 | 26 | 26 | 6 | 0.230769 | 7 | 304 |
| T | 4 | 23 | 23 | 9 | 0.391304 | 10 | 307 |
| T | 5 | 25 | 25 | 8 | 0.320000 | 9 | 315 |
| T | 6 | 23 | 23 | 9 | 0.391304 | 10 | 307 |
| T | 7 | 22 | 22 | 11 | 0.500000 | 12 | 318 |

---

## Provenance

| field | value |
|---|---|
| events (dose.json per_event) | 235 |
| run summaries read | 24 |
| dose.json sha256 | `9f39646103a63d7d243f6c6e5c6a6a82035ad8e0d3ede8b95369b4c975b17768` |
| emit_descriptives.py sha256 | `a1cfed65d46ee19f4c33dab4a2e14fa6503c9341f09b680feb934892dcfc5f34` |
| emitted | 2026-08-24T20:27:05 |

### verification performed before emission

- 235 events, each with exactly 6 novelty scores
- 24 run summaries, arm/seed field matching directory name, 8 per arm
- every per-event spread computed twice (numpy vs pure Python), |delta| <= 1e-12
- every summary computed twice (numpy vs pure Python), |delta| <= 1e-12
- expected overlap by exact 20-subset enumeration vs hypergeometric mean, |delta| <= 1e-12

