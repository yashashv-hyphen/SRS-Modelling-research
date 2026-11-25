"""Figures and tables for the Model 2 report (srs_simulation.py).

Run from the repo root or reports/: python reports/model2_figures.py
"""
import json

import matplotlib.pyplot as plt
import numpy as np

from _common import OUT, money, save

import srs_model as m
import srs_simulation as sim

POT = 953_537.0
R = 0.05
BRK = [None] * 10


def deemed(res, oi=0):
    """Total tax including the deemed withdrawal of the residual at window close."""
    return res["total_tax"] + m.tax(oi + m.INCLUSION * res["residual"]) - m.tax(oi)


# ---------------------------------------------------------- Fig 2.1 MAIN policy grids
def fig_policy():
    bals = [2_000_000, 1_500_000, 1_000_000, 600_000, 300_000, 100_000]
    years = list(range(10, 0, -1))
    incomes = [0, 40_000, 80_000, 160_000]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    for ax, oi in zip(axes.flat, incomes):
        W = np.array([[b * R / (1 - (1 + R) ** (-k)) for k in years] for b in bals])
        M = np.array([[m.marginal_rate(oi + 0.5 * w) * 100 for w in row] for row in W])
        im = ax.imshow(M, cmap="YlOrRd", vmin=0, vmax=24, aspect="auto")
        for i in range(len(bals)):
            for j in range(len(years)):
                ax.text(j, i, money(W[i, j]), ha="center", va="center", fontsize=7,
                        color="white" if M[i, j] > 16 else "black")
        ax.set_xticks(range(len(years)), years)
        ax.set_yticks(range(len(bals)), [money(b) for b in bals])
        ax.set_xlabel("Years left in the withdrawal window")
        ax.set_ylabel("SRS balance at the start of the year")
        ax.set_title(f"Non-SRS income {money(oi) if oi else '$0'}", fontsize=10)
    fig.colorbar(im, ax=axes, shrink=0.7, label="Marginal rate the withdrawal faces (%)")
    fig.suptitle("Figure 2.1: MAIN analysis, recommended withdrawal by balance × years left, "
                 "at four non-SRS incomes (r = 5%, today's schedule)", fontsize=11)
    save(fig, "fig2_1_policy")
    plt.close(fig)
    w = 1_000_000 * R / (1 - (1 + R) ** -10)
    print("w*($1M,10)", round(w), {oi: m.marginal_rate(oi + 0.5 * w) for oi in incomes})


# ---------------------------------------------------------- Fig 2.2 / 2.3 one path, three strategies
def run3(path, oi):
    lvl = sim.mpc_drawdown(POT, 10, path, BRK, other_income=oi, r_forecast=R, strategy="mpc", use_dp=False)
    dp = sim.mpc_drawdown(POT, 10, path, BRK, other_income=oi, r_forecast=R, strategy="mpc", use_dp=True, grid_size=160)
    r40 = sim.mpc_drawdown(POT, 10, path, BRK, other_income=oi, r_forecast=R, strategy="rule40")
    return {"Level drawdown (re-planned)": lvl, "Dynamic programming (re-planned)": dp, "$40,000 a year": r40}


STYLE = {"Level drawdown (re-planned)": ("#1f77b4", "o-"), "Dynamic programming (re-planned)": ("#ff7f0e", "D--"),
         "$40,000 a year": ("#7f7f7f", "s:")}


def fig_paths():
    rng = np.random.default_rng(17)
    vol = sim.historical_block_bootstrap_path(10, rng=rng)
    flat = [R] * 10
    out = {"return_path": list(vol), "volatile": [], "flat": {}}
    for name, path, fname, title in (
            ("volatile", vol, "fig2_2_volatile_path", "Figure 2.2: one real S&P 500 block-bootstrap path (seed 17)"),
            ("flat", flat, "fig2_3_flat_path", "Figure 2.3: the market returns exactly 5% every year")):
        res = run3(path, 0)
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True,
                                     gridspec_kw={"width_ratios": [2, 1]})
        yrs = np.arange(1, 11)
        for lab, r in res.items():
            c, st = STYLE[lab]
            a1.plot(yrs, np.array(r["withdrawals"]) / 1e3, st, color=c, label=f"{lab}: tax {money(deemed(r))}")
        a1.set_xticks(yrs)
        a1.set_xlabel("Year of the withdrawal window")
        a1.set_ylabel("Withdrawal ($k)")
        a1.grid(alpha=0.3)
        a1.legend(fontsize=8)
        a1.set_title(f"Withdrawals on a {money(POT)} pot, other income $0 (tax incl. deemed residual)", fontsize=9)
        a2.bar(yrs, np.array(path) * 100, color=["#d62728" if x < 0 else "#2ca02c" for x in path])
        a2.set_xticks(yrs)
        a2.set_xlabel("Year")
        a2.set_ylabel("Realised return (%)")
        a2.grid(alpha=0.3, axis="y")
        a2.set_title("Market return each year", fontsize=9)
        fig.suptitle(title, fontsize=11)
        save(fig, fname)
        plt.close(fig)
        for lab, r in res.items():
            print(name, lab, [round(w) for w in r["withdrawals"]], "residual", round(r["residual"]), "tax", round(deemed(r)))
        if name == "flat":
            out["flat"] = {lab: {"tax": deemed(r), "residual": r["residual"]} for lab, r in res.items()}
    print("vol path", [round(x, 4) for x in vol])
    for oi in (0, 40_000, 80_000, 160_000):
        res = run3(vol, oi)
        row = {"other_income": oi, **{lab: {"tax": deemed(r, oi), "residual": r["residual"]} for lab, r in res.items()}}
        out["volatile"].append(row)
        print("T3", oi, {k[:5]: (round(v["tax"]), round(v["residual"])) for k, v in row.items() if k != "other_income"})
    return out


# ---------------------------------------------------------- Fig 2.4 strategy tax vs contribution years
def fig_strategy():
    rows = []
    for y in range(10, 37, 2):
        pot = m.run(contrib_years=y)["srs_at_retirement"]
        lvl = m.run(contrib_years=y, strategy="level")["total_tax"]
        f40 = m.run(contrib_years=y, strategy="fixed40")["total_tax"]
        dp = sim.mpc_drawdown(pot, 10, [R] * 10, BRK, other_income=0, r_forecast=R, strategy="mpc",
                              use_dp=True, grid_size=160)["total_tax"]
        rows.append((y, pot, lvl, dp, f40))
    y, pot, lvl, dp, f40 = map(np.array, zip(*rows))
    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    ax.plot(y, lvl / 1e3, "o-", color="#1f77b4", label="Level drawdown (closed form)")
    ax.plot(y, dp / 1e3, "D", color="#ff7f0e", mfc="none", label="Dynamic programming (grid solver)")
    ax.plot(y, f40 / 1e3, "s:", color="#7f7f7f", label="$40,000 a year")
    ax.set_xlabel("Years of contributing (pot grows with years)")
    ax.set_ylabel("Total drawdown tax ($k)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax.set_title("Figure 2.4: total tax under three withdrawal strategies, flat 5% return, other income $0", fontsize=11)
    save(fig, "fig2_4_strategy_tax")
    plt.close(fig)
    for r in rows:
        print("S", r[0], round(r[1]), round(r[2]), round(r[3]), round(r[4]))


# ---------------------------------------------------------- Fig 2.5 Monte Carlo
def fig_monte_carlo():
    inc = sim.advantage_by_income(n_paths=200, seed=42)
    ret = sim.advantage_by_return(chargeable=120_000, n_paths=200, seed=42)
    reg = sim.advantage_by_tax_regime(chargeable=120_000, n_paths=200, seed=42)
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)

    def band(ax, x, rows, key="advantage", scale=1e3, xlab=""):
        med = np.array([r[key]["median"] for r in rows]) / scale
        lo = np.array([r[key]["p10"] for r in rows]) / scale
        hi = np.array([r[key]["p90"] for r in rows]) / scale
        ax.fill_between(x, lo, hi, color="#1f77b4", alpha=0.2, label="10th to 90th percentile")
        ax.plot(x, med, "o-", color="#1f77b4", label="Median")
        ax.set_xlabel(xlab)
        ax.grid(alpha=0.3)

    band(a1, [r["income"] / 1e3 for r in inc], inc, xlab="Chargeable income ($k)")
    a1.set_ylabel("SRS advantage at the end ($k)")
    a1.set_title("(a) By income", fontsize=10)
    a1.legend(fontsize=8)
    band(a2, [r["mean_return"] * 100 for r in ret], ret, xlab="Average market return (%)")
    a2.set_title("(b) By average return ($120k income)", fontsize=10)
    labels = [r["regime"] for r in reg]
    med = [r["advantage"]["median"] / 1e3 for r in reg]
    lo = [r["advantage"]["p10"] / 1e3 for r in reg]
    hi = [r["advantage"]["p90"] / 1e3 for r in reg]
    a3.bar(range(3), med, color="#1f77b4")
    a3.errorbar(range(3), med, yerr=[np.subtract(med, lo), np.subtract(hi, med)], fmt="none", color="black", capsize=5)
    a3.set_xticks(range(3), [lab.replace(" (", "\n(").replace(" + ", "\n+ ") for lab in labels], fontsize=8)
    a3.set_title("(c) By tax future ($120k income)", fontsize=10)
    a3.grid(alpha=0.3, axis="y")
    fig.suptitle("Figure 2.5: Monte Carlo, 200 simulated lifetimes per point (lognormal returns, "
                 "15% volatility, 2% wage growth, seed 42)", fontsize=11)
    save(fig, "fig2_5_monte_carlo")
    plt.close(fig)
    for r in inc:
        a = r["advantage"]
        print("inc", r["income"], round(a["median"]), round(a["p10"]), round(a["p90"]), round(r["total_relief_received"]["median"]))
    for r in ret:
        print("ret", r["mean_return"], round(r["advantage"]["median"]), round(r["advantage_pct"]["median"] * 100, 1))
    for r in reg:
        a = r["advantage"]
        print("reg", r["regime"], round(a["median"]), round(a["p10"]), round(a["p90"]))
    return {"income": inc, "return": ret, "regime": reg}


# ---------------------------------------------------------- Fig 2.6 early exit
def fig_early_exit():
    incomes = [0, 100_000, 300_000, 500_000]
    ytl = list(range(1, 10))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for oi, c in zip(incomes, ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728"]):
        vals = [sim.early_exit_breakeven_excess(POT, y, R, oi) * 100 for y in ytl]
        a1.plot(ytl, vals, "o-", color=c, label=f"Other income {money(oi) if oi else '$0'}")
    a1.set_xlabel("Years left before the penalty-free unlock")
    a1.set_ylabel("Excess return needed over staying invested (% a year)")
    a1.set_title(f"(a) Breakeven hurdle, {money(POT)} pot, 5% forecast", fontsize=10)
    a1.grid(alpha=0.3)
    a1.legend(fontsize=8)

    balance_path = [POT * (1 - i / 10) for i in range(11)]
    lams = [0.05, 0.1, 0.2, 0.3, 0.5]
    means = [0.03, 0.05, 0.08]
    for mx, c in zip(means, ["#7f7f7f", "#1f77b4", "#d62728"]):
        fr = [sim.simulate_early_exit_portfolio(balance_path, R, lam=l, mean_excess=mx, n_paths=2000, seed=42)
              ["fraction_that_ever_exit_early"] * 100 for l in lams]
        a2.plot(lams, fr, "o-", color=c, label=f"Mean excess offered {mx:.0%}")
    a2.set_xlabel("Opportunities arriving per year, λ")
    a2.set_ylabel("Lifetimes that ever exit early (%)")
    a2.set_title("(b) Simulated arrivals, 2,000 lifetimes per point", fontsize=10)
    a2.grid(alpha=0.3)
    a2.legend(fontsize=8)
    fig.suptitle("Figure 2.6: breaking the lock-up early as a real option", fontsize=11)
    save(fig, "fig2_6_early_exit")
    plt.close(fig)
    for oi in incomes:
        print("hurdle 5y", oi, round(sim.early_exit_breakeven_excess(POT, 5, R, oi) * 100, 2),
              "1y", round(sim.early_exit_breakeven_excess(POT, 1, R, oi) * 100, 2),
              "9y", round(sim.early_exit_breakeven_excess(POT, 9, R, oi) * 100, 2))
    p = sim.simulate_early_exit_portfolio(balance_path, R, lam=0.2, mean_excess=0.05, n_paths=2000, seed=42)
    print("base poisson", p["fraction_that_ever_exit_early"], p["exit_year_given_exit"])


if __name__ == "__main__":
    fig_policy()
    data = {"paths": fig_paths()}
    fig_strategy()
    fig_early_exit()
    data["monte_carlo"] = fig_monte_carlo()
    with open(OUT / "model2_numbers.json", "w") as f:
        json.dump(data, f, indent=1, default=float)
