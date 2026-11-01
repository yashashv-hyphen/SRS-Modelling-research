"""Singapore resident income tax (Model 1, formula M1.1)."""

import math

import pandas as pd


def load_schedule(csv_path, regime="YA2024-present"):
    """Return the tax bands for one regime as a list of (upper_edge, rate).

    rate is a decimal (7% -> 0.07). The top band's upper_edge is infinity.
    Raises ValueError if the bands do not start at 0, have gaps or overlaps,
    have rates outside 0-100%, or the top band has an upper edge.
    """
    df = pd.read_csv(csv_path)
    df = df[df["regime"] == regime].sort_values("lower_bound")
    if df.empty:
        raise ValueError(f"No rows for regime {regime!r} in {csv_path}")

    schedule = []
    expected_lower = 0.0
    for _, row in df.iterrows():
        lower = float(row["lower_bound"])
        if not math.isclose(lower, expected_lower):
            raise ValueError(f"{regime}: band starts at {lower:,.0f}, "
                             f"expected {expected_lower:,.0f} (gap or overlap)")
        rate = row["marginal_rate_pct"] / 100
        if not 0 <= rate <= 1:
            raise ValueError(f"{regime}: rate {rate:.2%} is outside 0-100%")
        upper = row["upper_bound"]
        upper = math.inf if pd.isna(upper) else float(upper)
        if upper <= lower:
            raise ValueError(f"{regime}: band {lower:,.0f} has upper edge {upper:,.0f}")
        schedule.append((upper, rate))
        expected_lower = upper

    if schedule[-1][0] != math.inf:
        raise ValueError(f"{regime}: top band must have no upper edge")
    return schedule


def tax(x, schedule):
    """Tax on chargeable income x: each band's slice taxed at that band's rate."""
    total = 0.0
    lower = 0.0
    for upper, rate in schedule:
        if x <= lower:
            break
        total += (min(x, upper) - lower) * rate
        lower = upper
    return total


def band_rate(x, schedule):
    """Rate on the last dollar of income x (an income exactly at a band edge
    stays in the lower band)."""
    for upper, rate in schedule:
        if x <= upper:
            return rate
    return schedule[-1][1]


if __name__ == "__main__":
    from srs_basic.config import REGIME, SCHEDULE_CSV

    schedule = load_schedule(SCHEDULE_CSV, REGIME)
    for income in [20_000, 50_000, 100_000, 150_000, 500_000]:
        print(f"Tax on ${income:,}: ${tax(income, schedule):,.2f}")
