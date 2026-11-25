"""Figure 3.6: tax revisions against the previous year's growth and inflation.

Data: data/sg_macro_tax_history_2003_2025.csv ([VERIFY] primary source:
presumed SingStat for CPI/GDP). Backward-looking only; not a forecast.

Run from the repo root: python -m srs_basic.figures.fig3_6_macro
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from srs_basic import config

OUTPUT = Path(config.OUTPUT_DIR)
MACRO_CSV = "data/sg_macro_tax_history_2003_2025.csv"
COLOUR = {"cut": "#2ca02c", "rise": "#d62728", "none": "#c7c7c7"}


def main():
    df = pd.read_csv(MACRO_CSV)
    df["direction"] = df.change_direction.fillna("none")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True,
                                 gridspec_kw={"width_ratios": [2.2, 1]})
    a1.bar(df.year, df.prior_year_real_gdp_growth_pct,
           color=[COLOUR[d] for d in df.direction])
    a1.plot(df.year, df.prior_year_cpi_inflation_pct, "k.-", lw=1, label="Prior-year CPI inflation")
    for _, row in df[df.direction != "none"].iterrows():
        a1.annotate(row.direction, (row.year, row.prior_year_real_gdp_growth_pct),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8,
                    color=COLOUR[row.direction])
    a1.axhline(0, color="black", lw=0.6)
    a1.set_xlabel("Year of assessment")
    a1.set_ylabel("Previous year's growth / inflation (%)")
    a1.set_title("Bars: previous year's real GDP growth (green = cut, red = rise)", fontsize=10)
    a1.grid(alpha=0.3, axis="y")
    a1.legend(fontsize=8)

    summary = (df.groupby("direction")
                 .agg(years=("year", lambda s: ", ".join(map(str, s)) if len(s) < 6 else f"{len(s)} years"),
                      gdp=("prior_year_real_gdp_growth_pct", "mean"),
                      cpi=("prior_year_cpi_inflation_pct", "mean"))
                 .reindex(["cut", "rise", "none"]))
    xs = np.arange(3)
    a2.bar(xs - 0.2, summary.gdp, 0.4, color=[COLOUR[d] for d in summary.index], label="Real GDP growth")
    a2.bar(xs + 0.2, summary.cpi, 0.4, color="white", edgecolor="black", hatch="//", label="CPI inflation")
    for x, v in zip(xs, summary.gdp):
        a2.text(x - 0.2, v + 0.1, f"{v:.1f}%", ha="center", fontsize=8)
    a2.set_xticks(xs, ["Cut years", "Rise years", "No change"])
    a2.set_ylabel("Average of the previous year (%)")
    a2.set_title("Averages by direction", fontsize=10)
    a2.grid(alpha=0.3, axis="y")
    a2.legend(fontsize=8)

    flag = (df.direction != "none").astype(float)
    corr = np.corrcoef(flag, df.prior_year_real_gdp_growth_pct)[0, 1]
    fig.suptitle(f"Figure 3.6: Singapore cut rates after strong years and raised them after weak "
                 f"ones (5 changes, 2003 to 2025; pooled correlation {corr:+.2f})", fontsize=11)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fig3_6_macro.png", dpi=200)
    plt.close(fig)
    print(summary.round(2).to_string())
    print(f"pooled correlation (changed vs prior-year real GDP growth): {corr:+.3f}")
    print("Saved", OUTPUT / "fig3_6_macro.png")


if __name__ == "__main__":
    main()
