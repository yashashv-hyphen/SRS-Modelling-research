"""Figure 2.5: optimal exit rate against the return earned during withdrawal.

Shows how growth during the 10-year window raises the exit rate above Model 1's
(which assumes no growth, i.e. r = 0). Other income $0, PV of tax minimised.
Also writes a table of the values used in the report (r = 0%, 3%, 5%, 8% at $1M).

Run from the repo root: python -m srs_basic.figures.fig2_5_exit_rate_vs_return
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

from srs_basic import config
from srs_basic.model2 import solve
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
RETURNS = np.round(np.arange(0, 0.1201, 0.005), 3)          # 0% to 12% in 0.5% steps
STARTS = [500_000, 1_000_000, 2_000_000, 3_000_000]
COLOURS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
REPORT_RETURNS = [0.0, 0.03, 0.05, 0.08]                    # values quoted in the report
OTHER = 0


def exit_rates(schedule):
    """Optimal exit rate (PV of tax / balance) for each return and starting balance."""
    idx = np.searchsorted(B_GRID, STARTS)
    rows = []
    for r in RETURNS:
        V, _, _, _ = solve(r, OTHER, config.K, B_GRID, schedule, I=config.I,
                           discount=config.DISCOUNT, deemed_separate=config.DEEMED_SEPARATE)
        for b, i in zip(STARTS, idx):
            rows.append({"r": r, "balance": b, "exit_rate": V[config.K, i] / b})
    return pd.DataFrame(rows)


def main():
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    df = exit_rates(schedule)

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    for colour, b in zip(COLOURS, STARTS):
        d = df[df.balance == b]
        ax.plot(100 * d.r, d.exit_rate, color=colour, lw=2, label=f"${b/1e6:g}M")
    base = df[df.balance == 1_000_000].set_index("r").exit_rate
    for r in REPORT_RETURNS:
        ax.plot(100 * r, base[r], "o", color="#2ca02c", ms=6)
        ax.annotate(f"{base[r]:.2%}", (100 * r, base[r]), xytext=(4, 8),
                    textcoords="offset points", fontsize=8, color="#2ca02c")
    ax.annotate("r = 0% is Model 1 (no growth during withdrawal)", (0, base[0.0]),
                xytext=(1.5, 0.0095), fontsize=8, color="grey",
                arrowprops=dict(arrowstyle="->", lw=0.8, color="grey"))
    ax.set_xlabel("Return during the withdrawal period, r (%)")
    ax.set_ylabel(f"Optimal exit rate ({'PV' if config.DISCOUNT else 'nominal'} tax / balance)")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.grid(alpha=0.3)
    ax.legend(title="Starting balance", fontsize=8, title_fontsize=8, loc="upper left")
    ax.set_title("Figure 2.5: growth during withdrawal raises the exit rate "
                 "(other income \\$0, YA2024 rates)", fontsize=10)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig2_5_exit_rate_vs_return.png", dpi=200)
    plt.close(fig)
    df.to_csv(OUTPUT / "fig2_5_exit_rate_vs_return.csv", index=False)
    table = (df[df.r.isin(REPORT_RETURNS)]
             .pivot(index="r", columns="balance", values="exit_rate"))
    print(table.map(lambda v: f"{v:.2%}").to_string())
    print("Saved", OUTPUT / "fig2_5_exit_rate_vs_return.png")


if __name__ == "__main__":
    main()
