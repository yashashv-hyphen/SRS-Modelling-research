"""Figures 2.1 to 2.3: optimal SRS withdrawal policy from the dynamic program.

2.1  recommended withdrawal ($) by balance and years left (base case)
2.2  the same policy as % of the balance, plus the range of equally good choices
2.3  recommended withdrawal for each level of other income

Run from the repo root: python -m srs_basic.figures.fig2_1_to_2_3_policy
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from srs_basic import config
from srs_basic.model2 import solve
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
YEARS = np.arange(config.K, 0, -1)                 # 10, 9, ..., 1 years left
SHOW = (B_GRID > 0) & (B_GRID <= config.B_PLOT_MAX)
MONEY = FuncFormatter(lambda v, _: f"${v/1e6:g}M" if v >= 1e6 else f"${v/1e3:g}k")


def policy(other, schedule):
    _, W, lo, hi = solve(config.R2, other, config.K, B_GRID, schedule,
                         I=config.I, discount=config.DISCOUNT,
                         deemed_separate=config.DEEMED_SEPARATE)
    rows = YEARS  # row n of W = n years left
    return W[rows][:, SHOW].T, lo[rows][:, SHOW].T, hi[rows][:, SHOW].T


def heatmap(ax, Z, label, cmap, vmax=None):
    """Columns = years left (10 on the left), rows = balance."""
    mesh = ax.pcolormesh(np.arange(len(YEARS) + 1), np.append(B_GRID[SHOW] - config.DB / 2,
                         B_GRID[SHOW][-1] + config.DB / 2), Z, cmap=cmap,
                         vmin=0, vmax=vmax, shading="flat")
    ax.set_xticks(np.arange(len(YEARS)) + 0.5, YEARS)
    ax.set_xlabel("Withdrawal years left")
    ax.yaxis.set_major_formatter(MONEY)
    ax.set_title(label, fontsize=10)
    return mesh


def save(fig, name, frames):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", dpi=200)
    plt.close(fig)
    pd.concat(frames).to_csv(OUTPUT / f"{name}.csv", index=False)
    print("Saved", OUTPUT / f"{name}.png")


def long_table(label, W, lo, hi):
    B, n = np.meshgrid(B_GRID[SHOW], YEARS, indexing="ij")
    return pd.DataFrame({"panel": label, "balance": B.ravel(), "years_left": n.ravel(),
                         "withdrawal": W.ravel(), "withdrawal_low": lo.ravel(),
                         "withdrawal_high": hi.ravel()})


def main():
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    setting = (f"r = {config.R2:.0%}, YA2024 rates, "
               f"{'PV of tax' if config.DISCOUNT else 'total nominal tax'} minimised")

    # Figure 2.1 and 2.2: base case, Yo = 0
    W, lo, hi = policy(0, schedule)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True, constrained_layout=True)
    m = heatmap(axes[0], W, "Recommended withdrawal ($)", "viridis")
    fig.colorbar(m, ax=axes[0]).ax.yaxis.set_major_formatter(MONEY)
    m = heatmap(axes[1], 100 * W / B_GRID[SHOW][:, None], "As % of balance", "viridis", 100)
    fig.colorbar(m, ax=axes[1], label="%")
    m = heatmap(axes[2], hi - lo, "Range of equally good withdrawals ($)", "magma")
    fig.colorbar(m, ax=axes[2]).ax.yaxis.set_major_formatter(MONEY)
    axes[0].set_ylabel("SRS balance at start of year")
    fig.suptitle(f"Figures 2.1 and 2.2: optimal withdrawal policy, other income $0 ({setting})",
                 fontsize=11)
    save(fig, "fig2_1_2_policy", [long_table("Yo=0", W, lo, hi)])

    # Figure 2.3: one panel per level of other income, shared colour scale
    results = [(yo, *policy(yo, schedule)) for yo in config.YO_PANELS]
    vmax = max(W.max() for _, W, _, _ in results)
    fig, axes = plt.subplots(1, len(results), figsize=(4 * len(results) + 1, 4.8),
                             sharey=True, constrained_layout=True)
    for ax, (yo, W, _, _) in zip(axes, results):
        m = heatmap(ax, W, f"Other income ${yo/1e3:g}k", "viridis", vmax)
    axes[0].set_ylabel("SRS balance at start of year")
    fig.colorbar(m, ax=axes, label="Recommended withdrawal").ax.yaxis.set_major_formatter(MONEY)
    fig.suptitle(f"Figure 2.3: optimal withdrawal by other income ({setting})", fontsize=11)
    save(fig, "fig2_3_other_income",
         [long_table(f"Yo={yo}", W, lo, hi) for yo, W, lo, hi in results])


if __name__ == "__main__":
    main()