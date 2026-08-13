"""Wave supervisor for the 24 state-dependent runs. HARD-GATED on APPROVED-liverun (Neel-only).

Near-copy of analysis/ablation/hover_swap/phase2_supervisor.py, which drove 243 pairs at width 8
without an OOM. What carries over unchanged: fixed width (never ramped), the vm_stat pre-spawn
memory tripwire, spawn stagger, per-run DONE/FAILED markers, resume-by-artifact, NO auto-relaunch,
and a cumulative spend tripwire computed from completed runs plus an in-flight estimate.

WHAT IS DIFFERENT HERE
  * Two phases. The live smoke (arm T, seed 0) runs ALONE and first (v2.1 §13-5), and the waves
    refuse to start until markers/SMOKE.DONE exists. The smoke is what turns every projection in
    plan.md into a measurement, and it is excluded from analysis unconditionally.
  * Waves are mixed-arm (§13-8), read from wave_manifest.json. The supervisor never reorders them.
  * Width is fixed and re-decided ONLY by editing WIDTH, on the smoke's RSS + backoff measurement.
    There is no auto-ramp: a ramp that guesses wrong costs a wave. The 2026-07-28 smoke measured
    1460.3 MB/process and 0 backoffs -- zero rate-limit pressure, but 57% ABOVE the ~0.93 GB the
    old width-8 default rested on. 8 x 1460.3 MB = 11.4 GB on a 16 GB machine; 6 x = 8.6 GB. So
    width came DOWN to 6, not up. Raising it again needs a new RSS measurement, not an argument.

  * Three gated phases, in order. --waves runs the 24 optimizations at WIDTH; --score then runs
    the §8b post-run pass as ONE PROCESS PER RUN DIR at SCORE_WIDTH. Per-dir processes are the
    correct shape, not just the faster one -- see do_score()'s docstring.
  * A program-level LIVERUN_CAP spans both phases via liverun_ledger.json. TRIPWIRE/HARDCAP are
    optimization-only and score_candidates.py's SPEND_CAP is per run dir; neither spanned the two.

  python3 analysis/state_dep/supervisor.py --plan     # $0, prints what would run, spawns nothing
  caffeinate -dims python3 analysis/state_dep/supervisor.py --smoke    # the live smoke, alone
  caffeinate -dims python3 analysis/state_dep/supervisor.py --waves    # the 24 runs
  caffeinate -dims python3 analysis/state_dep/supervisor.py --score    # the §8b pass

`caffeinate -dims` is not optional for the waves: the machine must not sleep mid-run. Launch it
under nohup if the session may drop:

  nohup caffeinate -dims python3 analysis/state_dep/supervisor.py --waves \
        >> analysis/state_dep/logs/supervisor.out 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PYBIN = os.path.join(HERE, ".venv-armT", "bin", "python")
HARNESS = os.path.join(HERE, "run_state_dep.py")
MANIFEST = os.path.join(HERE, "wave_manifest.json")
SCORER = os.path.join(HERE, "score_candidates.py")
SELECTION = os.path.join(HERE, "selection_split.json")
TEST = os.path.join(HERE, "test_split.json")
RUNS = os.path.join(HERE, "runs")
MARKERS = os.path.join(HERE, "markers")
LOGS = os.path.join(HERE, "logs")
SUPLOG = os.path.join(HERE, "supervisor.log")
LEDGER = os.path.join(HERE, "liverun_ledger.json")

sys.path.insert(0, HERE)

WIDTH = 6            # fixed; see the module docstring before touching this (was 8 pre-smoke)
MEM_MIN_GB = 1.5     # pre-spawn hold; running processes are never killed
SPAWN_STAGGER = 5    # s between launches, so one process's model load settles before the next check
POLL = 15
EST_PER_RUN = 2.90   # in-flight estimate. The smoke measured $1.8279 optimization (arm T; arm B
                     # derives to ~$1.96), so this overestimates by ~50%. LEFT HIGH DELIBERATELY:
                     # it only feeds the TRIPWIRE in-flight guard, where overestimating stops
                     # launching EARLIER. Total optimization is ~$45 against TRIPWIRE $80, so it
                     # never binds either way.
TRIPWIRE = 80.0      # stop launching (optimization only; the §8b pass is score_candidates.py)
HARDCAP = 95.0

SCORE_WIDTH = 4      # concurrent score_candidates.py --run processes in the --score phase.
                     # Each is internally 8-threaded already (eval_split.WORKERS), so 4 processes
                     # = 32 API streams. Bought with PROCESSES, not by raising WORKERS: a crash
                     # then costs one run, not the pair, and each process keeps the proven
                     # per-process shape.
                     #
                     # 2 -> 4 on 2026-08-10, on a measurement, per the docstring rule above
                     # ("raising it again needs a new RSS measurement, not an argument").
                     #
                     # THE OLD "~1.5 GB each" WAS WRONG -- it was the OPTIMIZATION runs'
                     # peak_rss_mb (measured at run_state_dep NUM_THREADS=1, and compressor-
                     # suppressed), never a scoring measurement. vmmap on a bootstrapped scorer
                     # after the §8-8 mmap fix:
                     #     physical footprint   791 M steady, 1.1 G peak
                     #     TOTAL                6.3 G virtual -> 1.2 G resident, 570.8 M DIRTY
                     #     mapped file          2.6 G virtual ->  13.9 M resident,   0 K dirty
                     # Only the 570.8 MB dirty anonymous multiplies with width; the index is
                     # mmapped AND is the same file in every process, so its pages are shared
                     # page cache, not per-process copies. 4 x 571 MB = 2.3 GB (6 x = 3.4 GB).
                     #
                     # SO MEMORY IS NO LONGER THE BINDING CONSTRAINT -- it would permit 6. What
                     # binds is rate-limit behaviour above 16 concurrent streams, which we have
                     # never observed and CANNOT SEE: rate_hit (:397) greps child stdout for
                     # "429"/"rate limit", but litellm retries internally and silently, so
                     # throttling shows up as longer elapsed_s and higher spend, not as a flag.
                     # 16 streams (width 2 x 8 workers) is the only sustained observation -- ~8 h
                     # clean, per-candidate spread 171-331 s with no fat tail. 4 is a 2x
                     # extrapolation from that; 6 would be 3x. The elapsed_s canary in plan.md
                     # §10 step 3, watched by a human, is what makes 4 safe -- not this comment.
                     #
                     # NOTE: MEM_MIN_GB (:63) may hold the 3rd/4th spawn on a busy desktop --
                     # avail_gb() read 3.66 GB with Chrome+Cursor up. That fails CLOSED (logs
                     # "MEM HOLD", runs at effective width 2-3); free memory before launching.

# The program-level cap, spanning BOTH phases. TRIPWIRE/HARDCAP above are optimization-only and
# SPEND_CAP in score_candidates.py is per run dir; nothing before this spanned the two, so the
# gate's headline number had no enforcement behind it. Blended projection is $135.83.
#
# Raised 150.0 -> 160.0 on 2026-08-10 on measurement, not on argument. $72.64 is committed; the 16
# unscored run dirs are 10,750 metric calls, which at the measured live-§8b rate of $0.005897/call
# is $63.39 (program $136.03) and at the conservative smoke rate of $0.006121 is $65.80 (program
# $138.44). Against a $150 cap that conservative bound leaves $11.56 -- less than one arm-B run dir,
# so a single overrun halts the pass mid-flight with dirs half-scored. $160 leaves $21.56, more than
# the largest single dir. NOTE: the on-disk APPROVED-liverun still reads "Program cap $150.00";
# only Neel can restate a gate file (gates.py:41), so that reconciliation is his, not CC's.
LIVERUN_CAP = 160.0


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(SUPLOG), exist_ok=True)
    open(SUPLOG, "a").write(line + "\n")


def avail_gb() -> float:
    """Available RAM in GB from vm_stat (stdlib only; psutil is not installed).

    free + inactive + speculative. 'Pages free' alone is near-zero by design on macOS -- RAM is
    page cache -- so gating on it would hold forever and never spawn. Purgeable is excluded (it
    overlaps the other buckets); compressor pages are live anonymous memory and count as used.
    """
    out = subprocess.check_output(["vm_stat"], text=True)
    m = re.search(r"page size of (\d+) bytes", out)
    pg = int(m.group(1)) if m else 16384
    vals = {}
    for line in out.splitlines()[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().rstrip(".")
        if v.isdigit():
            vals[k.strip()] = int(v)
    pages = vals.get("Pages free", 0) + vals.get("Pages inactive", 0) + vals.get("Pages speculative", 0)
    return pages * pg / 1073741824.0


def ledger_read() -> list[dict]:
    return json.load(open(LEDGER)) if os.path.exists(LEDGER) else []


def ledger_total() -> float:
    """Everything APPROVED-liverun has spent so far, across both phases.

    Rebuilt from the ledger file rather than held in memory, so it survives a restart and so the
    --score phase sees what --waves spent. The smoke is NOT in here: it is APPROVED-smoke's cost.
    """
    return round(sum(e["spend_usd"] for e in ledger_read()), 4)


def ledger_append(phase: str, name: str, spend: float) -> float:
    entries = ledger_read()
    if any(e["phase"] == phase and e["run"] == name for e in entries):
        return ledger_total()  # idempotent: a resumed run must not be counted twice
    entries.append({"phase": phase, "run": name, "spend_usd": round(spend, 4)})
    json.dump(entries, open(LEDGER, "w"), indent=2)
    return ledger_total()


def cap_ok(phase: str, in_flight: int, est_each: float) -> bool:
    """Pre-spawn program cap. Refuses when committed + in-flight estimate would breach LIVERUN_CAP."""
    projected = ledger_total() + (in_flight + 1) * est_each
    if projected >= LIVERUN_CAP:
        log(f"LIVERUN CAP: ${ledger_total():.2f} spent + {in_flight + 1} in flight x ${est_each} "
            f"would reach ${projected:.2f} >= ${LIVERUN_CAP} — stop launching ({phase})")
        return False
    return True


def run_name(arm: str, seed: int, smoke: bool = False) -> str:
    return f"smoke_{arm}_seed{seed}" if smoke else f"{arm}_seed{seed}"


def completed(name: str) -> bool:
    return os.path.exists(os.path.join(RUNS, name, "run_summary.json"))


def cost_of(name: str) -> float:
    p = os.path.join(RUNS, name, "run_summary.json")
    return json.load(open(p)).get("spend_usd", 0.0) if os.path.exists(p) else 0.0


def spawn(arm: str, seed: int, smoke: bool):
    name = run_name(arm, seed, smoke)
    os.makedirs(LOGS, exist_ok=True)
    lf = open(os.path.join(LOGS, f"{name}.log"), "w")
    cmd = [PYBIN, "-u", HARNESS, "--arm", arm, "--seed", str(seed)] + (["--smoke"] if smoke else [])
    p = subprocess.Popen(cmd, cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
    return name, p, lf


def reap(running: dict, state: dict) -> list[str]:
    fin = [n for n, (p, _, _) in running.items() if p.poll() is not None]
    for name in fin:
        p, lf, ts = running.pop(name)
        lf.close()
        rc = p.returncode
        txt = open(os.path.join(LOGS, f"{name}.log")).read().lower()
        rate_hit = ("429" in txt) or ("rate limit" in txt) or ("ratelimit" in txt)
        ok = rc == 0 and completed(name)
        os.makedirs(MARKERS, exist_ok=True)
        if ok:
            c = cost_of(name)
            state["cost"] += c
            if not name.startswith("smoke_"):   # the smoke belongs to APPROVED-smoke, not liverun
                ledger_append("optimization", name, c)
            state["done"].append(name)
            open(os.path.join(MARKERS, f"{name}.DONE"), "w").write(f"cost={c} rc=0")
        else:
            state["failed"].append(name)
            open(os.path.join(MARKERS, f"{name}.FAILED"), "w").write(f"rc={rc} rate_hit={rate_hit}")
        if (not ok) or rate_hit:
            log(f"DEGRADE on {name} (rc={rc} ok={ok} rate_hit={rate_hit}) — width stays {WIDTH}, "
                f"no auto-relaunch")
        log(f"{'DONE' if ok else 'FAILED'} {name} rc={rc} {time.time() - ts:.0f}s "
            f"cum=${state['cost']:.4f} done={len(state['done'])} failed={len(state['failed'])} "
            f"running={len(running)}")
    return fin


def require_gate(name: str) -> None:
    from gates import require
    g = require(name)
    log(f"{name} present: {g['bytes']} bytes sha256={g['sha256'][:16]}...")


def require_splits() -> bool:
    """The smoke evaluates its own endpoint, so both splits must already exist (v2.1 §8a/§8b)."""
    missing = [os.path.basename(p) for p in (SELECTION, TEST) if not os.path.exists(p)]
    if missing:
        log(f"REFUSING: missing {', '.join(missing)} — run build_test_split.py behind "
            f"APPROVED-testsplit first. The smoke's endpoint evaluation has nothing to score on.")
        return False
    return True


def smoke_measurements() -> dict | None:
    p = os.path.join(RUNS, run_name("T", 0, smoke=True), "run_summary.json")
    return json.load(open(p)) if os.path.exists(p) else None


def do_smoke() -> int:
    """The live smoke: one arm-T seed-0 run AND its own §8b post-run pass, under APPROVED-smoke.

    Both halves are the smoke's cost, so both sit behind the smoke's own gate (v2.1.1 §13-7). The
    post-run pass is included deliberately: a smoke that measures only the optimization half would
    leave the §8b selection evaluations -- the single largest new line in the budget -- projected
    rather than measured, which is the thing the smoke exists to prevent.
    """
    require_gate("APPROVED-smoke")
    if not require_splits():
        return 2
    name = run_name("T", 0, smoke=True)
    state = {"cost": 0.0, "done": [], "failed": []}

    if completed(name):
        log(f"smoke optimization already complete ({name}) — skipping to the post-run pass")
    else:
        log(f"LIVE SMOKE: {name}, alone, full budget. Excluded from analysis (v2.1 §13-5).")
        n, p, lf = spawn("T", 0, smoke=True)
        running = {n: (p, lf, time.time())}
        while running:
            if not reap(running, state):
                time.sleep(POLL)

    s = smoke_measurements()
    if not s:
        log("SMOKE FAILED — no run_summary.json. STOP; do not launch waves.")
        return 1
    if not s["counter_matches_model"]:
        log(f"SMOKE COUNTER MISMATCH: total_num_evals={s['total_num_evals']} vs five-site model "
            f"{s['predicted_total_five_site']} — STOP, Neel decides. No post-run pass, no waves.")
        return 1

    log(f"smoke optimization: cost=${s['spend_usd']} wall={s['wall_clock_s']}s "
        f"rss={s['peak_rss_mb']}MB backoffs={s['backoffs']} counter_ok=True "
        f"events={s['child_bearing_events']} candidates={s['candidates_incl_seed']}")

    log("smoke §8b post-run pass (selection split, then test) — same gate")
    rc = subprocess.call([PYBIN, "-u", SCORER, "--run", name], cwd=REPO)
    if rc != 0:
        log(f"post-run pass FAILED rc={rc} — STOP; the endpoint half of the smoke is unmeasured.")
        return 1
    ep = json.load(open(os.path.join(RUNS, name, "endpoints.json")))

    total = s["spend_usd"] + ep["post_run_spend_usd"]
    marker = {
        "run": name,
        "optimization": {k: s[k] for k in (
            "spend_usd", "wall_clock_s", "peak_rss_mb", "backoffs", "total_num_evals",
            "predicted_total_five_site", "counter_matches_model", "child_bearing_events",
            "candidates_incl_seed", "accepts", "task_calls", "reflection_calls")},
        "post_run": {"selection_evals": ep["n_candidates"] * ep["selection_split"]["n"],
                     "test_evals": ep["test_split"]["n"],
                     "spend_usd": ep["post_run_spend_usd"],
                     "sel_best_idx": ep["sel_best_idx"],
                     "agrees_with_val_argmax": ep["agrees_with_val_argmax"],
                     "endpoint_test_mean": ep["endpoint_test_mean"]},
        "total_spend_usd": round(total, 4),
        "projection_24": {
            "spend_usd": round(total * 24, 2),
            "wall_clock_h_at_width": round(s["wall_clock_s"] * 24 / WIDTH / 3600, 2),
            "width": WIDTH,
            "caveat": "arm T only; B is cheaper per run and C sits between them",
        },
    }
    os.makedirs(MARKERS, exist_ok=True)
    open(os.path.join(MARKERS, "SMOKE.DONE"), "w").write(json.dumps(marker, indent=2))

    log(f"SMOKE DONE total=${total:.4f} (opt ${s['spend_usd']} + post-run "
        f"${ep['post_run_spend_usd']})  endpoint={ep['endpoint_test_mean']:.4f} "
        f"cand={ep['sel_best_idx']} agrees_with_val_argmax={ep['agrees_with_val_argmax']}")
    log(f"PROJECTION x24: ${total * 24:.2f}, "
        f"{s['wall_clock_s'] * 24 / WIDTH / 3600:.1f}h at width {WIDTH} "
        f"(arm T only — B is cheaper, C between)")
    log(f"RSS {s['peak_rss_mb']} MB/process, backoffs {s['backoffs']} — width stays {WIDTH} unless "
        f"BOTH say otherwise")
    log("Next: update plan.md §4 with these measurements, THEN APPROVED-liverun, THEN --waves.")
    return 0


def do_waves() -> int:
    require_gate("APPROVED-liverun")
    if not require_splits():
        return 2
    if not os.path.exists(os.path.join(MARKERS, "SMOKE.DONE")):
        log("REFUSING: markers/SMOKE.DONE absent. The live smoke runs first, under its own gate "
            "APPROVED-smoke (v2.1.1 §13-7).")
        return 2
    man = json.load(open(MANIFEST))
    state = {"cost": 0.0, "done": [], "failed": []}

    pending = []
    resumed = 0
    for w in man["waves"]:
        for r in w["runs"]:
            name = run_name(r["arm"], r["seed"])
            if completed(name):
                resumed += 1
                state["cost"] += cost_of(name)
                continue
            pending.append((w["wave"], r["arm"], r["seed"], name))
    log(f"waves: {len(pending)} pending, {resumed} already complete (resumed ${state['cost']:.4f}), "
        f"width={WIDTH} tripwire=${TRIPWIRE} hardcap=${HARDCAP} avail={avail_gb():.2f} GB")

    running: dict = {}
    halt = False
    while pending or running:
        while pending and len(running) < WIDTH and not halt:
            if state["cost"] >= HARDCAP:
                halt = True
                log(f"HARD CAP ${HARDCAP} reached (completed ${state['cost']:.2f}) — stop launching")
                break
            if state["cost"] + (len(running) + 1) * EST_PER_RUN >= TRIPWIRE:
                halt = True
                log(f"TRIPWIRE guard: ${state['cost']:.2f} + in-flight estimate would exceed "
                    f"${TRIPWIRE} — stop launching")
                break
            if not cap_ok("waves", len(running), EST_PER_RUN):
                halt = True
                break
            av = avail_gb()
            if av < MEM_MIN_GB:
                log(f"MEM HOLD: available={av:.2f} GB < {MEM_MIN_GB} GB — not spawning "
                    f"(running={len(running)}, pending={len(pending)}); retry next reap cycle")
                break
            wave, arm, seed, name = pending.pop(0)
            n, p, lf = spawn(arm, seed, smoke=False)
            running[n] = (p, lf, time.time())
            log(f"launched {n} (wave {wave}, width={WIDTH}, running={len(running)}, "
                f"pending={len(pending)}, avail={av:.2f} GB)")
            if pending and len(running) < WIDTH:
                time.sleep(SPAWN_STAGGER)
        if not reap(running, state):
            time.sleep(POLL)

    log(f"COMPLETE done={len(state['done'])} failed={len(state['failed'])} resumed={resumed} "
        f"optimization_cost=${state['cost']:.4f}")
    log("Next: score_candidates.py --all  (the §8b post-run pass), THEN the MDE + framing label, "
        "THEN results.md.")
    return 0 if not state["failed"] else 1


EST_SCORE_PER_RUN = 4.63   # arm B, the expensive arm on §8b (12.125 cand); T/C are $3.37


def scored(name: str) -> bool:
    """Resume-by-artifact, same discipline as completed(): endpoints.json IS the marker."""
    return os.path.exists(os.path.join(RUNS, name, "endpoints.json"))


def score_cost_of(name: str) -> float:
    p = os.path.join(RUNS, name, "endpoints.json")
    return json.load(open(p)).get("post_run_spend_usd") or 0.0 if os.path.exists(p) else 0.0


def spawn_score(name: str):
    os.makedirs(LOGS, exist_ok=True)
    lf = open(os.path.join(LOGS, f"score_{name}.log"), "w")
    cmd = [PYBIN, "-u", SCORER, "--run", os.path.join(RUNS, name)]
    p = subprocess.Popen(cmd, cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
    return p, lf


def reap_score(running: dict, state: dict) -> None:
    fin = [n for n, (p, _, _) in running.items() if p.poll() is not None]
    for name in fin:
        p, lf, ts = running.pop(name)
        lf.close()
        rc = p.returncode
        txt = open(os.path.join(LOGS, f"score_{name}.log")).read().lower()
        rate_hit = ("429" in txt) or ("rate limit" in txt) or ("ratelimit" in txt)
        ok = rc == 0 and scored(name)
        os.makedirs(MARKERS, exist_ok=True)
        if ok:
            c = score_cost_of(name)
            state["cost"] += c
            total = ledger_append("score", name, c)
            state["done"].append(name)
            open(os.path.join(MARKERS, f"score_{name}.DONE"), "w").write(f"cost={c} rc=0")
            log(f"SCORED {name} rc=0 {time.time() - ts:.0f}s ${c:.4f} "
                f"liverun_total=${total:.2f}/{LIVERUN_CAP} done={len(state['done'])} "
                f"failed={len(state['failed'])} running={len(running)}")
        else:
            state["failed"].append(name)
            open(os.path.join(MARKERS, f"score_{name}.FAILED"), "w").write(
                f"rc={rc} rate_hit={rate_hit}")
            log(f"SCORE FAILED {name} rc={rc} rate_hit={rate_hit} — no auto-relaunch, "
                f"width stays {SCORE_WIDTH}")


def do_score() -> int:
    """The §8b post-run pass, one process PER RUN DIR, SCORE_WIDTH at a time.

    Per-dir processes are not merely faster than `score_candidates.py --all` -- they are the
    correct shape. `--all` shares one LM across every dir, and Meter.spend() sums the whole of
    lm.history, so from dir 2 on it reports cumulative spend as per-dir and trips its own
    per-dir SPEND_CAP mid-pass. A process per dir gives each one a fresh history.
    """
    require_gate("APPROVED-liverun")
    if not require_splits():
        return 2
    if not os.path.exists(os.path.join(MARKERS, "SMOKE.DONE")):
        log("REFUSING: markers/SMOKE.DONE absent — the smoke runs first (v2.1.1 §13-7).")
        return 2

    man = json.load(open(MANIFEST))
    state = {"cost": 0.0, "done": [], "failed": []}
    pending, resumed, waiting = [], 0, []
    for w in man["waves"]:
        for r in w["runs"]:
            name = run_name(r["arm"], r["seed"])
            if scored(name):
                resumed += 1
                state["cost"] += score_cost_of(name)
                continue
            if not completed(name):
                waiting.append(name)     # optimization not finished; nothing to score yet
                continue
            pending.append(name)

    if waiting:
        log(f"NOTE: {len(waiting)} run(s) have no run_summary.json yet and are skipped this pass "
            f"({', '.join(waiting[:6])}{'...' if len(waiting) > 6 else ''}). Re-run --score after "
            f"--waves completes; scoring is resume-by-artifact and costs $0 for what is done.")
    log(f"score: {len(pending)} pending, {resumed} already scored (${state['cost']:.4f}), "
        f"{len(waiting)} not yet optimized, width={SCORE_WIDTH} "
        f"liverun_total=${ledger_total():.2f}/{LIVERUN_CAP} avail={avail_gb():.2f} GB")
    if not pending:
        log("nothing to score")
        return 0 if not waiting else 1

    running: dict = {}
    halt = False
    while pending or running:
        while pending and len(running) < SCORE_WIDTH and not halt:
            if not cap_ok("score", len(running), EST_SCORE_PER_RUN):
                halt = True
                break
            av = avail_gb()
            if av < MEM_MIN_GB:
                log(f"MEM HOLD: available={av:.2f} GB < {MEM_MIN_GB} GB — not spawning "
                    f"(running={len(running)}, pending={len(pending)})")
                break
            name = pending.pop(0)
            p, lf = spawn_score(name)
            running[name] = (p, lf, time.time())
            log(f"scoring {name} (width={SCORE_WIDTH}, running={len(running)}, "
                f"pending={len(pending)}, avail={av:.2f} GB)")
            if pending and len(running) < SCORE_WIDTH:
                time.sleep(SPAWN_STAGGER)
        reap_score(running, state)
        if running:
            time.sleep(POLL)

    log(f"SCORE COMPLETE done={len(state['done'])} failed={len(state['failed'])} "
        f"§8b spend=${state['cost']:.4f}  liverun total=${ledger_total():.2f}/{LIVERUN_CAP}")
    log("Next: the MDE + §11-2 framing label (needs APPROVED-backfill), THEN results.md.")
    return 0 if not (state["failed"] or waiting) else 1


def do_plan() -> int:
    man = json.load(open(MANIFEST))
    print(f"=== supervisor plan ($0, nothing spawned) ===")
    print(f"  harness    : {os.path.relpath(HARNESS, REPO)}")
    print(f"  interpreter: {os.path.relpath(PYBIN, REPO)}")
    print(f"  width      : {WIDTH}   mem hold < {MEM_MIN_GB} GB   avail now {avail_gb():.2f} GB")
    print(f"  tripwire   : ${TRIPWIRE}   hard cap ${HARDCAP}   est/run ${EST_PER_RUN}")
    print(f"  score      : width {SCORE_WIDTH}   est/run ${EST_SCORE_PER_RUN} (arm B; T/C $3.37)")
    print(f"  liverun cap: ${LIVERUN_CAP} across BOTH phases   spent so far ${ledger_total():.2f}")
    print(f"  smoke      : {run_name('T', 0, True)} — alone, first, own gate APPROVED-smoke, "
          f"excluded from analysis")
    smoke_done = os.path.exists(os.path.join(MARKERS, 'SMOKE.DONE'))
    print(f"  SMOKE.DONE : {'present' if smoke_done else 'ABSENT — --waves will refuse'}")
    splits = [os.path.basename(p) for p in (SELECTION, TEST) if os.path.exists(p)]
    print(f"  splits     : {', '.join(splits) if splits else 'ABSENT — both --smoke and --waves '
          'will refuse'}")
    for w in man["waves"]:
        cells = []
        for r in w["runs"]:
            n = run_name(r["arm"], r["seed"])
            cells.append(f"{r['arm']}{r['seed']}{'*' if completed(n) else ''}")
        print(f"  wave {w['wave']}   : {'  '.join(cells)}")
    print("  (* = already complete, would be skipped on resume)")
    print(f"\n  launch: caffeinate -dims python3 {os.path.relpath(__file__, REPO)} --smoke")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--waves", action="store_true")
    ap.add_argument("--score", action="store_true",
                    help="the §8b post-run pass, one process per run dir, SCORE_WIDTH at a time")
    a = ap.parse_args()
    if a.plan:
        raise SystemExit(do_plan())
    if a.smoke:
        raise SystemExit(do_smoke())
    if a.waves:
        raise SystemExit(do_waves())
    if a.score:
        raise SystemExit(do_score())
    ap.error("pick --plan ($0), --smoke, --waves, or --score (the last three are gated)")
