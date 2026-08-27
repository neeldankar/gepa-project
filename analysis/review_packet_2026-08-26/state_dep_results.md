# state-dependent novelty selection — results

Numbers only. No interpretation, no verdicts, no grid-cell assignment. Read against v2 §9.
Emitted by `emit_results.py` from 24 run directories.

Endpoint = §8b selection-split argmax, evaluated on the 150-claim test split.
Paired by seed. `p` is the exact two-sided sign-flip over all 2^8 = 256 patterns.
CIs are a paired bootstrap, 10,000 resamples, seed 20260709, over the same
resample indices: percentile and BCa, both reported per v2 §10 M2.
MDE (v2 §11-2, endpoint units): 0.06332

**SAP deviation, corrected 2026-08-24.** v2 §10 M2 requires the percentile bootstrap CI
*alongside* BCa. The first emission of this file (2026-08-12) carried percentile only. BCa
has been added; no previously emitted number was removed or altered, and re-running the
unchanged code paths reproduces every one of them. M2's reason for wanting both stands:
BCa's acceleration constant comes from a jackknife over 8 points and is unstable at this n.

---

## Anomaly overlay — C − B

| seed | C | B | C − B |
|---|---|---|---|
| 0 | 0.628889 | 0.633333 | -0.004444 |
| 1 | 0.593333 | 0.617778 | -0.024444 |
| 2 | 0.591111 | 0.564444 | +0.026667 |
| 3 | 0.566667 | 0.602222 | -0.035556 |
| 4 | 0.557778 | 0.568889 | -0.011111 |
| 5 | 0.584444 | 0.591111 | -0.006667 |
| 6 | 0.608889 | 0.640000 | -0.031111 |
| 7 | 0.568889 | 0.575556 | -0.006667 |

| quantity | value |
|---|---|
| paired mean | -0.011667 |
| MDE (§11-2) | 0.06332 |
| p (exact two-sided sign-flip) | 0.132812 |
| bootstrap 95% CI (percentile) | [-0.023611, +0.001667] |
| bootstrap 95% CI (BCa) | [-0.022500, +0.003056] |

## Contrast — T − C

| seed | T | C | T − C |
|---|---|---|---|
| 0 | 0.571111 | 0.628889 | -0.057778 |
| 1 | 0.568889 | 0.593333 | -0.024444 |
| 2 | 0.575556 | 0.591111 | -0.015556 |
| 3 | 0.568889 | 0.566667 | +0.002222 |
| 4 | 0.657778 | 0.557778 | +0.100000 |
| 5 | 0.573333 | 0.584444 | -0.011111 |
| 6 | 0.604444 | 0.608889 | -0.004444 |
| 7 | 0.571111 | 0.568889 | +0.002222 |

| quantity | value |
|---|---|
| paired mean | -0.001111 |
| MDE (§11-2) | 0.06332 |
| p (exact two-sided sign-flip) | 0.968750 |
| bootstrap 95% CI (percentile) | [-0.025833, +0.031667] |
| bootstrap 95% CI (BCa) | [-0.022500, +0.039722] |

## Contrast — T − B

| seed | T | B | T − B |
|---|---|---|---|
| 0 | 0.571111 | 0.633333 | -0.062222 |
| 1 | 0.568889 | 0.617778 | -0.048889 |
| 2 | 0.575556 | 0.564444 | +0.011111 |
| 3 | 0.568889 | 0.602222 | -0.033333 |
| 4 | 0.657778 | 0.568889 | +0.088889 |
| 5 | 0.573333 | 0.591111 | -0.017778 |
| 6 | 0.604444 | 0.640000 | -0.035556 |
| 7 | 0.571111 | 0.575556 | -0.004444 |

| quantity | value |
|---|---|
| paired mean | -0.012778 |
| MDE (§11-2) | 0.06332 |
| p (exact two-sided sign-flip) | 0.484375 |
| bootstrap 95% CI (percentile) | [-0.039444, +0.021118] |
| bootstrap 95% CI (BCa) | [-0.035556, +0.029444] |

---

## Per-run endpoint scores

### Arm B

| seed | run | endpoint_test_mean | n_candidates | sel_best_idx |
|---|---|---|---|---|
| 0 | `B_seed0` | 0.633333 | 11 | 7 |
| 1 | `B_seed1` | 0.617778 | 11 | 2 |
| 2 | `B_seed2` | 0.564444 | 9 | 0 |
| 3 | `B_seed3` | 0.602222 | 11 | 1 |
| 4 | `B_seed4` | 0.568889 | 14 | 7 |
| 5 | `B_seed5` | 0.591111 | 9 | 2 |
| 6 | `B_seed6` | 0.640000 | 13 | 3 |
| 7 | `B_seed7` | 0.575556 | 14 | 11 |

### Arm C

| seed | run | endpoint_test_mean | n_candidates | sel_best_idx |
|---|---|---|---|---|
| 0 | `C_seed0` | 0.628889 | 7 | 5 |
| 1 | `C_seed1` | 0.593333 | 4 | 0 |
| 2 | `C_seed2` | 0.591111 | 7 | 6 |
| 3 | `C_seed3` | 0.566667 | 9 | 6 |
| 4 | `C_seed4` | 0.557778 | 10 | 2 |
| 5 | `C_seed5` | 0.584444 | 7 | 2 |
| 6 | `C_seed6` | 0.608889 | 8 | 4 |
| 7 | `C_seed7` | 0.568889 | 8 | 0 |

### Arm T

| seed | run | endpoint_test_mean | n_candidates | sel_best_idx |
|---|---|---|---|---|
| 0 | `T_seed0` | 0.571111 | 10 | 3 |
| 1 | `T_seed1` | 0.568889 | 11 | 5 |
| 2 | `T_seed2` | 0.575556 | 10 | 0 |
| 3 | `T_seed3` | 0.568889 | 7 | 5 |
| 4 | `T_seed4` | 0.657778 | 10 | 6 |
| 5 | `T_seed5` | 0.573333 | 9 | 0 |
| 6 | `T_seed6` | 0.604444 | 10 | 9 |
| 7 | `T_seed7` | 0.571111 | 12 | 11 |

## Per-arm mean and SD

| arm | n | mean | SD (ddof=1) |
|---|---|---|---|
| B | 8 | 0.599167 | 0.029118 |
| C | 8 | 0.587500 | 0.023576 |
| T | 8 | 0.586389 | 0.031144 |

---

## Provenance

| field | value |
|---|---|
| run directories read | 24 (24 non-smoke; smoke excluded) |
| selection split | n=50 sha256 `b53216962a3efc46799a4871b379330eb3d460c4c9d5598b5e7cbabb03270fcc` |
| test split | n=150 sha256 `a463c94af0aa65ad5187395c74d6a5060c3a8f7a723ceba3017752f08b7a2430` |
| gepa version | 0.0.27 |
| dspy version | 3.2.1 |
| task LM | {'model': 'openai/gpt-4.1-mini', 'max_tokens': 3000, 'cache': False, 'temperature': 'dspy default (0.0)'} |
| max_metric_calls | 300 |
| git commit (run config) | d963929f3bc43a1754a87a83d78ab895f5bf890c |
| design | state-dependent-design-v2.1.1-frozen |
| mde_sim.py sha256 | `6d11de278014b7e7de41cf55cb56cad4f92680f5b5f6159e7c6583bf84bce5cc` |
| emit_results.py sha256 | `c60cd689821cd8cd0d0c0087f50f4b8107fa2e6d27572c359f35c1aae9c62b8e` |

### endpoints.json mtimes

| run | mtime | path |
|---|---|---|
| `B_seed0` | 2026-08-10T18:30:07 | `runs/B_seed0/endpoints.json` |
| `B_seed1` | 2026-08-11T01:43:06 | `runs/B_seed1/endpoints.json` |
| `B_seed2` | 2026-08-06T06:07:36 | `runs/B_seed2/endpoints.json` |
| `B_seed3` | 2026-08-10T19:00:43 | `runs/B_seed3/endpoints.json` |
| `B_seed4` | 2026-08-11T01:14:51 | `runs/B_seed4/endpoints.json` |
| `B_seed5` | 2026-08-06T08:43:23 | `runs/B_seed5/endpoints.json` |
| `B_seed6` | 2026-08-10T18:32:05 | `runs/B_seed6/endpoints.json` |
| `B_seed7` | 2026-08-11T02:48:30 | `runs/B_seed7/endpoints.json` |
| `C_seed0` | 2026-08-06T07:13:54 | `runs/C_seed0/endpoints.json` |
| `C_seed1` | 2026-08-06T04:47:09 | `runs/C_seed1/endpoints.json` |
| `C_seed2` | 2026-08-11T00:51:25 | `runs/C_seed2/endpoints.json` |
| `C_seed3` | 2026-08-10T19:00:44 | `runs/C_seed3/endpoints.json` |
| `C_seed4` | 2026-08-10T18:22:22 | `runs/C_seed4/endpoints.json` |
| `C_seed5` | 2026-08-11T01:54:08 | `runs/C_seed5/endpoints.json` |
| `C_seed6` | 2026-08-06T07:25:01 | `runs/C_seed6/endpoints.json` |
| `C_seed7` | 2026-08-06T04:53:30 | `runs/C_seed7/endpoints.json` |
| `T_seed0` | 2026-08-11T01:15:15 | `runs/T_seed0/endpoints.json` |
| `T_seed1` | 2026-08-11T00:26:16 | `runs/T_seed1/endpoints.json` |
| `T_seed2` | 2026-08-10T18:27:20 | `runs/T_seed2/endpoints.json` |
| `T_seed3` | 2026-08-11T01:54:04 | `runs/T_seed3/endpoints.json` |
| `T_seed4` | 2026-08-06T08:38:35 | `runs/T_seed4/endpoints.json` |
| `T_seed5` | 2026-08-06T05:57:53 | `runs/T_seed5/endpoints.json` |
| `T_seed6` | 2026-08-11T01:17:05 | `runs/T_seed6/endpoints.json` |
| `T_seed7` | 2026-08-11T00:27:22 | `runs/T_seed7/endpoints.json` |

### verification performed before emission

- 24 endpoint files, 8 per arm, seeds [0, 1, 2, 3, 4, 5, 6, 7] present in B, C, T
- endpoint_test_mean == mean(endpoint_test_scores) for all 24, |delta| <= 1e-12
- split sha256 identical across all 24 run dirs
- C-B: mean/p/CI agree across stored-scalar and vector-recomputed paths, and across two implementations each (<=1e-12)
- T-C: mean/p/CI agree across stored-scalar and vector-recomputed paths, and across two implementations each (<=1e-12)
- T-B: mean/p/CI agree across stored-scalar and vector-recomputed paths, and across two implementations each (<=1e-12)

