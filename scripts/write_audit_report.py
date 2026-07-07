"""Assemble Phase-1.5 audit deliverables: analysis/scorer_audit.parquet + analysis/scorer_audit.md.

Recomputes the core per-scorer stats (variance + raw/partial-LOO + contamination), attaches the
hand-audit + re-screen findings and the final failure category per scorer, and writes both files.
Offline, $0. Never touches logs/phase2/.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.ceiling_probe import CONTROLS
from gepa_si.screen.screen_scorers import KEYS, aggregate_events, batch_frame, loro_partial, screen_scorer

SCORERS_PARQUET = "analysis/scorers.parquet"
BAR = 0.172  # constraint_tractability partial-LOO survival bar

FAILED = [
    "valset_prevalence", "input_typicality", "prevalence_x_headroom", "typicality_x_headroom",
    "parent_near_frontier", "pool_disagreement_voi", "coverage_gap", "coverage_gap_x_prevalence",
    "seed_to_parent_regression", "output_repairability", "output_n_words",
]

# Final categories + findings (from the hand-audit + re-screens; see scorer_audit.md narrative).
# category in {STRUCTURAL-DEAD, DIFFICULTY-COLLAPSE, SPARSITY-ARTIFACT, IMPLEMENTATION-DEFECT, THRESHOLD-SENSITIVE}
JUDGEMENT = {
    "valset_prevalence":        dict(category="DIFFICULTY-COLLAPSE", defect=False, rescreened="—", verdict_changed=False,
        note="raw 0.178->partial 0.049; contam_diff 0.659. Prevalence per se is difficulty-shadowed."),
    "input_typicality":         dict(category="STRUCTURAL-DEAD", defect=False, rescreened="k{3,5,10,20}x{combined,word,char}", verdict_changed=False,
        note="TF-IDF fallback confirmed; swept k+backend, max partial 0.030 (char k20). Embedding choice irrelevant -> robustly dead. Neural embedder untestable offline (low-priority enrichment)."),
    "prevalence_x_headroom":    dict(category="DIFFICULTY-COLLAPSE", defect=False, rescreened="—", verdict_changed=False,
        note="contam_diff 0.666; raw 0.117->partial -0.032. Headroom injected difficulty -> WORSE than clean prevalence (0.049)."),
    "typicality_x_headroom":    dict(category="DIFFICULTY-COLLAPSE", defect=False, rescreened="—", verdict_changed=False,
        note="contam_diff 0.271; raw 0.001->partial -0.060. Headroom term added difficulty to a no-signal base."),
    "parent_near_frontier":     dict(category="DIFFICULTY-COLLAPSE", defect=False, rescreened="—", verdict_changed=False,
        note="raw 0.129->partial -0.014; contam_diff 0.655. Opportunity weighting collapses to difficulty."),
    "pool_disagreement_voi":    dict(category="STRUCTURAL-DEAD", defect=False, rescreened="peakedness-alone", verdict_changed=False,
        note="Full variance (1057 distinct), contam 0.052. partial|peakedness-alone 0.017, |full 0.025. Peakedness IS a control; genuinely no signal, NOT under-credited."),
    "coverage_gap":             dict(category="DIFFICULTY-COLLAPSE", defect=True, rescreened="tightened-kw + embed x5 thr", verdict_changed=False,
        note="Hand-audit: matcher coarse (false-PRESENTs via generic/wrong-direction cues). Re-screen with better matchers: best partial 0.073 (<0.172), LORO unstable; contamination RISES with better matchers (0.48->0.75). Matcher defect real but not the cause -> root cause difficulty. Prompts are generic meta-instructions, so type-coverage is near-constant per type."),
    "coverage_gap_x_prevalence":dict(category="DIFFICULTY-COLLAPSE", defect=True, rescreened="(inherits coverage matcher)", verdict_changed=False,
        note="68% zero (ABSENT-and-high-prevalence intersection is rare). Inherits coverage_gap's matcher; partial 0.017. Correctly dead."),
    "seed_to_parent_regression":dict(category="SPARSITY-ARTIFACT", defect=False, rescreened="n/a (no data)", verdict_changed=False,
        note="99.5% zero at event level; only 6/382 b3 batches nonzero. Where it fires it is CLEAN (contam 0.036). Not a real failure - a data limitation. Revival: dense seed-eval logging (eval the seed on ALL trainset examples) or more runs."),
    "output_repairability":     dict(category="THRESHOLD-SENSITIVE", defect=True, rescreened="composite vs raw n_words", verdict_changed=False,
        note="Arbitrary composite (120-word cap, structure weights). Raw n_words variant (0.061) beats composite (0.035) but both <0.172 and LORO-unstable. Fix doesn't revive."),
    "output_n_words":           dict(category="STRUCTURAL-DEAD", defect=False, rescreened="—", verdict_changed=False,
        note="Cleanest failure: partial 0.061, contam 0.078, but LORO 0.062+-0.113 (unstable) and far below bar. Weak real signal, sub-threshold."),
}


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def compute_rows(b3, events):
    rows = []
    for s in FAILED:
        col = f"{s}_mean"
        sc = screen_scorer(b3, col)
        lo = loro_partial(b3, col, "loo_contribution")
        ev = events[s].to_numpy(); ev = ev[~np.isnan(ev)]
        r = np.round(ev, 6)
        mode_frac = pd.Series(r).value_counts(normalize=True).iloc[0]
        j = JUDGEMENT[s]
        rows.append({
            "scorer": s, "category": j["category"],
            "raw_loo": round(sc["raw_spear_loo"], 3), "partial_loo": round(sc["partial_loo"], 3),
            "drop": round(abs(sc["raw_spear_loo"]) - abs(sc["partial_loo"]), 3),
            "contam_difficulty": round(sc["corr_difficulty"], 3),
            "loro_mean": round(lo["loro_mean"], 3), "loro_sd": round(lo["loro_sd"], 3),
            "ev_frac_zero": round(float((ev == 0).mean()), 3), "ev_mode_frac": round(float(mode_frac), 3),
            "ev_n_distinct": int(len(np.unique(r))),
            "defect_found": j["defect"], "rescreened": j["rescreened"],
            "rescreen_verdict_changed": j["verdict_changed"], "note": j["note"],
        })
    return pd.DataFrame(rows)


def main():
    runs = load_corpus()
    events = pd.read_parquet(SCORERS_PARQUET)
    bf = batch_frame(runs)
    agg = aggregate_events(events, FAILED)
    b3 = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = b3[b3.b == 3]

    tab = compute_rows(b3, events)
    tab.to_parquet("analysis/scorer_audit.parquet", index=False)

    # ---- markdown ----
    correctly_dead = tab[tab.category.isin(["STRUCTURAL-DEAD", "DIFFICULTY-COLLAPSE"])]
    sparsity = tab[tab.category == "SPARSITY-ARTIFACT"]
    fixable_cross = tab[(tab.rescreen_verdict_changed) & (tab.partial_loo.abs() >= BAR)]

    show = ["scorer", "category", "raw_loo", "partial_loo", "drop", "contam_difficulty",
            "loro_mean", "ev_frac_zero", "ev_n_distinct", "defect_found", "rescreen_verdict_changed"]
    md = []
    md.append("# Phase 1.5 — Scorer failure audit\n")
    md.append("Adversarial post-mortem of every failed Phase-1 scorer. Offline, $0 (TF-IDF only, no API). "
              "Target = LOO unique contribution, partial-Spearman residualizing the 4 controls "
              f"{CONTROLS}, b3 pooled. Survival bar (constraint_tractability) = partial-LOO {BAR}, LORO 0.171.\n")
    md.append("## Summary table\n")
    md.append(_md_table(tab[show]))
    md.append("\n## Failure categories\n")
    md.append("- **CORRECTLY DEAD** (structural or difficulty-collapse, not re-screened): "
              f"{len(correctly_dead)} — {', '.join(correctly_dead.scorer)}")
    md.append(f"- **SPARSITY-ARTIFACT** (data limitation, not a real failure): {len(sparsity)} — "
              f"{', '.join(sparsity.scorer)}")
    md.append("- **IMPLEMENTATION-DEFECT / THRESHOLD-SENSITIVE that crosses the bar after a fix**: "
              f"{len(fixable_cross)} — {', '.join(fixable_cross.scorer) if len(fixable_cross) else 'NONE'}")
    md.append("- **Batch scorers (coherent-gap, complementary-SI): NOT BUILT in Phase 1** (only a "
              "docstring note in scorers_wave3.py) — nothing to post-mortem.\n")
    md.append("## Defects found (real, but none revive across the bar)\n")
    md.append("- **coverage_gap matcher** — coarse keyword matcher with false-PRESENTs (generic tokens, "
              "wrong-direction cues). Hand-audit on 16 distinct (prompt,type) pairs + re-screen with "
              "tightened-keyword and TF-IDF-embedding matchers (5 thresholds): best partial-LOO 0.073, "
              "still < bar, LORO unstable, and contamination RISES as the matcher improves. The evolved "
              "system prompts are generic meta-instructions enumerating nearly all constraint categories, "
              "so type-coverage is near-constant per type -> coverage_gap is collinear with type/difficulty. "
              "Root cause = DIFFICULTY-COLLAPSE, not the matcher.")
    md.append("- **output_repairability composite** — arbitrary constants; raw n_words is a better feature "
              "(0.061 vs 0.035) but still sub-bar.\n")
    md.append("## Per-scorer notes\n")
    for _, r in tab.iterrows():
        md.append(f"- **{r.scorer}** [{r.category}] — {r.note}")
    md.append("\n## Bottom line\n")
    md.append(f"Of the 11 built failed scorers: **{len(correctly_dead)} are correctly dead** "
              "(difficulty-collapse or structural — real signal absence), **1 is a sparsity artifact** "
              "(seed_to_parent_regression: clean where it fires but ~99% degenerate; a data limitation, "
              "revivable only by denser seed-eval logging or more runs), and **0 cross the survival bar "
              "after a legitimate fix**. Two real defects exist (coverage_gap matcher; output_repairability "
              "composite) but fixing them does not revive either scorer. ")
    md.append("**constraint_tractability remains the sole Phase-2 candidate.** No failed scorer is "
              "rescued. The one worth revisiting *if the corpus changes* is seed_to_parent_regression — "
              "it failed for lack of data, not lack of signal.")

    with open("analysis/scorer_audit.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")

    print("wrote analysis/scorer_audit.parquet + analysis/scorer_audit.md")
    print("\n=== SUMMARY TABLE ===")
    print(tab[show].to_string(index=False))
    print(f"\ncorrectly dead: {len(correctly_dead)}  sparsity: {len(sparsity)}  "
          f"fixable-crosses-bar: {len(fixable_cross)}")


if __name__ == "__main__":
    main()
