"""Model 2: optimal SRS withdrawal policy, solved by dynamic programming.

State: SRS balance B and withdrawal years left n (other income and the tax
schedule are held fixed). Decision: this year's withdrawal w. Withdrawals are
made at the start of each year; what is left grows at r.
"""

import numpy as np

from srs_basic.tax import tax_vec

TIE_TOL = 0.01  # $: choices within this of the best are treated as equally good

# same incremental concept as Model 1 but for one year 
def withdrawal_tax(w, other, I, schedule):
    """Extra tax from withdrawing w this year: T(other + I*w) - T(other). Arrays OK."""
    w = np.asarray(w, dtype=float)
    return tax_vec(other + I * w, schedule) - tax_vec(other, schedule)

def level_payment(B, n, r):
    """Equal start-of-year withdrawal that empties B over n years at return r."""
    B = np.asarray(B, dtype=float)
    if r == 0:
        return B / n
    return B * r / ((1 - (1 + r) ** -n) * (1 + r))

#Basically for solve, we first list every possible choice, before we tax every choice once and at the start of the last year, we apply V[1] = tax(B). After we work backwardss n = 2, ... 10 
def solve(r, other, K, B_grid, schedule, I=0.5, discount=True, deemed_separate=False):
    """Backward induction over balance and years left.
    Returns V, W, W_lo, W_hi, each shaped (K + 1, len(B_grid)); row n = n years left.
      V     lowest remaining tax (present value if discount) from that state
      W     recommended withdrawal (among ties: closest to the level payment)
      W_lo  smallest withdrawal that is still optimal
      W_hi  largest withdrawal that is still optimal
    Base case (deemed_separate=False): the leftover balance is taxed with year K,
    so with 1 year left everything comes out.
    """
    B = np.asarray(B_grid, dtype=float)
    rows = np.arange(len(B))
    d = 1 / (1 + r) if discount else 1.0

    # Decision = which grid balance to carry into next year (no interpolation needed)
    W_mat = B[:, None] - B[None, :] / (1 + r)
    feasible = W_mat >= -1e-9
    W_mat = np.where(feasible, np.clip(W_mat, 0, None), np.nan)
    T_mat = np.where(feasible,
                     withdrawal_tax(np.nan_to_num(W_mat), other, I, schedule), np.inf)

    shape = (K + 1, len(B))
    V, W, W_lo, W_hi = (np.full(shape, np.nan) for _ in range(4))

    lump = withdrawal_tax(B, other, I, schedule)
    if deemed_separate:
        V[0], first = lump, 1          # year after the window: deemed withdrawal
    else:
        V[1], W[1], W_lo[1], W_hi[1] = lump, B, B, B
        first = 2

    for n in range(first, K + 1):
        cost = T_mat + d * V[n - 1][None, :]
        best = cost.min(axis=1)
        ok = cost <= best[:, None] + TIE_TOL
        target = level_payment(B, n, r)
        dist = np.where(ok, np.abs(W_mat - target[:, None]), np.inf)
        j = dist.argmin(axis=1)
        V[n] = best
        W[n] = W_mat[rows, j]
        W_lo[n] = np.where(ok, W_mat, np.inf).min(axis=1)
        W_hi[n] = np.where(ok, W_mat, -np.inf).max(axis=1)
    return V, W, W_lo, W_hi

# Allows out to play out the scenario for 10 years 
def _run(rule, B0, r, K, other, schedule, I, discount, deemed_separate):
    """Follow a withdrawal rule(B, n_left) from B0; return the path and total tax."""
    d = 1 / (1 + r) if discount else 1.0
    B, withdrawals, taxes = float(B0), [], []
    for t in range(K):
        n_left = K - t
        if n_left == 1 and not deemed_separate:
            w = B
        else:
            w = min(max(float(rule(B, n_left)), 0.0), B)
        withdrawals.append(w)
        taxes.append(float(withdrawal_tax(w, other, I, schedule)))
        B = (B - w) * (1 + r)
    if deemed_separate:                       # leftover taxed the year after the window
        withdrawals.append(B)
        taxes.append(float(withdrawal_tax(B, other, I, schedule)))
    total = sum(tax * d ** t for t, tax in enumerate(taxes))
    return {"withdrawals": np.array(withdrawals), "taxes": np.array(taxes),
            "total_tax": total, "exit_rate": total / B0 if B0 > 0 else 0.0}

def simulate(W, B_grid, B0, r, K, other, schedule, I=0.5, discount=True,
             deemed_separate=False):
    """Follow the optimal policy W (from solve) starting from balance B0."""
    rule = lambda B, n: np.interp(B, B_grid, W[n])
    return _run(rule, B0, r, K, other, schedule, I, discount, deemed_separate)

BENCHMARKS = {
    "lump": lambda B, n, r: B,                       # everything in year 1
    "even": lambda B, n, r: B / n,                   # equal share of what is left
    "level": lambda B, n, r: level_payment(B, n, r),
}

def benchmark(policy, B0, r, K, other, schedule, I=0.5, discount=True,
              deemed_separate=False):
    """Run a simple policy: 'lump', 'even' or 'level'."""
    rule = lambda B, n: BENCHMARKS[policy](B, n, r)
    return _run(rule, B0, r, K, other, schedule, I, discount, deemed_separate)