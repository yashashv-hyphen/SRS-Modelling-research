"""
Tests for srs_simulation.py. The key correctness check: with volatility and tax-drift turned
off, the random simulation must collapse back to the deterministic numbers already verified
in docs/findings.md and pinned in tests/test_srs_model.py — randomness is additive, not a
replacement for the base model.

Run with:  python -m pytest tests/        (or, without pytest)  python tests/test_srs_simulation.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np  # noqa: E402

import srs_model as m  # noqa: E402
import srs_simulation as sim  # noqa: E402


def close(a, b, tol):
    return abs(a - b) <= tol


# ------------------------------------------------------------------- random growth
def test_zero_vol_returns_are_constant():
    path = sim.random_return_path(29, mean=0.05, vol=0.0)
    assert all(close(r, 0.05, 1e-9) for r in path)


def test_return_path_length_and_no_total_wipeout():
    rng = np.random.default_rng(1)
    path = sim.random_return_path(50, mean=0.05, vol=0.3, rng=rng)
    assert len(path) == 50
    assert all(r > -1.0 for r in path)  # lognormal: can't lose more than 100%


# ------------------------------------------------------ historical block bootstrap
def test_historical_bootstrap_only_uses_real_years():
    rng = np.random.default_rng(1)
    series = [0.1, 0.2, -0.3, 0.4, 0.05]
    path = sim.historical_block_bootstrap_path(50, series, block_size=3, rng=rng)
    assert len(path) == 50
    assert all(r in series for r in path)


def test_historical_bootstrap_preserves_block_order():
    # A block starting at index i must appear as the contiguous slice series[i:i+block_size]
    # (wrapping), not a shuffled/independent resample of single years within the block —
    # that's the whole point of block (vs. iid) bootstrap: it keeps real sequences intact.
    series = list(range(10))  # distinct "years" so order is easy to check
    rng = np.random.default_rng(2)
    path = sim.historical_block_bootstrap_path(12, series, block_size=4, rng=rng)
    for start in range(0, 12, 4):
        block = path[start:start + 4]
        if len(block) < 4:
            break
        first = block[0]
        expected = [(first + i) % 10 for i in range(4)]
        assert block == expected, (block, expected)


def test_historical_bootstrap_wraps_around_end_of_series():
    rng = np.random.default_rng(42)
    series = [1, 2, 3]
    # With only 3 years and a block of 5, any start must wrap at least once; run enough draws
    # that a wrap is virtually certain to have been exercised, and just confirm no crash and
    # every value is still a real series value.
    path = sim.historical_block_bootstrap_path(5, series, block_size=5, rng=rng)
    assert len(path) == 5
    assert all(r in series for r in path)


def test_historical_dataset_loads_and_is_real_market_data():
    # Spot-check against well-known values (1929 crash year, 2008 financial crisis) rather
    # than trusting the loader blindly — catches a corrupted/truncated data file.
    by_year = dict(json.load(open(sim._HISTORICAL_PATH))["returns"])
    assert by_year[1929] < -0.05   # 1929 crash
    assert by_year[2008] < -0.30   # 2008 financial crisis
    assert len(sim.HISTORICAL_RETURNS) == len(by_year)


def test_simulate_one_path_historical_mode_runs_and_uses_real_returns():
    rng = np.random.default_rng(6)
    path = sim.simulate_one_path(120_000, return_mode="historical", historical_block_size=5,
                                  rng=rng)
    assert len(path["yearly_contributions"]) == 29
    assert path["srs_at_retirement"] > 0
    assert all(r in sim.HISTORICAL_RETURNS for r in path["draw_returns"])


def test_simulate_one_path_rejects_unknown_return_mode():
    try:
        sim.simulate_one_path(120_000, return_mode="made_up")
        assert False, "expected ValueError"
    except ValueError:
        pass


# ------------------------------------------------------------- tax-bracket drift
def test_zero_shock_prob_never_shifts():
    path = sim.random_policy_shift_path(39, shock_prob=0.0)
    assert all(s == 0.0 for s in path)


def test_shifted_brackets_stay_monotonic_and_bounded():
    shifted = sim.shifted_brackets(m.BRACKETS, 0.5)  # extreme shift
    rates = [r for _, r in shifted]
    assert rates == sorted(rates)
    assert all(0.0 <= r <= 0.30 for r in rates)
    shifted_down = sim.shifted_brackets(m.BRACKETS, -0.5)
    rates_down = [r for _, r in shifted_down]
    assert rates_down == sorted(rates_down)
    assert all(0.0 <= r <= 0.30 for r in rates_down)


def test_bracket_creep_income_grows_geometrically():
    assert close(sim.bracket_creep_income(100_000, 0.02, 0), 100_000, 0.01)
    assert close(sim.bracket_creep_income(100_000, 0.02, 10), 100_000 * 1.02 ** 10, 0.01)
    assert sim.bracket_creep_income(100_000, 0.0, 29) == 100_000


# ---------------------------------------------------------- DP / MPC correctness
def test_dp_matches_level_under_flat_forecast():
    # A flat forecast (same brackets, same return, every remaining year) must reach the same
    # *future-value-compounded total tax* as the closed-form level plan - this is the
    # optimality property the fast shortcut in mpc_drawdown's default path relies on.
    # Singapore's brackets are piecewise-constant, so several different withdrawal splits can
    # tie for optimal (docs/findings.md #7 documents these plateaus as real, not bugs) - the
    # DP is free to land on any of them, so we check the cost, not the exact withdrawal split.
    balance = 953_537.49
    years_left = 10
    r = 0.05
    forecast = [m.BRACKETS] * years_left
    _, dp_fv_tax = sim._dp_solve(balance, years_left, forecast, r, 0.0, grid_size=120)

    w_level = m.level_payment(balance, r, years_left)
    level_fv_tax = sum(m.tax(m.INCLUSION * w_level) * (1 + r) ** (years_left - 1 - t) for t in range(years_left))
    # Grid DP is an approximation - accept a few percent of the level plan's FV-tax cost.
    assert close(dp_fv_tax, level_fv_tax, level_fv_tax * 0.05), (dp_fv_tax, level_fv_tax)


def test_mpc_drawdown_flat_schedule_matches_level_totals():
    balance = 953_537.49
    r = 0.05
    returns = [r] * 10
    brackets = [m.BRACKETS] * 10
    result = sim.mpc_drawdown(balance, 10, returns, brackets, 0.0, r)
    expected = m.run()  # base case, level drawdown, same defaults
    assert close(result["total_tax"], expected["total_tax"], 1.0)
    assert close(result["total_withdrawn"], expected["total_withdrawn"], 1.0)
    assert close(result["residual"], 0.0, 1.0)


def test_mpc_dp_mode_agrees_with_fast_mode_under_flat_schedule():
    balance = 500_000.0
    r = 0.05
    returns = [r] * 5
    brackets = [m.BRACKETS] * 5
    fast = sim.mpc_drawdown(balance, 5, returns, brackets, 0.0, r, use_dp=False)
    dp = sim.mpc_drawdown(balance, 5, returns, brackets, 0.0, r, use_dp=True, grid_size=100)
    assert close(fast["total_tax"], dp["total_tax"], max(50.0, fast["total_tax"] * 0.05))


def test_rule40_strategy_matches_srs_model_fixed40():
    # mpc_drawdown(strategy="rule40") replaces the inline $40k/yr loop that used to live in
    # simulate_one_path — under the same flat zero-noise schedule, its withdrawals/residual
    # must reproduce srs_model's already-pinned 'fixed40' route (docs/findings.md #9) once the
    # residual is deemed-withdrawn the same way srs_model.run does it internally.
    expected = m.run(strategy="fixed40")
    result = sim.mpc_drawdown(expected["srs_at_retirement"], 10, [0.05] * 10, [m.BRACKETS] * 10,
                              0.0, 0.05, strategy="rule40")
    residual_tax = m.tax(m.INCLUSION * result["residual"]) - m.tax(0.0)
    assert close(result["total_tax"] + residual_tax, expected["total_tax"], 1.0)
    assert close(result["total_withdrawn"] + result["residual"], expected["total_withdrawn"], 1.0)


def test_static_level_matches_mpc_under_flat_schedule():
    # Under a flat forecast that never changes, re-planning every year ("mpc") and planning
    # once and never revising ("static_level") solve the identical problem, so they must tie
    # out to floating-point noise. They're expected to diverge only once returns/brackets
    # actually move (test_drawdown_strategies_diverge_under_real_drift covers that case).
    balance, r = 953_537.49, 0.05
    returns, brackets = [r] * 10, [m.BRACKETS] * 10
    mpc = sim.mpc_drawdown(balance, 10, returns, brackets, 0.0, r, strategy="mpc")
    static = sim.mpc_drawdown(balance, 10, returns, brackets, 0.0, r, strategy="static_level")
    assert close(mpc["total_tax"], static["total_tax"], 1.0)
    assert all(close(a, b, 0.01) for a, b in zip(mpc["withdrawals"], static["withdrawals"]))


def test_drawdown_strategies_diverge_under_real_drift():
    # The whole point of exposing separate strategies: once returns actually move around, a
    # plan that never re-plans (static_level) and one that does (mpc) must part ways.
    rng = np.random.default_rng(11)
    returns = sim.random_return_path(10, mean=0.05, vol=0.2, rng=rng)
    brackets = [m.BRACKETS] * 10
    mpc = sim.mpc_drawdown(953_537.49, 10, returns, brackets, 0.0, 0.05, strategy="mpc")
    static = sim.mpc_drawdown(953_537.49, 10, returns, brackets, 0.0, 0.05, strategy="static_level")
    assert mpc["withdrawals"] != static["withdrawals"]


def test_balance_path_length_and_final_value_matches_residual():
    result = sim.mpc_drawdown(500_000.0, 7, [0.05] * 7, [m.BRACKETS] * 7, 0.0, 0.05, strategy="mpc")
    assert len(result["balance_path"]) == 7
    assert close(result["balance_path"][-1], result["residual"], 1e-6)


def test_mpc_never_withdraws_more_than_available():
    rng = np.random.default_rng(7)
    returns = sim.random_return_path(10, mean=0.05, vol=0.4, rng=rng)  # high vol, can go negative-ish
    shifts = sim.random_policy_shift_path(10, shock_prob=0.3, rng=rng)
    brackets = [sim.shifted_brackets(m.BRACKETS, s) for s in shifts]
    result = sim.mpc_drawdown(200_000.0, 10, returns, brackets, 0.0, 0.05)
    assert result["residual"] >= 0.0
    assert all(w >= 0.0 for w in result["withdrawals"])


# --------------------------------------------------------- after-window comparison
def test_spend_to_zero_exhausts_and_bequest_grows():
    result = sim.spend_to_zero_vs_bequest(1_000_000.0, 0.05, 12)
    balance = 1_000_000.0
    for _ in range(12):
        balance = balance * 1.05 - result["spend_to_zero_annual"]
    assert close(balance, 0.0, 1.0)
    assert close(result["bequest_if_untouched"], 1_000_000.0 * 1.05 ** 12, 0.01)
    assert result["bequest_if_untouched"] > result["spend_to_zero_annual"] * 12  # growth adds value


def test_bequest_after_spending_matches_the_two_endpoints():
    lump, r, years = 1_000_000.0, 0.05, 12
    both = sim.spend_to_zero_vs_bequest(lump, r, years)
    assert close(sim.bequest_after_spending(lump, r, years, 0.0),
                 both["bequest_if_untouched"], 1e-6)
    assert close(sim.bequest_after_spending(lump, r, years, both["spend_to_zero_annual"]),
                 0.0, 1.0)


def test_bequest_after_spending_is_linear_in_spend():
    lump, r, years = 1_000_000.0, 0.05, 12
    spend_to_zero = sim.spend_to_zero_vs_bequest(lump, r, years)["spend_to_zero_annual"]
    half_spend_bequest = sim.bequest_after_spending(lump, r, years, spend_to_zero / 2)
    full_bequest = sim.bequest_after_spending(lump, r, years, 0.0)
    assert close(half_spend_bequest, full_bequest / 2, 1.0)


def test_bequest_after_spending_zero_years_is_identity():
    assert sim.bequest_after_spending(500_000.0, 0.05, 0, 10_000.0) == 500_000.0


def test_spend_to_zero_zero_years_is_identity():
    result = sim.spend_to_zero_vs_bequest(500_000.0, 0.05, 0)
    assert result["spend_to_zero_annual"] == 500_000.0
    assert result["bequest_if_untouched"] == 500_000.0


# ------------------------------------------------------------- early-exit breakeven
def test_early_exit_breakeven_zero_years_is_none():
    assert sim.early_exit_breakeven_return(100_000.0, 0, 0.05) is None


def test_early_exit_breakeven_matches_manual_solve():
    balance, years, r = 300_000.0, 10, 0.05
    x = sim.early_exit_breakeven_return(balance, years, r)
    net = m.early_withdrawal(balance)["net"]
    stay = balance * (1 + r) ** years
    # Verify the closed form actually ties the two sides out at the solved rate.
    assert close(net * (1 + x) ** years, stay, 1.0)


def test_early_exit_breakeven_is_positive_when_penalty_costs_more_than_relief_saved():
    # Breaking the lock-up always costs something (penalty + full inclusion), so beating
    # "just leave it" always requires a positive external return.
    x = sim.early_exit_breakeven_return(300_000.0, 10, 0.05)
    assert x > 0.0


# --------------------------------------------------------------- full path / portfolio
def test_simulate_one_path_runs_and_shapes_are_sane():
    rng = np.random.default_rng(42)
    path = sim.simulate_one_path(120_000, vol=0.0, wage_growth=0.0, shock_prob=0.0, rng=rng)
    assert len(path["yearly_contributions"]) == 29
    assert len(path["mpc_drawdown"]["withdrawals"]) == 10
    assert path["srs_at_retirement"] > 0
    assert path["wealth_with_srs"] > 0
    assert path["wealth_without_srs"] > 0


def test_simulate_one_path_zero_noise_matches_base_case():
    # With vol=0, wage_growth=0, shock_prob=0, this should reduce to the exact base case
    # already pinned in tests/test_srs_model.py::test_base_case_regression: the SRS pot, the
    # no-SRS counterfactual (endB), and the whole point — the advantage between them.
    rng = np.random.default_rng(0)
    path = sim.simulate_one_path(120_000, vol=0.0, wage_growth=0.0, shock_prob=0.0, rng=rng)
    expected = m.run()  # chargeable=120_000 default, r=0.05 default
    assert close(path["srs_at_retirement"], expected["srs_at_retirement"], 1.0)
    assert close(path["wealth_with_srs"], expected["endA"], 1.0)
    assert close(path["wealth_without_srs"], expected["endB"], 1.0)
    assert close(path["advantage"], expected["advantage"], 1.0)  # $152,557 — the headline


def test_higher_income_earns_more_relief_but_same_pot():
    # The pot is fixed by the contribution cap; only relief scales with income. This is the
    # separation docs/findings.md relies on — verify the simulation preserves it.
    rng = np.random.default_rng(3)
    low = sim.simulate_one_path(60_000, vol=0.0, wage_growth=0.0, shock_prob=0.0, rng=np.random.default_rng(3))
    high = sim.simulate_one_path(200_000, vol=0.0, wage_growth=0.0, shock_prob=0.0, rng=np.random.default_rng(3))
    assert close(low["srs_at_retirement"], high["srs_at_retirement"], 1.0)
    assert high["total_relief_received"] > low["total_relief_received"]
    assert high["advantage"] > low["advantage"]  # more relief saved => bigger advantage


def test_smart_drawdown_never_pays_more_tax_than_rule40():
    # The MPC (smart) plan is optimising tax; the $40k rule of thumb is not. On a big pot the
    # smart plan must pay no more tax than the rule (usually strictly less).
    rng = np.random.default_rng(5)
    path = sim.simulate_one_path(120_000, vol=0.0, wage_growth=0.0, shock_prob=0.0,
                                  contrib_years=34, rng=rng)  # 34y => ~$1.3M pot, gap is real
    assert path["smart_vs_rule40_tax_gap"] >= -1.0  # smart is at least as good (tolerance for rounding)


def test_simulate_portfolio_percentiles_are_ordered():
    result = sim.simulate_portfolio(120_000, n_paths=30, seed=1, vol=0.15, shock_prob=0.05)
    s = result["summary"]
    for key in ("advantage", "wealth_with_srs", "wealth_without_srs", "srs_at_retirement"):
        assert s[key]["p10"] <= s[key]["median"] <= s[key]["p90"], key
    assert "median_path" in result


def test_wealth_path_ends_at_the_pinned_scalars():
    # wealth_with_srs_path / wealth_without_srs_path are built by the new forward-recurrence
    # trajectory; their last entry must equal the (already-tested) scalar endA/endB exactly,
    # under real randomness, not just the zero-noise base case.
    rng = np.random.default_rng(9)
    path = sim.simulate_one_path(120_000, vol=0.2, wage_growth=0.02, shock_prob=0.05, rng=rng)
    assert len(path["wealth_with_srs_path"]) == 29 + 10
    assert close(path["wealth_with_srs_path"][-1], path["wealth_with_srs"], 1e-6)
    assert close(path["wealth_without_srs_path"][-1], path["wealth_without_srs"], 1e-6)


def test_base_brackets_override_changes_relief():
    # A custom starting schedule (here: everything at a flat 30%) must actually take effect,
    # not silently fall back to the IRAS default.
    flat_30 = [(float("inf"), 0.30)]
    rng = np.random.default_rng(4)
    path = sim.simulate_one_path(120_000, vol=0.0, wage_growth=0.0, shock_prob=0.0,
                                  base_brackets=flat_30, rng=rng)
    assert close(path["yearly_contributions"][0]["relief_rate"], 0.30, 1e-9)


def test_prob_srs_wins_is_a_fraction_in_range():
    result = sim.simulate_portfolio(120_000, n_paths=25, seed=2, vol=0.1, shock_prob=0.03)
    p = result["summary"]["prob_srs_wins"]
    assert 0.0 <= p <= 1.0
    # Favourable, low-noise settings at this income should win nearly every simulated future.
    assert p > 0.9


# --------------------------------------------------------------- sweeps across the axes
def test_advantage_rises_with_income():
    # Higher income => higher relief rate => bigger advantage (the pot is identical). At vol=0
    # with no tax drift this is monotonic non-decreasing (60k and 80k tie in the 7% band).
    rows = sim.advantage_by_income(n_paths=1, seed=0, vol=0.0, wage_growth=0.0, shock_prob=0.0)
    meds = [r["advantage"]["median"] for r in rows]
    assert meds == sorted(meds), meds
    assert meds[-1] > meds[0]  # $500k clearly beats $60k


def test_dollar_advantage_rises_with_return():
    # findings.md §5: the dollar advantage grows with the return even as the % edge shrinks.
    rows = sim.advantage_by_return(chargeable=120_000, n_paths=1, seed=0,
                                    vol=0.0, wage_growth=0.0, shock_prob=0.0)
    meds = [r["advantage"]["median"] for r in rows]
    assert meds == sorted(meds), meds  # 3% < 4% < ... < 8% in dollars


def test_pct_edge_shrinks_with_return():
    # The counterintuitive finding: the *percentage* advantage falls as returns rise.
    rows = sim.advantage_by_return(chargeable=120_000, n_paths=1, seed=0,
                                    vol=0.0, wage_growth=0.0, shock_prob=0.0)
    pcts = [r["advantage_pct"]["median"] for r in rows]
    assert pcts == sorted(pcts, reverse=True), pcts  # strictly decreasing


def test_bracket_creep_raises_advantage_over_frozen():
    # Bracket creep pushes contribution-year income into higher bands => more relief => a
    # bigger advantage than a frozen-brackets world (the pot is unchanged).
    rows = sim.advantage_by_tax_regime(chargeable=100_000, wage_growth=0.03, shock_prob=0.0,
                                        n_paths=1, seed=0, vol=0.0)
    by_name = {r["regime"]: r["advantage"]["median"] for r in rows}
    assert by_name["Bracket creep (pay rises)"] >= by_name["Brackets frozen forever"]
    assert all(v > 0 for v in by_name.values())


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}  {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
