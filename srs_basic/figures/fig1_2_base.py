"""Figure 1.2: Model 1 base case heatmap, x = tc, y = r, N and B fixed."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from srs_basic.config import REGIME, SCHEDULE_CSV
from srs_basic.model1 import grid
from srs_basic.tax import load_schedule

OUTPUT = Path("srs_basic/output")
N, B = 20, 1_000_000
TC_VALUES = np.linspace(0, 0.24, 241)    # 0% to 24% in 0.1% steps
R_VALUES = np.linspace(0.03, 0.12, 91)   # 3% to 12% in 0.1% steps
LEVELS = [0.25, 0.5, 1.0, 1.5, 2.0]      # labelled contour lines ($ per $1)


def plot_advantage(ax, TC, R, A, vmin, vmax):
    """Draw one heatmap panel. Reused by the sweep figures (1.3 to 1.5)."""
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    fill = ax.contourf(TC * 100, R * 100, A, levels=60, cmap="RdBu", norm=norm)
    lines = ax.contour(TC * 100, R * 100, A, levels=LEVELS,
                       colors="grey", linewidths=0.6)
    ax.clabel(lines, fmt=lambda v: f"+\\${v:g}", fontsize=7)
    ax.contour(TC * 100, R * 100, A, levels=[0], colors="black", linewidths=2)
    ax.set_xlabel("Tax rate saved on contribution, tc (%)")
    ax.set_ylabel("Annual return, r (%)")
    return fill


if __name__ == "__main__":
    schedule = load_schedule(SCHEDULE_CSV, REGIME)
    TC, R, EW, A = grid(TC_VALUES, R_VALUES, N, schedule, B=B)
    ew = EW[0, 0]

    # Save the numbers: one row per (tc, r) point
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tc": TC.ravel(), "r": R.ravel(), "exit_rate": EW.ravel(),
                  "advantage": A.ravel()}).to_csv(OUTPUT / "fig1_2_base.csv", index=False)

    fig, ax = plt.subplots(figsize=(7.5, 5))
    fill = plot_advantage(ax, TC, R, A, vmin=A.min(), vmax=A.max())
    ax.annotate(f"Breakeven: tc = exit rate = {ew:.2%}", xy=(ew * 100, 11),
                xytext=(4, 11.2), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate("Outside SRS wins", xy=(0.6, 5), xytext=(3, 5.5), fontsize=9,
                color="darkred", arrowprops=dict(arrowstyle="->", color="darkred"))
    ax.text(20, 4.0, "SRS wins", fontsize=10, ha="center", color="navy")

    cbar = fig.colorbar(fill, ax=ax)
    cbar.set_label(r"SRS advantage per \$1 of pre-tax income (\$)")
    ax.set_title(f"Figure 1.2: SRS vs investing outside SRS\n"
                 f"N = {N} years, balance at retirement = \\${B/1e6:g}M, "
                 f"10-year withdrawal, YA2024 rates", fontsize=11)

    fig.tight_layout()
    fig.savefig(OUTPUT / "fig1_2_base.png", dpi=200)
    print("Saved", OUTPUT / "fig1_2_base.png")