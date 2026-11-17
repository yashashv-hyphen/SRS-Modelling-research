"""Figures 2.1 to 2.3: optimal SRS withdrawal policy from the dynamic program.

2.1  recommended withdrawal ($k) by balance and years left (heatmap)
2.2  recommended withdrawal as % of balance: heatmap + line chart
2.3  year-by-year withdrawals from several starting balances: heatmap + line chart

The policy is the same for every level of other income in config.YO_PANELS
(other income changes the tax paid, not the best schedule); Figure 2.1 states
the largest difference found. Figures 2.2 and 2.3 use other income $0.

Run from the repo root: python -m srs_basic.figures.fig2_1_to_2_3_policy
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

from srs_basic import config
from srs_basic.model2 import benchmark, level_payment, simulate, solve
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
YEARS_LEFT = np.arange(config.K, 1, -1)                     # 10 ... 2 years left
ROWS = np.arange(250_000, config.B_PLOT_MAX + 1, 250_000)   # balances in the heatmaps
ROW_IDX = np.searchsorted(B_GRID, ROWS)
ROW_LABELS = [f"${b/1e6:g}M" for b in ROWS[::-1]]           # largest balance on top
STARTS = [500_000, 1_000_000, 2_000_000, 3_000_000]         # balances in the line charts
COLOURS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]
THOUSANDS = FuncFormatter(lambda v, _: f"${v/1e3:,.0f}k")
K_TICKS = FuncFormatter(lambda v, _: f"{v/1e3:.0f}")


def setting():
    goal = "PV of tax" if config.DISCOUNT else "total nominal tax"
    return f"r = {config.R2:.0%}, YA2024 rates, {goal} minimised"


def solve_policy(other, schedule):
    return solve(config.R2, other, config.K, B_GRID, schedule, I=config.I,
                 discount=config.DISCOUNT, deemed_separate=config.DEEMED_SEPARATE)


def annotated(ax, Z, fmt, xlabels, xlabel, cbar_label, fig, cbar_fmt=None):
    """Light-to-dark blue heatmap with each cell's value written in it."""
    im = ax.imshow(Z, cmap="Blues", aspect="auto", vmin=0, vmax=Z.max())
    for (i, j), v in np.ndenumerate(Z):
        ax.text(j, i, fmt(v), ha="center", va="center", fontsize=8,
                color="white" if v > 0.55 * Z.max() else "black")
    ax.set_xticks(range(len(xlabels)), xlabels)
    ax.set_yticks(range(len(ROW_LABELS)), ROW_LABELS)
    ax.set_xlabel(xlabel)
    cbar = fig.colorbar(im, ax=ax, label=cbar_label)
    if cbar_fmt:
        cbar.ax.yaxis.set_major_formatter(cbar_fmt)


def save(fig, name, frame):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", dpi=200)
    plt.close(fig)
    frame.to_csv(OUTPUT / f"{name}.csv", index=False)
    print("Saved", OUTPUT / f"{name}.png")


def figure_2_1(policies):
    """Heatmap of the recommended withdrawal ($k), other income $0."""
    W = policies[0][1]
    Z = W[YEARS_LEFT][:, ROW_IDX].T[::-1]
    diff = max(np.abs(p[1][YEARS_LEFT][:, ROW_IDX] - W[YEARS_LEFT][:, ROW_IDX]).max()
               for yo, p in policies.items() if yo != 0)

    fig, ax = plt.subplots(figsize=(9, 6.5), constrained_layout=True)
    annotated(ax, Z, lambda v: f"{v/1e3:.0f}", YEARS_LEFT,
              "Withdrawal years left (with 1 year left, everything is withdrawn)",
              "Recommended withdrawal ($k)", fig, K_TICKS)
    ax.set_ylabel("SRS balance at start of year")
    others = ", ".join(f"\\${yo/1e3:g}k" for yo in config.YO_PANELS)
    ax.set_title(f"Figure 2.1: recommended withdrawal (\\$k) this year\n"
                 f"Same for other income of {others} (largest difference \\${diff:,.0f}). "
                 f"{setting()}", fontsize=9)

    n, B = np.meshgrid(YEARS_LEFT, ROWS[::-1])
    save(fig, "fig2_1_policy",
         pd.DataFrame({"balance": B.ravel(), "years_left": n.ravel(), "withdrawal": Z.ravel()}))


def figure_2_2(policies):
    """Recommended withdrawal as % of balance: heatmap (left) + line chart (right)."""
    W = policies[0][1]
    pct = 100 * W[YEARS_LEFT][:, ROW_IDX].T[::-1] / ROWS[::-1][:, None]
    years = np.arange(config.K, 0, -1)
    level = 100 * level_payment(1.0, years, config.R2)

    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True,
                                      gridspec_kw={"width_ratios": [1.1, 1]})
    annotated(left, pct, lambda v: f"{v:.1f}",
              [f"{n}\n{p:.1f}%" for n, p in zip(YEARS_LEFT, level)],
              "Withdrawal years left (second line: level payment, % of balance)",
              "% of balance", fig)
    left.set_ylabel("SRS balance at start of year")
    left.set_title("Heatmap: % of balance to withdraw this year", fontsize=10)

    rows = []
    right.plot(years, level, color="black", lw=1.5, label="Level payment (formula)")
    for colour, b in zip(COLOURS, STARTS):
        y = 100 * W[years, np.searchsorted(B_GRID, b)] / b
        right.plot(years, y, "o", color=colour, ms=7, mfc="none", mew=1.8,
                   label=f"Optimal, balance ${b/1e6:g}M")
        rows.append(pd.DataFrame({"balance": b, "years_left": years, "pct_withdrawn": y}))
    for n, p in zip(years, level):
        right.annotate(f"{p:.1f}%", (n, p), xytext=(0, 10), textcoords="offset points",
                       ha="center", fontsize=8)
    right.invert_xaxis()
    right.set_xticks(years)
    right.set_xlabel("Withdrawal years left")
    right.set_ylabel("Withdrawal this year (% of balance)")
    right.set_ylim(0, 110)
    right.grid(alpha=0.3)
    right.legend(fontsize=8, loc="upper left")
    right.set_title("Line chart: every balance follows the level-payment curve", fontsize=10)

    fig.suptitle(f"Figure 2.2: the optimal share to withdraw depends only on years left "
                 f"(other income \\$0, {setting()})", fontsize=11)
    rows.append(pd.DataFrame({"balance": "level", "years_left": years, "pct_withdrawn": level}))
    save(fig, "fig2_2_share_withdrawn", pd.concat(rows))


def figure_2_3(policies, schedule):
    """Year-by-year withdrawals: heatmap (left) + line chart (right)."""
    W = policies[0][1]
    years = np.arange(1, config.K + 1)
    path = lambda b: simulate(W, B_GRID, b, config.R2, config.K, 0, schedule, I=config.I,
                              discount=config.DISCOUNT)["withdrawals"][:config.K]
    Z = np.array([path(b) for b in ROWS[::-1]])

    fig, (left, right) = plt.subplots(1, 2, figsize=(16, 6), constrained_layout=True,
                                      gridspec_kw={"width_ratios": [1.1, 1]})
    annotated(left, Z, lambda v: f"{v/1e3:.0f}", years, "Year of withdrawal period",
              "Withdrawal that year ($k)", fig, K_TICKS)
    left.set_ylabel("SRS balance at start of withdrawals")
    left.set_title("Heatmap: optimal withdrawal each year (\\$k)", fontsize=10)

    rows = []
    for colour, b in zip(COLOURS, STARTS):
        opt = path(b)
        even = benchmark("even", b, config.R2, config.K, 0, schedule, I=config.I,
                         discount=config.DISCOUNT)["withdrawals"][:config.K]
        right.plot(years, opt, color=colour, lw=2.2, marker="o", ms=4,
                   label=f"${b/1e6:g}M: optimal")
        right.plot(years, even, color=colour, lw=1.2, ls="--", label=f"${b/1e6:g}M: even share")
        right.annotate(f"${opt.mean()/1e3:,.0f}k a year", (config.K, opt[-1]), xytext=(8, 0),
                       textcoords="offset points", va="center", fontsize=8, color=colour)
        rows.append(pd.DataFrame({"start_balance": b, "year": years,
                                  "optimal": opt, "even": even}))
    right.set_xticks(years)
    right.set_xlim(0.5, config.K + 2.4)
    right.set_xlabel("Year of withdrawal period")
    right.set_ylabel("Withdrawal that year")
    right.yaxis.set_major_formatter(THOUSANDS)
    right.grid(alpha=0.3)
    right.legend(fontsize=8, ncol=2, loc="upper left")
    right.set_title("Line chart: optimal (solid) is flat; even share (dashed) rises",
                    fontsize=10)

    fig.suptitle(f"Figure 2.3: year-by-year withdrawals (other income \\$0, {setting()})",
                 fontsize=11)
    heat = pd.DataFrame(Z, columns=[f"year_{y}" for y in years])
    heat.insert(0, "start_balance", ROWS[::-1])
    save(fig, "fig2_3_paths", pd.concat(rows))
    heat.to_csv(OUTPUT / "fig2_3_paths_heatmap.csv", index=False)


def main():
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    policies = {yo: solve_policy(yo, schedule) for yo in config.YO_PANELS}
    figure_2_1(policies)
    figure_2_2(policies)
    figure_2_3(policies, schedule)


if __name__ == "__main__":
    main()