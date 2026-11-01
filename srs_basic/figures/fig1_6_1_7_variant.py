"""Figures 1.6 and 1.7: fixed annual contribution instead of fixed balance."""

from srs_basic.figures.panels import sweep_figure

C = 15_300  # SRS annual cap for citizens and PRs

# Figure 1.6: base horizon, plus the fixed-B base case for comparison
sweep_figure(
    "fig1_6_variant",
    f"Figure 1.6: fixed balance vs fixed contribution of \\${C:,} a year (N = 20)",
    [("Fixed balance B = \\$1M", {"N": 20, "B": 1_000_000}),
     (f"Fixed contribution \\${C:,}/yr", {"N": 20, "C": C})],
)

# Figure 1.7: fixed contribution across horizons
sweep_figure(
    "fig1_7_variant_horizon",
    f"Figure 1.7: fixed contribution of \\${C:,} a year, varying the horizon N",
    [(f"N = {N} years", {"N": N, "C": C}) for N in (10, 20, 30, 40)],
)