"""Figures 1.3 to 1.5: change one parameter at a time from the base case.

Run from the repo root: python -m srs_basic.figures.fig1_3_to_1_5_sweeps
"""

from srs_basic import config
from srs_basic.figures.panels import sweep_figure


def main():
    N, B = config.N, config.B

    sweep_figure(
        "fig1_3_horizon",
        f"Figure 1.3: varying the horizon N (B = \\${B/1e6:g}M, whole-balance evaluation)",
        [(f"N = {n} years", {"N": n, "B": B}) for n in (10, 20, 30, 40)],
    )
    sweep_figure(
        "fig1_4_balance",
        f"Figure 1.4: varying the balance at retirement B (N = {N}, whole-balance evaluation)",
        [(f"B = \\${b/1e6:g}M", {"N": N, "B": b})
         for b in (500_000, 1_000_000, 2_000_000, 3_000_000)],
    )
    sweep_figure(
        "fig1_5_other_income",
        f"Figure 1.5: varying other retirement income (N = {N}, B = \\${B/1e6:g}M)",
        [(f"Other income = \\${y/1000:g}k", {"N": N, "B": B, "other": y})
         for y in (0, 30_000, 60_000)],
    )


if __name__ == "__main__":
    main()
