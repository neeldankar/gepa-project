# Stage-1 HoVer baselines — manifest (raw facts, no interpretation)

- Repo: gepa-si-curriculum | model gpt-4.1-mini | BM25 (NUM_DOCS=10, NUM_HOPS=3) | title-recall metric | max_metric_calls=300 | N_TRAIN=100 N_VAL=10 | config otherwise identical to scratch/hover_probe/necrosis/
- Seeds: 0–7 (8 total). Seed 0 = Phase-1 smoke; seeds 1–7 = Phase-2 batch (supervisor run_seeds.sh, max 3 concurrent).
- Trainset source: scratch/hover_probe/threehop.jsonl, graded slice [50:450] → 245 graded, 123 imperfect (recall<1.0); 100 train + 10 val drawn imperfect-only, no cycling.
- Grading (one-time): $1.0942, 16.1 min. Records: scratch/hover_stage1/graded_records.jsonl ; ids: graded_summary.json['imperfect_ids'].
- Exact trainset/valset threehop ids per seed: stage1_seed<N>/trainset_manifest.json (identical across seeds; only GEPA seed differs).

## Per-seed facts

| seed | events | trace | cand(incl seed) | accepts | event_trace_aligned | cost USD | duration s | reflect_out files |
|---|---|---|---|---|---|---|---|---|
| 0 | 32 | 32 | 11 | 10 | True | 1.9078 | 7975 | 32 |
| 1 | 34 | 34 | 11 | 10 | True | 2.1705 | 9436 | 34 |
| 2 (recovered) | 28 | 30 | 13 | 12 | False | ~1.9606 (est) | ~8758 (est) | 28 |
| 3 | 33 | 33 | 11 | 10 | True | 1.9308 | 8529 | 33 |
| 4 | 27 | 27 | 14 | 13 | True | 2.1410 | 9029 | 27 |
| 5 | 34 | 34 | 10 | 9 | True | 2.0329 | 9023 | 34 |
| 6 (recovered) | 28 | 29 | 13 | 12 | False | ~1.9455 (est) | ~9006 (est) | 28 |
| 7 | 27 | 27 | 14 | 13 | True | 1.9024 | 9393 | 27 |

- Totals: 243 reflection events across 8 seeds; spend (incl. 2 estimated) $15.9915 for seeds + $1.0942 grading = $17.0857 Stage-1.

## File paths (per seed, N=0..7 under scratch/hover_stage1/)

- Per-example score vectors — `stage1_seed<N>/gepa_result.json`:
  - `prog_candidate_val_subscores`: list[per-candidate] of per-val-instance scores (len N_VAL=10 each; candidates incl. seed).
  - `full_program_trace`: per-iteration `subsample_scores` (parent) + `new_subsample_scores` (child) minibatch vectors (len 3 each); `subsample_ids` index into `trainset_threehop_ids`.
  - also `parent_program_for_candidate`, `num_metric_calls_by_discovery`, `program_candidates`, `trainset_threehop_ids`, `valset_threehop_ids`.
- Child text — `stage1_seed<N>/reflect_out_*.txt` (one file per reflection event) and `stage1_seed<N>/reflections.json` (idx/prompt/output list).
- Reflection inputs — `stage1_seed<N>/reflect_in_*.txt`. Per-eval retrieval — `stage1_seed<N>/retrieval_log.jsonl`. GEPA state — `stage1_seed<N>/gepa_log/gepa_state.bin`. Summary — `stage1_seed<N>/run_summary.json`.

## Data provenance / caveats (raw facts)

- Seeds 2 and 6: original `run_summary.json` was never written — the end-of-run summary block raised `KeyError('new_subsample_scores')` on trace entries with no child scores (seed2 entries [5,15]; seed6 entry [27]). The GEPA compile itself completed and all raw dumps (`gepa_result.json`, `reflect_*`, `reflections.json`, `retrieval_log.jsonl`, `gepa_log/`) were written before the crash. `run_summary.json` for these two was re-derived read-only (see each file's `recovered_note`).
- For seeds 2 & 6, `task_calls`, `spend_usd`, `wall_clock_s` were in process memory and are not exactly recoverable: `spend_est_usd` = mean clean-seed spend/metric-eval × logged evals; `wall_clock_est_s` = gepa_result.json − trainset_manifest.json mtime. Both flagged in-file.
- `stage1_run.py` patched so the summary block tolerates child-less trace entries (no re-run performed).
