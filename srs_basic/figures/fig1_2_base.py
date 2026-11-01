"""Figure 1.2: Model 1 base case heatmap, x = tc, y = r, N and B fixed.

Run from the repo root: python -m srs_basic.figures.fig1_2_base
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from srs_basic import config
from srs_basic.model1 import grid
from srs_basic.tax import load_schedule

LEVELS = [0.25, 0.5, 1.0, 1.5, 2.0]      # labelled contour lines ($ per $1)


def plot_advantage(ax, TC, R, A, vmin, vmax):
    """Draw one heatmap panel."""
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    fill = ax.contourf(TC * 100, R * 100, A, levels=60, cmap="RdBu", norm=norm)
    lines = ax.contour(TC * 100, R * 100, A, levels=LEVELS,
                       colors="grey", linewidths=0.6)
    ax.clabel(lines, fmt=lambda v: f"+\\${v:g}", fontsize=7)
    ax.contour(TC * 100, R * 100, A, levels=[0], colors="black", linewidths=2)
    ax.set_xlabel("Tax rate saved on contribution, tc (%)")
    ax.set_ylabel("Annual return, r (%)")
    return fill


def main():
    output = Path(config.OUTPUT_DIR)
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    tc_values = np.linspace(*config.TC_RANGE, config.TC_STEPS)
    r_values = np.linspace(*config.R_RANGE, config.R_STEPS)
    TC, R, EW, A = grid(tc_values, r_values, config.N, schedule, B=config.B,
                        k=config.K, other=config.OTHER, I=config.I)
    ew = EW[0, 0]

    fig, ax = plt.subplots(figsize=(7.5, 5))
    fill = plot_advantage(ax, TC, R, A, vmin=A.min(), vmax=A.max())
    ax.annotate(f"Breakeven (whole balance):\ntc = average exit rate = {ew:.2%}",
                xy=(ew * 100, 11), xytext=(4, 10.9), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("Outside SRS wins", xy=(ew * 50, 5), xytext=(3, 5.5), fontsize=9,
                color="darkred", arrowprops=dict(arrowstyle="->", color="darkred"))
    ax.text(20, 4.0, "SRS wins", fontsize=10, ha="center", color="navy")

    cbar = fig.colorbar(fill, ax=ax)
    cbar.set_label(r"SRS advantage per \$1 of pre-tax income (\$)")
    ax.set_title(f"Figure 1.2: SRS vs investing outside SRS (whole-balance evaluation)\n"
                 f"N = {config.N} years, balance at retirement = \\${config.B/1e6:g}M, "
                 f"{config.K}-year withdrawal, {config.REGIME} rates", fontsize=10)
    fig.tight_layout()

    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / "fig1_2_base.png", dpi=200)
    pd.DataFrame({"tc": TC.ravel(), "r": R.ravel(), "exit_rate": EW.ravel(),
                  "advantage": A.ravel()}).to_csv(output / "fig1_2_base.csv", index=False)
    print("Saved", output / "fig1_2_base.png")


if __name__ == "__main__":
    main()
