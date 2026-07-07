# HoVer batch-swap feasibility inventory (read-only, offline, $0)

Scope: which ingredients of the batch-swap v2 design (`scripts/batch_swap_v2_run.py`,
`scripts/batch_swap_v2_analysis.py`) exist in the frozen HoVer logs, which are absent/unportable,
and what one child evaluation would require. Facts, counts, and paths only. Computed offline via
`scripts/hover_swap_inventory_probe.py` (local JSON only, `HF_DATASETS_OFFLINE=1`, no LM, program
never executed) plus static reads of the HoVer program/metric source. Frozen corpora unmodified.

## Task 1 — HoVer corpus inventory

### 1a. Locate and enumerate

All HoVer material lives under `scratch/hover_probe/`. One real multi-event frozen GEPA run
(`necrosis/`, 33 events); a dry run (`necrosis_dry/`, trace-misaligned); a message-only GATE-1
capture (`capture/`); plus supporting corpora and the retrieval index.

| Path | Format | Size (B) | Date | Contents |
|---|---|---|---|---|
| `scratch/hover_probe/necrosis/gepa_result.json` | json | 72,916 | 2026-07-01 | GEPA state dump: `full_program_trace` (33), `program_candidates` (11 × `{gen_query.predict, append_notes.predict}`), `prog_candidate_val_subscores` (11×10), `parent_program_for_candidate`, `num_metric_calls_by_discovery`, `n_val=10`, `trainset_claims` (12) |
| `scratch/hover_probe/necrosis/reflections.json` | json list | 695,629 | 2026-07-01 | 33 × `{idx, prompt, output}` — reflection-LM input (SI+examples) and proposed child instruction |
| `scratch/hover_probe/necrosis/reflect_in_1..33.txt` | text | 6,892–32,468 ea. | 2026-07-01 | 33 verbatim reflection-LM inputs (Inputs / Generated Outputs / Feedback sections) |
| `scratch/hover_probe/necrosis/reflect_out_1..33.txt` | text | ~2.5–6 KB ea. | 2026-07-01 | 33 verbatim proposer outputs (child instructions) |
| `scratch/hover_probe/necrosis/retrieval_log.jsonl` | jsonl | 903,645 | 2026-07-01 | 407 BM25 traces `{claim, gold, retrieved, recall, n_retrieved, overlap, per_hop}` — scalar recall only, no per-doc binary |
| `scratch/hover_probe/necrosis/run_summary.json` | json | 254 | 2026-07-01 | `reflection_events=33, trace_entries=33, candidates_incl_seed=11, accepts_inferred=10, task_calls=1848, reflection_calls=33, spend_usd=1.9602, mm=300` |
| `scratch/hover_probe/necrosis/gepa_log/gepa_state.bin` | binary (pickle) | 49,200 | 2026-07-01 | full pickled GEPA state |
| `scratch/hover_probe/necrosis_dry/gepa_result.json` | json | 817 | 2026-07-01 | dry run; `full_program_trace` has **1** entry (`run_summary.event_trace_aligned:false`, `reflection_calls=2`) |
| `scratch/hover_probe/necrosis_dry/reflections.json` | json list | 38,316 | 2026-07-01 | 2 reflection `{idx,prompt,output}` records |
| `scratch/hover_probe/capture/reflect_{1,2,3}.json` | json list | 7,474 / 24,101 / 10,757 | 2026-06-30 | GATE-1: `[{role:"user", content:...}]` — reflection prompt only; no ids/scores/trace |
| `scratch/hover_probe/capture/equality.json` | json | 169 | 2026-06-30 | `{reflection_calls:3, task_calls:144, byte_equal_A_B:true, spend_usd:0.142, max_metric_calls:24}` |
| `scratch/hover_probe/threehop.jsonl` | jsonl | 412,270 | 2026-06-30 | 1,865 HoVer 3-hop rows `{claim, titles}` (gold titles) |
| `scratch/hover_probe/eyeball_records.jsonl` | jsonl | 92,881 | 2026-06-30 | 40 records `{claim, gold, per_hop, all_retrieved, missed, recall, si}`; 22 with `recall<1.0` (the GEPA train/val source) |
| `scratch/hover_probe/records.jsonl` | jsonl | 22,734 | 2026-06-30 | 10-claim probe records `{claim, gold_titles, per_hop, all_retrieved, si}` |
| `scratch/hover_probe/bm25s_index/` (corpus.jsonl 1,675,708,846 + 4 more) | npy+json | ~2.7 GB | 2026-06-30 | local BM25 retrieval index (5.23M wiki abstracts) |
| `scratch/hover_probe/wiki.abstracts.2017.jsonl` | jsonl | 1,780,742,620 | 2021-12-07 | raw wiki-abstracts corpus (retrieval source) |
| `analysis/hover_scope.md` | md | 5,828 | 2026-06-30 | HoVer scope writeup |
| `analysis/hover_viability_summary.md` | md | 4,401 | 2026-06-30 | HoVer viability writeup |

Program/metric source (read statically for 1d, not executed): `scratch/hover_probe/probe.py`,
`scratch/hover_probe/necrosis_run.py`, `scratch/hover_probe/gepa_capture.py`.

**MISSING check.** Every HoVer artifact referenced in `analysis/PROJECT_STATE.md` (HoVer section)
resolves on disk. No MISSING artifacts.

### 1b. Reflection-event census

Presence matrix. Columns = HoVer run logs; entries = present / absent, per
`scripts/hover_swap_inventory_probe.py` over the respective `gepa_result.json` / `reflections.json`.

| Field | necrosis (n=33) | necrosis_dry | capture/GATE-1 | Source key / path |
|---|---|---|---|---|
| Parent program text (all modules) | present | present | absent | `gepa_result.program_candidates[selected_program_candidate]` (both `gen_query.predict`+`append_notes.predict`); also `reflect_in_N.txt` |
| Minibatch example ids | present | present | absent | `full_program_trace[i].subsample_ids` |
| Minibatch example CONTENT (inputs) | present | present | present | embedded in `reflections.json[i].prompt` / `reflect_in_N.txt` (Inputs); resolvable via `trainset_claims`+ids |
| Generated outputs | present | present | present | embedded in reflection prompt (Generated Outputs) |
| SI / reflective-dataset / Feedback strings | present | present | present | `reflections.json[i].prompt` / `reflect_in_N.txt` (Feedback); `capture/reflect_N.json` content |
| Per-example PARENT scores on minibatch | present | present | absent | `full_program_trace[i].subsample_scores` |
| Per-example CHILD scores post-mutation | present | present | absent | `full_program_trace[i].new_subsample_scores` (b=3 minibatch only, not a full eval) |
| Child program text | present | present | absent | `reflections.json[i].output` / `reflect_out_N.txt` |
| Accept decision | absent (inferred) | absent (inferred) | absent | no accept key in `full_program_trace`; `run_summary.accepts_inferred=10` derived from new vs old scores |
| Valset scores | per-candidate only | per-candidate only | absent | `gepa_result.prog_candidate_val_subscores` (11×10); not per-event |

- Minibatch size **b = 3, constant** in necrosis (`set(len(subsample_ids)) == {3}`, verified) and in the
  one dry-run trace entry. `capture/` does not log minibatch structure (`max_metric_calls=24`, `task_calls=144`).
- necrosis event structure is exactly `{i, selected_program_candidate, subsample_ids, subsample_scores,
  new_subsample_scores}` (`full_program_trace`).
- necrosis_dry n_events counts the **1** logged trace entry; its `run_summary.json` reports
  `reflection_calls=2, event_trace_aligned:false`.
- capture/GATE-1 = 3 reflection captures, message-only (`equality.json`).

### 1c. Pairability

v2 pairing criteria, read from `scripts/batch_swap_v2_run.py`: same run/seed (`X[0]==s`, :164),
same tercile (`terc[X]==terc[B]`; terciles per-run over iteration index, :111-114), disjoint
minibatches (`not(set(batches[X]) & bset)`, :164-165), parent text available for both (`allb`, :115),
and failure-match — under parent P_B, ≥2 of the 3 examples score `<1.0` (:170). `type_jaccard` (:180)
is a **recorded covariate, not a pairing filter**.

Unportable / caveated criteria:
- **type_jaccard covariate** — depends on constraint-type composition; HoVer has no constraint types
  in the logs, so the v2 overlap-decomposition covariate has no HoVer analogue (it is not a pairing
  filter, so it does not change pair counts).
- **v2 failure-match** re-evaluates parent P_B on B′'s batch (a live cross-eval), which is not
  available offline. The offline count below uses each batch's OWN logged `subsample_scores` as the
  failure proxy, labeled as such.

Counts (`scratch/hover_probe/necrosis/gepa_result.json`, via `scripts/hover_swap_inventory_probe.py`):

| Criterion set | eligible unordered pairs | events with ≥1 partner | runs |
|---|---|---|---|
| Portable v2 (same run + same tercile + disjoint minibatches + parent available + own-batch failure-proxy ≥2/3 `<1.0`) | **82** | 32 / 33 | 1 |
| Weakest sane (same run + distinct minibatches + parent available) | **239** | 33 / 33 | 1 |

- HoVer necrosis is a **single run**; tercile sizes 11 / 11 / 11 over the 33 events.
- necrosis_dry yields **0** pairs under both criterion sets (1 trace entry).

### 1d. Evaluation-path requirements (static analysis only — program not executed)

Read from `scratch/hover_probe/necrosis_run.py` (`build_program`, `metric`, config) and
`scratch/hover_probe/probe.py` (`search`, `title_of`, `build_si`):

- **One child eval on one example** — DSPy `HoverMultiHop.forward` (`necrosis_run.py:62-73`) loops
  `probe.NUM_HOPS = 3` hops, each hop = 1 `gen_query` `ChainOfThought` call + 1 `append_notes`
  `ChainOfThought` call ⇒ **6 task LM calls per example**. Corroborated by the frozen run:
  `task_calls=1848` ÷ 6 = 308 example-evaluations (`necrosis/run_summary.json`).
- **Model** — `openai/gpt-4.1-mini` for both task and reflection LMs (`necrosis_run.py:24`,
  `MODEL`; `dspy.LM(MODEL, max_tokens=3000, cache=False)` :92, reflection LM :113).
- **Retrieval** — `probe.search` (`probe.py:30-42`) uses `bm25s` over a **local** index loaded via
  `bm25s.BM25.load("bm25s_index", load_corpus=True)` (`probe.py:24`). **Available offline: yes** —
  `scratch/hover_probe/bm25s_index/` (~2.7 GB, present) + `wiki.abstracts.2017.jsonl` (present). No
  remote retrieval API at eval time.
- **Dataset splits on disk** — trainset/valset are built from `eyeball_records.jsonl`
  (`recall<1.0`, cycled to `N_TRAIN=12` + `N_VAL=10`; `necrosis_run.py:131-137`); raw claims in
  `threehop.jsonl`. Both present (`scratch/hover_probe/`).
- **Minibatch id resolution** — `subsample_ids` index into `trainset_claims` (12).
  Spot-check of the 12 unique ids used (range 0–11): **12/12 resolve (100%)**
  (`scripts/hover_swap_inventory_probe.py`, `1d_id_resolve_necrosis`).
- **Metric determinism** — `metric` (`necrosis_run.py:118-128`) = `len(gold∩got)/len(gold)` title
  recall; feedback = `probe.build_si` (pure set logic, `probe.py:49-55`). **Deterministic given a
  child output; no LM judge.** (The child output itself comes from the 6 stochastic LM calls above.)
- **Timing / cost metadata** — logged per run: `spend_usd=1.9602`, `task_calls=1848`,
  `reflection_calls=33` (`necrosis/run_summary.json`); `capture/equality.json` `spend_usd=0.142`.
  **Per-example / per-eval latency: absent** (not logged; not estimated).

### 1e. Score statistics (computed offline)

Per-example scores exist for both parent and child in HoVer necrosis, so all requested statistics are
computable (contrast: IFBench batch-swap v2 discarded draw-level per-example child scores). Source:
`scratch/hover_probe/necrosis/gepa_result.json` `full_program_trace`, via
`scripts/hover_swap_inventory_probe.py`. necrosis is the single powered run, so per-run = pooled.

necrosis (n=33 events, b=3 ⇒ 99 per-example values, 33 batch margins):

| Statistic | n | mean | sd | min | max | frac at floor 0.0 | frac at ceil 1.0 |
|---|---|---|---|---|---|---|---|
| Parent per-example score | 99 | 0.6532 | 0.1703 | 0.0 | 1.0 | 0.0202 | 0.0909 |
| Child per-example score | 99 | 0.6532 | 0.1566 | 0.3333 | 1.0 | 0.0 | 0.0909 |
| Child − parent per-example delta | 99 | 0.0000 | 0.1641 | −0.3333 | 0.3333 | 0.7576 (= exactly 0) | — |
| Per-batch sum margin (Σchild − Σparent) | 33 | 0.0000 | 0.2722 | −0.6667 | 0.3333 | 0.3939 (= exactly 0) | — |

(For the delta/margin rows, "frac at floor 0.0" is the fraction of exactly-zero values.)

necrosis_dry (1 trace entry, 3 per-example values): parent mean 0.5556 (sd 0.1571, min 0.3333, max
0.6667); child identical; all 3 deltas 0.0; batch margin 0.0.

### 1f. BLOCKERS

- HoVer has a single frozen run with a trace (`scratch/hover_probe/necrosis/`, 33 events) — run-clustered inference across runs is unavailable from frozen logs.
- Accept decision is not logged; it is inferred (`scratch/hover_probe/necrosis/run_summary.json` `accepts_inferred=10`).
- Valset scores are per-candidate, not per-event (`scratch/hover_probe/necrosis/gepa_result.json` `prog_candidate_val_subscores`, 11×10).
- The v2 failure-match on B′ requires a live cross-eval of parent P_B on B′'s batch, absent from the frozen logs (`scripts/batch_swap_v2_run.py:166-170`).
- The v2 `type_jaccard` covariate has no HoVer analogue in the logs — HoVer events carry no constraint types (`scratch/hover_probe/necrosis/gepa_result.json` events have no type fields).
- Per-doc retrieval binary is absent; the retrieval log stores scalar recall only (`scratch/hover_probe/necrosis/retrieval_log.jsonl`).
- Re-evaluating one HoVer child requires 6 live `gpt-4.1-mini` calls per example (`scratch/hover_probe/necrosis_run.py:62-73,24`).
- The GATE-1 capture has no trace, ids, or scores — reflection prompts only (`scratch/hover_probe/capture/reflect_{1,2,3}.json`).
- necrosis_dry is trace-misaligned: 1 trace entry vs 2 reflection calls (`scratch/hover_probe/necrosis_dry/run_summary.json` `event_trace_aligned:false`).

## Task 2 / Task 3 — change log

| File | Action | Additions |
|---|---|---|
| `analysis/findings_summary.md` | edited (additions only) | 3 new `**Bold.**` evidence entries in `## What's live` (batch-swap v2 verified headline; lottery correction 0.415/deprecate 0.382/note 0.32; gate-instability P(flip)); 3 new rows appended inside the trailing traceability-map HTML comment. No existing line altered. |
| `docs/cc-brief-template-rules.md` | created (new `docs/`) | CALIBRATION RULE + PERSISTENCE RULE (no template file previously existed). |
| `analysis/ablation/batch_swap_v2/plan.md` | edited (append only) | new `## 0.6 Post-run reconciliation` section (projected ~$29 / ~8h vs actual $38.74 / ~14h, point-sample calibration). Original `## 0.3` / `## 0.5` projection lines unchanged. |

## Provenance

- **Scripts written:** `scripts/hover_swap_inventory_probe.py` — offline read-only probe; computes
  the 1b census, 1c pair counts, 1d id-resolve rate, and 1e score statistics from local JSON. It
  never imports the DSPy program, never calls an LM, and never contacts HuggingFace; run with
  `HF_DATASETS_OFFLINE=1`.
- **Inputs read:** `scratch/hover_probe/necrosis/{gepa_result.json, run_summary.json, reflections.json,
  retrieval_log.jsonl, reflect_in_*.txt, reflect_out_*.txt, gepa_log/gepa_state.bin}`;
  `scratch/hover_probe/necrosis_dry/{gepa_result.json, run_summary.json, reflections.json}`;
  `scratch/hover_probe/capture/{reflect_*.json, equality.json}`;
  `scratch/hover_probe/{threehop.jsonl, eyeball_records.jsonl, records.jsonl, probe.py,
  necrosis_run.py, gepa_capture.py}`; `scratch/hover_probe/bm25s_index/` (listing only);
  `analysis/{PROJECT_STATE.md, hover_scope.md, hover_viability_summary.md, findings_summary.md,
  verification_postswap.md}`; `scripts/{batch_swap_v2_run.py, batch_swap_v2_analysis.py}`;
  `analysis/ablation/batch_swap_v2/plan.md`; `notes/runs/2026-07-05-batch-swap-v2.md`.
- **No network calls were made.** The probe reads local JSON only under `HF_DATASETS_OFFLINE=1`; the
  HoVer program and metric were read statically and never executed.
- **No frozen file was modified.** New files created: `analysis/hover_swap_inventory.md`,
  `scripts/hover_swap_inventory_probe.py`, `docs/cc-brief-template-rules.md`. Existing files appended
  to (additions only): `analysis/findings_summary.md`, `analysis/ablation/batch_swap_v2/plan.md`. No
  file under `scratch/hover_probe/`, no batch-swap v2 output, and no IFBench log was written.
