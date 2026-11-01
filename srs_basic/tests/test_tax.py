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

def test_band_rate_at_edge_stays_in_lower_band():
    assert band_rate(20_000, S) == 0.0
    assert band_rate(20_001, S) == pytest.approx(0.02)
    assert band_rate(80_000, S) == pytest.approx(0.07)

HEADER = "regime,ya_from,ya_to,lower_bound,upper_bound,marginal_rate_pct\n"

@pytest.mark.parametrize("rows", [
    "X,1,1,0,20000,0\nX,1,1,25000,,2\n",       # gap
    "X,1,1,0,20000,0\nX,1,1,15000,,2\n",       # overlap
    "X,1,1,1000,20000,0\nX,1,1,20000,,2\n",    # does not start at 0
    "X,1,1,0,20000,0\nX,1,1,20000,30000,2\n",  # top band has an upper edge
    "X,1,1,0,20000,0\nX,1,1,20000,,150\n",     # rate above 100%
])
def test_malformed_schedule_raises(tmp_path, rows):
    path = tmp_path / "bad.csv"
    path.write_text(HEADER + rows)
    with pytest.raises(ValueError):
        load_schedule(path, "X")
