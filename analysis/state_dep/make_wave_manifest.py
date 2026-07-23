"""Build the 24-run wave manifest. $0, deterministic, no gate (it writes a plan, not a spend).

24 runs = 3 arms x 8 paired seeds, in 3 waves of 8. Two constraints, both from v2.1:

  MIXED ARMS PER WAVE (§13-8). Never "all of arm T first". If a wave is arm-pure and the machine,
  the API, or the day drifts, that drift is perfectly confounded with the arm. Each wave here
  carries 2-3 runs of every arm.

  PAIRING IS BY SEED (§7, §10). Seed s appears exactly once in each arm across the 24, so the
  paired differences T_s - C_s are defined for all 8 seeds. Waves are a scheduling device and
  carry no analysis meaning -- but a seed's three arms are spread across different waves rather
  than run together, so a wave-level disturbance cannot hit one seed's three arms alone.

Emitted order within a wave is the launch order; the supervisor takes them at width 8.

  python3 analysis/state_dep/make_wave_manifest.py [--print]
"""
from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "wave_manifest.json")

ARMS = ("B", "C", "T")
SEEDS = tuple(range(8))
WAVES = 3
WIDTH = 8


def build() -> dict:
    # (arm, seed) for all 24, laid out so that wave w takes arm ARMS[(i + w) % 3] for seed i.
    # Each wave then holds 8 runs with arm counts (3, 3, 2) rotating, and each seed's three arms
    # land in three different waves.
    waves = []
    for w in range(WAVES):
        runs = [{"arm": ARMS[(s + w) % len(ARMS)], "seed": s} for s in SEEDS]
        # interleave so adjacent launches differ in arm wherever possible
        runs.sort(key=lambda r: (r["seed"] % 2, r["arm"]))
        waves.append(runs)

    flat = [(r["arm"], r["seed"]) for w in waves for r in w]
    assert len(flat) == 24, len(flat)
    assert len(set(flat)) == 24, "duplicate (arm, seed) cell"
    for arm in ARMS:
        assert sorted(s for a, s in flat if a == arm) == list(SEEDS), f"arm {arm} is not 1x8 seeds"
    for i, w in enumerate(waves):
        seeds_in_wave = [r["seed"] for r in w]
        assert len(set(seeds_in_wave)) == 8, f"wave {i} repeats a seed"

    return {
        "design": "state-dependent-design-v2.1-frozen §7, §13-8",
        "n_runs": 24,
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "width": WIDTH,
        "width_note": "8 is the proven floor (swap ran width 8 at ~0.93 GB/process). Raise only if "
                      "the live smoke shows RSS headroom AND zero backoffs. Never 16 untested.",
        "smoke": {"arm": "T", "seed": 0, "excluded_from_analysis": True,
                  "note": "v2.1 §13-5: runs first, measured, excluded; T/seed0 is rerun in wave 1 "
                          "like every other cell"},
        "waves": [{"wave": i + 1, "runs": w} for i, w in enumerate(waves)],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args()
    man = build()
    json.dump(man, open(OUT, "w"), indent=2)
    print(f"wrote {os.path.basename(OUT)}: {man['n_runs']} runs in {len(man['waves'])} waves, "
          f"width {man['width']}")
    if a.show:
        for w in man["waves"]:
            cells = "  ".join(f"{r['arm']}{r['seed']}" for r in w["runs"])
            counts = {arm: sum(1 for r in w["runs"] if r["arm"] == arm) for arm in ARMS}
            print(f"  wave {w['wave']}: {cells}    ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
