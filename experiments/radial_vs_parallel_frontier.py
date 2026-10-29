"""
Standalone experiment — NOT part of the three built models (srs_model.py,
srs_simulation.py, srs_tax_regime.py). Nothing in those files imports this, and
nothing here is imported by them. Delete this whole directory and the three
models still work and still pass their tests.

Question it answers: when the SRS tax wedge (relief at contribution, 50%-taxable
at withdrawal) is applied to a whole efficient frontier rather than a single
point, does it shift the frontier PARALLEL (a flat additive bump to annualized
return, same at every risk level) or RADIALLY (every point scaled by a constant
factor, so the frontier gets measurably steeper at higher risk)?

Raised in a 2026-10-17 WhatsApp discussion about Model 1a (the investment-
universe/leverage extension — not yet built). A collaborator's derivation
computed an annualized additive shift (+0.32%/yr at entry, -0.08%/yr at
withdrawal, net +0.24%/yr) but described the *combined* effect as "radial
expansion from the origin" making the frontier "slightly steeper." Those two
descriptions are not obviously the same transform, and which one is right
changes where any A-vs-SRS breakeven risk level would fall once Model 1a is
actually built with real asset-class data. This script derives the exact
relationship in closed form and checks both verbal claims against it.

Only srs_model.per_dollar_ratio is reused — the already-tested, horizon-
independent SRS/ordinary terminal-wealth ratio (docs/findings.md #1). No tax
logic is re-derived here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import srs_model as m  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------- the exact relationship
def annualized_wedge(tc, tw, years):
    """
    k = per_dollar_ratio(tc, tw) is the SRS/ordinary ratio of TERMINAL WEALTH for one
    pre-tax dollar — proven horizon-independent (docs/findings.md #1). Spreading that
    one-off ratio evenly over `years` of holding gives the annualized "wedge" delta
    such that (1 + delta)^years = k.
    """
    k = m.per_dollar_ratio(tc, tw)
    delta = k ** (1.0 / years) - 1.0
    return delta, k


def exact_srs_point(mu_b, sigma_b, delta):
    """
    The exact transform. The tax wedge multiplies TERMINAL WEALTH by the same factor
    regardless of which portfolio was chosen (per_dollar_ratio doesn't depend on r), so
    for every portfolio on frontier B:
        (1 + r_srs) = (1 + delta) * (1 + r_b)
        =>  r_srs   = r_b + delta + delta * r_b
    Taking the standard deviation of both sides (delta is a constant, not random):
        sigma_srs = (1 + delta) * sigma_b
    This is radial scaling of the GROSS return factor (1+r) from the true origin —
    equivalently, radial scaling of NET return from the point (sigma=0, mu=-100%), not
    from (0, 0). At realistic plotting ranges (mu, sigma a few percent), -100% is far
    off the chart, which is why this looks almost-but-not-quite like a parallel shift.
    """
    mu_srs = mu_b + delta + delta * mu_b
    sigma_srs = (1.0 + delta) * sigma_b
    return mu_srs, sigma_srs


def parallel_approx_point(mu_b, sigma_b, delta):
    """
    First-order approximation: r_srs ~= r_b + delta, sigma unchanged. This drops the
    delta*r_b cross-term and the sigma stretch from exact_srs_point — valid whenever
    delta is small, which the script checks numerically rather than assuming.
    """
    return mu_b + delta, sigma_b


def naive_radial_from_origin_point(mu_b, sigma_b, k):
    """
    The LITERAL reading of "the frontier expands radially from the origin" using the
    raw (un-annualized) multiplier k directly on the annualized (sigma, mu) axes — i.e.
    treating the chart's %-per-year numbers as the thing k scales. Included to show how
    different this is from what the chart's own numbers (e.g. B: 3.00% -> B'': 3.24%)
    actually used, which was the annualized delta, not raw k.
    """
    return k * mu_b, k * sigma_b


# --------------------------------------------------------------- toy frontier (illustrative)
def toy_frontier(sigma, mu0, slope, power):
    """
    mu0 + slope * sigma**power — a generic concave risk/return curve for comparing the
    three transforms against each other on common ground. NOT calibrated to real asset
    data (no real SRS-eligible-vs-general-universe return/variance inputs used) — that
    calibration is real Model 1a work and is explicitly out of scope here.
    """
    return mu0 + slope * (sigma ** power)


# --------------------------------------------------------------------------- experiment
CASES = [
    {"label": "project base case (tc=11.5%, tw=7%)", "tc": 0.115, "tw": 0.07, "years": 33},
    {"label": "WhatsApp example (tc=10%, tw=5%)", "tc": 0.10, "tw": 0.05, "years": 33},
]

# Illustrative frontier B: ~3.0% at sigma=0 rising to ~4.7% at sigma=13%, power 0.5
# (sqrt-concave). Pure illustration, loosely shaped like the collaborator's chart.
FRONTIER_B = {"mu0": 0.030, "slope": 0.04715, "power": 0.5}
SIGMA_GRID = [round(0.01 * i, 4) for i in range(0, 21)]  # 0% .. 20% in 1pp steps


def run_case(case):
    delta, k = annualized_wedge(case["tc"], case["tw"], case["years"])
    rows = []
    for sigma_b in SIGMA_GRID:
        mu_b = toy_frontier(sigma_b, **FRONTIER_B)
        mu_exact, sigma_exact = exact_srs_point(mu_b, sigma_b, delta)
        mu_par, sigma_par = parallel_approx_point(mu_b, sigma_b, delta)
        mu_naive, sigma_naive = naive_radial_from_origin_point(mu_b, sigma_b, k)
        rows.append({
            "sigma_b_pct": round(sigma_b * 100, 4),
            "mu_b_pct": round(mu_b * 100, 6),
            "mu_exact_pct": round(mu_exact * 100, 6),
            "sigma_exact_pct": round(sigma_exact * 100, 6),
            "mu_parallel_approx_pct": round(mu_par * 100, 6),
            "mu_naive_radial_raw_k_pct": round(mu_naive * 100, 6),
            "exact_minus_parallel_pp": round((mu_exact - mu_par) * 100, 6),
            "exact_minus_naive_radial_pp": round((mu_exact - mu_naive) * 100, 6),
        })
    max_exact_vs_parallel_gap = max(abs(r["exact_minus_parallel_pp"]) for r in rows)
    max_exact_vs_naive_gap = max(abs(r["exact_minus_naive_radial_pp"]) for r in rows)
    sigma_stretch_factor = 1.0 + delta  # sigma_exact / sigma_b, constant across the grid
    return {
        "label": case["label"], "tc": case["tc"], "tw": case["tw"], "years": case["years"],
        "delta_annualized_wedge": delta, "k_terminal_multiplier": k,
        "sigma_stretch_factor_exact_vs_parallel": sigma_stretch_factor,
        "max_abs_gap_exact_vs_parallel_pp": max_exact_vs_parallel_gap,
        "max_abs_gap_exact_vs_naive_radial_pp": max_exact_vs_naive_gap,
        "rows": rows,
    }


def main():
    results = [run_case(c) for c in CASES]

    print("=" * 78)
    print("Radial vs. parallel frontier-shift experiment (not part of the 3 models)")
    print("=" * 78)
    for r in results:
        print(f"\n{r['label']}  (years={r['years']})")
        print(f"  k (terminal-wealth multiplier, from srs_model.per_dollar_ratio) = {r['k_terminal_multiplier']:.6f}")
        print(f"  delta (annualized wedge, (1+delta)^years = k)                   = {r['delta_annualized_wedge']*100:.4f}%/yr")
        print(f"  exact sigma stretch factor (sigma_exact = stretch * sigma_b)    = {r['sigma_stretch_factor_exact_vs_parallel']:.6f}")
        print(f"  max |exact - parallel_approx| across sigma in [0%,20%]          = {r['max_abs_gap_exact_vs_parallel_pp']:.6f} pp")
        print(f"  max |exact - naive_radial_from_origin(raw k)| across same grid  = {r['max_abs_gap_exact_vs_naive_radial_pp']:.6f} pp")

    ratios = [r["max_abs_gap_exact_vs_naive_radial_pp"] / r["max_abs_gap_exact_vs_parallel_pp"] for r in results]
    ratio_str = f"{sum(ratios) / len(ratios):.0f}x"
    print("\n" + "-" * 78)
    print("Reading: the 'parallel' approximation (flat additive annualized bump, sigma")
    print("unchanged) tracks the exact transform to within ~0.01-0.02pp across the whole")
    print("0-20% risk range. The literal 'radial scaling by the raw multiplier k' reading")
    print(f"is about {ratio_str} further from the exact transform over the same range -- roughly")
    print("one order of magnitude worse, not the dominant error source either way. The")
    print("exact transform IS technically radial, but from (sigma=0, mu=-100%) in net-")
    print("return space, not from (0,0) -- at realistic sigma/mu this is indistinguishable")
    print("from a parallel shift. Conclusion: it is safe for Model 1a to use the cheap")
    print("parallel-shift approximation; the 'radial from the origin, steeper' framing in")
    print("the WhatsApp derivation describes a real but small effect, an order of")
    print("magnitude smaller than 'radial from the origin' implies if taken literally")
    print("with the raw (un-annualized) multiplier instead of the annualized delta.")

    out_path = os.path.join(_HERE, "radial_vs_parallel_results.json")
    with open(out_path, "w") as f:
        json.dump({
            "frontier_b_illustrative_params": FRONTIER_B,
            "note": "Illustrative toy frontier only -- not calibrated to real asset-class "
                    "data. Not a Model 1a finding. Exists to compare the three transform "
                    "methods against each other on common ground.",
            "cases": results,
        }, f, indent=2)
    print(f"\nWrote {out_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, len(results), figsize=(7 * len(results), 5), squeeze=False)
        for ax, r in zip(axes[0], results):
            sigmas = [row["sigma_b_pct"] for row in r["rows"]]
            mu_b = [row["mu_b_pct"] for row in r["rows"]]
            mu_exact = [row["mu_exact_pct"] for row in r["rows"]]
            mu_par = [row["mu_parallel_approx_pct"] for row in r["rows"]]
            mu_naive = [row["mu_naive_radial_raw_k_pct"] for row in r["rows"]]
            ax.plot(sigmas, mu_b, label="B (no SRS wedge)", color="gray", linestyle="--")
            ax.plot(sigmas, mu_exact, label="exact transform", color="black", linewidth=2)
            ax.plot(sigmas, mu_par, label="parallel approx", color="tab:blue", linestyle=":")
            ax.plot(sigmas, mu_naive, label="naive radial (raw k)", color="tab:red", linestyle="-.")
            ax.set_title(r["label"])
            ax.set_xlabel("sigma (% per year)")
            ax.set_ylabel("mu (% per year)")
            ax.legend(fontsize=8)
        fig.suptitle("Exact transform tracks 'parallel approx', not 'naive radial (raw k)'")
        fig.tight_layout()
        png_path = os.path.join(_HERE, "radial_vs_parallel_frontier.png")
        fig.savefig(png_path, dpi=150)
        print(f"Wrote {png_path}")
    except ImportError:
        print("\n(matplotlib not available -- skipped the plot, JSON results still written)")


if __name__ == "__main__":
    main()
