"""Figure 3.1: the six real resident schedules since YA2003.

Left: marginal rate against chargeable income for each regime.
Right: the rate in each band edge range by year of assessment, showing that
revisions move rates, never band edges.

Run from the repo root: python -m srs_basic.figures.fig3_1_schedules
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from srs_basic import config
from srs_basic.model3 import all_schedules, calibration, regimes
from srs_basic.tax import band_rate

OUTPUT = Path(config.OUTPUT_DIR)
COLOURS = ["#9e9e9e", "#bcbd22", "#17becf", "#1f77b4", "#ff7f0e", "#d62728"]
PROBES = [25_000, 60_000, 100_000, 140_000, 250_000, 1_200_000]   # one income per band


def main():
    scheds = all_schedules()
    regs = regimes()
    x = np.linspace(0, 400_000, 4001)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for colour, (name, _) in zip(COLOURS, regs):
        a1.step(x / 1000, [100 * band_rate(v, scheds[name]) for v in x], where="post",
                color=colour, lw=1.8, label=name)
    a1.set_xlabel("Chargeable income ($k)")
    a1.set_ylabel("Marginal rate (%)")
    a1.set_title("Marginal rate by income, each regime", fontsize=10)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=8)

    years = list(range(2003, 2027))
    ya_from = [ya for _, ya in regs]
    rows = []
    for y in years:
        name = regs[int(np.searchsorted(ya_from, y, side="right")) - 1][0]
        for p in PROBES:
            rows.append({"ya": y, "income": p, "rate": band_rate(p, scheds[name]), "regime": name})
    df = pd.DataFrame(rows)
    cmap = plt.get_cmap("viridis")
    for i, p in enumerate(PROBES):
        d = df[df.income == p]
        a2.step(d.ya, 100 * d.rate, where="post", color=cmap(i / (len(PROBES) - 1)), lw=1.8,
                label=f"${p/1000:,.0f}k")
    for ya in calibration()["revision_yas"]:
        a2.axvline(ya, color="grey", ls=":", lw=1)
    a2.set_xlabel("Year of assessment")
    a2.set_ylabel("Marginal rate (%)")
    a2.set_title("Rate at a fixed chargeable income, by year (dotted: revisions since YA2007)",
                 fontsize=10)
    a2.grid(alpha=0.3)
    a2.legend(title="Chargeable income", fontsize=8, title_fontsize=8, ncol=2)
    fig.suptitle("Figure 3.1: Singapore resident income tax, YA2003 to today "
                 "(band edges never move; rates do)", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_1_schedules.png", dpi=200)
    plt.close(fig)
    df.to_csv(OUTPUT / "fig3_1_schedules.csv", index=False)
    print(calibration())
    print("Saved", OUTPUT / "fig3_1_schedules.png")


if __name__ == "__main__":
    main()
