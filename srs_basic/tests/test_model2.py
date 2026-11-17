import numpy as np
import pytest

from srs_basic import config
from srs_basic.model2 import benchmark, level_payment, simulate, solve, withdrawal_tax
from srs_basic.tax import load_schedule

S = load_schedule(config.SCHEDULE_CSV, config.REGIME)
B_GRID = np.arange(0, config.B_MAX + config.DB, config.DB)
def idx(balance):
    """Position of a balance in B_GRID (the balance must be on the grid)."""
    i = int(np.searchsorted(B_GRID, balance))
    assert B_GRID[i] == balance, f"{balance} is not on the grid"
    return i


I_1M = idx(1_000_000)
I_400K = idx(400_000)
GRID_TOL = 200    # $: the solver picks next year's balance from the grid, so it can
                  # miss a continuous rule (e.g. the level payment) by up to about this


def test_withdrawal_tax():
    assert withdrawal_tax(100_000, 0, 0.5, S) == pytest.approx(1_250)
    assert withdrawal_tax(100_000, 20_000, 0.5, S) == pytest.approx(2_650)


def test_level_payment():
    assert level_payment(1_000_000, 10, 0) == pytest.approx(100_000)
    assert level_payment(1_000_000, 10, 0.05) == pytest.approx(123_337.69, abs=0.01)


def test_last_year_takes_everything():
    V, W, _, _ = solve(0.05, 0, 10, B_GRID, S)
    assert W[1] == pytest.approx(B_GRID)
    assert V[1] == pytest.approx(withdrawal_tax(B_GRID, 0, 0.5, S))


def test_matches_model1_when_r_is_zero():
    V, W, _, _ = solve(0, 0, 10, B_GRID, S)
    assert V[10, I_1M] == pytest.approx(12_500)
    path = simulate(W, B_GRID, 1_000_000, 0, 10, 0, S)
    assert path["withdrawals"] == pytest.approx([100_000] * 10)


def test_tax_free_zone():
    V, _, _, _ = solve(0, 0, 10, B_GRID, S)
    assert V[10, I_400K] == pytest.approx(0)


@pytest.mark.parametrize("other, expected", [
    (20_000, 26_500), (50_000, 44_000), (100_000, 68_000),
])
def test_other_income(other, expected):
    V, _, _, _ = solve(0, other, 10, B_GRID, S)
    assert V[10, I_1M] == pytest.approx(expected)


def test_lump_sum_benchmark():
    out = benchmark("lump", 1_000_000, 0, 10, 0, S)
    assert out["total_tax"] == pytest.approx(84_150)


def test_closed_form_at_5pct():
    # Every year in the 7% band: tax = 0.07 x taxable - 2,250 per year
    expected = 0.035 * 1_000_000 - 2_250 * sum(1.05 ** -t for t in range(10))
    V, _, _, _ = solve(0.05, 0, 10, B_GRID, S)
    assert V[10, I_1M] == pytest.approx(expected, abs=0.01)
    level = benchmark("level", 1_000_000, 0.05, 10, 0, S)
    assert level["total_tax"] == pytest.approx(expected, abs=0.01)


def test_brute_force_two_years():
    r, d, B0 = 0.05, 1 / 1.05, 1_000_000
    V, _, _, _ = solve(r, 0, 2, B_GRID, S)
    carry = B_GRID[B_GRID <= B0 * (1 + r)]
    w1 = B0 - carry / (1 + r)
    costs = withdrawal_tax(w1, 0, 0.5, S) + d * withdrawal_tax(carry, 0, 0.5, S)
    assert V[2, I_1M] == pytest.approx(costs.min())


@pytest.mark.parametrize("r, other", [(0, 0), (0.05, 0), (0.05, 50_000), (0.08, 20_000)])
def test_optimum_beats_benchmarks(r, other):
    V, W, _, _ = solve(r, other, 10, B_GRID, S)
    best = simulate(W, B_GRID, 1_000_000, r, 10, other, S)["total_tax"]
    assert best == pytest.approx(V[10, I_1M], abs=0.01)
    for policy in ("lump", "even", "level"):
        assert best <= benchmark(policy, 1_000_000, r, 10, other, S)["total_tax"] + GRID_TOL


def test_tie_range_contains_choice():
    _, W, lo, hi = solve(0.05, 0, 10, B_GRID, S)
    assert np.all(lo[2:] <= W[2:] + 1e-9) and np.all(W[2:] <= hi[2:] + 1e-9)


def test_deemed_separate_gives_an_extra_tax_year():
    V_sep, _, _, _ = solve(0, 0, 10, B_GRID, S, deemed_separate=True)
    V_base, _, _, _ = solve(0, 0, 10, B_GRID, S)
    i = idx(440_000)
    assert V_sep[10, i] == pytest.approx(0)        # $440k = 11 x $40k tax-free
    assert V_base[10, i] > 0


def test_undiscounted_front_loads():
    _, W_pv, _, _ = solve(0.05, 0, 10, B_GRID, S, discount=True)
    _, W_nom, _, _ = solve(0.05, 0, 10, B_GRID, S, discount=False)
    assert W_nom[10, I_1M] > W_pv[10, I_1M]


def test_simulate_rejects_balance_outside_grid():
    _, W, _, _ = solve(0.05, 0, 10, B_GRID, S)
    with pytest.raises(ValueError):
        simulate(W, B_GRID, B_GRID[-1] + 1, 0.05, 10, 0, S)


def test_solve_rejects_oversized_grid():
    with pytest.raises(ValueError):
        solve(0.05, 0, 10, np.arange(0, 5_000_000, 1_000), S)
