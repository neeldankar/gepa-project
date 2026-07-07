"""Task 2 — provenance of the 0.382 lottery figure ($0, reads calls.csv only).

Reproduces the within-arm accept-disagreement statistic exactly as coded in
scripts/batch_swap_v2_analysis.py:73-77 (accept = margin_on_B > 0 for BOTH arms;
disagreement = non-unanimity of accept across the 3 draws in each (pair,arm) cell;
mean over cells, n=764), and the own-margin sum-margin variants (>0, >=0).

    HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/verify_task2_lottery.py
"""
from __future__ import annotations

import collections
import csv

OUT = "analysis/ablation/batch_swap_v2"


def load():
    rows = list(csv.DictReader(open(f"{OUT}/calls.csv")))
    by_pair = collections.defaultdict(list)
    for r in rows:
        by_pair[r["B_id"]].append(r)
    return by_pair


def disagreement(by_pair, accept_of_row):
    """Mean over (pair,arm) cells (>=2 draws) of non-unanimity indicator of accept."""
    dis = []
    for pid, rs in by_pair.items():
        for arm in ("R_B", "R_Bp"):
            acc = [accept_of_row(r, arm) for r in rs if r["arm"] == arm]
            if len(acc) >= 2:
                dis.append(0 if len(set(acc)) == 1 else 1)
    return sum(dis) / len(dis), len(dis)


def match(name, got, ref, dp=4):
    verdict = "MATCH" if round(got, dp) == round(ref, dp) else "MISMATCH"
    print(f"  {name}: got={got:.4f} ref={ref:.4f} -> {verdict}")
    return verdict


def main():
    by_pair = load()

    # ---- coded lottery: margin_on_B > 0 for BOTH arms ----
    coded, n = disagreement(by_pair, lambda r, arm: float(r["margin_on_B"]) > 0)
    print(f"[coded lottery] margin_on_B>0 both arms, n={n} cells")
    match("coded disagreement (0.382)", coded, 0.382, dp=3)
    print(f"  4dp value: {coded:.4f}")

    # ---- own-margin variants ----
    def own(r, arm):
        return float(r["margin_on_B"]) if arm == "R_B" else float(r["margin_on_Bp"])

    own_gt, n1 = disagreement(by_pair, lambda r, arm: own(r, arm) > 0)
    own_ge, n2 = disagreement(by_pair, lambda r, arm: own(r, arm) >= 0)
    print(f"\n[own-margin variants] own = margin_on_B (R_B) / margin_on_Bp (R_Bp), n={n1} cells")
    match("own-margin >0  (ref 0.4149)", own_gt, 0.4149)
    match("own-margin >=0 (ref 0.3979)", own_ge, 0.3979)

    # also: coded rule with >=0 (margin_on_B>=0 both arms), for completeness
    coded_ge, _ = disagreement(by_pair, lambda r, arm: float(r["margin_on_B"]) >= 0)
    print(f"\n[reference-only] coded rule margin_on_B>=0 both arms: {coded_ge:.4f}")


if __name__ == "__main__":
    main()
