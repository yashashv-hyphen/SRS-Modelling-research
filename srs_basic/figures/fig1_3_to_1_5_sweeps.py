"""Figures 1.3 to 1.5: change one parameter at a time from the base case."""

from srs_basic.figures.panels import sweep_figure

BASE_N, BASE_B = 20, 1_000_000

# Figure 1.3: horizon N, balance fixed at $1M
sweep_figure(
    "fig1_3_horizon",
    "Figure 1.3: varying the horizon N (B = \\$1M, no other income)",
    [(f"N = {N} years", {"N": N, "B": BASE_B}) for N in (10, 20, 30, 40)],
)

# Figure 1.4: balance at retirement B, horizon fixed at 20 years
sweep_figure(
    "fig1_4_balance",
    "Figure 1.4: varying the balance at retirement B (N = 20, no other income)",
    [(f"B = \\${B/1e6:g}M", {"N": BASE_N, "B": B})
     for B in (500_000, 1_000_000, 2_000_000, 3_000_000)],
)

# Figure 1.5: other taxable income in retirement
sweep_figure(
    "fig1_5_other_income",
    "Figure 1.5: varying other retirement income (N = 20, B = \\$1M)",
    [(f"Other income = \\${y/1000:g}k", {"N": BASE_N, "B": BASE_B, "other": y})
     for y in (0, 30_000, 60_000)],
)