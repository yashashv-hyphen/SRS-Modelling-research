"""Figure 3.2: Models 1 and 2 replayed under each historical schedule.

Left: Model 1's average exit rate against the balance at retirement.
Right: Model 2's optimal exit rate (PV of tax / balance, r = 5%) at four
starting balances. Other income $0, I = 0.5, k = 10.

Run from the repo root: python -m srs_basic.figures.fig3_2_history
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

from srs_basic import config
from srs_basic.exit_rate import avg_exit_rate
from srs_basic.model2 import solve
from srs_basic.model3 import all_schedules

OUTPUT = Path(config.OUTPUT_DIR)
COLOURS = ["#9e9e9e", "#bcbd22", "#17becf", "#1f77b4", "#ff7f0e", "#d62728"]
STARTS = [500_000, 1_000_000, 2_000_000, 3_000_000]
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)


def main():
    scheds = all_schedules()
    balances = np.arange(0, 4_000_001, 10_000)
    rows = []

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for colour, (name, s) in zip(COLOURS, scheds.items()):
        ew = [avg_exit_rate(b, config.K, config.OTHER, config.I, s) for b in balances]
        a1.plot(balances / 1e6, ew, color=colour, lw=1.8, label=name)
        V, *_ = solve(config.R2, config.OTHER, config.K, B_GRID, s, I=config.I,
                      discount=config.DISCOUNT, deemed_separate=config.DEEMED_SEPARATE)
        for b in STARTS:
            i = int(np.searchsorted(B_GRID, b))
            rows.append({"regime": name, "balance": b,
                         "model1_exit_rate": avg_exit_rate(b, config.K, config.OTHER, config.I, s),
                         "model2_exit_rate": V[config.K, i] / b})
    a1.set_xlabel("SRS balance at retirement, B ($M)")
    a1.set_ylabel("Model 1 average exit rate (= breakeven tc)")
    a1.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=1))
    a1.set_title("Model 1: even split, no growth during withdrawal", fontsize=10)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=8)

    df = pd.DataFrame(rows)
    width = 0.13
    xs = np.arange(len(STARTS))
    for j, (colour, name) in enumerate(zip(COLOURS, scheds)):
        d = df[df.regime == name]
        a2.bar(xs + (j - 2.5) * width, d.model2_exit_rate, width, color=colour, label=name)
    a2.set_xticks(xs, [f"${b/1e6:g}M" for b in STARTS])
    a2.set_xlabel("Starting balance")
    a2.set_ylabel("Model 2 optimal exit rate (PV tax / balance)")
    a2.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    a2.set_title(f"Model 2: optimal withdrawals, r = {config.R2:.0%}", fontsize=10)
    a2.grid(alpha=0.3, axis="y")
    a2.legend(fontsize=8)
    fig.suptitle("Figure 3.2: the same SRS balance under each historical schedule "
                 "(other income \\$0)", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_2_history.png", dpi=200)
    plt.close(fig)
    df.to_csv(OUTPUT / "fig3_2_history.csv", index=False)
    for col in ("model1_exit_rate", "model2_exit_rate"):
        print(col)
        print(df.pivot(index="regime", columns="balance", values=col)
                .map(lambda v: f"{v:.2%}").to_string())
    print("Saved", OUTPUT / "fig3_2_history.png")


if __name__ == "__main__":
    main()
