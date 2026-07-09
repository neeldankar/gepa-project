"""Stage-2 Phase 2 supervisor — full 243-pair batch-swap. HARD-GATED on analysis/ablation/hover_swap/
APPROVED (Neel-only). FIXED concurrency width 8 (no ramp): the mmap'd index costs ~0.92 GB private
per pair process, so 8 fits 16 GB with the OS held at 4 GB. Pre-spawn memory tripwire holds launching
when available RAM drops below MEM_MIN_GB; running pairs are never killed. Per-pair DONE/FAILED
markers, NO auto-relaunch. Cumulative spend tripwire $80 / hard cap $90 (from completed-pair costs +
in-flight estimate). Resumable: pairs with an existing meta.json are skipped. Writes supervisor.log;
manifest on completion.

  python3 analysis/ablation/hover_swap/phase2_supervisor.py
"""
import json, os, re, subprocess, sys, time
from itertools import combinations  # noqa

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(REPO, "analysis", "ablation", "hover_swap")
PYBIN = os.path.join(REPO, "scratch", "hover_probe", ".venv", "bin", "python")
HARNESS = os.path.join(OUT, "hover_swap_run.py")
APPROVAL = os.path.join(OUT, "APPROVED")
PAIRS_DIR = os.path.join(OUT, "pairs"); MARKERS = os.path.join(OUT, "markers")
LOGS = os.path.join(OUT, "logs", "pairs")
TRIPWIRE, HARDCAP, EST = 80.0, 90.0, 0.35
WIDTH = 8          # fixed concurrency, never ramped
MEM_MIN_GB = 1.5   # pre-spawn tripwire: hold if available RAM is below this
SPAWN_STAGGER = 5  # s between launches, so each index load settles before the next check
POLL = 15

def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    open(os.path.join(OUT, "supervisor.log"), "a").write(line + "\n")

def avail_gb():
    """Available RAM in GB, from vm_stat (stdlib only; psutil is not installed).

    Counts free + inactive + speculative. 'Pages free' alone is near-zero by design on macOS
    (RAM is used as page cache, and the mmap'd BM25 index now lives there), so gating on it
    would hold forever and never spawn. Purgeable is excluded: it overlaps the other buckets.
    Compressor pages are live anonymous memory and correctly count as used.
    """
    out = subprocess.check_output(["vm_stat"], text=True)
    m = re.search(r"page size of (\d+) bytes", out)
    pg = int(m.group(1)) if m else 16384
    vals = {}
    for line in out.splitlines()[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1); v = v.strip().rstrip(".")
        if v.isdigit():
            vals[k.strip()] = int(v)
    pages = vals.get("Pages free", 0) + vals.get("Pages inactive", 0) + vals.get("Pages speculative", 0)
    return pages * pg / 1073741824.0

def main():
    if not os.path.exists(APPROVAL):
        sys.exit(f"REFUSING TO START: {APPROVAL} does not exist (Neel-only).")
    log(f"APPROVED present (mtime={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(APPROVAL)))})")
    log(f"APPROVED contents: {open(APPROVAL).read().strip()}")
    os.makedirs(PAIRS_DIR, exist_ok=True); os.makedirs(MARKERS, exist_ok=True); os.makedirs(LOGS, exist_ok=True)

    plan = [json.loads(l) for l in open(os.path.join(OUT, "pairing_plan.jsonl"))]
    pending, skipped = [], 0
    completed_cost = 0.0
    for r in plan:
        pid = f"seed{r['seed']}_i{r['trace_i']}"
        meta_p = os.path.join(PAIRS_DIR, pid, "meta.json")
        if os.path.exists(meta_p):  # resume: already done
            skipped += 1
            completed_cost += json.load(open(meta_p)).get("pair_cost_usd", 0.0)
            continue
        pending.append((r["seed"], r["trace_i"], pid))
    log(f"pairs total={len(plan)} pending={len(pending)} already_done={skipped} resumed_cost=${completed_cost:.4f}")

    running = {}  # pid -> (popen, logfile_handle, start_ts)
    done, failed, spend_halt = [], [], False
    log(f"start FIXED width={WIDTH} (no ramp) tripwire=${TRIPWIRE} hardcap=${HARDCAP} "
        f"mem_min={MEM_MIN_GB} GB avail={avail_gb():.2f} GB")

    while pending or running:
        # launch
        while pending and len(running) < WIDTH and not spend_halt:
            if completed_cost >= HARDCAP:
                spend_halt = True; log(f"HARD CAP ${HARDCAP} reached (completed=${completed_cost:.2f}) — stop launching"); break
            if completed_cost + (len(running) + 1) * EST >= TRIPWIRE:
                spend_halt = True; log(f"TRIPWIRE guard: completed=${completed_cost:.2f} + in-flight est would exceed ${TRIPWIRE} — stop launching"); break
            av = avail_gb()
            if av < MEM_MIN_GB:
                mem_held = True
                log(f"MEM HOLD: available={av:.2f} GB < {MEM_MIN_GB} GB — not spawning "
                    f"(running={len(running)}, pending={len(pending)}); retry next reap cycle")
                break
            seed, trace_i, pid = pending.pop(0)
            lf = open(os.path.join(LOGS, f"{pid}.log"), "w")
            p = subprocess.Popen([PYBIN, "-u", HARNESS, "--pair", str(seed), str(trace_i)],
                                 cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
            running[pid] = (p, lf, time.time())
            log(f"launched {pid} (width={WIDTH}, running={len(running)}, pending={len(pending)}, avail={av:.2f} GB)")
            if pending and len(running) < WIDTH:
                time.sleep(SPAWN_STAGGER)  # let this process's index load settle before re-reading avail
        # poll
        fin = [pid for pid, (p, _, _) in running.items() if p.poll() is not None]
        for pid in fin:
            p, lf, ts = running.pop(pid); lf.close()
            rc = p.returncode
            logtxt = open(os.path.join(LOGS, f"{pid}.log")).read().lower()
            rate_hit = ("429" in logtxt) or ("rate limit" in logtxt) or ("ratelimit" in logtxt)
            meta_p = os.path.join(PAIRS_DIR, pid, "meta.json")
            ok = (rc == 0 and os.path.exists(meta_p))
            if ok:
                cost = json.load(open(meta_p)).get("pair_cost_usd", 0.0)
                completed_cost += cost; done.append(pid)
                open(os.path.join(MARKERS, f"{pid}.DONE"), "w").write(f"cost={cost} rc=0")
            else:
                failed.append(pid)
                open(os.path.join(MARKERS, f"{pid}.FAILED"), "w").write(f"rc={rc} rate_hit={rate_hit}")
            if (not ok) or rate_hit:
                log(f"DEGRADE on {pid} (rc={rc} ok={ok} rate_hit={rate_hit}) — width stays {WIDTH}, no auto-relaunch")
            log(f"{'DONE' if ok else 'FAILED'} {pid} rc={rc} {time.time()-ts:.0f}s "
                f"cum=${completed_cost:.4f} done={len(done)} failed={len(failed)} width={WIDTH} running={len(running)} pending={len(pending)}")
        if not fin:
            time.sleep(POLL)

    log(f"COMPLETE done={len(done)} failed={len(failed)} skipped_resumed={skipped} total_cost=${completed_cost:.4f}")
    write_manifest(plan, done, failed)

def write_manifest(plan, done, failed):
    rows, total_cost, total_wall, exact = [], 0.0, 0.0, 0
    per_seed = {}
    for r in plan:
        pid = f"seed{r['seed']}_i{r['trace_i']}"
        meta_p = os.path.join(PAIRS_DIR, pid, "meta.json")
        if not os.path.exists(meta_p):
            rows.append((pid, r["seed"], r["trace_i"], "FAILED/absent", "", "", "", "", "")); continue
        m = json.load(open(meta_p))
        total_cost += m["pair_cost_usd"]; total_wall += m["pair_wall_s"]; exact += 1 if m["match_exact"] else 0
        per_seed[r["seed"]] = per_seed.get(r["seed"], 0) + 1
        rows.append((pid, m["seed"], m["trace_i"], "DONE", m["comp"], m["match_exact"],
                     round(m["match_l1"], 3), m["n_draws"], m["pair_cost_usd"]))
    n_done = sum(1 for x in rows if x[3] == "DONE")
    L = ["# Stage-2 HoVer batch-swap — Phase-2 manifest (raw facts, no interpretation)\n"]
    L.append(f"- Gate: `APPROVED` — {open(APPROVAL).read().strip()}")
    L.append(f"- Pairs: planned {len(plan)}, DONE {n_done}, FAILED/absent {len(plan)-n_done}.")
    L.append(f"- Total cost (completed pairs): ${total_cost:.4f}. Total pair wall (sum): {total_wall/3600:.2f} h.")
    L.append(f"- Failure-match: exact multiset {exact}/{n_done} ({100*exact/max(1,n_done):.1f}%).")
    L.append(f"- Per-seed completed: {dict(sorted(per_seed.items()))}")
    L.append(f"- Draws persisted per pair: 2 arms x {3} draws x (A_e[3] + B_e[3]) per-example vectors + child text.")
    L.append("\n## Paths")
    L.append("- Per pair: `pairs/seed<S>_i<T>/{draws.jsonl, reflect_in_SAME.txt, reflect_in_SWAP.txt, meta.json}`")
    L.append("- Markers: `markers/<pid>.DONE|.FAILED`. Per-pair logs: `logs/pairs/<pid>.log`. Supervisor: `supervisor.log`.")
    L.append("\n## Per-pair table\n")
    L.append("| pair | seed | trace_i | status | comp | match_exact | L1 | draws | cost |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for x in rows:
        L.append("| " + " | ".join(str(v) for v in x) + " |")
    open(os.path.join(OUT, "hover_swap_manifest.md"), "w").write("\n".join(L) + "\n")
    log(f"wrote hover_swap_manifest.md ({n_done} DONE, ${total_cost:.4f})")

if __name__ == "__main__":
    main()
