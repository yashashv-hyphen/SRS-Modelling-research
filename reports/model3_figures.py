"""Figures and tables for the Model 3 report (srs_tax_regime.py).

Run from the repo root or reports/: python reports/model3_figures.py
"""
import matplotlib.pyplot as plt
import numpy as np

from _common import money, save

import srs_model as m
import srs_tax_regime as tr

F = tr.FACTS


def fig_top_rate():
    hist = tr.HISTORY
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    xs, ys = [], []
    for i, h in enumerate(hist):
        end = hist[i + 1]["ya"] if i + 1 < len(hist) else 2026
        xs += [h["ya"], end]
        ys += [h["brackets"][-1][1] * 100] * 2
    a1.plot(xs, ys, color="black", lw=2.2, label="Actual (IRAS, YA2003 to today)")
    disc, smooth = tr.project_discrete(50), tr.project_smooth(50)
    yrs = np.arange(0, 51)
    a1.step(2024 + yrs, [disc[y][-1][1] * 100 for y in yrs], where="post", color="#d62728", lw=1.8,
            label=f"Discrete: +{F['avg_step_per_revision']*100:.2f}pp every {F['avg_interval_years']:.1f} years")
    a1.plot(2024 + yrs, [smooth[y][-1][1] * 100 for y in yrs], "--", color="#1f77b4", lw=1.8,
            label=f"Smooth: +{F['smooth_drift_per_year']*100:.3f}pp a year")
    for ya in F["revision_yas"]:
        a1.axvline(ya, color="grey", ls=":", lw=0.8)
    a1.set_xlabel("Year of assessment")
    a1.set_ylabel("Top marginal rate (%)")
    a1.set_title("(a) Top rate, actual and projected to 2074", fontsize=10)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=8)

    colours = ["#9e9e9e", "#bcbd22", "#17becf", "#1f77b4", "#ff7f0e", "#d62728"]
    x = np.linspace(0, 400_000, 2001)
    for c, h in zip(colours, hist):
        a2.step(x / 1e3, [m.marginal_rate(v, h["brackets"]) * 100 for v in x], where="post", color=c, lw=1.6,
                label=f"YA{h['ya']}")
    a2.set_xlabel("Chargeable income ($k)")
    a2.set_ylabel("Marginal rate (%)")
    a2.set_title("(b) The six schedules: edges up to $80k never move", fontsize=10)
    a2.grid(alpha=0.3)
    a2.legend(fontsize=8)
    fig.suptitle("Figure 3.1: Singapore's resident income tax, YA2003 to today, and two 50-year projections", fontsize=11)
    save(fig, "fig3_1_top_rate")
    plt.close(fig)
    print("FACTS", F)
    for h in hist:
        print(h["ya"], len(h["brackets"]), h["brackets"][-1][1], h["effective_through"])
    for y in (10, 20, 30, 40, 50):
        print("top", y, round(disc[y][-1][1] * 100, 2), round(smooth[y][-1][1] * 100, 2))


def fig_historical_frontier():
    rows = tr.historical_frontier(relief_rates=(0.0, 0.02, 0.035, 0.07, 0.115))
    yas = [h["ya"] for h in tr.HISTORY]
    rates = (0.0, 0.02, 0.035, 0.07, 0.115)
    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    width = 0.15
    cols = ["#9e9e9e", "#2ca02c", "#17becf", "#1f77b4", "#d62728"]
    for j, (tc, c) in enumerate(zip(rates, cols)):
        vals = [next(r["crossover_pot"] for r in rows if r["year_of_assessment"] == ya and r["relief_rate"] == tc)
                for ya in yas]
        xs = np.arange(len(yas)) + (j - 2) * width
        ax.bar(xs, [v or 0 for v in vals], width, color=c, label=f"tc = {tc:.1%}")
        for x, v in zip(xs, vals):
            if not v:
                ax.text(x, 3.2e5, "none", rotation=90, ha="center", fontsize=7, color=c)
        print(tc, [None if v is None else round(v) for v in vals])
    ax.set_yscale("log")
    ax.set_ylim(2e5, 3e7)
    ax.set_xticks(range(len(yas)), [f"YA{y}" for y in yas])
    ax.set_ylabel("Crossover pot (log): next dollar stops paying above this")
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8, ncol=5, loc="upper left")
    ax.set_title("Figure 3.2: participation crossover pot under each real schedule "
                 "(\"none\" = contributing always pays)", fontsize=11)
    save(fig, "fig3_2_historical_frontier")
    plt.close(fig)


def fig_projected_frontier():
    rows = tr.projected_frontier(relief_rates=(0.07, 0.115), checkpoints=tuple(range(0, 51, 1)))
    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    for tc, c in ((0.115, "#d62728"), (0.07, "#1f77b4")):
        d = [r for r in rows if r["relief_rate"] == tc]
        ax.step([r["year"] for r in d], [r["crossover_discrete"] for r in d], where="post", color=c, lw=2,
                label=f"tc = {tc:.1%}, discrete")
        ax.step([r["year"] for r in d], [r["crossover_smooth"] for r in d], where="post", color=c, lw=1.5, ls="--",
                label=f"tc = {tc:.1%}, smooth")
    ax.set_yscale("log")
    ax.set_yticks([3e5, 5e5, 1e6, 2e6, 5e6, 1e7, 1.5e7], ["$0.3M", "$0.5M", "$1M", "$2M", "$5M", "$10M", "$15M"])
    ax.set_xlabel("Years from today")
    ax.set_ylabel("Crossover pot (log)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title("Figure 3.3: projected participation crossover pot, discrete vs smooth drift", fontsize=11)
    save(fig, "fig3_3_projected_frontier")
    plt.close(fig)
    for r in tr.projected_frontier():
        print("proj", r["relief_rate"], r["year"], round(r["crossover_discrete"] or 0), round(r["crossover_smooth"] or 0))


def fig_macro():
    rows = tr.MACRO
    col = {"cut": "#2ca02c", "rise": "#d62728", None: "#c7c7c7", "": "#c7c7c7"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True, gridspec_kw={"width_ratios": [2.2, 1]})
    yrs = [int(r["year"]) for r in rows]
    a1.bar(yrs, [r["prior_year_real_gdp_growth_pct"] for r in rows], color=[col[r["change_direction"]] for r in rows])
    a1.plot(yrs, [r["prior_year_cpi_inflation_pct"] for r in rows], "k.-", lw=1, label="Prior-year CPI inflation")
    for r in rows:
        if r["change_direction"]:
            a1.annotate(r["change_direction"], (int(r["year"]), r["prior_year_real_gdp_growth_pct"]), xytext=(0, 4),
                        textcoords="offset points", ha="center", fontsize=8, color=col[r["change_direction"]])
    a1.axhline(0, color="black", lw=0.6)
    a1.set_xlabel("Year")
    a1.set_ylabel("Previous year's real GDP growth (bars) / CPI (%)")
    a1.grid(alpha=0.3, axis="y")
    a1.legend(fontsize=8)
    a1.set_title("Green = rate cut that year, red = rate rise", fontsize=10)
    d = tr.macro_by_direction()
    keys = ["cut", "rise", "none"]
    a2.bar(range(3), [d[k]["avg_prior_year_real_gdp_growth"] for k in keys], color=["#2ca02c", "#d62728", "#c7c7c7"])
    for i, k in enumerate(keys):
        v = d[k]["avg_prior_year_real_gdp_growth"]
        a2.text(i, v + 0.1, f"{v:.2f}%", ha="center", fontsize=9)
    a2.set_xticks(range(3), ["Cuts\n2006, 2007, 2012", "Rises\n2017, 2024", f"No change\n({d['none']['n']} years)"])
    a2.set_ylabel("Average previous-year real GDP growth (%)")
    a2.grid(alpha=0.3, axis="y")
    a2.set_title("Averages by direction", fontsize=10)
    mc = tr.macro_correlation_facts()
    fig.suptitle(f"Figure 3.4: tax changes vs the previous year's economy, 2003 to 2025 "
                 f"(pooled correlation with GDP {mc['correlation_change_vs_prior_year_gdp']:+.2f})", fontsize=11)
    save(fig, "fig3_4_macro")
    plt.close(fig)
    print("MACRO", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in mc.items()})
    print("DIR", {k: (v["years"], round(v["avg_prior_year_real_gdp_growth"], 2), round(v["avg_prior_year_cpi_inflation"], 2)) for k, v in d.items() if k != "none"})


if __name__ == "__main__":
    fig_top_rate()
    fig_historical_frontier()
    fig_projected_frontier()
    fig_macro()
