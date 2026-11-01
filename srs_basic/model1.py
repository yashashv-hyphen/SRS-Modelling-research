"""Model 1: SRS vs non-SRS for one pre-tax dollar (formulas M1.3 to M1.6)."""

import numpy as np

from srs_basic.exit_rate import avg_exit_rate

# what $1 of pre-tax income becomes by each route
def terminal_wealth(tc, r, N, ew):
    """M1.3: after-tax wealth per pre-tax dollar, returned as (srs, non_srs)."""
    growth = (1 + r) ** N
    return growth * (1 - ew), (1 - tc) * growth

# SRS minus outside
def advantage(tc, r, N, ew):
    """M1.4: SRS minus non-SRS wealth per pre-tax dollar. Positive = SRS wins."""
    return (1 + r) ** N * (tc - ew)

# SRS/outside
def ratio(tc, ew):
    """M1.5: SRS wealth / non-SRS wealth. Above 1 = SRS wins. No r or N."""
    return (1 - ew) / (1 - tc)

# Pot built from fixed yearly contribution  
def pot_from_contribution(C, r, N):
    """M1.6: balance after N end-of-year contributions of C growing at r."""
    if r == 0:
        return C * N
    return C * ((1 + r) ** N - 1) / r

#Refers to the advantage (SRS-outside) at every (tc, r) point for the heatmap
def grid(tc_values, r_values, N, schedule, B=None, C=None, k=10, other=0, I=0.5):
    """Advantage over every (tc, r) pair.

    Give B for a fixed ending balance (base case), or C for a fixed
    annual contribution (variant). Returns TC, R, EW, A as 2-D arrays,
    with rows = returns and columns = tax rates.
    """
    if (B is None) == (C is None):
        raise ValueError("Give exactly one of B or C")

    TC, R = np.meshgrid(tc_values, r_values)

    if B is not None:
        # Fixed pot: one exit rate for the whole grid
        EW = np.full_like(TC, avg_exit_rate(B, k, other, I, schedule))
    else:
        # Fixed contribution: the pot, and so the exit rate, changes with r
        ew_by_r = [avg_exit_rate(pot_from_contribution(C, r, N), k, other, I, schedule)
                   for r in r_values]
        EW = np.tile(np.array(ew_by_r)[:, None], (1, len(tc_values)))

    A = advantage(TC, R, N, EW)
    return TC, R, EW, A