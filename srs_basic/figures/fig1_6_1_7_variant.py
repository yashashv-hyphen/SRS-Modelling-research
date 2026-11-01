"""Figures 1.6 and 1.7: fixed annual contribution instead of fixed balance.

Run from the repo root: python -m srs_basic.figures.fig1_6_1_7_variant
"""

from srs_basic import config
from srs_basic.figures.panels import sweep_figure


def main():
    C = config.C

    sweep_figure(
        "fig1_6_variant",
        f"Figure 1.6: fixed balance vs fixed contribution of \\${C:,} a year (N = {config.N})",
        [(f"Fixed balance B = \\${config.B/1e6:g}M (per \\$1 at year 0)",
          {"N": config.N, "B": config.B}),
         (f"Fixed contribution \\${C:,}/yr (per \\$1 contributed)",
          {"N": config.N, "C": C})],
        cbar_label=r"SRS advantage per \$1 (\$)",
    )
    sweep_figure(
        "fig1_7_variant_horizon",
        f"Figure 1.7: fixed contribution of \\${C:,} a year, varying the horizon N",
        [(f"N = {n} years", {"N": n, "C": C}) for n in (10, 20, 30, 40)],
        cbar_label=r"SRS advantage per \$1 contributed (\$)",
    )


if __name__ == "__main__":
    main()
