"""Singapore resident income tax (Model 1, formula M1.1)."""

import math

import pandas as pd

## turns the csv into a simply list, keeps the rows for one regime, sort the brands from lowest to highest, convert each row into (upper_edge, rate), if the regime name doesnt match any row, it will stop with an error 
def load_schedule(csv_path, regime="YA2024-present"):
    """Return the tax bands for one regime as a list of (upper_edge, rate).

    rate is a decimal (7% -> 0.07). The top band's upper_edge is infinity.
    """
    df = pd.read_csv(csv_path)
    df = df[df["regime"] == regime].sort_values("lower_bound")
    if df.empty:
        raise ValueError(f"No rows for regime {regime!r} in {csv_path}")

    schedule = []
    for _, row in df.iterrows():
        upper = row["upper_bound"]
        if pd.isna(upper):
            upper = math.inf
        schedule.append((float(upper), row["marginal_rate_pct"] / 100))
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
    """Rate of the band that income x falls in (the marginal rate)."""
    for upper, rate in schedule:
        if x < upper:
            return rate
    return schedule[-1][1]

if __name__ == "__main__":
    schedule = load_schedule("data/sg_resident_tax_schedules_YA2003_present.csv")
    print("Bands:", schedule)
    for income in [20_000, 50_000, 100_000, 150_000, 500_000]:
        print(f"Tax on ${income:,}: ${tax(income, schedule):,.2f}")
    print("Marginal rate at $64,752:", band_rate(64_752, schedule))