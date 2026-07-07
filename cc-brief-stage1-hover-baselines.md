# CC Brief — Stage 1: fresh HoVer baseline runs

**Repo:** `gepa-si-curriculum`
**Supersedes:** nothing — this is the first Stage-1 brief.
**Feeds into:** Stage 2 (the HoVer batch-swap, drafted separately, not yet written).

## Why this run exists (context for a cold reader)

The frozen HoVer run (`scratch/hover_probe/necrosis/`) is real data — 1 run, 33 events, 12-claim
trainset, deterministic title-recall metric, $1.96 total cost — but too thin to run the batch-swap
on: frozen-only MDE is ≈0.08-0.10, too weak to say anything. It was also cheap, which is the whole
reason a two-stage plan is worth it instead of abandoning HoVer. Stage 1 (this brief) generates a
bigger, freshly-logged baseline corpus. Stage 2 (separate brief, later) runs the swap on top of it.

Do not conflate the two. This brief only produces baseline runs — no swap logic, no batch
manipulation. Just more of what the frozen run already is, at a bigger trainset and seed count,
with full persistence.

## Known facts about the frozen reference run — verify, do not assume

These are believed true from the inventory pass. Confirm each against the actual files in
`scratch/hover_probe/necrosis/` before relying on it — do not carry these numbers forward without
checking the bytes:

- Local BM25 retrieval index (`bm25s`), ~2.7GB on disk, already built
- gpt-4.1-mini used for the eval calls, ~6 calls per example
- Deterministic title-recall metric, no LLM judge, metric grid is coarse: {0, 1/3, 2/3, 1}
- 12-claim trainset, ids 0-11, cycled to produce 33 events
- Some stopping-budget parameter referred to as `mm=300` — confirm the actual harness config key
  and value, the label above may not be exact
- Total cost $1.96, single run, per-example parent AND child scores persisted (this run already
  did better persistence than IFBench v2 — match or exceed it, don't regress)

## Preflight — do this before touching anything

1. Confirm `gepa-si-curriculum` has at least one git commit (`git log`). If it does not, **stop
   and report** — do not commit yourself, that is being handled separately.
2. Read the frozen run's actual config directly from its files, not from this brief. Match model,
   retrieval, metric, and stopping budget exactly, except for the two changes below (trainset size,
   seed).
3. Confirm the existing BM25 index still loads. **Do not rebuild it.** If it's missing or broken,
   stop and flag rather than rebuilding with different parameters.
4. Locate `eyeball_records/threehop`, count usable claim records, and pick a trainset size in the
   40-100 range — prefer more if cheaply available, but report the exact count and the ids used.
   If fewer than 40 usable records exist, stop and flag.
5. Confirm `capture_traces=True` will be set on every run below, including the smoke run. No
   exceptions — this is the standing persistence rule (`docs/cc-brief-template-rules.md`).

## Phase 1 — seed-0-first smoke (do this now, nothing else)

- Run exactly one fresh HoVer baseline: seed 0, the trainset chosen above, otherwise identical
  config to the frozen reference run.
- `capture_traces=True` — persist per-example parent AND child score vectors plus full child text.
- Measure end-to-end, for real, not estimated: wall-clock time, total dollar cost from actual
  usage/cost logs, event count.
- Write `plan.md` in the stage-1 output directory. Contents, nothing else:
  - trainset size and the exact claim ids used
  - measured seed-0 numbers: cost, time, event count
  - projected cost and time for N=6 total seeds and for N=8 total seeds (measured × N)
  - one line: `STOP — awaiting APPROVED`
- **Stop here.** Do not run additional seeds. Do not create the `APPROVED` file — only Neel does
  that, and only after reading the measured numbers in `plan.md`.

## Phase 2 — remaining seeds (only once an `APPROVED` file exists)

- Re-read `plan.md` for the seed count Neel has approved. Do not assume a default — if it isn't
  written down, stop and ask rather than guessing 6 vs 8.
- Fire the remaining seeds (1 through N-1), identical config to seed 0.
- Save everything under a new stage-1-specific directory, e.g. `scratch/hover_stage1/`. **Never
  write into or modify** `scratch/hover_probe/necrosis/`, the IFBench corpora, or the batch-swap v2
  outputs — those are frozen.
- Write `stage1_manifest.md`: raw facts only — per-run event count, cost, duration, and the file
  paths where per-example score vectors and child text live. **No interpretation. No summary
  prose about what the numbers mean.** A CC-generated interpretive summary is not an acceptable
  substitute for the raw manifest on this project, even as a first pass — this has happened before
  and is the thing to not repeat.

## Budget

Two-stage plan target for Stage 1 is ~$15-50 total across 6-8 seeds. Treat that as a sanity ceiling,
not a target — the smoke measurement in Phase 1 is what actually decides whether 6 or 8 seeds fits,
or whether this needs a different call from Neel.

## Explicit do-not list

- Do not skip the seed-0-first smoke, and do not fire all seeds at once.
- Do not create the `APPROVED` file yourself.
- Do not touch any frozen corpus.
- Do not rebuild the BM25 index.
- Do not deliver an interpretive summary in place of the raw manifest.
- Do not guess at the frozen run's config values — read them from its actual files.
