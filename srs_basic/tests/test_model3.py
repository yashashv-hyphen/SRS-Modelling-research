import numpy as np
import pytest

from srs_basic import config
from srs_basic import model3 as m3
from srs_basic.exit_rate import avg_exit_rate
from srs_basic.model2 import solve
from srs_basic.tax import load_schedule

S = load_schedule(config.SCHEDULE_CSV, config.REGIME)
CALIB = m3.calibration()
B_GRID = np.arange(0, 2_000_001, 5_000)


def test_calibration_matches_history():
    assert CALIB["revision_yas"] == [2012, 2017, 2024]
    assert CALIB["avg_interval"] == pytest.approx(17 / 3)
    assert CALIB["avg_step"] == pytest.approx(0.04 / 3)
    assert CALIB["drift_per_year"] == pytest.approx(0.04 / 17)
    assert CALIB["low_edges_frozen"]


def test_shift_keeps_edges_and_zero_band():
    shifted = m3.shift_schedule(S, 0.01)
    assert [u for u, _ in shifted] == [u for u, _ in S]
    assert shifted[0][1] == 0.0
    assert shifted[1][1] == pytest.approx(0.03)
    top_only = m3.shift_schedule(S, 0.01, from_edge=160_000)
    assert top_only[4][1] == pytest.approx(0.115)       # $80k-$120k band untouched
    assert top_only[-1][1] == pytest.approx(0.25)


def test_discrete_steps_land_on_schedule():
    assert m3.scenario_shift(5, "discrete", CALIB) == 0.0
    assert m3.scenario_shift(6, "discrete", CALIB) == pytest.approx(CALIB["avg_step"])
    assert m3.scenario_shift(17, "discrete", CALIB) == pytest.approx(3 * CALIB["avg_step"])


def test_fixed_schedule_reproduces_model1():
    for B in (500_000, 1_000_000, 3_000_000):
        assert m3.avg_exit_rate_tv(B, 0, 0.5, [S] * 10) == pytest.approx(
            avg_exit_rate(B, 10, 0, 0.5, S))
    assert m3.breakeven_tc(1_000_000, 20, "frozen", S, CALIB) == pytest.approx(0.0125)


def test_history_model1_exit_rate_at_1m():
    s = m3.all_schedules()
    assert avg_exit_rate(1_000_000, 10, 0, 0.5, s["YA2007-YA2011"]) == pytest.approx(0.0175)
    assert avg_exit_rate(1_000_000, 10, 0, 0.5, s["YA2003-YA2005"]) == pytest.approx(0.019)


def test_top_band_drift_does_not_touch_a_1m_pot():
    assert m3.breakeven_tc(1_000_000, 40, "top", S, CALIB) == pytest.approx(0.0125)


def test_parallel_drift_raises_breakeven_with_horizon():
    vals = [m3.breakeven_tc(1_000_000, N, "smooth", S, CALIB) for N in (0, 10, 20, 30, 40)]
    assert all(b > a for a, b in zip(vals, vals[1:]))
    assert vals[2] == pytest.approx(0.0298, abs=5e-5)


def test_solve_tv_matches_model2_with_fixed_schedule():
    V, W = m3.solve_tv(0.05, 0, B_GRID, [S] * 10)
    V2, W2, _, _ = solve(0.05, 0, 10, B_GRID, S)
    assert V[10] == pytest.approx(V2[10])
    assert W[10] == pytest.approx(W2[10])


def test_known_rise_front_loads_and_saves_tax():
    scheds = m3.jump_schedules(S, 10, 5, CALIB["avg_step"])
    _, W = m3.solve_tv(0.05, 0, B_GRID, scheds)
    opt = m3.optimal_path(W, B_GRID, 1_000_000, 0.05, 0, scheds)
    lvl = m3.level_path(1_000_000, 0.05, 0, scheds)
    assert opt["withdrawals"][:5].mean() > 150_000 > 90_000 > opt["withdrawals"][5:].mean()
    assert lvl["total_tax"] - opt["total_tax"] == pytest.approx(998, abs=5)
