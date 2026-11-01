"""Model 1: SRS vs non-SRS for one pre-tax dollar (formulas M1.3 to M1.6)."""

import numpy as np

from srs_basic.exit_rate import avg_exit_rate


def terminal_wealth(tc, r, N, ew):
    """M1.3: after-tax wealth per pre-tax dollar, returned as (srs, non_srs)."""
    growth = (1 + r) ** N
    return growth * (1 - ew), (1 - tc) * growth


def advantage(tc, r, N, ew):
    """M1.4: SRS minus non-SRS wealth for one pre-tax dollar invested at
    year 0 and held N years. Positive = SRS wins."""
    return (1 + r) ** N * (tc - ew)


def advantage_per_contribution(tc, ew, pot, C, N):
    """Fixed-contribution mode: SRS advantage per $1 contributed.

    Each contribution grows to its share of the pot, so the total advantage
    is pot x (tc - ew); dividing by the C x N dollars contributed gives the
    advantage per contributed dollar.
    """
    return pot * (tc - ew) / (C * N)


def ratio(tc, ew):
    """M1.5: SRS wealth / non-SRS wealth. Above 1 = SRS wins. No r or N."""
    return (1 - ew) / (1 - tc)


def pot_from_contribution(C, r, N):
    """M1.6: balance after N end-of-year contributions of C growing at r."""
    if r == 0:
        return C * N
    return C * ((1 + r) ** N - 1) / r


def grid(tc_values, r_values, N, schedule, B=None, C=None, k=10, other=0, I=0.5):
    """Advantage over every (tc, r) pair.

    Give B for a fixed ending balance (base case): A = advantage per $1
    invested at year 0. Or give C for a fixed annual contribution (variant):
    A = advantage per $1 contributed. Both use the average exit rate, so
    they evaluate the whole balance, not the next dollar.
    Returns TC, R, EW, A as 2-D float arrays (rows = returns, cols = tax rates).
    """
    if (B is None) == (C is None):
        raise ValueError("Give exactly one of B or C")

    tc_values = np.asarray(tc_values, dtype=float)
    r_values = np.asarray(r_values, dtype=float)
    TC, R = np.meshgrid(tc_values, r_values)

    if B is not None:
        EW = np.full(TC.shape, avg_exit_rate(B, k, other, I, schedule), dtype=float)
        A = advantage(TC, R, N, EW)
    else:
        pots = np.array([pot_from_contribution(C, r, N) for r in r_values])
        ew_by_r = np.array([avg_exit_rate(p, k, other, I, schedule) for p in pots])
        EW = np.tile(ew_by_r[:, None], (1, len(tc_values)))
        POT = np.tile(pots[:, None], (1, len(tc_values)))
        A = advantage_per_contribution(TC, EW, POT, C, N)
    return TC, R, EW, A
