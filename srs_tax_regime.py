"""
SRS tax-regime model (Model 3, URECA NBS26004) — extends srs_model.py / srs_simulation.py,
modifies neither.

Resolves the historical-foundation half of docs/open-tasks.md T4: "Look at historical personal
income tax policies (the brackets) in Singapore. Project the changes into the future." Does NOT
attempt the inflation/GDP correlation extension (Oxford Economics / SingStat / BIS) — that stays
open, see docs/open-tasks.md.

Data: data/tax_brackets_historical.json, six real IRAS resident-rate schedules (YA2003, 2006,
2007, 2012, 2017, 2024) from the Data.gov.sg / IRAS open dataset "Tax Rates for Individual Income
Tax" (resource_id d_f73055c69144d2e7734c28811d3982aa) — see that file for the full citation and
confidence note. This is a real historical series, not a hypothetical scenario.

Three empirical facts drive everything below (see `calibration_facts`):
  1. The $20,000 / $30,000 / $40,000 / $80,000 band thresholds have not moved once in 21+ years
     (YA2003-2024). Nominal bracket creep (srs_simulation.bracket_creep_income) already models
     this correctly — it is the observed pattern, not an assumption needing supervisor sign-off.
  2. Since the schedule settled in YA2007, there have been exactly three revisions (YA2012,
     YA2017, YA2024), averaging one every ~5.7 years.
  3. Revisions change RATES, not thresholds, and the top band rose exactly 4 percentage points
     over the 17 years from YA2007 (20%) to YA2024 (24%) — 0pp in 2012, +2pp in 2017, +2pp in
     2024. That is simultaneously the input to the discrete-jump projection (jumps of +1.33pp
     every 5.7 years) and the smooth projection (+0.235pp/year, the same long-run total, arriving
     continuously instead of in lumps) — the two scenarios are calibrated to agree on magnitude
     and differ only on lumpy-vs-continuous, which is the actual question in task T4.

Everything below works in the same plain-numbers-in/out style as the rest of the project and
returns brackets in the (upper, rate) tuple form srs_model.py already consumes via its
`brackets=` argument.
"""
import json
import os

import srs_model as m
import srs_simulation as sim

_HERE = os.path.dirname(os.path.abspath(__file__))
_HISTORICAL_PATH = os.path.join(_HERE, "data", "tax_brackets_historical.json")

ANCHOR_YA = 2007  # first YA of the multi-year-stable schedule; 2003/2006 were the tail end of
                   # an earlier phased cut and aren't representative of a steady-state regime


def load_historical(path=_HISTORICAL_PATH):
    """Real IRAS resident-rate schedules by Year of Assessment. See the JSON file's "source"
    field for the citation; each entry's brackets use the same (upper, rate) shape as
    srs_model.BRACKETS, loaded here the same way srs_model.load_brackets() does."""
    with open(path) as f:
        raw = json.load(f)["history"]
    out = []
    for entry in raw:
        brackets = [(float("inf") if u is None else float(u), float(r)) for u, r in entry["brackets"]]
        out.append({"ya": entry["year_of_assessment"], "effective_through": entry["effective_through"],
                    "brackets": brackets})
    return out


HISTORY = load_historical()


def calibration_facts(history=None, anchor_ya=ANCHOR_YA):
    """
    Empirical facts from HISTORY, anchored at `anchor_ya` onward (see module docstring for why
    2003/2006 are excluded). Returns the three facts used by project_discrete/project_smooth.
    """
    history = history or HISTORY
    anchored = [h for h in history if h["ya"] >= anchor_ya]
    yas = [h["ya"] for h in anchored]
    intervals = [b - a for a, b in zip(yas[:-1], yas[1:])]
    top_rates = [h["brackets"][-1][1] for h in anchored]
    steps = [b - a for a, b in zip(top_rates[:-1], top_rates[1:])]
    total_years = yas[-1] - yas[0]
    thresholds_frozen = all(
        [u for u, _ in h["brackets"][:4]] == [20000.0, 30000.0, 40000.0, 80000.0] for h in history
    )
    return {
        "anchor_ya": anchor_ya,
        "revision_yas": yas[1:],
        "avg_interval_years": sum(intervals) / len(intervals),
        "top_rate_steps": steps,
        "avg_step_per_revision": sum(steps) / len(steps),
        "smooth_drift_per_year": (top_rates[-1] - top_rates[0]) / total_years,
        "thresholds_frozen_since_ya": history[0]["ya"] if thresholds_frozen else None,
    }


FACTS = calibration_facts()


# ----------------------------------------------------------------- 50-year forward projections
def project_discrete(years=50, start_brackets=None, avg_interval=None, avg_step=None):
    """
    Simplest discrete-jump projection: starting from today's brackets (YA2026, identical to the
    YA2024 schedule), a revision lands every `avg_interval` years (default: the real historical
    average since YA2007) and shifts every band's rate by `avg_step` (default: the real
    historical average per revision). Thresholds never move, matching 21+ years of history.
    Returns {year_index: brackets} for year_index 0..years inclusive, year_index 0 = today.
    """
    avg_interval = FACTS["avg_interval_years"] if avg_interval is None else avg_interval
    avg_step = FACTS["avg_step_per_revision"] if avg_step is None else avg_step
    base = list(start_brackets) if start_brackets else list(m.BRACKETS)
    path = {0: base}
    shift, next_revision = 0.0, avg_interval
    for y in range(1, years + 1):
        if y >= next_revision:
            shift += avg_step
            next_revision += avg_interval
        path[y] = sim.shifted_brackets(base, shift)
    return path


def project_smooth(years=50, start_brackets=None, drift_per_year=None):
    """
    Simplest smooth alternative: every band's rate drifts by `drift_per_year` (default: the real
    historical average, calibrated so this scenario's total 50-year drift matches
    project_discrete's) continuously instead of in lumps.
    """
    drift_per_year = FACTS["smooth_drift_per_year"] if drift_per_year is None else drift_per_year
    base = list(start_brackets) if start_brackets else list(m.BRACKETS)
    path = {0: base}
    for y in range(1, years + 1):
        path[y] = sim.shifted_brackets(base, drift_per_year * y)
    return path


# --------------------------------------------------------- frontier-shift demo (the deliverable)
def historical_frontier(relief_rates=(0.07, 0.115), r=0.05, draw_years=10):
    """How the real T1 participation crossover (docs/findings.md #7) actually moved across the
    six real historical schedules. `None` = no crossover at any pot size (the relief rate beats
    breakeven everywhere)."""
    return [
        {"year_of_assessment": h["ya"], "relief_rate": tc,
         "crossover_pot": m.participation_crossover_pot(tc, r=r, years=draw_years, brackets=h["brackets"])}
        for h in HISTORY for tc in relief_rates
    ]


def projected_frontier(relief_rates=(0.07, 0.115), checkpoints=(0, 10, 20, 30, 40, 50),
                        r=0.05, draw_years=10):
    """How the T1 crossover moves under the two 50-year forward projections."""
    years = max(checkpoints)
    discrete, smooth = project_discrete(years=years), project_smooth(years=years)
    rows = []
    for tc in relief_rates:
        for y in checkpoints:
            rows.append({
                "relief_rate": tc, "year": y,
                "crossover_discrete": m.participation_crossover_pot(tc, r=r, years=draw_years, brackets=discrete[y]),
                "crossover_smooth": m.participation_crossover_pot(tc, r=r, years=draw_years, brackets=smooth[y]),
            })
    return rows


if __name__ == "__main__":
    out = {
        "calibration_facts": FACTS,
        "historical_frontier": historical_frontier(),
        "projected_frontier": projected_frontier(),
    }
    with open("results_tax_regime.json", "w") as f:
        json.dump(out, f, indent=1, default=float)

    print("Calibration facts (YA2007 onward):")
    for k, v in FACTS.items():
        print(f"  {k:28} {v}")

    print("\nHistorical frontier — real crossover pot by YA:")
    for row in out["historical_frontier"]:
        cp = f"${row['crossover_pot']:,.0f}" if row["crossover_pot"] else "no crossover (always worth it)"
        print(f"  YA{row['year_of_assessment']}  tc={row['relief_rate']:.1%}  {cp}")

    print("\nProjected frontier — discrete vs smooth, tc=11.5%:")
    for row in out["projected_frontier"]:
        if row["relief_rate"] != 0.115:
            continue
        d = f"${row['crossover_discrete']:,.0f}" if row["crossover_discrete"] else "none"
        s = f"${row['crossover_smooth']:,.0f}" if row["crossover_smooth"] else "none"
        print(f"  +{row['year']:>2}y  discrete={d:>14}  smooth={s:>14}")

    print("\nwrote results_tax_regime.json")
