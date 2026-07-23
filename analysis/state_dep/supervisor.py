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
  * Width 8 is the proven floor. It is raised ONLY by editing WIDTH after the smoke reports RSS
    headroom AND zero backoffs. There is no auto-ramp: a ramp that guesses wrong costs a wave.

  python3 analysis/state_dep/supervisor.py --plan     # $0, prints what would run, spawns nothing
  caffeinate -dims python3 analysis/state_dep/supervisor.py --smoke    # the live smoke, alone
  caffeinate -dims python3 analysis/state_dep/supervisor.py --waves    # the 24 runs

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
RUNS = os.path.join(HERE, "runs")
MARKERS = os.path.join(HERE, "markers")
LOGS = os.path.join(HERE, "logs")
SUPLOG = os.path.join(HERE, "supervisor.log")

sys.path.insert(0, HERE)

WIDTH = 8            # fixed; see the module docstring before touching this
MEM_MIN_GB = 1.5     # pre-spawn hold; running processes are never killed
SPAWN_STAGGER = 5    # s between launches, so one process's model load settles before the next check
POLL = 15
EST_PER_RUN = 2.90   # in-flight estimate, superseded by the smoke's measurement
TRIPWIRE = 80.0      # stop launching (optimization only; the §8b pass is score_candidates.py)
HARDCAP = 95.0


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


def require_gate() -> None:
    from gates import require
    g = require("APPROVED-liverun")
    log(f"APPROVED-liverun present: {g['bytes']} bytes sha256={g['sha256'][:16]}...")


def smoke_measurements() -> dict | None:
    p = os.path.join(RUNS, run_name("T", 0, smoke=True), "run_summary.json")
    return json.load(open(p)) if os.path.exists(p) else None


def do_smoke() -> int:
    require_gate()
    name = run_name("T", 0, smoke=True)
    if completed(name):
        log(f"smoke already complete ({name}) — nothing to do")
        return 0
    log(f"LIVE SMOKE: {name}, alone, full budget. Excluded from analysis (v2.1 §13-5).")
    n, p, lf = spawn("T", 0, smoke=True)
    running = {n: (p, lf, time.time())}
    state = {"cost": 0.0, "done": [], "failed": []}
    while running:
        if not reap(running, state):
            time.sleep(POLL)
    s = smoke_measurements()
    if not s:
        log("SMOKE FAILED — no run_summary.json. STOP; do not launch waves.")
        return 1
    os.makedirs(MARKERS, exist_ok=True)
    open(os.path.join(MARKERS, "SMOKE.DONE"), "w").write(json.dumps(s, indent=2))
    log(f"SMOKE DONE cost=${s['spend_usd']} wall={s['wall_clock_s']}s rss={s['peak_rss_mb']}MB "
        f"backoffs={s['backoffs']} counter_ok={s['counter_matches_model']} "
        f"events={s['child_bearing_events']} candidates={s['candidates_incl_seed']}")
    log(f"PROJECTION x24 (optimization only): ${s['spend_usd'] * 24:.2f}, "
        f"{s['wall_clock_s'] * 24 / WIDTH / 3600:.1f}h at width {WIDTH}")
    if not s["counter_matches_model"]:
        log("SMOKE COUNTER MISMATCH vs the §6a five-site model — STOP, Neel decides.")
        return 1
    log("Next: update plan.md with these measurements, THEN --waves.")
    return 0


def do_waves() -> int:
    require_gate()
    if not os.path.exists(os.path.join(MARKERS, "SMOKE.DONE")):
        log("REFUSING: markers/SMOKE.DONE absent. The live smoke runs first (v2.1 §13-5).")
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


def do_plan() -> int:
    man = json.load(open(MANIFEST))
    print(f"=== supervisor plan ($0, nothing spawned) ===")
    print(f"  harness    : {os.path.relpath(HARNESS, REPO)}")
    print(f"  interpreter: {os.path.relpath(PYBIN, REPO)}")
    print(f"  width      : {WIDTH}   mem hold < {MEM_MIN_GB} GB   avail now {avail_gb():.2f} GB")
    print(f"  tripwire   : ${TRIPWIRE}   hard cap ${HARDCAP}   est/run ${EST_PER_RUN}")
    print(f"  smoke      : {run_name('T', 0, True)} — runs alone, first, excluded from analysis")
    smoke_done = os.path.exists(os.path.join(MARKERS, 'SMOKE.DONE'))
    print(f"  SMOKE.DONE : {'present' if smoke_done else 'ABSENT — --waves will refuse'}")
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
    a = ap.parse_args()
    if a.plan:
        raise SystemExit(do_plan())
    if a.smoke:
        raise SystemExit(do_smoke())
    if a.waves:
        raise SystemExit(do_waves())
    ap.error("pick --plan ($0), --smoke (gated), or --waves (gated)")
