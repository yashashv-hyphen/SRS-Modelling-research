import pytest
from srs_basic.config import SCHEDULE_CSV, REGIME
from srs_basic.tax import load_schedule
from srs_basic.exit_rate import avg_exit_rate

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