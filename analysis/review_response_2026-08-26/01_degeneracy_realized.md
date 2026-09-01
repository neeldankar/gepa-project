# Item 1: which corpus is the degeneracy check computed on

Numbers only. No interpretation.

## Finding

`dose.json`'s 235 events are **(b), the pre-experiment corpus**, not the live runs.

| evidence | value |
|---|---|
| `dose_compute.py:48` | `SCREEN = analysis/hover_screen` |
| `dose_compute.py:232` | enumerates events from `SCREEN/events_index.json` |
| `events_index.json` | 243 entries, mtime 2026-07-09, keys `{seed, trace_i, ordinal, idx, subsample_ids, accept, ...}` |
| `dose_acquire.py:50-52` | texts resolved from `analysis/ablation/hover_swap/pairs` (243 pair dirs) |
| 243 minus 8 ordinal-0 events with no k=3 archive | **235** |
| live experiment reflection events | 645 across 24 runs; 187 in arm T |

The realized live novelty scores WERE persisted, in `runs/<arm>_seed<n>/event_log.json` as a
per-event `novelties` 6-vector. The realized distribution is computed below.

## Events available

| arm | events in log | usable (complete non-NaN 6-vector) | excluded |
|---|---|---|---|
| B | 0 | 0 | none |
| C | 208 | 200 | coldstart_archive_lt_3 8 |
| T | 187 | 179 | coldstart_archive_lt_3 8 |

Arm B draws 3 examples directly and has no 6-candidate step, so no novelty vector exists for it.

## Realized spread, live runs

### Arm T (179 events)

| statistic | n | mean | SD | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|---|---|
| SD of the 6 | 179 | 0.034592 | 0.017391 | 0.005435 | 0.021681 | 0.031402 | 0.043707 | 0.096383 |
| range (max minus min) | 179 | 0.091947 | 0.046903 | 0.014582 | 0.057801 | 0.082401 | 0.114818 | 0.259944 |
| top3 minus bottom3 mean | 179 | 0.050232 | 0.024739 | 0.006804 | 0.032002 | 0.046508 | 0.062668 | 0.133280 |
| SD / within-run SD | 179 | 1.366711 | 0.703124 | 0.222458 | 0.879738 | 1.219407 | 1.695848 | 3.818990 |
| range / within-run SD | 179 | 3.635473 | 1.907943 | 0.596823 | 2.275983 | 3.240576 | 4.458190 | 10.299773 |
| (top3 minus bottom3) / within-run SD | 179 | 1.980984 | 0.981827 | 0.311130 | 1.295573 | 1.819848 | 2.435174 | 5.169971 |
| selected_min minus E[random-3 min] | 179 | 0.030982 | 0.017894 | 0.002228 | 0.017753 | 0.026193 | 0.040955 | 0.122488 |
| that gap / within-run SD | 179 | 1.220102 | 0.690181 | 0.101855 | 0.691473 | 1.047497 | 1.600455 | 4.214044 |

Exact zeros: range == 0 in **0/179**; top3 minus bottom3 == 0 in **0/179**.

Per seed, (top3 minus bottom3) / within-run SD:

| seed | n | mean | SD | min | median | max |
|---|---|---|---|---|---|---|
| 0 | 22 | 2.168379 | 1.119893 | 0.311130 | 1.762899 | 4.782271 |
| 1 | 21 | 2.029244 | 1.007908 | 0.343634 | 1.939952 | 4.435111 |
| 2 | 22 | 1.883610 | 0.885474 | 0.809233 | 1.659953 | 4.455282 |
| 3 | 25 | 2.002906 | 0.930083 | 0.317481 | 1.992083 | 4.702924 |
| 4 | 22 | 1.550890 | 0.775221 | 0.547595 | 1.488460 | 3.724842 |
| 5 | 24 | 1.928369 | 1.107090 | 0.491497 | 1.662800 | 5.169971 |
| 6 | 22 | 2.206316 | 0.798970 | 1.025441 | 2.048204 | 4.444765 |
| 7 | 21 | 2.086962 | 1.161055 | 0.472216 | 1.819848 | 5.022280 |

### Arm C (200 events)

| statistic | n | mean | SD | min | p25 | median | p75 | max |
|---|---|---|---|---|---|---|---|---|
| SD of the 6 | 200 | 0.045981 | 0.020785 | 0.006292 | 0.030245 | 0.043562 | 0.059604 | 0.097556 |
| range (max minus min) | 200 | 0.120680 | 0.055335 | 0.017175 | 0.078314 | 0.115072 | 0.155371 | 0.259974 |
| top3 minus bottom3 mean | 200 | 0.065823 | 0.029914 | 0.008029 | 0.044356 | 0.061610 | 0.082781 | 0.165470 |
| SD / within-run SD | 200 | 1.816555 | 0.839910 | 0.277207 | 1.155729 | 1.735384 | 2.310242 | 3.926623 |
| range / within-run SD | 200 | 4.768091 | 2.237565 | 0.701562 | 3.080339 | 4.490213 | 6.111457 | 10.664420 |
| (top3 minus bottom3) / within-run SD | 200 | 2.599998 | 1.204474 | 0.367121 | 1.725922 | 2.410310 | 3.258052 | 6.235241 |
| selected_min minus E[random-3 min] | 200 | 0.036102 | 0.020917 | 0.002312 | 0.021341 | 0.032095 | 0.045885 | 0.122247 |
| that gap / within-run SD | 200 | 1.425700 | 0.826520 | 0.087113 | 0.834043 | 1.270625 | 1.795196 | 4.606510 |

Exact zeros: range == 0 in **0/200**; top3 minus bottom3 == 0 in **0/200**.

Per seed, (top3 minus bottom3) / within-run SD:

| seed | n | mean | SD | min | median | max |
|---|---|---|---|---|---|---|
| 0 | 26 | 3.000854 | 1.352595 | 0.367121 | 3.201993 | 5.588680 |
| 1 | 29 | 2.703198 | 1.372752 | 0.583557 | 2.807270 | 5.706692 |
| 2 | 26 | 2.340852 | 0.935389 | 0.933023 | 2.315165 | 4.523400 |
| 3 | 24 | 2.582479 | 1.102640 | 1.455882 | 2.106956 | 5.492098 |
| 4 | 22 | 2.383005 | 0.933032 | 0.905663 | 2.397395 | 4.149719 |
| 5 | 25 | 2.943410 | 1.156197 | 1.218604 | 2.789382 | 5.399375 |
| 6 | 24 | 2.588843 | 1.214804 | 0.723161 | 2.354993 | 5.826026 |
| 7 | 24 | 2.191642 | 1.348506 | 0.408062 | 2.011524 | 6.235241 |

## Design-time (dose.json, 235 events) beside realized arm T

| statistic | dose.json median | dose.json min | arm T median | arm T min |
|---|---|---|---|---|
| SD of the 6 | 0.039240 | 0.009070 | 0.031402 | 0.005435 |
| range (max minus min) | 0.100014 | 0.019604 | 0.082401 | 0.014582 |
| top3 minus bottom3 mean | 0.058594 | 0.013339 | 0.046508 | 0.006804 |
| SD / within-run SD | 1.553828 | 0.351328 | 1.219407 | 0.222458 |
| range / within-run SD | 4.028318 | 0.845162 | 3.240576 | 0.596823 |
| (top3 minus bottom3) / within-run SD | 2.282464 | 0.533328 | 1.819848 | 0.311130 |
| selected_min minus E[random-3 min] | 0.032786 | 0.003574 | 0.026193 | 0.002228 |
| that gap / within-run SD | 1.317044 | 0.154064 | 1.047497 | 0.101855 |

## Provenance

| field | value |
|---|---|
| dose.json sha256 | `9f39646103a63d7d243f6c6e5c6a6a82035ad8e0d3ede8b95369b4c975b17768` |
| dose.json events | 235 |
| live arm-T events used | 179 |
| live arm-C events used | 200 |
| normalizer | SD_PER_SEED, dose_compute.py:74-77 |

Every statistic above computed twice (numpy vs pure Python) and asserted to 1e-12.

