import pytest
from srs_basic.config import SCHEDULE_CSV, REGIME
from srs_basic.tax import load_schedule
from srs_basic.exit_rate import avg_exit_rate, marginal_breakeven

S = load_schedule(SCHEDULE_CSV, REGIME)

@pytest.mark.parametrize("B, k, other, expected", [
    (400_000, 10, 0, 0.0),
    (1_000_000, 10, 0, 0.0125),
    (3_000_000, 10, 0, 0.0415),
    (1_000_000, 10, 30_000, 0.0315),
    (1_000_000, 1, 0, 0.08415),
])
def test_avg_exit_rate(B, k, other, expected):
    assert avg_exit_rate(B, k, other, 0.5, S) == pytest.approx(expected, abs=1e-4)

def test_marginal_breakeven():
    assert marginal_breakeven(1_000_000, 10, 0, 0.5, S) == pytest.approx(0.035)
    assert marginal_breakeven(400_000, 10, 0, 0.5, S) == 0.0   # exactly at $20k edge

@pytest.mark.parametrize("k", [0, -1, 2.5])
def test_bad_years_raise(k):
    with pytest.raises(ValueError):
        avg_exit_rate(1_000_000, k, 0, 0.5, S)
    with pytest.raises(ValueError):
        marginal_breakeven(1_000_000, k, 0, 0.5, S)
