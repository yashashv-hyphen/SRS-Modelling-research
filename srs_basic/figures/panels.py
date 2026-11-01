"""Shared helper: a row of Model 1 heatmaps on one colour scale."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

from srs_basic import config
from srs_basic.model1 import grid
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
TC_VALUES = np.linspace(*config.TC_RANGE, config.TC_STEPS)
R_VALUES = np.linspace(*config.R_RANGE, config.R_STEPS)
DEFAULTS = {"k": config.K, "other": config.OTHER, "I": config.I}
LEVELS = [0.25, 0.5, 1.0, 2.0, 4.0]      # labelled contour lines ($ per $1)


def sweep_figure(name, title, panels, cbar_label=r"SRS advantage per \$1 pre-tax (\$)"):
    """Draw one heatmap per panel, all on the same colour scale.

    name   file name without extension, e.g. "fig1_3_horizon"
    title  figure title
    panels list of (panel_label, grid_kwargs), where grid_kwargs is passed
           to model1.grid, e.g. {"N": 20, "B": 1_000_000}
    """
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)

    # 1. Compute every panel first, so the colour scale can be shared
    results = []
    for label, kwargs in panels:
        TC, R, EW, A = grid(TC_VALUES, R_VALUES, schedule=schedule,
                            **{**DEFAULTS, **kwargs})
        results.append((label, kwargs, TC, R, EW, A))

    vmin = min(A.min() for *_, A in results)
    vmax = max(A.max() for *_, A in results)
    vmin = min(vmin, -0.01)  # keep a red band even if no panel loses
    levels = np.concatenate([np.linspace(vmin, 0, 11)[:-1], np.linspace(0, vmax, 51)])
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)

    # 2. Plot
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(3.6 * n + 1.2, 4.2),
                             sharex=True, sharey=True, constrained_layout=True)
    axes = np.atleast_1d(axes)
    for ax, (label, kwargs, TC, R, EW, A) in zip(axes, results):
        fill = ax.contourf(TC * 100, R * 100, A, levels=levels, cmap="RdBu", norm=norm)
        lines = ax.contour(TC * 100, R * 100, A, levels=LEVELS, colors="grey",
                           linewidths=0.6)
        ax.clabel(lines, fmt=lambda v: f"+\\${v:g}", fontsize=7)
        ax.contour(TC * 100, R * 100, A, levels=[0], colors="black", linewidths=2)

        ew = EW[:, 0]
        if np.allclose(ew, ew[0]):
            note = f"breakeven tc = {ew[0]:.2%}"
        else:
            note = f"breakeven tc: {ew[0]:.2%} to {ew[-1]:.2%}"
        ax.set_title(f"{label}\n{note}", fontsize=10)
        ax.set_xlabel("tc (%)")
    axes[0].set_ylabel("Annual return, r (%)")

    cbar = fig.colorbar(fill, ax=axes, shrink=0.9)
    cbar.set_label(cbar_label)
    fig.suptitle(title, fontsize=11)

    # 3. Save the PNG, then the numbers behind every panel
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{name}.png", dpi=200)
    plt.close(fig)
    frames = [pd.DataFrame({"panel": label, "tc": TC.ravel(), "r": R.ravel(),
                            "exit_rate": EW.ravel(), "advantage": A.ravel()})
              for label, kwargs, TC, R, EW, A in results]
    pd.concat(frames).to_csv(OUTPUT / f"{name}.csv", index=False)
    print("Saved", OUTPUT / f"{name}.png")
