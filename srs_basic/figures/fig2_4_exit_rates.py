"""Figures 2.1 to 2.3: optimal SRS withdrawal policy from the dynamic program.

2.1  recommended withdrawal ($k) by balance and years left, other income $0
2.2  the same policy as % of the balance
2.3  recommended withdrawal ($k) for each level of other income

Each cell is labelled with its value. The last year (1 year left) is left out
of the colour scale: everything is withdrawn then, by rule.

Run from the repo root: python -m srs_basic.figures.fig2_1_to_2_3_policy
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from srs_basic import config
from srs_basic.model2 import level_payment, solve
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
YEARS = np.arange(config.K, 1, -1)                          # 10 ... 2 years left
ROWS = np.arange(250_000, config.B_PLOT_MAX + 1, 250_000)   # balances shown
ROW_IDX = np.searchsorted(B_GRID, ROWS)


def policy(other, schedule):
    """Recommended withdrawal, rows = ROWS (top = largest), columns = YEARS."""
    _, W, lo, hi = solve(config.R2, other, config.K, B_GRID, schedule, I=config.I,
                         discount=config.DISCOUNT, deemed_separate=config.DEEMED_SEPARATE)
    pick = lambda M: M[YEARS][:, ROW_IDX].T[::-1]
    return pick(W), pick(lo), pick(hi)


def annotated(ax, Z, fmt, cmap, vmin, vmax, title):
    """Heatmap with each cell's value written in it."""
    im = ax.imshow(Z, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    for (i, j), v in np.ndenumerate(Z):
        shade = (v - vmin) / (vmax - vmin) if vmax > vmin else 0
        ax.text(j, i, fmt(v), ha="center", va="center", fontsize=7,
                color="black" if shade > 0.55 else "white")
    ax.set_xticks(range(len(YEARS)), YEARS)
    ax.set_yticks(range(len(ROWS)), [f"${b/1e6:g}M" for b in ROWS[::-1]])
    ax.set_xlabel("Withdrawal years left (1 year left: withdraw everything)")
    ax.set_title(title, fontsize=10)
    return im


def long_table(label, W, lo, hi):
    n, B = np.meshgrid(YEARS, ROWS[::-1])
    return pd.DataFrame({"panel": label, "balance": B.ravel(), "years_left": n.ravel(),
                         "withdrawal": W.ravel(), "withdrawal_low": lo.ravel(),
                         "withdrawal_high": hi.ravel()})


def save(fig, name, frames):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", dpi=200)
    plt.close(fig)
    pd.concat(frames).to_csv(OUTPUT / f"{name}.csv", index=False)
    print("Saved", OUTPUT / f"{name}.png")


def main():
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    setting = (f"r = {config.R2:.0%}, YA2024 rates, "
               f"{'PV of tax' if config.DISCOUNT else 'total nominal tax'} minimised")
    k_fmt = lambda v: f"{v/1e3:.0f}"

    # Figures 2.1 and 2.2: base case, other income $0
    W, lo, hi = policy(0, schedule)
    pct = 100 * W / ROWS[::-1][:, None]
    level = 100 * level_payment(1.0, YEARS, config.R2)       # level payment, % of balance
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    im = annotated(axes[0], W, k_fmt, "viridis", 0, W.max(),
                   "Figure 2.1: recommended withdrawal ($k)")
    fig.colorbar(im, ax=axes[0], label="$k").ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v/1e3:.0f}"))
    im = annotated(axes[1], pct, lambda v: f"{v:.1f}", "viridis", 0, pct.max(),
                   "Figure 2.2: recommended withdrawal (% of balance)")
    fig.colorbar(im, ax=axes[1], label="% of balance")
    axes[1].set_xticks(range(len(YEARS)), [f"{n}\n{p:.1f}%" for n, p in zip(YEARS, level)])
    axes[1].set_xlabel("Withdrawal years left (second line: level payment, % of balance)")
    axes[0].set_ylabel("SRS balance at start of year")
    fig.suptitle(f"Optimal withdrawal policy, other income \\$0 ({setting})", fontsize=11)
    save(fig, "fig2_1_2_policy", [long_table("Yo=0", W, lo, hi)])

    # Figure 2.3: 2 x 2 panels, one per level of other income, shared colour scale
    results = [(yo, *policy(yo, schedule)) for yo in config.YO_PANELS]
    vmax = max(W.max() for _, W, _, _ in results)
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), constrained_layout=True)
    for ax, (yo, W, _, _) in zip(axes.ravel(), results):
        im = annotated(ax, W, k_fmt, "viridis", 0, vmax, f"Other income \\${yo/1e3:g}k a year")
    for ax in axes[:, 0]:
        ax.set_ylabel("SRS balance at start of year")
    cbar = fig.colorbar(im, ax=axes, label="Recommended withdrawal ($k)", shrink=0.6)
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e3:.0f}"))
    fig.suptitle(f"Figure 2.3: recommended withdrawal ($k) by other income ({setting})",
                 fontsize=11)
    save(fig, "fig2_3_other_income",
         [long_table(f"Yo={yo}", W, lo, hi) for yo, W, lo, hi in results])


if __name__ == "__main__":
    main()