"""Figure 3.4: Figure 1.3 redrawn with a drifting tax regime.

Same axes as Figure 1.2 (tax rate saved tc against return r), B = $1M,
other income $0, k = 10, N = 10, 20, 30, 40. Top row: today's schedule
(Figure 1.3). Bottom row: the smooth scenario, where each withdrawal year
uses the schedule projected for that year.

Run from the repo root: python -m srs_basic.figures.fig3_4_heatmaps
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from srs_basic import config
from srs_basic.model1 import advantage
from srs_basic.model3 import breakeven_tc, calibration
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
TC = np.linspace(*config.TC_RANGE, config.TC_STEPS)
R = np.linspace(*config.R_RANGE, config.R_STEPS)
HORIZONS = (10, 20, 30, 40)
ROWS = (("frozen", "Today's schedule"), ("smooth", "Smooth drift (+0.235pp/yr)"))
LEVELS = [0.25, 0.5, 1.0, 2.0, 4.0]


def main():
    base = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    calib = calibration()
    TCg, Rg = np.meshgrid(TC, R)
    panels = []
    for sc, row_label in ROWS:
        for N in HORIZONS:
            ew = breakeven_tc(config.B, N, sc, base, calib)
            panels.append((sc, row_label, N, ew, advantage(TCg, Rg, N, ew)))

    vmin = min(min(A.min() for *_, A in panels), -0.01)
    vmax = max(A.max() for *_, A in panels)
    levels = np.concatenate([np.linspace(vmin, 0, 11)[:-1], np.linspace(0, vmax, 51)])
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    fig, axes = plt.subplots(2, 4, figsize=(15.6, 8), sharex=True, sharey=True,
                             constrained_layout=True)
    for ax, (sc, row_label, N, ew, A) in zip(axes.flat, panels):
        fill = ax.contourf(TCg * 100, Rg * 100, A, levels=levels, cmap="RdBu", norm=norm)
        lines = ax.contour(TCg * 100, Rg * 100, A, levels=LEVELS, colors="grey", linewidths=0.6)
        ax.clabel(lines, fmt=lambda v: f"+\\${v:g}", fontsize=7)
        ax.contour(TCg * 100, Rg * 100, A, levels=[0], colors="black", linewidths=2)
        ax.set_title(f"{row_label}, N = {N}\nbreakeven tc = {ew:.2%}", fontsize=9)
        ax.grid(alpha=0.2)
    for ax in axes[-1]:
        ax.set_xlabel("Tax rate saved on contribution, tc (%)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Annual return, r (%)")
    cbar = fig.colorbar(fill, ax=axes, shrink=0.85)
    cbar.set_label(r"SRS advantage per \$1 pre-tax (\$)")
    fig.suptitle(f"Figure 3.4: varying the horizon N with and without tax drift "
                 f"(B = \\${config.B/1e6:g}M, other income \\$0)", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_4_heatmaps.png", dpi=200)
    plt.close(fig)
    for sc, _, N, ew, A in panels:
        i6 = int(np.argmin(abs(R - 0.06)))
        j7 = int(np.argmin(abs(TC - 0.07)))
        print(f"{sc:7} N={N}: breakeven {ew:.2%}; gain at tc=7%, r=6%: ${A[i6, j7]:.2f}")
    print("Saved", OUTPUT / "fig3_4_heatmaps.png")


if __name__ == "__main__":
    main()
