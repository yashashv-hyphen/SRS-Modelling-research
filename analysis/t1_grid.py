"""
T1 grid sweep: run srs_model.run() across the URECA parameter grid and save one CSV.

Put this file in a new folder `analysis/` inside the repo, then run from the repo root:
    python analysis/t1_grid.py

It does NOT modify srs_model.py. Output: analysis/t1_grid.csv (one row per scenario).

Columns added on top of run():
  marginal_exit_rate  rate on the next withdrawn dollar (participation decision)
  breakeven_tc        0.5 x marginal_exit_rate; SRS adds value on the next dollar if relief_rate > this
  srs_irr             annual return on the SRS route's out-of-pocket outlays, measured to the same
                      end date as endA. The non-SRS IRR is r by construction (no tax drag in SG),
                      so srs_irr > r  <=>  advantage > 0.
"""
import csv
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root, so srs_model imports
import srs_model as m

# --- grid (edit here) -------------------------------------------------------------
# Chargeable incomes chosen so the relief rate lands in each band, 0% up to 24%.
CHARGEABLE = [20_000, 35_000, 60_000, 100_000, 140_000, 180_000, 220_000,
              260_000, 300_000, 400_000, 700_000, 1_200_000]
RETURNS = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
HORIZONS = [10, 15, 20, 25, 30, 35, 40]          # contribution years
CONTRIBUTIONS = [5_000, 10_000, m.CAP_CITIZEN]    # add m.CAP_FOREIGN for the foreigner map
DRAW_YEARS = [1, 5, 10]                           # withdrawal smoothing
OTHER_INCOME = [0, 30_000]                        # taxable retirement income (NOT CPF LIFE)
STRATEGY = "level"


def srs_irr(outlay, contrib_years, draw_years, end_value):
    """Solve x: FV of `outlay` paid each year for contrib_years, grown to the end of the
    drawdown window, equals end_value. Bisection; returns None if no outlay."""
    if outlay <= 0:
        return None

    def gap(x):
        return m.fv_annuity(outlay, x, contrib_years) * (1 + x) ** draw_years - end_value

    lo, hi = -0.5, 1.0
    if gap(lo) > 0 or gap(hi) < 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if gap(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def main():
    rows = []
    for c, r, n, k, d, oi in itertools.product(CHARGEABLE, RETURNS, HORIZONS,
                                               CONTRIBUTIONS, DRAW_YEARS, OTHER_INCOME):
        if k > c:  # cannot deduct more than chargeable income
            continue
        res = m.run(chargeable=c, contribution=k, r=r, contrib_years=n, draw_years=d,
                    other_retirement_income=oi, strategy=STRATEGY)
        pot = res["srs_at_retirement"]
        mer = m.marginal_exit_rate(pot, r=r, years=d, other_income=oi)
        rows.append({
            "chargeable": c, "contribution": k, "r": r, "contrib_years": n,
            "draw_years": d, "other_income": oi,
            "relief_rate": round(res["relief_rate"], 6),
            "pot_at_retirement": round(pot, 2),
            "average_exit_rate": round(res["average_exit_rate"], 6),
            "marginal_exit_rate": mer,
            "breakeven_tc": m.INCLUSION * mer,
            "endA_srs": round(res["endA"], 2),
            "endB_ordinary": round(res["endB"], 2),
            "advantage": round(res["advantage"], 2),
            "advantage_pct": round(res["advantage_pct"], 6),
            "srs_irr": srs_irr(res["out_of_pocket"], n, d, res["endA"]),
            "ordinary_irr": r,
        })

    out = os.path.join(HERE, "t1_grid.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows):,} rows to {out}")

    # Sanity check: the IRR rule and the advantage sign must agree on every row.
    bad = [x for x in rows if x["srs_irr"] is not None
           and (x["srs_irr"] > x["r"]) != (x["advantage"] > 0) and abs(x["advantage"]) > 1e-6]
    print("IRR vs advantage sign check:", "OK" if not bad else f"{len(bad)} mismatches")

    # Reproduce the repo's base case (docs/findings.md): advantage should be ~ $152,557.
    base = m.run()
    print(f"base case advantage: ${base['advantage']:,.0f} (expect ~$152,557)")


if __name__ == "__main__":
    main()