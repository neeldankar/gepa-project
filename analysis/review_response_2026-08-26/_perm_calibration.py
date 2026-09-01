"""Item 3: permutation calibration of the 108-cell conjunction rule. $0, no network.

Null: permute the outcome spec_i WITHIN SEED, holding all 108 scorers fixed. This preserves the
cross-cell correlation structure, which is what makes a maximum over 108 cells a valid null.
Mirrors the negative-control block at screen_part4_stats.py:23-30, which permutes within run.

Reuses CellEngine, perrun_z and bca_ci from screen_part4_stats.py unchanged, at the original
B = P = 9999. Permutation 0 is the identity pass and must reproduce the published survivor set.
"""
import importlib.util, json, multiprocessing as mp, os, sys, time
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SCREEN = os.path.join(os.path.dirname(HERE), "hover_screen")
N_PERM = int(sys.argv[1]) if len(sys.argv) > 1 else 200
NPROC = int(sys.argv[2]) if len(sys.argv) > 2 else 8
OUT = os.path.join(HERE, "_perm_raw.json")

_G = {}


def init():
    os.environ["OMP_NUM_THREADS"] = "1"
    spec = importlib.util.spec_from_file_location("s4", os.path.join(SCREEN, "screen_part4_stats.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    feats = pd.read_csv(os.path.join(SCREEN, "features.csv"))
    outs = pd.read_csv(os.path.join(SCREEN, "outcomes.csv"))
    df = feats.merge(outs[["pair_id", "spec_i", "trans_i", "sign_i"]], on="pair_id",
                     validate="one_to_one")
    assert len(df) == 243, len(df)
    void = [c for c in feats.columns if c.startswith(m.VOID_PREFIX)]
    cand = [c for c in feats.columns if c not in m.BOOKKEEP and c not in void]
    race = [c for c in cand if feats[c].nunique(dropna=True) > 1]
    assert len(race) == 108, len(race)
    _G.update(m=m, df=df, race=race, eng=m.CellEngine(df),
              seeds=df["seed"].to_numpy(), y0=df["spec_i"].to_numpy(float),
              base=["iteration", "parent_pool_score"],
              zc={c: m.perrun_z(df[c].to_numpy(float), df["seed"].to_numpy()) for c in race})


def one_perm(p):
    m, df, race, eng = _G["m"], _G["df"], _G["race"], _G["eng"]
    seeds, base = _G["seeds"], _G["base"]
    y = _G["y0"].copy()
    if p > 0:                                    # p == 0 is the identity pass
        rng = np.random.default_rng(1_000_000 + p)
        for s in np.unique(seeds):
            msk = seeds == s
            y[msk] = rng.permutation(y[msk])
    ss = np.random.SeedSequence(m.SEED_PERM + p)
    cell_rngs = dict(zip(race, ss.spawn(len(race))))
    rec, boots = {}, {}
    for c in race:
        z = _G["zc"][c]
        r41 = eng.run(z, y, base, np.random.default_rng(cell_rngs[c]))
        ctrl42 = base + [x for x in m.CTRL_AXIS if x != c]
        r42 = eng.run(z, y, ctrl42, np.random.default_rng(cell_rngs[c]))
        rec[c] = {k: {"beta": float(r["beta"]), "lo": float(r["lo"]), "hi": float(r["hi"]),
                      "p": float(r["p"]), "loro": int(r["loro"])}
                  for k, r in (("41", r41), ("42", r42))}
        boots[c] = r41["boot_betas"]

    # MCB over |beta| on read 4.1, shared draws -- screen_part4_stats.py:289-297 verbatim
    ok_cells = [c for c in race if boots[c] is not None]
    mcb = []
    if ok_cells:
        Bmat = np.abs(np.stack([boots[c] for c in ok_cells]))
        for i, c in enumerate(ok_cells):
            others = np.delete(Bmat, i, axis=0).max(axis=0)
            if np.percentile(others - Bmat[i], 5) <= 0:
                mcb.append(c)

    out = {"mcb": mcb, "cells": rec,
           "max_beta": max(rec[c]["41"]["beta"] for c in race),
           "max_abs_beta": max(abs(rec[c]["41"]["beta"]) for c in race)}
    return p, out


def crit_a(rec, c, loro_min):
    r = rec[c]["41"]
    return (not np.isnan(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0)
            and r["loro"] >= loro_min and r["p"] < 0.05)


def crit_b(rec, c, loro_min):
    """screen_part4_stats.py:281-284 -- crit_b CHAINS crit_a and does not re-check LORO on 4.2."""
    r = rec[c]["42"]
    return (crit_a(rec, c, loro_min) and not np.isnan(r["lo"])
            and (r["lo"] > 0 or r["hi"] < 0) and r["p"] < 0.05)


if __name__ == "__main__":
    t0 = time.time()
    with mp.Pool(NPROC, initializer=init) as pool:
        out = {}
        for i, (p, rec) in enumerate(pool.imap_unordered(one_perm, range(N_PERM + 1)), 1):
            out[p] = rec
            if i % 10 == 0 or i == N_PERM + 1:
                el = time.time() - t0
                print(f"  {i}/{N_PERM + 1} perms  {el/60:.1f} min  "
                      f"eta {el/i*(N_PERM+1-i)/60:.1f} min", flush=True)
    json.dump(out, open(OUT, "w"))
    print(f"wrote {OUT}  ({time.time()-t0:.0f}s)")
