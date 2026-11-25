"""Figure 3.3: projected schedules and what they do to Model 1's breakeven.

Left: the 7% band's rate and the top rate over 50 years in each scenario.
Right: Model 1's breakeven tax rate saved (average exit rate on a $1M
balance withdrawn evenly over years N to N+9) against the horizon N.

Run from the repo root: python -m srs_basic.figures.fig3_3_projection
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

from srs_basic import config
from srs_basic.model3 import SCENARIOS, breakeven_tc, calibration, projected_schedule
from srs_basic.tax import band_rate, load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
STYLE = {"frozen": ("black", "-"), "discrete": ("#d62728", "-"),
         "smooth": ("#1f77b4", "--"), "top": ("#2ca02c", ":")}
LABEL = {"frozen": "Frozen (today's rates)", "discrete": "Discrete: +1.33pp every 5.7 years",
         "smooth": "Smooth: +0.235pp a year", "top": "Smooth, top bands only (≥ \\$160k)"}
BALANCES = [500_000, 1_000_000, 2_000_000, 3_000_000]
HORIZONS = range(0, 41)
REPORT_N = [0, 10, 20, 30, 40]


def main():
    base = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    calib = calibration()
    years = np.arange(0, config.PROJECTION_YEARS + 1)

    rows = []
    for sc in SCENARIOS:
        for B in BALANCES:
            for N in HORIZONS:
                rows.append({"scenario": sc, "balance": B, "N": N,
                             "breakeven_tc": breakeven_tc(B, N, sc, base, calib)})
    df = pd.DataFrame(rows)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for sc in SCENARIOS:
        colour, ls = STYLE[sc]
        top = [100 * projected_schedule(base, y, sc, calib)[-1][1] for y in years]
        mid = [100 * band_rate(60_000, projected_schedule(base, y, sc, calib)) for y in years]
        a1.plot(years, top, color=colour, ls=ls, lw=1.8, label=LABEL[sc])
        a1.plot(years, mid, color=colour, ls=ls, lw=1.2, alpha=0.7)
        d = df[(df.scenario == sc) & (df.balance == 1_000_000)]
        a2.plot(d.N, d.breakeven_tc, color=colour, ls=ls, lw=2, label=LABEL[sc])
    a1.text(30, 27, "top band (> \\$1M)", fontsize=8, color="grey")
    a1.text(20, 4.5, "\\$40k to \\$80k band (7% today)", fontsize=8, color="grey")
    a1.set_xlabel("Years from today")
    a1.set_ylabel("Marginal rate (%)")
    a1.set_title("Projected rates (calibrated to YA2007 to YA2024 revisions)", fontsize=10)
    a1.grid(alpha=0.3)
    a1.set_ylim(0, 45)
    a1.legend(fontsize=8, loc="upper left")

    for tc in (0.02, 0.035):
        a2.axhline(tc, color="grey", lw=0.8, ls="-.")
        a2.text(40.3, tc, f"{tc:.1%} band", fontsize=7, va="center", color="grey")
    a2.set_xlabel("Years from contribution to retirement, N")
    a2.set_ylabel("Breakeven tax rate saved, tc (= average exit rate)")
    a2.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=1))
    a2.set_title("Model 1 breakeven, B = \\$1M, other income \\$0, k = 10", fontsize=10)
    a2.grid(alpha=0.3)
    a2.legend(fontsize=8, loc="upper left")
    fig.suptitle("Figure 3.3: if rates keep drifting up, the horizon N starts to move "
                 "Model 1's breakeven", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_3_projection.png", dpi=200)
    plt.close(fig)
    df.to_csv(OUTPUT / "fig3_3_projection.csv", index=False)
    t = df[df.N.isin(REPORT_N)].pivot_table(index=["scenario", "balance"], columns="N",
                                            values="breakeven_tc")
    print(t.map(lambda v: f"{v:.2%}").to_string())
    print("Saved", OUTPUT / "fig3_3_projection.png")


if __name__ == "__main__":
    main()
