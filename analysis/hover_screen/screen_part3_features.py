"""HoVer heterogeneity screen — Part 3 feature extraction. $0, read-only on frozen dirs.

Implements spec.md EXACTLY (spec written and frozen before this ran; every definition,
censoring rule and NaN code lives there). One row per event (243) -> features.csv.
No outcome column is read or joined here.

Run: analysis/hover_screen/.venv-screen/bin/python analysis/hover_screen/screen_part3_features.py
"""
from __future__ import annotations

import ast
import collections
import json
import os
import re
import sys
import zlib

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen_part0 import parse_si, PAIRS, STAGE1  # noqa: E402
from screen_part2 import FEEDBACK_RE  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(REPO, "analysis", "hover_screen")
K_CAP = 1000
CENSOR = K_CAP + 1

try:
    from sentence_transformers import SentenceTransformer
    _ST = SentenceTransformer("all-MiniLM-L6-v2")
    HAVE_EMB = True
except Exception as e:  # noqa: BLE001
    _ST = None
    HAVE_EMB = False
    print(f"[embedding variant OFF: {type(e).__name__}: {e}]")


def agg(vals, prefix, with_n=True):
    """spec item 6: mean/max/min/std (ddof=0) over non-NaN example values, + coverage _n."""
    v = np.array([x for x in vals if x is not None and not (isinstance(x, float) and np.isnan(x))],
                 dtype=float)
    out = {}
    if len(v):
        out[f"{prefix}_mean"] = float(v.mean())
        out[f"{prefix}_max"] = float(v.max())
        out[f"{prefix}_min"] = float(v.min())
        out[f"{prefix}_std"] = float(v.std(ddof=0))
    else:
        out.update({f"{prefix}_{s}": np.nan for s in ("mean", "max", "min", "std")})
    if with_n:
        out[f"{prefix}_n"] = int(len(v))
    return out


def tfidf_pair(corpus):
    """spec item 4: word 1-2 gram + char_wb 3-5 gram TfidfVectorizers, sublinear_tf."""
    vw = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
    vc = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    return vw.fit(corpus), vc.fit(corpus)


def pair_sims(vw, vc, queries, refs):
    """Mean of word- and char-vectorizer cosine sims, shape (n_queries, n_refs)."""
    sw = cosine_similarity(vw.transform(queries), vw.transform(refs))
    sc = cosine_similarity(vc.transform(queries), vc.transform(refs))
    return (sw + sc) / 2.0


def C(b: bytes) -> int:
    return len(zlib.compress(b, 9))


def ncd(x: str, y: str) -> float:
    bx, by = x.encode("utf-8"), y.encode("utf-8")
    cx, cy = C(bx), C(by)
    cyx = C(by + bx)  # archive-then-current (spec item; 32KB-window caveat documented)
    return (cyx - min(cx, cy)) / max(cx, cy)


def main():
    ev_index = json.load(open(os.path.join(OUTDIR, "events_index.json")))
    manifest = json.load(open(os.path.join(STAGE1, "stage1_seed0", "trainset_manifest.json")))
    graded = {r["threehop_idx"]: r for r in
              (json.loads(l) for l in open(os.path.join(STAGE1, "graded_records.jsonl")))}
    train_ids = manifest["train_threehop_ids"]
    train_recs = [graded[t] for t in train_ids]
    val_gold = collections.Counter(t for tid in manifest["val_threehop_ids"]
                                   for t in graded[tid]["gold"])
    ranks = pd.read_csv(os.path.join(OUTDIR, "bm25_ranks.csv"))
    rank_of = {(r.split, r.pos, r.title): (r.rank if r.rank > 0 else CENSOR)
               for r in ranks.itertuples()}
    censored = {(r.split, r.pos, r.title): r.rank < 0 for r in ranks.itertuples()}
    gres = {s: json.load(open(os.path.join(STAGE1, f"stage1_seed{s}", "gepa_result.json")))
            for s in range(8)}
    metas = {pid: json.load(open(os.path.join(PAIRS, pid, "meta.json")))
             for pid in sorted(os.listdir(PAIRS))}

    # ---------- static: representativeness over the 100 shared trainset claims ----------
    claims = [r["claim"] for r in train_recs]
    vw, vc = tfidf_pair(claims)
    sims = pair_sims(vw, vc, claims, claims)
    np.fill_diagonal(sims, np.nan)
    repr_static = np.nanmean(sims, axis=1)  # pos -> representativeness

    # ---------- parse all SI blocks once; embed once if available ----------
    blocks_by_pid = {}
    for pid in sorted(os.listdir(PAIRS)):
        text = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        blocks_by_pid[pid] = parse_si(text, pid)

    def variant_texts(blk):
        fb = blk["Feedback"]
        full = blk["Inputs"] + "\n" + blk["Generated Outputs"] + "\n" + blk["Feedback"]
        return fb, full

    emb = {}
    if HAVE_EMB:
        keys, texts = [], []
        for pid, blks in blocks_by_pid.items():
            for j, blk in enumerate(blks):
                fb, full = variant_texts(blk)
                keys += [(pid, j, "fb"), (pid, j, "full")]
                texts += [fb, full]
        M = _ST.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
        emb = {k: M[i] for i, k in enumerate(keys)}
        print(f"[embedded {len(texts)} block texts, dim {M.shape[1]}]")

    # ---------- per-run chronological loop ----------
    out_rows = []
    for seed in range(8):
        evs = sorted([e for k, e in ev_index.items() if e["seed"] == seed],
                     key=lambda e: e["ordinal"])
        pool = collections.defaultdict(list)      # pos -> [(ordinal, score, kind)]
        visits = collections.defaultdict(list)    # pos -> [ordinal]
        arch_items = {"fb": [], "full": []}       # per-example archive texts, ordinal order
        arch_concat_len = None                    # rebuilt per event from arch_items
        arch_emb = {"fb": [], "full": []}
        sig_archive = set()
        pair_archive = set()
        subs = gres[seed]["prog_candidate_val_subscores"]

        for ev in evs:
            pid = f"seed{seed}_i{ev['trace_i']}"
            o = ev["ordinal"]
            blks = blocks_by_pid[pid]
            meta = metas[pid]
            row = dict(pair_id=pid, seed=seed, trace_i=ev["trace_i"], event_ordinal=o,
                       iteration=o, comp=meta["comp"],
                       parent_candidate_idx=meta["parent_candidate_idx"],
                       parent_pool_score=float(np.mean(list(subs[meta["parent_candidate_idx"]].values()))),
                       accept=int(ev["accept"]))

            # ----- per-example Class A -----
            f = collections.defaultdict(list)
            for slot in range(3):
                pos = ev["subsample_ids"][slot]
                rec = graded[train_ids[pos]]
                prior = [s for (po, s, _) in pool[pos]]
                f["diffbest"].append(1 - max(prior) if prior else np.nan)
                f["diffmean"].append(1 - float(np.mean(prior)) if prior else np.nan)
                sbar = float(np.mean(prior)) if prior else np.nan
                f["peaked"].append(sbar * (1 - sbar) if prior else np.nan)
                f["stale"].append(o - visits[pos][-1] if visits[pos] else o + 1)
                f["visits"].append(len(visits[pos]))
                f["diffbase"].append(1 - rec["recall"])
                f["ctok"].append(len(rec["claim"].split()))
                f["ngold"].append(len(rec["gold"]))
                rk = [rank_of[("train", pos, t)] for t in rec["gold"]]
                f["hardworst"].append(-np.log10(max(rk)))
                f["hardmean"].append(float(np.mean([-np.log10(r) for r in rk])))
                f["_cens"].append(sum(censored[("train", pos, t)] for t in rec["gold"]))
                f["repr"].append(float(repr_static[pos]))
                vt = sum(val_gold[t] for t in rec["gold"])
                f["vt_count"].append(vt)
                f["vt_any"].append(int(vt > 0))

                # forgetting (spec 17)
                if visits[pos]:
                    events_at = collections.defaultdict(dict)
                    for (po, s, kind) in pool[pos]:
                        events_at[po][kind] = s
                    improvements = []
                    prev_max = None
                    for po in sorted(events_at):
                        d = events_at[po]
                        if "child" in d and "parent" in d and d["child"] > d["parent"]:
                            improvements.append(d["child"])
                        m = max(d.values())
                        if prev_max is not None and m > prev_max:
                            improvements.append(m)
                        prev_max = m if prev_max is None else max(prev_max, m)
                    cur_parent = ev["subsample_scores"][slot]
                    f["forget"].append(int(bool(improvements) and max(improvements) > cur_parent))
                else:
                    f["forget"].append(np.nan)

            # ----- per-example Class B -----
            n_arch = len(arch_items["fb"])
            fits = {}
            if n_arch >= 1:
                for var in ("fb", "full"):
                    fits[var] = tfidf_pair(arch_items[var])
            knn = {v: [] for v in ("fb", "full")}
            knn_e = {v: [] for v in ("fb", "full")}
            ncdv = {v: [] for v in ("fb", "full")}
            act = {v: [] for v in ("fb", "full", "delta")}
            fm = []
            signov, fix, cofail = [], [], []
            cur_sigs, cur_pairs_all = [], []
            comp_is_query = meta["comp"] == "gen_query.predict"

            for slot, blk in enumerate(blks):
                pos = ev["subsample_ids"][slot]
                rec = graded[train_ids[pos]]
                fb_t, full_t = variant_texts(blk)
                m = FEEDBACK_RE.search(blk["Feedback"])
                correct = ast.literal_eval(m.group(3))
                missed = ast.literal_eval(m.group(4))
                io_text = (blk["Inputs"] + "\n" + blk["Generated Outputs"]).lower()

                # 9/10: novelty vs archive
                for var, txt in (("fb", fb_t), ("full", full_t)):
                    if n_arch >= 3:
                        s = pair_sims(*fits[var], [txt], arch_items[var])[0]
                        knn[var].append(float(np.mean(1 - np.sort(s)[-3:])))
                    else:
                        knn[var].append(np.nan)
                    if n_arch >= 1:
                        ncdv[var].append(ncd(txt, "\n\n".join(arch_items[var])))
                    else:
                        ncdv[var].append(np.nan)
                    if HAVE_EMB:
                        if n_arch >= 3:
                            A = np.stack(arch_emb[var])
                            s = A @ emb[(pid, slot, var)]
                            knn_e[var].append(float(np.mean(1 - np.sort(s)[-3:])))
                        else:
                            knn_e[var].append(np.nan)

                # 11: actionability (frozen re-instantiation)
                c1 = len(missed) / len(rec["gold"])
                c2 = int(len(correct) > 0 and len(missed) > 0)
                c3 = (float(np.mean([t.lower() in io_text for t in missed]))
                      if missed else np.nan)
                act["fb"].append((c1 + c2) / 2)
                act["full"].append((c1 + c2 + c3) / 3 if not np.isnan(c3) else np.nan)
                act["delta"].append(c3)

                # 13: failure mode
                gen = blk["Generated Outputs"]
                secs = dict(zip(re.findall(r"^### (\w+)$", gen, re.MULTILINE),
                                [s.strip() for s in re.split(r"^### \w+$", gen, flags=re.MULTILINE)[1:]]))
                if not missed:
                    fm.append("F0")
                else:
                    if comp_is_query:
                        malformed = len(secs.get("query", "").split()) < 5
                    else:
                        malformed = (secs.get("new_notes", "").strip() in ("", "[]")
                                     or secs.get("titles", "").strip() in ("", "[]"))
                    if malformed:
                        fm.append("F1")
                    elif all(t.lower() in io_text for t in missed):
                        fm.append("F3")
                    else:
                        fm.append("F2")

                # 14/15/16
                sig = tuple(sorted(missed))
                cur_sigs.append(sig)
                signov.append(np.nan if not missed else int(sig not in sig_archive))
                if missed:
                    best = min(rank_of[("train", pos, t)] for t in missed)
                    fix.append(-np.log10(best))
                else:
                    fix.append(np.nan)
                if len(missed) >= 2:
                    prs = {tuple(sorted(p)) for p in
                           [(a, b) for i, a in enumerate(missed) for b in missed[i + 1:]]}
                    cur_pairs_all.append(prs)
                    cofail.append(float(np.mean([p in pair_archive for p in prs])))
                else:
                    cur_pairs_all.append(set())
                    cofail.append(np.nan)

            # ----- assemble row -----
            for name in ("diffbest", "diffmean", "peaked", "stale", "visits", "forget"):
                row.update(agg(f[name], name))
            for name in ("diffbase", "ctok", "ngold", "hardworst", "hardmean",
                         "repr", "vt_count", "vt_any"):
                row.update(agg(f[name], name, with_n=False))
            row["stale_never_share"] = float(np.mean([v == 0 for v in f["visits"]]))
            row["hard_censored_n"] = int(sum(f["_cens"]))

            for var in ("fb", "full"):
                row.update(agg(knn[var], f"knn_{var}", with_n=False))
                row.update(agg(ncdv[var], f"ncd_{var}", with_n=False))
            row.update(agg([a - b for a, b in zip(knn["full"], knn["fb"])], "knn_delta", with_n=False))
            row.update(agg([a - b for a, b in zip(ncdv["full"], ncdv["fb"])], "ncd_delta", with_n=False))
            for var in ("fb", "full", "delta"):
                row.update(agg(act[var], f"act_{var}", with_n=(var != "fb")))
            for var in ("fb", "full", "delta"):
                a_ = act[var]
                k_ = (knn[var] if var != "delta"
                      else [x - y for x, y in zip(knn["full"], knn["fb"])])
                row.update(agg([k * v for k, v in zip(k_, a_)], f"nxa_{var}", with_n=False))
            if HAVE_EMB:
                row.update(agg(knn_e["fb"], "knn_emb_fb", with_n=False))
                row.update(agg(knn_e["full"], "knn_emb_full", with_n=False))
                ked = [a - b for a, b in zip(knn_e["full"], knn_e["fb"])]
                row.update(agg(ked, "knn_emb_delta", with_n=False))
                for var, k_ in (("fb", knn_e["fb"]), ("full", knn_e["full"]), ("delta", ked)):
                    row.update(agg([k * v for k, v in zip(k_, act[var])],
                                   f"nxa_emb_{var}", with_n=False))
            for lab in ("F1", "F2", "F3"):
                row[f"fm_{lab.lower()}_share"] = float(np.mean([x == lab for x in fm]))
            row.update(agg(signov, "signov"))
            row.update(agg(fix, "fix"))
            row.update(agg(cofail, "cofail"))
            out_rows.append(row)

            # ----- advance archives (STRICTLY after computing this event) -----
            for slot, blk in enumerate(blks):
                pos = ev["subsample_ids"][slot]
                pool[pos].append((o, ev["subsample_scores"][slot], "parent"))
                pool[pos].append((o, ev["new_subsample_scores"][slot], "child"))
                visits[pos].append(o)
                fb_t, full_t = variant_texts(blk)
                arch_items["fb"].append(fb_t)
                arch_items["full"].append(full_t)
                if HAVE_EMB:
                    arch_emb["fb"].append(emb[(pid, slot, "fb")])
                    arch_emb["full"].append(emb[(pid, slot, "full")])
                sig_archive.add(cur_sigs[slot])
                pair_archive |= cur_pairs_all[slot]
        print(f"seed{seed}: {len(evs)} events done")

    df = pd.DataFrame(out_rows)
    assert len(df) == 243, len(df)
    per_seed = df.groupby("seed").size().to_dict()
    assert per_seed == {0: 32, 1: 34, 2: 28, 3: 33, 4: 27, 5: 34, 6: 28, 7: 27}, per_seed
    df.to_csv(os.path.join(OUTDIR, "features.csv"), index=False)
    print(f"[wrote features.csv] {df.shape[0]} rows x {df.shape[1]} cols; "
          f"embedding variant: {'ON' if HAVE_EMB else 'OFF'}")
    # coverage / degeneracy report (numbers only)
    nn = df.notna().mean().sort_values()
    print("\nlowest-coverage columns (share non-NaN):")
    print(nn[nn < 1.0].head(20).to_string())
    const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    print(f"\nconstant columns: {const}")


if __name__ == "__main__":
    main()
