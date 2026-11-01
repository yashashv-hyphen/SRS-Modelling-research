"""Figure 1.1: average exit rate against SRS balance at retirement.

Run from the repo root: python -m srs_basic.figures.fig1_1_exit_rate
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter

from srs_basic.config import I, K, OTHER, OUTPUT_DIR, REGIME, SCHEDULE_CSV
from srs_basic.exit_rate import avg_exit_rate
from srs_basic.tax import load_schedule


def main():
    output = Path(OUTPUT_DIR)
    schedule = load_schedule(SCHEDULE_CSV, REGIME)
    balances = np.linspace(0, 4_000_000, 401)  # $0 to $4M in $10k steps
    exit_rates = [avg_exit_rate(b, K, OTHER, I, schedule) for b in balances]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(balances, exit_rates, linewidth=2)
    for b, offset in [(400_000, (-62, 10)), (1_000_000, (8, -14)), (3_000_000, (8, -14))]:
        e = avg_exit_rate(b, K, OTHER, I, schedule)
        ax.plot(b, e, "o", color="black", markersize=5)
        ax.annotate(f"\\${b/1e6:g}M: {e:.2%}", (b, e), textcoords="offset points",
                    xytext=offset, fontsize=9)

    ax.set_xlabel("SRS balance at retirement")
    ax.set_ylabel("Average exit rate (tax ÷ amount withdrawn)")
    ax.set_title(f"Figure 1.1: SRS exit rate rises with balance\n"
                 f"{K}-year even withdrawal, other income \\${OTHER:,}, {REGIME} rates",
                 fontsize=11)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x/1e6:g}M"))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_xlim(0, 4_000_000)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / "fig1_1_exit_rate.png", dpi=200)
    pd.DataFrame({"balance": balances, "avg_exit_rate": exit_rates}).to_csv(
        output / "fig1_1_exit_rate.csv", index=False)
    print("Saved", output / "fig1_1_exit_rate.png")


if __name__ == "__main__":
    main()
