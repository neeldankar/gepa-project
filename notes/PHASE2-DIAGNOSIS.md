# Phase 2 (§8b scoring) memory blowup — diagnosis

**Date:** 2026-08-10 · **Status:** diagnosis only. No spend, no restarts, no gate files created.
No code changed. §3 is a recommendation awaiting a decision.

Phase 1 (24 GEPA optimization runs, $46.69) completed clean. Phase 2 (`supervisor.py --score`)
has destabilised the machine repeatedly: SIGKILLed scorers, a kernel panic, and a 54.37 GB
"out of application memory" attribution to Terminal.app.

---

## 0. Contradictions with the brief (stated first, not reconciled silently)

**0.1 — It is 8 SIGKILLs, not 7, and two more runs died with no marker at all.**
`analysis/state_dep/markers/` holds 8 `.FAILED` files, each containing exactly `rc=-9 rate_hit=False`:
`score_B_seed6` (08-06 01:56), `score_B_seed0` (02:42), `score_C_seed4` (03:02), `score_B_seed3` (03:25),
`score_T_seed2` (03:47), `score_T_seed1` (10:40), `score_T_seed7` (10:53), `score_B_seed4` (10:56).
Separately, **C_seed3** (`supervisor.log:89`) and **C_seed2** (`supervisor.log:101`) were launched for
scoring and never got a terminal marker — the supervisor itself died before writing one.

**0.2 — The kills do not cluster "in time not by arm". They cluster by candidate count.**

| outcome | candidate counts |
|---|---|
| scored OK (8) | 4, 7, 8, 8, 9, 9, 9, 10 |
| `rc=-9` (8) | 10, 10, 11, 11, 11, 12, 13, 14 |

Every run with **≥11 candidates was killed**; 10 is the boundary. Arm is incidental — this is a
memory threshold, and candidate count is what walks the process across it.

**0.3 — Growth is NOT "over a run dir's ~8-12 candidate50 evals". It is entirely in candidate 0.**
This is the single most important correction. From the surviving artifacts,
`runs/*/selection_scores.json` `elapsed_s`, per candidate in order:

```
B_seed2  [1910.2, 201.5, 192.8, 179.4, 232.8, 191.2, 186.4, 198.3, 216.7]
C_seed1  [3857.6, 183.7, 171.3, 209.7]
T_seed4  [1875.0, 257.3, 294.5, 227.8, 252.4, 262.7, 243.6, 294.6, 274.1, 263.0]
C_seed7  [2094.5, 196.2, 173.4, 174.8, 178.1, 229.1, 194.3, 218.7]
```

Candidate 0 costs **1778–3858 s**. Every subsequent candidate costs **170–330 s**. A 7–20× penalty
that lands once, on the first candidate, and never again. The memory event is a startup event.

**0.4 — The panic is a watchdog timeout, not a pageout panic.** The literal `panicString` in
`panic-full-2026-08-06-110006.0002.panic` is:

> `panic(cpu 7 caller 0xfffffe003d21512c): watchdog timeout: no checkins from watchdogd in 94 seconds`

`VM_compressor` is present but in `TH_WAIT`/`TH_UNINT`, and `memoryStatus` at panic reads
`free: 906` pages (**14 MB free**) and `fileBacked: 1595` pages (**26 MB** — the entire file cache had
been evicted). So the *cause* is VM collapse, as the brief says; the *panic type* is a watchdog
timeout caused by it. Also, at panic `mds` had 94,019,923 page faults but `mds_stores` had
**163,239,904**.

**0.5 — Everything else in the brief checks out.** 60 MB at spawn: consistent. 54.37 GB attributed
to Terminal.app: that is the sum of the two `python3.12` children (measured 29.39 + 28.03 GB at
01:30:40, 27.12 + 25.76 GB at 01:12:44). Not Cursor. Confirmed inside our own process tree.

---

## 1. State of the world (from disk)

### 1a. Artifact counts
- `runs/` holds **25 directories**: 24 live + 1 smoke (`smoke_T_seed0`).
- **25/25 have `gepa_result.json`** (all 24 live + smoke).
- **9 have `endpoints.json`** → **8 live + 1 smoke**. `selection_scores.json` exists in exactly the
  same 9.
- Scored (8): `B_seed2 B_seed5 C_seed0 C_seed1 C_seed6 C_seed7 T_seed4 T_seed5`.
- Unscored (16): `B_seed0 B_seed1 B_seed3 B_seed4 B_seed6 B_seed7 C_seed2 C_seed3 C_seed4 C_seed5
  T_seed0 T_seed1 T_seed2 T_seed3 T_seed6 T_seed7`.

### 1b. Integrity of every scored run — all 9 clean, zero partials
All 9 parse as valid JSON, carry an identical 20-key schema, and end with the closing
`"test_evaluated": false } }` — none truncated. Per file:

| run | size | mtime | `len(selection_means)` vs `n_candidates` | test scores | winner | test mean |
|---|---|---|---|---|---|---|
| B_seed2 | 5242 | 08-06 06:07:36 | 9 == 9 | 150, 0 null | `sel_best_idx=0` | 0.564444 |
| B_seed5 | 5130 | 08-06 08:43:23 | 9 == 9 | 150, 0 null | 2 | 0.591111 |
| C_seed0 | 5133 | 08-06 07:13:54 | 7 == 7 | 150, 0 null | 5 | 0.628889 |
| C_seed1 | 5046 | 08-06 04:47:09 | 4 == 4 | 150, 0 null | 0 | 0.593333 |
| C_seed6 | 5079 | 08-06 07:25:01 | 8 == 8 | 150, 0 null | 4 | 0.608889 |
| C_seed7 | 5119 | 08-06 04:53:30 | 8 == 8 | 150, 0 null | 0 | 0.568889 |
| T_seed4 | 5072 | 08-06 08:38:35 | 10 == 10 | 150, 0 null | 6 | 0.657778 |
| T_seed5 | 5141 | 08-06 05:57:53 | 9 == 9 | 150, 0 null | 0 | 0.573333 |
| smoke_T_seed0 | 5031 | **07-29 02:23:40** | 8 == 8 | 150, 0 null | 3 | 0.651111 |

Checks that passed on all 9:
- `len(selection_means) == n_candidates == len(gepa_result.program_candidates)`.
- `endpoint_test_mean` **recomputed from `endpoint_test_scores` matches the stored value to the last
  digit** in every file.
- `selection_split.sha256 = b53216962a3e…0fcc` (n=50) and `test_split.sha256 = a463c94af0aa…2430`
  (n=150) are byte-identical across all 9 and match `splits_manifest.json`.
- `midpoint.test_evaluated == false` everywhere (midpoint was never test-evaluated — as intended per
  the last commit).
- `agrees_with_val_argmax` is True only for C_seed1; False for the other 7 live runs.

### 1c. Ledger — no double-charge
`liverun_ledger.json` (2631 B, mtime 08-06 08:47:55), flat array of `{phase, run, spend_usd}`:
- **32 entries, total $72.6367.**
- `optimization`: 24 entries, **$46.6905**. `score`: 8 entries, **$25.9462**.
- 24 distinct `run` values. **No `(phase, run)` pair repeats.** The 8 runs that appear twice appear
  once under each phase — by design.
- Per-entry score spends match each `endpoints.json:post_run_spend_usd` exactly.
- Cross-checks against `supervisor.log:60` (`optimization_cost=$46.6905`) and `:90`
  (`liverun_total=$72.64/150.0`).
- The smoke run is not in the ledger (its $5.1942 lives only in `markers/SMOKE.DONE`).

**Caveat, and it points the safe way:** the ledger is appended only on `rc=0`. B_seed0 and B_seed6
were launched for scoring **three times** (08-06 01:08, 08-06 10:56, 08-10 16:34) and died each time.
Any API spend from those aborted attempts is **unrecorded**. The ledger therefore *undercounts*, never
overcounts. Given the killed runs died before candidate 0 finished, the unrecorded amount is small
but not zero.

### 1d. Verdict — the completed work is trustworthy and resumable

**Trustworthy.** All 8 live scored runs (plus smoke) are complete and internally consistent; the
recomputed means match, the split hashes are pinned and identical, and no artifact is truncated.
**No scored run was interrupted mid-write.** The mechanism protects you here: `endpoints.json` is
written once at the end (`score_candidates.py:155`), so a killed process leaves *no* file rather than
a half one — which is exactly what the 8 `.FAILED` runs show. OOM kills a process; it does not
silently corrupt arithmetic derived from API responses.

**Resumable.** The unscored 16 are independent per-run-dir units. The two-split design means
resuming costs nothing but the 16 runs' own evaluation.

**One honest caveat about stopping here:** the scored 8 are *not* a random subset — they are the
low-candidate-count runs (§0.2), which is a selection effect correlated with how much GEPA explored.
That biases any analysis run on the partial set. It resolves completely once all 24 are scored; it
would be a real problem if you analysed the 8 as if they were representative.

---

## 2. What is actually growing

### 2a. Two defects, both live only on the `--score` path

**D1 — `probe.load_index()` is an unlocked check-then-set, and 8 threads race it.**

`scratch/hover_probe/probe.py:21-27`
```python
def load_index():
    global _retriever, _corpus
    if _retriever is None:
        r = bm25s.BM25.load("bm25s_index", load_corpus=True)
        _retriever = r
        _corpus = r.corpus
    return _retriever
```

No `threading.Lock`. The caller is 8-wide — `eval_split.py:42` (`WORKERS = 8`) and `:155-156`:
```python
with ThreadPoolExecutor(max_workers=workers) as ex:
    pairs = list(ex.map(one, split))
```
Every worker enters `forward()` (`eval_split.py:70-81`), whose first action is an LM call (`:73`) and
whose second is `probe.search` → `load_index()` (`:74`). All 8 threads return from `gen_query` within
milliseconds of each other and hit a still-`None` global while the load takes tens of seconds. Nothing
warms it first: `score_candidates.py:214-215` calls `bootstrap()` then `build_program()`, neither of
which retrieves. **All 8 loads complete; only the last assignment survives; all 8 are resident at
peak.**

**D2 — the mmap monkeypatch is not installed on this path.**

The patch exists and is documented at `analysis/ablation/hover_swap/hover_swap_run.py:26-46`:
```python
# Cuts peak footprint per pair process from 5.06 GB to 0.92 GB.
def _load_index_mmap():
    if probe._retriever is None:
        r = bm25s.BM25.load("bm25s_index", load_corpus=True, mmap=True)
        ...
probe.load_index = _load_index_mmap

def assert_mmap():
    """Fail loudly rather than silently loading a 5 GB private copy of the index."""
```
`hover_swap_run.py:156` calls `assert_mmap()` *before any spend* — which both enforces mmap **and**
warms the global single-threaded. That path is immune to D1 and D2 by construction.

`eval_split.bootstrap()` (`eval_split.py:47-57`) imports **raw `probe`** — no `hover_swap_run`, no
`screen_bm25`, no `assert_mmap`. `score_candidates.py` imports only `gates` (`:201`) and `eval_split`
(`:212`). So `mmap` defaults to `False` and `bm25s/__init__.py:1245-1250` takes the fully-resident
branch. **The scoring path is the one path in the repo that lost a protection every sibling path has.**

### 2b. Measured, at $0

**Measurement 1 — what a non-mmap index actually costs.** Parsed `corpus.jsonl` prefixes and
extrapolated to its 5,233,330 lines (linear and stable across 25k→400k docs):

```
  25,000 docs |  0.88 KB/doc | inflation 2.53x | PROJECTED FULL: 4.61 GB
 100,000 docs |  0.82 KB/doc | inflation 2.61x | PROJECTED FULL: 4.31 GB
 400,000 docs |  0.82 KB/doc | inflation 2.61x | PROJECTED FULL: 4.31 GB   (~14 s to parse in full)
```
Plus, measured directly: `vocab.index.json` → **0.687 GB** (2,549,172 tokens), `data.csc` +
`indices.csc` + `indptr` → **1.07 GB** resident when not mmapped.
**Total ≈ 6.07 GB per copy** — corroborating the repo's own 5.06 GB figure at
`hover_swap_run.py:29`.

**Measurement 2 — the race, demonstrated.** Substituted a bounded 100 MB stub for
`bm25s.BM25.load` and ran the real `probe.load_index` through a real 8-thread
`ThreadPoolExecutor` with a cold global:

```
threads that entered the loader body : 8 / 8
peak CONCURRENT constructions        : 8
peak RSS                             : 0.890 GB   (baseline 0.051 + 8x100MB = 0.833 expected)
```

**8 of 8.** Not a narrow race — a guaranteed one. Extrapolated to the real index:
**8 × 5.06 GB ≈ 40 GB per process**, × `SCORE_WIDTH = 2` ≈ 81 GB machine-wide peak demand.

**Measurement 3 — what the machine actually recorded.** 20 `JetsamEvent` reports from 08-06
01:09→01:30. Two `python3.12` processes, pids 98936 / 98961, coalition 806:

| time | pid 98936 | pid 98961 | sum |
|---|---|---|---|
| 01:09:33 | 26.13 GB | 24.77 GB | 50.9 GB |
| 01:12:44 | 27.12 GB | 25.76 GB | 52.9 GB |
| 01:27:31 | 29.28 GB | 27.92 GB | 57.2 GB |
| 01:30:40 | 29.39 GB | 28.03 GB | 57.4 GB |

**That sum is the 54.37 GB dialog.** Two decisive details:
- `physicalPages.internal = [13624, 1580531]` — only ~223 MB *truly* resident; **25.9 GB is in the VM
  compressor.** Allocated, then never touched again. That is the exact signature of a large structure
  built at startup and abandoned — not of a working set.
- Converting `age` from mach ticks (41.67 ns): pid 98936 was **72.6 seconds old** at 01:09:33, pid
  98961 **67.6 s**. The supervisor session started at 01:08:05 (`supervisor.log:62`), so they were
  spawned ~15 s later — the arithmetic closes. **They reached 26 GB within ~73 seconds of spawn.**

This kills the "accumulates over 8-12 candidate evals" hypothesis outright, and it agrees with §0.3's
`elapsed_s` evidence and with the truncated logs: every killed run's log stops at `[gate ok]`
(319–321 B), i.e. inside candidate 0's executor. `logs/score_T_seed2.log` carries the classic
kill-mid-flight tail: `resource_tracker: There appear to be 1 leaked semaphore objects`.

### Suspect-by-suspect (as asked)

| suspect | verdict | evidence |
|---|---|---|
| **BM25 index resident + per-thread** | **CONFIRMED — primary** | `probe.py:21-27` unlocked; mmap patch absent from `eval_split.py:47-57`; `bm25s/__init__.py:1245-1250`; 8/8 measured |
| dspy `lm.history` | **CONFIRMED but secondary (~150–250 MB)** | `settings.py:35` `max_history_size = 10000`; `base_lm.py:236-239` pops at the bound — but ~4,500 entries for 12 candidates never reaches 10k. `Meter.spend()` (`eval_split.py:121-127`) is O(n) per `tick()` (`:132`, once per example) → quadratic CPU, ~750 shallow copies of a 4,500-element list. Real, but not GB. |
| `capture_traces` / retained traces | **RULED OUT** | `eval_split.py:146-152` returns only `(int, float)`; `capture_traces` appears nowhere in `eval_split.py`/`score_candidates.py` — only on the optimization path (`proposer.py:176,182`) |
| ThreadPoolExecutor futures/results | **RULED OUT** | `eval_split.py:155-156`; results are ≤150 two-tuples of `(int, float)`; executor joins per candidate |
| reflections / per-example texts / deepcopies | **RULED OUT** | `apply_candidate` (`eval_split.py:86-92`) deepcopies into a `score_candidate` local; the `REFLECTIONS` list is `run_state_dep.py:160,167-170`, optimization-only; dspy's LRU is bypassed by `cache=False` (`eval_split.py:179`) |

Worth knowing but not a leak: `bm25s/__init__.py:654` allocates `np.zeros(5_233_330, float32)` =
**20.9 MB per query**, 8 in flight → ~168 MB of live churn.

### 2c. Are the 8 SIGKILLs and the panic fully explained? Yes.

- **The 8 kills.** 40 GB transient demand per process × 2 processes on 16 GB. Runs with ≤10 candidates
  survived because the compressor could hold the abandoned copies long enough to reach steady state;
  ≥11 could not. The threshold behaviour in §0.2 is exactly what a fixed-overhead-plus-increment model
  predicts.
- **Why jetsam killed the OS instead of us.** Across all 20 reports, the two `python3.12` processes are
  **never the victim**. Jetsam killed, in order: Chrome renderers, then `corespotlightd`, `suggestd`,
  `photolibraryd`, then the daemon layer wholesale — `chronod`, `homed`, `secd`, `callservicesd`,
  `UIKitSystem`, `bluetoothd`, `assistantd`, `com.apple.dock.extra`. Terminal's children sit in a high
  jetsam band, so the OS dismantled itself to keep them alive.
- **The panic.** With the daemon layer dead and 14 MB free, `watchdogd` could not check in for 94 s and
  the kernel panicked. At 11:00 there were **four** `python3.12` processes: 28.26 GB (15,274,820 page
  faults), 17.37 GB, 17.10 GB, 5.55 GB — **68.3 GB** demanded. `mds`/`mds_stores` at 94M/163M page
  faults were a *symptom* of the collapsed file cache, not the cause; excluding the repo from Spotlight
  was reasonable hygiene but was never going to fix this.

**Nothing remains unaccounted for.** The one loose end is bookkeeping, not memory: unrecorded spend
from the aborted attempts (§1c).

---

## 3. How to run the remaining 16 — ranked recommendation

Sizing, from `gepa_result.json` candidate counts: **167 candidates, 10,750 metric calls.**
The in-repo rate `M = $0.004543` **underestimates by ~30%** — fitting against the 8 actuals gives
**$0.005897/call** (per-run ratios 1.11–1.42).

| | at `M` | at fitted rate |
|---|---|---|
| remaining 16 | $48.84 | **$63.39** |
| running total after | $121.48 | **$136.03 / $150** |

⚠️ **Two budget warnings.** (i) Only **~$14 of headroom** against the $150 line at the fitted rate.
(ii) `score_candidates.py:48` sets `SPEND_CAP = 6.00` **per run dir**, and B_seed4/B_seed7 (14
candidates) project to **~$5.01** — a 20% margin before the tripwire raises `RuntimeError` and
discards that dir's work. B_seed6 (13 cands) is ~$4.72. Decide deliberately whether to raise that cap
for the three big dirs.

### Option 1 (RECOMMENDED) — fix both defects, run locally

**The fix, both parts required.** D2 alone → 0.92 × 8 = 7.4 GB peak, still fatal at width 2.
D1 alone → 5.06 × 2 = 10.1 GB, still fatal on 16 GB.

1. In `eval_split.bootstrap()` (`eval_split.py:47-57`), after `import probe`, rebind
   `probe.load_index` to the mmap variant and assert it took. **Reuse the existing code** — the
   `_load_index_mmap` + `assert_mmap` pair at `hover_swap_run.py:30-46` is already verified
   byte-identical over 135 live queries / 1350 docs (seed0_i0, 2026-07-08). Lift or import it rather
   than writing a third copy (there are already two: `hover_swap_run.py:30-50` and
   `screen_bm25.py:42-58`).
2. **Warm the global single-threaded** before any executor exists — call the equivalent of
   `assert_mmap()` right after `bootstrap()` at `score_candidates.py:214`. This closes D1 without
   touching frozen `probe.py`, and the assertion makes silent regression impossible. (A
   `threading.Lock` inside `load_index` is the alternative, but `probe.py` is deliberately frozen, so
   the warm-up belongs in `eval_split`.)
3. Optional, cheap: `dspy.settings.configure(disable_history=True)` and take spend from a litellm
   success callback — the pattern `run_state_dep.py:181-196` already uses. Removes ~200 MB and the
   quadratic `Meter.tick` cost. Note `lm.history.clear()` alone frees nothing: `base_lm.py:230`
   appends the *same dict objects* to `GLOBAL_HISTORY`.

**Memory profile after:** ~0.92 GB/process, and mmapped pages are file-backed and evictable rather
than anonymous — the compressor stops being involved at all. At `SCORE_WIDTH=2`: **~1.8 GB.** Width 4
becomes defensible (~3.7 GB) on measurement, not argument.

**Confidence: high.** The failure is fully characterised (§2b), the fix is the protection every
sibling path already has, and it is verifiable *before* spending: run `--dry-run` plus the assertion,
and watch RSS on candidate 0. If candidate 0 does not drop from ~1900 s to ~250 s, stop.

- **Wall clock:** ~250 s/candidate steady state (from the surviving `elapsed_s`) → 167 × 250 s +
  16 × ~700 s test ≈ 14.4 h serial → **~7 h at width 2, ~3.5 h at width 4.** Saves ~30–60 min *per
  dir* versus the broken path.
- **Cost:** **~$63** (fitted). No new spend from the fix itself.
- **What could go wrong:** the per-dir `SPEND_CAP = 6.00` on the 13–14 candidate dirs; and if the
  mmap assertion is written loosely it could pass while the corpus is still a list — assert both
  `isinstance(scores["data"], np.memmap)` **and** `type(_corpus).__name__ == "JsonlCorpus"`, as
  `hover_swap_run.py:43-46` does.

### Option 2 — mitigations only (SCORE_WIDTH=1, fewer WORKERS, per-candidate processes, recycling)

Treats the symptom. `WORKERS=1` would serialise the race away but multiplies wall clock ~8× (→ ~4–5
days). `SCORE_WIDTH=1` still leaves 8 × 5.06 GB ≈ 40 GB in one process. One process per *candidate*
makes it **worse**: 167 separate 5 GB non-mmap loads instead of 16. Periodic recycling doesn't help a
startup spike. **Cost ~$63, wall clock far worse, and it leaves a landmine for the next §8b consumer
(`backfill_stage1.py` imports the same `eval_split`).** Not recommended.

### Option 3 — move phase 2 to a cloud VM

**CHECK, answered: yes, §8b evaluation genuinely needs the BM25 index.** `eval_split.py:70-81`
`forward()` calls `probe.search` at `:74` on every hop; `titles` at `:80` derives *exclusively* from
retrieval, and the metric at `:150-152` is title recall against gold. Note the LLM's own `titles`
output field is declared at `:67-68` but **discarded** — only `new_notes` is read at `:78`. Without
the index every score is 0. It is not purely API-bound.

**Transfer cost:** the full `bm25s_index/` is **2.85 GB** (corpus.jsonl 1.676 + corpus.mmindex.json
0.054 + data.csc 0.527 + indices.csc 0.527 + indptr 0.020 + vocab 0.049), plus `threehop.jsonl`,
the repo, the `.venv-armT` lockfile venv (rebuild, don't copy — it's arm64), the two split artifacts,
the 16 run dirs' `gepa_result.json`, and the API key.

**Arm comparability is not threatened, and here is the reasoning rather than the assertion:** scoring
is deterministic evaluation, not optimization. BM25 retrieval is a pure function of the index bytes,
which are hash-pinned in `splits_manifest.json` and verified identical across all 9 existing
`endpoints.json`. The task LM is temp-0 with `cache=False` (`eval_split.py:179`) and runs API-side —
the same endpoint answers a VM and this laptop. Whatever nondeterminism remains at temp 0 is a
property of the provider, not of the host, so it is already present *within* the 8 runs scored here.
Provenance does need recording: the run artifacts carry no host field, so note the split in
`notes/` and the ledger.

- **Wall clock:** ~3.5 h compute at width 4 on an 8-core box, **plus** ~1–2 h setup and transfer.
- **Cost:** ~$63 API + ~$3–8 VM (a 16 GB box for a few hours).
- **What could go wrong:** you would be paying to relocate a bug that a ~15-line fix removes — and
  the unfixed code would still load 5 GB × 8 on the VM, so **Option 3 does not work without Option 1's
  fix anyway.** Worth it only if the laptop is needed for other work meanwhile.

### Option 4 — things not on the brief's list

**4a. Score all 16 dirs in ONE process (do this alongside Option 1).** `supervisor.py:410` runs one
process *per run dir*, so the index is loaded 16 times. `score_candidates.py --all` already exists
(`:167`) and `bootstrap()` runs once for the whole batch. With mmap + warm-up, one process × 16 dirs
loads the index **once**, and concurrency comes from `--workers` instead of processes. This removes
the multi-process memory multiplier entirely and is strictly less code than Option 2's process
juggling. The one cost: a single kill loses more progress — mitigate by keeping `supervisor.py --score`
for its per-dir markers and simply raising `--workers` at `SCORE_WIDTH=1`.

**4b. Add the memory guard the supervisor is missing.** `supervisor.py:457-461` checks
`avail_gb() < MEM_MIN_GB` (1.5 GB, `:63`) **only before spawn**; `reap_score` (`:382`) then polls
`p.poll()` and nothing else. A process ballooning to 40 GB is never noticed. A per-poll RSS check that
halts the wave is ~10 lines and would have caught this on the first run instead of the eighth.

**4c. Correct the supervisor's memory model.** `supervisor.py:74-78` justifies `SCORE_WIDTH = 2` with
"~1.5 GB each", taken from the *optimization* runs' `peak_rss_mb`. Those ran at `NUM_THREADS = 1`
(`run_state_dep.py:57`) and were compressor-suppressed — note `wall_clock_s: 8615` for ~302 metric
calls (28 s/call), which is a paging signature. That comment should record the measured scoring
footprint, not inherit the optimization one.

**4d. Re-fit the cost constant.** `M = 0.004543` is 30% low against 8 actuals (§3 header). Update it
or the $150 line will be crossed without warning.

---

## 4. Verification sequence (before any spend)

1. `score_candidates.py --run runs/C_seed3 --dry-run` — exercises sizing and gates, spends nothing.
2. Assert-only check: `bootstrap()` → warm-up → confirm `isinstance(probe._retriever.scores["data"],
   np.memmap)` and `type(probe._corpus).__name__ == "JsonlCorpus"`. $0.
3. Re-run the race demo against the fixed `eval_split` — expect **1** loader entry, not 8.
4. Live canary on **one small dir** (`C_seed5` or `T_seed3`, 7 candidates, ~$2.95): watch RSS stays
   under ~1.5 GB and candidate 0's `elapsed_s` lands near ~250 s, not ~1900 s. Abort if either misses.
5. Only then release the remaining 15.
