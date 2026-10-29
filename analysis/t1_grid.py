"""
T1 grid sweep: run srs_model.run() across the URECA parameter grid and save one CSV.

Put this file in `analysis/` inside the repo, then run from the repo root:
    python analysis/t1_grid.py

It does NOT modify srs_model.py. Output: analysis/t1_grid.csv (one row per scenario).
Exits with status 1, and leaves any existing CSV untouched, if a validation check fails.

Two decision units, kept separate and labelled (CLAUDE.md pitfall #1):

  BLOCK (whole annual contribution)
    block_relief_rate   average tax saving across the full contribution: relief / contribution
    block_advantage     endA - endB from run(): the incremental advantage of contributing the
                        whole block versus investing the same out-of-pocket cash outside SRS
    block_srs_wins      block_advantage > 0
    srs_irr             return on the SRS route's out-of-pocket outlays, measured to the same
                        end date as endA. The non-SRS IRR is r by construction (no tax drag in
                        SG), so srs_irr > r  <=>  block_advantage > 0.

  NEXT DOLLAR (one more dollar on top of the block)
    marginal_relief_rate     tax saved by deducting one more dollar: the rate on the band just
                             below (chargeable - contribution). At an exact band edge the next
                             dollar deducted comes off the LOWER band.
    marginal_exit_rate       tax rate on the next dollar of the taxable half withdrawn. At an
                             exact band edge the next dollar withdrawn lands in the UPPER band.
    next_dollar_breakeven_tc 0.5 x marginal_exit_rate
    next_dollar_srs_wins     marginal_relief_rate > next_dollar_breakeven_tc

Never compare block_relief_rate with next_dollar_breakeven_tc: they answer different questions.
"""
import csv
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))  # repo root, so srs_model imports
import srs_model as m

# --- grid (edit here) -------------------------------------------------------------
# Chargeable incomes chosen so a $5,000 contribution earns relief wholly inside each band,
# 0% up to 24%. validate_band_coverage() asserts this, so edit the list with care.
CHARGEABLE = [20_000, 30_000, 35_000, 45_000, 60_000, 100_000, 140_000, 180_000,
              220_000, 260_000, 300_000, 400_000, 700_000, 1_200_000]
RETURNS = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]
HORIZONS = [10, 15, 20, 25, 30, 35, 40]          # contribution years
CONTRIBUTIONS = [5_000, 10_000, m.CAP_CITIZEN]    # add m.CAP_FOREIGN for the foreigner map
DRAW_YEARS = [1, 5, 10]                           # withdrawal smoothing
OTHER_INCOME = [0, 30_000]                        # taxable retirement income (NOT CPF LIFE)
STRATEGY = "level"

COVERAGE_CONTRIBUTION = 5_000      # band-coverage check is defined on this contribution size
BASE_CASE_EXPECTED = 152_557       # docs/findings.md, CLAUDE.md pitfall #7
BASE_CASE_TOLERANCE = 1.0          # dollars
OUT_PATH = os.path.join(HERE, "t1_grid.csv")


# --- next-dollar rates with explicit edge conventions -------------------------------
def next_withdrawal_rate(taxable_income, brackets=None):
    """Rate on the next dollar ADDED to taxable_income. At an exact band edge, returns the
    upper band's rate (srs_model.marginal_rate returns the lower one, which understates it)."""
    brackets = brackets or m.BRACKETS
    for upper, rate in brackets:
        if taxable_income < upper:
            return rate
    return brackets[-1][1]


def next_relief_rate(chargeable_after, brackets=None):
    """Tax saved by deducting one more dollar from chargeable_after. At an exact band edge the
    dollar comes off the lower band, which is srs_model.marginal_rate's convention."""
    if chargeable_after <= 0:
        return 0.0
    return m.marginal_rate(chargeable_after, brackets)


# --- IRR ----------------------------------------------------------------------------
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


# --- build ------------------------------------------------------------------------------
def build_rows():
    rows = []
    for c, r, n, k, d, oi in itertools.product(CHARGEABLE, RETURNS, HORIZONS,
                                               CONTRIBUTIONS, DRAW_YEARS, OTHER_INCOME):
        if k > c:  # cannot deduct more than chargeable income
            continue
        res = m.run(chargeable=c, contribution=k, r=r, contrib_years=n, draw_years=d,
                    other_retirement_income=oi, strategy=STRATEGY)
        pot = res["srs_at_retirement"]
        taxable_half = m.INCLUSION * m.level_payment(pot, r, d) + oi
        mer = next_withdrawal_rate(taxable_half)
        mrr = next_relief_rate(c - k)
        be = m.INCLUSION * mer
        rows.append({
            "chargeable": c, "contribution": k, "r": r, "contrib_years": n,
            "draw_years": d, "other_income": oi,
            "pot_at_retirement": round(pot, 2),
            # block decision unit
            "block_relief_rate": round(res["relief_rate"], 6),
            "average_exit_rate": round(res["average_exit_rate"], 6),
            "endA_srs": round(res["endA"], 2),
            "endB_ordinary": round(res["endB"], 2),
            "block_advantage": round(res["advantage"], 2),
            "block_advantage_pct": round(res["advantage_pct"], 6),
            "block_srs_wins": int(res["advantage"] > 0),
            "srs_irr": srs_irr(res["out_of_pocket"], n, d, res["endA"]),
            "ordinary_irr": r,
            # next-dollar decision unit
            "marginal_relief_rate": mrr,
            "marginal_exit_rate": mer,
            "next_dollar_breakeven_tc": be,
            "next_dollar_srs_wins": int(mrr > be),
        })
    return rows


# --- validation -------------------------------------------------------------------------
def validate(rows):
    """Return a list of failure messages (empty list = all checks pass)."""
    failures = []

    # 1. IRR rule and block advantage sign agree on every row.
    bad = [x for x in rows if x["srs_irr"] is not None and abs(x["block_advantage"]) > 1e-6
           and (x["srs_irr"] > x["r"]) != (x["block_advantage"] > 0)]
    if bad:
        failures.append(f"IRR vs advantage sign: {len(bad)} mismatches")

    # 2. Base case reproduces docs/findings.md.
    adv = m.run()["advantage"]
    if abs(adv - BASE_CASE_EXPECTED) > BASE_CASE_TOLERANCE:
        failures.append(f"base case advantage ${adv:,.2f}, expected ${BASE_CASE_EXPECTED:,}")

    # 3. Every tax band is sampled with relief earned wholly inside it.
    band_rates = sorted({rate for _, rate in m.BRACKETS})
    seen = {round(x["block_relief_rate"], 6) for x in rows
            if x["contribution"] == COVERAGE_CONTRIBUTION}
    missing = [rt for rt in band_rates if round(rt, 6) not in seen]
    if missing:
        failures.append("bands with no whole-band relief scenario at "
                        f"${COVERAGE_CONTRIBUTION:,}: " + ", ".join(f"{x:.1%}" for x in missing))

    # 4. Edge conventions behave as documented.
    if next_withdrawal_rate(20_000) <= m.marginal_rate(20_000):
        failures.append("next_withdrawal_rate does not move to the upper band at an exact edge")
    return failures


# --- write ------------------------------------------------------------------------------
def write_csv_atomic(rows, path):
    """Write to a temp file in the same folder, then swap it in, so an interrupted or failed
    write never leaves a partial CSV or destroys the last complete one."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    rows = build_rows()
    failures = validate(rows)
    if failures:
        for msg in failures:
            print("CHECK FAILED:", msg, file=sys.stderr)
        print("CSV not written; existing output left untouched.", file=sys.stderr)
        sys.exit(1)
    write_csv_atomic(rows, OUT_PATH)
    print(f"all checks passed; wrote {len(rows):,} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()