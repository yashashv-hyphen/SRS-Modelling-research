"""Figure 3.5: Model 2 when a tax revision lands during the withdrawal window.

A revision of +1.33pp on every taxed band (the YA2007 to YA2024 average)
lands in window year config.JUMP_YEAR + 1 and is known in advance.
Left: optimal withdrawals vs the level payment on $1M. Right: extra PV tax
the level payment pays over the optimum, by balance and other income.
r = 5%, I = 0.5, PV of tax minimised.

Run from the repo root: python -m srs_basic.figures.fig3_5_window
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from srs_basic import config
from srs_basic.model3 import calibration, jump_schedules, level_path, optimal_path, solve_tv
from srs_basic.tax import load_schedule

OUTPUT = Path(config.OUTPUT_DIR)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
STARTS = [500_000, 1_000_000, 2_000_000, 3_000_000]
OTHERS = (0, 20_000, 50_000, 100_000)


def main():
    base = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    step = calibration()["avg_step"]
    K, r = config.K, config.R2
    cases = {"frozen": [base] * K, "jump": jump_schedules(base, K, config.JUMP_YEAR, step)}

    rows, paths = [], {}
    for other in OTHERS:
        for case, scheds in cases.items():
            _, W = solve_tv(r, other, B_GRID, scheds, I=config.I, discount=config.DISCOUNT)
            for B0 in STARTS:
                opt = optimal_path(W, B_GRID, B0, r, other, scheds, config.I, config.DISCOUNT)
                lvl = level_path(B0, r, other, scheds, config.I, config.DISCOUNT)
                rows.append({"case": case, "other": other, "balance": B0,
                             "optimal_tax": opt["total_tax"], "level_tax": lvl["total_tax"],
                             "extra_level": lvl["total_tax"] - opt["total_tax"],
                             "optimal_exit_rate": opt["exit_rate"]})
                if other == 0 and B0 == 1_000_000:
                    paths[case] = (opt["withdrawals"], lvl["withdrawals"])
    df = pd.DataFrame(rows)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    yrs = np.arange(1, K + 1)
    a1.plot(yrs, paths["frozen"][0] / 1e3, "o-", color="black", label="Optimal, no revision")
    a1.plot(yrs, paths["jump"][0] / 1e3, "o-", color="#d62728",
            label=f"Optimal, +{step*100:.2f}pp from year {config.JUMP_YEAR + 1}")
    a1.plot(yrs, paths["jump"][1] / 1e3, "s--", color="grey", label="Level payment")
    a1.axvline(config.JUMP_YEAR + 0.5, color="#d62728", ls=":", lw=1)
    a1.axhline(160, color="#1f77b4", lw=0.8, ls="-.")
    a1.text(1.2, 161.5, "\\$160k withdrawal = \\$80k taxable (top of the 7% band)", fontsize=7,
            color="#1f77b4")
    a1.set_xticks(yrs)
    a1.set_xlabel("Year of the withdrawal window")
    a1.set_ylabel("Withdrawal ($k)")
    a1.set_title("Withdrawals on \\$1M, other income \\$0", fontsize=10)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=8)

    d = df[df.case == "jump"]
    width = 0.2
    xs = np.arange(len(STARTS))
    cmap = plt.get_cmap("viridis")
    for j, other in enumerate(OTHERS):
        v = d[d.other == other].extra_level
        a2.bar(xs + (j - 1.5) * width, v, width, color=cmap(j / 3), label=f"${other/1000:g}k")
    a2.set_xticks(xs, [f"${b/1e6:g}M" for b in STARTS])
    a2.set_xlabel("Starting balance")
    a2.set_ylabel("Extra PV tax of level payment over optimum ($)")
    a2.set_title("Cost of ignoring a known revision", fontsize=10)
    a2.grid(alpha=0.3, axis="y")
    a2.legend(title="Other income", fontsize=8, title_fontsize=8)
    fig.suptitle(f"Figure 3.5: a known rate rise during the window makes front-loading "
                 f"worth it (r = {r:.0%})", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_5_window.png", dpi=200)
    plt.close(fig)
    df.to_csv(OUTPUT / "fig3_5_window.csv", index=False)
    for case, (o, l) in paths.items():
        print(case, "optimal $k:", np.round(o / 1e3, 1), "level $k:", np.round(l / 1e3, 1))
    print(df.round(0).to_string(index=False))
    print("Saved", OUTPUT / "fig3_5_window.png")


if __name__ == "__main__":
    main()
