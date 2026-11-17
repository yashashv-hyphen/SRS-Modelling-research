"""Figure 2.4: what the withdrawal policy is worth.

Left:  exit rate under the optimal policy (solid) and a lump sum (dashed),
       one colour per level of other income.
Right: extra tax paid by the "even share of what is left" rule compared with
       the optimum (basis points of the balance). The level payment is not
       drawn: it matches the optimum to within the solver's grid accuracy.

Exit rate = total tax on withdrawals (PV if DISCOUNT) / starting balance.
Run from the repo root: python -m srs_basic.figures.fig2_4_exit_rates
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, PercentFormatter

from srs_basic import config
from srs_basic.model2 import benchmark, solve
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
STARTS = np.arange(25_000, config.B_PLOT_MAX + 1, 25_000)
COLOURS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
MILLIONS = FuncFormatter(lambda v, _: f"${v/1e6:g}M")


def exit_rates(other, schedule, opts):
    V, _, _, _ = solve(config.R2, other, config.K, B_GRID, schedule, **opts)
    rates = {"optimal": V[config.K, np.searchsorted(B_GRID, STARTS)] / STARTS}
    for policy in ("level", "even", "lump"):
        rates[policy] = np.array([benchmark(policy, b, config.R2, config.K, other,
                                            schedule, **opts)["exit_rate"] for b in STARTS])
    return rates, V[config.K]


def main():
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    opts = dict(I=config.I, discount=config.DISCOUNT, deemed_separate=config.DEEMED_SEPARATE)
    results, values = {}, {}
    for yo in config.YO_PANELS:
        results[yo], values[yo] = exit_rates(yo, schedule, opts)

    fig, (left, right) = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)

    # Left: optimal (solid) vs lump sum (dashed)
    for colour, (yo, rates) in zip(COLOURS, results.items()):
        left.plot(STARTS, rates["optimal"], color=colour, lw=2.2)
        left.plot(STARTS, rates["lump"], color=colour, lw=1.2, ls="--")
        left.annotate(f"starts at {rates['optimal'][0]:.2%}", (STARTS[0], rates["optimal"][0]),
                      xytext=(6, 5), textcoords="offset points", fontsize=8, color=colour)

    base = results[0]
    i1m = int(np.searchsorted(STARTS, 1_000_000))
    left.annotate(f"\\$1M, other income \\$0:\noptimal {base['optimal'][i1m]:.2%}",
                  (1_000_000, base["optimal"][i1m]), xytext=(1_250_000, 0.003),
                  fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    left.annotate(f"\\$1M, other income \\$0:\nlump sum {base['lump'][i1m]:.2%}",
                  (1_000_000, base["lump"][i1m]), xytext=(1_250_000, 0.072),
                  fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    taxed = B_GRID[np.argmax(values[0] > 0.5)]           # first balance that pays any tax
    left.axvline(taxed, color="grey", lw=0.8, ls=":")
    left.text(taxed, 0.115, f" other income \\$0:\n no tax up to ~\\${taxed/1e3:.0f}k",
              fontsize=8, va="top", color="grey")
    left.set_ylim(-0.002, 0.12)
    left.set_title("Exit rate: optimal policy vs lump sum", fontsize=10)
    left.set_ylabel("Exit rate (PV of tax / balance)")
    left.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    handles = [Line2D([], [], color=c, lw=2.2, label=f"\\${yo/1e3:g}k")
               for c, yo in zip(COLOURS, config.YO_PANELS)]
    handles += [Line2D([], [], color="black", lw=2.2, label="optimal"),
                Line2D([], [], color="black", lw=1.2, ls="--", label="lump sum")]
    left.legend(handles=handles, fontsize=8, loc="lower right",
                title="Other income / policy", title_fontsize=8)

    left.set_xlabel("SRS balance at start of withdrawals")
    left.xaxis.set_major_formatter(MILLIONS)
    left.grid(alpha=0.3)

    # Right: extra tax ($) of the even rule over the optimum at a few balances
    bars = [500_000, 1_000_000, 2_000_000, 3_000_000]
    pos = np.searchsorted(STARTS, bars)
    width = 0.8 / len(results)
    for k, (colour, (yo, rates)) in enumerate(zip(COLOURS, results.items())):
        extra = (rates["even"][pos] - rates["optimal"][pos]) * np.array(bars)
        x = np.arange(len(bars)) + (k - (len(results) - 1) / 2) * width
        right.bar(x, extra, width, color=colour, label=f"\\${yo/1e3:g}k")
        for xi, v in zip(x, extra):
            right.text(xi, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=7)
    gap = max(np.max(np.abs(r["level"] - r["optimal"]) * STARTS) for r in results.values())
    right.text(0.02, 0.97, f"Level payment = optimum to within \\${gap:,.0f}\n"
               f"(solver grid accuracy), so not shown", transform=right.transAxes,
               fontsize=8, va="top")
    right.set_xticks(range(len(bars)), [f"\\${b/1e6:g}M" for b in bars])
    right.set_xlabel("SRS balance at start of withdrawals")
    right.set_ylabel("Extra tax vs optimum (PV, $)")
    right.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    right.set_title('Extra tax from the "even share of what is left" rule', fontsize=10)
    right.legend(fontsize=8, title="Other income", title_fontsize=8, loc="upper right")
    right.grid(alpha=0.3, axis="y")
    fig.suptitle(f"Figure 2.4: what the withdrawal policy is worth (r = {config.R2:.0%}, "
                 f"YA2024 rates)", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig2_4_exit_rates.png", dpi=200)
    plt.close(fig)
    rows = [pd.DataFrame({"other_income": yo, "policy": p, "balance": STARTS, "exit_rate": y})
            for yo, rates in results.items() for p, y in rates.items()]
    pd.concat(rows).to_csv(OUTPUT / "fig2_4_exit_rates.csv", index=False)
    print("Saved", OUTPUT / "fig2_4_exit_rates.png")


if __name__ == "__main__":
    main()