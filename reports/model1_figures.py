"""Figures and tables for the Model 1 report (srs_model.py).

Run from the repo root: python reports/model1_figures.py
"""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import PercentFormatter

from _common import money, save

import srs_model as m

# ---------------------------------------------------------------- Fig 1.1 per-dollar condition
def fig_per_dollar():
    tc = np.linspace(0, 0.24, 241)
    tw = np.linspace(0, 0.24, 241)
    TC, TW = np.meshgrid(tc, tw)
    A = (1 - 0.5 * TW) / (1 - TC) - 1
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    norm = TwoSlopeNorm(vmin=A.min(), vcenter=0, vmax=A.max())
    lv = np.concatenate([np.linspace(A.min(), 0, 13)[:-1], np.linspace(0, A.max(), 31)]) * 100
    norm = TwoSlopeNorm(vmin=A.min() * 100, vcenter=0, vmax=A.max() * 100)
    cf = a1.contourf(TC * 100, TW * 100, A * 100, levels=lv, cmap="RdBu", norm=norm)
    a1.plot(tc * 100, 2 * tc * 100, "k-", lw=2)
    a1.set_ylim(0, 24)
    a1.text(3.2, 20, "SRS loses\n(tc < 0.5·tw)", fontsize=9)
    a1.text(15, 6, "SRS wins\n(tc > 0.5·tw)", fontsize=9)
    a1.set_xlabel("Relief rate at contribution, tc (%)")
    a1.set_ylabel("Marginal rate on the taxable half at withdrawal, tw (%)")
    a1.set_title("Advantage per pre-tax dollar, (1 − 0.5·tw)/(1 − tc) − 1", fontsize=10)
    fig.colorbar(cf, ax=a1, label="Advantage per dollar (%)")

    rs = np.linspace(0.02, 0.09, 50)
    for n, ls in ((10, "-"), (29, "--"), (40, ":")):
        srs = (1 + rs) ** n * (1 - 0.5 * 0.07)
        ordn = (1 - 0.115) * (1 + rs) ** n
        a2.plot(rs * 100, srs / ordn, ls=ls, lw=2, label=f"n = {n} years")
    a2.set_ylim(1.0, 1.15)
    a2.set_xlabel("Annual return, r (%)")
    a2.set_ylabel("SRS wealth / ordinary-account wealth")
    a2.set_title("tc = 11.5%, tw = 7%: the ratio is 1.0904 for every r and n", fontsize=10)
    a2.grid(alpha=0.3)
    a2.legend(fontsize=8)
    fig.suptitle("Figure 1.1: the whole participation decision is tc > 0.5·tw", fontsize=11)
    save(fig, "fig1_1_per_dollar")
    plt.close(fig)
    print("ratio", m.per_dollar_ratio(0.115, 0.07))


# ---------------------------------------------------------------- Fig 1.2 exit-rate staircase
def fig_staircase():
    pots = np.concatenate([np.arange(100_000, 2_000_001, 25_000), np.arange(2_050_000, 16_000_001, 50_000)])
    marg = [m.marginal_exit_rate(p) for p in pots]
    avg = [m.average_exit_rate(p) for p in pots]
    be = [m.breakeven_tc(p) for p in pots]
    fig, ax = plt.subplots(figsize=(11, 5.5), constrained_layout=True)
    ax.step(pots / 1e6, marg, where="post", color="#d62728", lw=2, label="Marginal exit rate (decides: keep contributing?)")
    ax.step(pots / 1e6, be, where="post", color="#1f77b4", lw=2, label="Breakeven relief rate = 0.5 × marginal")
    ax.plot(pots / 1e6, avg, color="#2ca02c", lw=2, label="Average exit rate (evaluates: what did it cost?)")
    ax.axhline(0.12, color="grey", ls=":", lw=1)
    ax.text(10, 0.125, "12% cap = 24% × 50%", fontsize=8, color="grey")
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10, 16], ["$0.1M", "$0.2M", "$0.5M", "$1M", "$2M", "$5M", "$10M", "$16M"])
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel("SRS pot at withdrawal age (log scale)")
    ax.set_ylabel("Rate")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Figure 1.2: exit tax rates by pot size (level 10-year drawdown at 5%, no other income)", fontsize=11)
    save(fig, "fig1_2_exit_rates")
    plt.close(fig)
    for p in (200_000, 400_000, 1_000_000, 2_000_000, 3_000_000, 5_000_000, 8_000_000):
        print(f"pot {p:>10,}: avg {m.average_exit_rate(p):.2%}  marg {m.marginal_exit_rate(p):.1%}  be {m.breakeven_tc(p):.2%}")


# ---------------------------------------------------------------- Fig 1.3 crossover pots
def fig_crossovers():
    rates = [0.0, 0.02, 0.035, 0.07, 0.115]
    pots = [m.participation_crossover_pot(tc) for tc in rates]
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    labels = [f"{tc:.1%}".replace(".0%", "%") for tc in rates] + ["≥ 15%"]
    vals = pots + [None]
    for i, (lab, v) in enumerate(zip(labels, vals)):
        if v:
            ax.bar(i, v, color="#1f77b4")
            ax.text(i, v * 1.15, money(v), ha="center", fontsize=9)
        else:
            ax.text(i, 3e5, "never\n(exit rate\ncaps at 12%)", ha="center", fontsize=9)
    ax.set_yscale("log")
    ax.set_ylim(1e5, 5e7)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_xlabel("Relief rate at contribution, tc")
    ax.set_ylabel("Pot at which the next dollar stops paying (log)")
    ax.grid(alpha=0.3, axis="y")
    ax.set_title("Figure 1.3: participation crossover pot, pot* = 2·L·a(10, 5%)", fontsize=11)
    save(fig, "fig1_3_crossovers")
    plt.close(fig)
    for tc, p in zip(rates, pots):
        print(f"tc {tc:.1%}: {p:,.0f}")


# ---------------------------------------------------------------- Fig 1.4 MAIN heatmaps
TCS = [0.0, 0.02, 0.035, 0.07, 0.115, 0.15, 0.18, 0.20, 0.22, 0.24]
RS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09]
PANELS = [(10, 500_000), (30, 500_000), (10, 3_000_000), (30, 3_000_000)]


def fig_main():
    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5), constrained_layout=True)
    norm = TwoSlopeNorm(vmin=-12, vcenter=0, vmax=30)
    for ax, (n, pot) in zip(axes.flat, PANELS):
        grid = np.array([[100 * (m.per_dollar_ratio(tc, m.marginal_exit_rate(pot, r=r, years=10)) - 1)
                          for tc in TCS] for r in RS])
        im = ax.imshow(grid, cmap="RdBu", norm=norm, aspect="auto", origin="lower")
        for i in range(len(RS)):
            for j in range(len(TCS)):
                v = grid[i, j]
                ax.text(j, i, f"{v:+.1f}" if abs(v) < 10 else f"{v:+.0f}", ha="center", va="center",
                        fontsize=7, color="white" if abs(v) > 15 else "black")
        tws = sorted({round(100 * m.marginal_exit_rate(pot, r=r, years=10), 1) for r in RS})
        ax.set_xticks(range(len(TCS)), [f"{t*100:g}" for t in TCS])
        ax.set_yticks(range(len(RS)), [f"{r*100:.0f}%" for r in RS])
        ax.set_xlabel("Marginal tax rate at contribution, tc (%)")
        ax.set_ylabel("Return, r")
        ax.set_title(f"Horizon n = {n} years, ending balance {money(pot)} "
                     f"(exit rate tw = {' to '.join(f'{t:g}%' for t in (tws[0], tws[-1]))})", fontsize=9)
    fig.colorbar(im, ax=axes, shrink=0.7, label="Advantage per pre-tax dollar (%)")
    fig.suptitle("Figure 1.4: MAIN analysis, return × tax rate at contribution, 2 × 2 of (horizon, ending balance)",
                 fontsize=11)
    save(fig, "fig1_4_main")
    plt.close(fig)
    for pot in (500_000, 3_000_000):
        print(pot, [round(100 * m.breakeven_tc(pot, r=r), 2) for r in RS])


# ---------------------------------------------------------------- Fig 1.5 sensitivity
def fig_sensitivity():
    rs = [r / 1000 for r in range(20, 91, 5)]
    by_r = [m.run(r=r) for r in rs]
    incs = list(range(40_000, 520_001, 10_000))
    by_i = [m.run(chargeable=c) for c in incs]
    yrs = list(range(5, 41))
    by_y = [m.run(contrib_years=y) for y in yrs]
    ois = list(range(0, 100_001, 5_000))
    by_o = [m.run(other_retirement_income=o) for o in ois]

    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), constrained_layout=True)
    a = axes[0, 0]
    a.plot([r * 100 for r in rs], [x["advantage"] / 1e3 for x in by_r], "o-", color="#1f77b4", label="$ advantage")
    a.set_xlabel("Return, r (%)"); a.set_ylabel("Advantage at 73 ($k)")
    b = a.twinx()
    b.plot([r * 100 for r in rs], [x["advantage_pct"] * 100 for x in by_r], "s--", color="#d62728", label="% advantage")
    b.set_ylabel("Advantage (%)", color="#d62728")
    a.set_title("(a) Return: $ rises, % falls", fontsize=10); a.grid(alpha=0.3)
    a = axes[0, 1]
    a.step([c / 1e3 for c in incs], [x["advantage"] / 1e3 for x in by_i], where="mid", color="#1f77b4", lw=2)
    a.set_xlabel("Chargeable income ($k)"); a.set_ylabel("Advantage at 73 ($k)")
    a.set_title("(b) Tax bracket at contribution: a staircase", fontsize=10); a.grid(alpha=0.3)
    a = axes[1, 0]
    a.plot(yrs, [x["advantage"] / 1e3 for x in by_y], "o-", color="#1f77b4", ms=3)
    a.set_xlabel("Years of contributing"); a.set_ylabel("Advantage at 73 ($k)")
    a.set_title("(c) Years of contributing", fontsize=10); a.grid(alpha=0.3)
    a = axes[1, 1]
    a.plot([o / 1e3 for o in ois], [x["advantage"] / 1e3 for x in by_o], "o-", color="#1f77b4", ms=3)
    a.set_xlabel("Other taxable income in each drawdown year ($k)"); a.set_ylabel("Advantage at 73 ($k)")
    a.set_title("(d) Other retirement income", fontsize=10); a.grid(alpha=0.3)
    fig.suptitle("Figure 1.5: one factor at a time from the base case "
                 "(\\$120k chargeable, \\$15,300 a year for 29 years, 5%, level drawdown)", fontsize=11)
    save(fig, "fig1_5_sensitivity")
    plt.close(fig)
    print("by r:", [(r, round(x["advantage"]), round(x["advantage_pct"] * 100, 2)) for r, x in zip(rs, by_r)][::2])
    print("income range", round(min(x["advantage"] for x in by_i)), round(max(x["advantage"] for x in by_i)))
    print("years range", round(by_y[0]["advantage"]), round(by_y[-1]["advantage"]))
    print("other income", round(by_o[0]["advantage"]), round(by_o[-1]["advantage"]))


def tables():
    b = m.run()
    print("BASE", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in b.items() if not isinstance(v, (list, dict))})
    for c in (60_000, 100_000, 160_000, 200_000, 320_000, 500_000):
        x = m.run(chargeable=c)
        print(c, round(x["relief_rate"], 4), round(x["advantage"]), round(x["advantage_pct"] * 100, 2))
    for bal in (50_000, 100_000, 200_000, 400_000):
        print("early", bal, m.early_withdrawal(bal))


if __name__ == "__main__":
    fig_per_dollar()
    fig_staircase()
    fig_crossovers()
    fig_main()
    fig_sensitivity()
    tables()
