import numpy as np
import pytest
from srs_basic.config import SCHEDULE_CSV, REGIME
from srs_basic.tax import load_schedule
from srs_basic.model1 import advantage, ratio, pot_from_contribution, terminal_wealth, grid

S = load_schedule(SCHEDULE_CSV, REGIME)

def test_breakeven_independent_of_r_and_N():
    for r in (0.03, 0.08, 0.12):
        for N in (10, 40):
            assert advantage(0.0125, r, N, 0.0125) == pytest.approx(0)

def test_advantage_matches_terminal_wealth():
    srs, non = terminal_wealth(0.07, 0.05, 20, 0.0125)
    assert advantage(0.07, 0.05, 20, 0.0125) == pytest.approx(srs - non)

def test_ratio():
    assert ratio(0.07, 0.07) == pytest.approx(1)
    assert ratio(0.07, 0.0125) == pytest.approx(0.9875 / 0.93)

def test_pot_from_contribution():
    assert pot_from_contribution(15_300, 0.05, 20) == pytest.approx(505_904, rel=1e-4)
    assert pot_from_contribution(15_300, 0.0, 20) == pytest.approx(306_000)

def test_grid_fixed_B_breakeven_is_vertical():
    tc = np.linspace(0, 0.24, 97)   # step 0.25%
    r = np.linspace(0.03, 0.12, 10)
    TC, R, EW, A = grid(tc, r, 20, S, B=1_000_000)
    assert A.shape == (10, 97)
    col = np.argmin(np.abs(tc - 0.0125))
    assert np.allclose(A[:, col], 0)
    assert (A[:, :col] < 0).all() and (A[:, col + 1:] > 0).all()

def test_grid_fixed_C_exit_rate_rises_with_r():
    TC, R, EW, A = grid(np.linspace(0, 0.24, 5), np.linspace(0.03, 0.12, 10), 20, S, C=15_300)
    assert (np.diff(EW[:, 0]) >= 0).all()

def test_grid_needs_exactly_one_of_B_or_C():
    with pytest.raises(ValueError):
        grid([0.1], [0.05], 20, S)