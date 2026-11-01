import pytest
from srs_basic.config import SCHEDULE_CSV, REGIME
from srs_basic.tax import load_schedule, tax, band_rate

S = load_schedule(SCHEDULE_CSV, REGIME)

@pytest.mark.parametrize("x, expected", [
    (0, 0), (20_000, 0), (50_000, 1_250), (100_000, 5_650),
    (150_000, 12_450), (500_000, 84_150),
])
def test_tax(x, expected):
    assert tax(x, S) == pytest.approx(expected)

def test_band_rate():
    assert band_rate(64_752, S) == pytest.approx(0.07)
    assert band_rate(2_000_000, S) == pytest.approx(0.24)