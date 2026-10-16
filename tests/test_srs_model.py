"""
Regression tests for srs_model.py. Every expected value below was verified in the research
conversation (docs/findings.md explains each). If a change breaks one of these, the change is
wrong or the finding needs re-deriving — do not just update the number.

Run with:  python -m pytest tests/        (or, without pytest)  python tests/test_srs_model.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import srs_model as m  # noqa: E402


def close(a, b, tol):
    return abs(a - b) <= tol


# ------------------------------------------------------------------ tax schedule
def test_bracket_table_shape():
    assert len(m.BRACKETS) == 13
    uppers = [u for u, _ in m.BRACKETS]
    assert uppers == sorted(uppers)
    assert m.BRACKETS[-1][1] == 0.24


def test_tax_spot_values():
    expected = {20_000: 0, 30_000: 200, 40_000: 550, 80_000: 3_350, 100_000: 5_650,
                120_000: 7_950, 104_700: 6_190.50, 84_700: 3_890.50, 79_800: 3_336,
                64_500: 2_265, 88_000: 4_270, 72_700: 2_839}
    for income, t in expected.items():
        assert close(m.tax(income), t, 0.01), (income, m.tax(income), t)


# ------------------------------------------------------------------------ relief
def test_relief_clean_band():
    # whole $15,300 stays inside the 11.5% band
    assert close(m.relief_value(120_000), 1_759.50, 0.01)
    assert close(m.relief_value(100_000), 1_759.50, 0.01)


def test_relief_gross_vs_chargeable():
    # "$100k income" as GROSS -> ~$79,800 chargeable after CPF relief + EIR -> 7% band
    assert close(m.relief_value(79_800), 1_071.00, 0.01)


def test_relief_straddles_band_edge():
    # $88k -> $72.7k crosses $80k: $8,000 @11.5% + $7,300 @7% = $1,431 (blended 9.35%)
    assert close(m.relief_value(88_000), 1_431.00, 0.01)


# ------------------------------------------------------- per-dollar separability
def test_per_dollar_ratio_value():
    assert close(m.per_dollar_ratio(0.115, 0.07), 0.965 / 0.885, 1e-12)


def test_per_dollar_growth_cancels():
    tc, tw = 0.115, 0.07
    target = m.per_dollar_ratio(tc, tw)
    for r in (0.03, 0.05, 0.07):
        for n in (10, 29, 40):
            srs = (1 + r) ** n * (1 - 0.5 * tw)
            ordinary = (1 - tc) * (1 + r) ** n
            assert close(srs / ordinary, target, 1e-12)


# ---------------------------------------------------------------------- base case
def test_base_case_regression():
    b = m.run()   # chargeable $120k, 5%, 29 contribution years, level drawdown 64-73
    assert close(b["out_of_pocket"], 13_540.50, 0.01)
    assert close(b["srs_at_retirement"], 953_537.49, 1)
    assert close(b["annual_withdrawal"], 123_487.47, 1)
    assert close(b["annual_tax"], 2_072.06, 1)
    assert close(b["total_tax"], 20_720.61, 1)
    assert close(b["endA"], 1_527_149.93, 1)
    assert close(b["endB"], 1_374_592.71, 1)
    assert close(b["advantage"], 152_557.23, 1)


def test_advantage_identity():
    # advantage == FV(relief invested) - FV(tax paid), exactly
    for kwargs in ({}, {"r": 0.03}, {"r": 0.07}, {"chargeable": 60_000},
                   {"chargeable": 500_000}, {"strategy": "fixed40"}):
        b = m.run(**kwargs)
        assert close(b["advantage"], b["fv_relief_invested"] - b["fv_taxes_paid"], 1e-6), kwargs


def test_advantage_by_income():
    for income, pct in ((60_000, 5.72), (160_000, 15.67), (500_000, 26.05)):
        assert close(m.run(chargeable=income)["advantage_pct"] * 100, pct, 0.02), income


def test_higher_return_lowers_pct_advantage():
    assert close(m.run(r=0.03)["advantage_pct"] * 100, 12.17, 0.02)
    assert close(m.run(r=0.07)["advantage_pct"] * 100, 9.97, 0.02)


# ---------------------------------------------------------- marginal vs average
def test_marginal_and_average_differ():
    pot = m.run()["srs_at_retirement"]
    assert m.marginal_exit_rate(pot) == 0.07
    assert close(m.average_exit_rate(pot), 0.01678, 0.00001)


def test_exit_rate_cap_is_twelve_percent():
    assert m.breakeven_tc(1e10) == 0.12
    assert m.average_exit_rate(1e10) < 0.12


def _crossover(tc):
    lo, hi, hit = 50_000, 80_000_000, None
    for _ in range(80):
        mid = (lo + hi) / 2
        if m.breakeven_tc(mid) > tc:
            hi, hit = mid, mid
        else:
            lo = mid
    return hit


def test_participation_crossovers():
    assert close(_crossover(0.07), 1_853_000, 5_000)      # ~$1.85m, NOT $5m (that was average)
    assert close(_crossover(0.115), 15_443_000, 10_000)   # ~$15.4m
    assert _crossover(0.15) is None                       # never: cap is 12%


def test_participation_crossover_pot_matches_bisection():
    # Closed form must agree with the independent binary-search helper above at the same
    # relief rates (the UI uses the closed form directly; this is what proves it's not a
    # one-off hand-derived number going stale).
    assert close(m.participation_crossover_pot(0.07), _crossover(0.07), 1.0)
    assert close(m.participation_crossover_pot(0.115), _crossover(0.115), 1.0)
    assert m.participation_crossover_pot(0.15) is None


def test_participation_crossover_pot_scales_with_actual_relief_rate():
    # The bug this guards: a single hardcoded "$1.85m stop-adding line" is only correct for a
    # 7% relief rate. An 11.5% earner's line is nearly 10x further out, not the same number.
    low = m.participation_crossover_pot(0.07)
    high = m.participation_crossover_pot(0.115)
    assert high > low * 5


def test_frontier_is_a_step_function():
    # flat plateau across the 23% band: indifferent between ~$8m and ~$15.4m
    assert m.breakeven_tc(8_000_000) == m.breakeven_tc(12_000_000) == 0.115


# ------------------------------------------------------------- drawdown strategy
def test_fixed40_capacity():
    assert close(40_000 * (1 - 1.05 ** -10) / 0.05, 308_869.40, 0.01)


def test_fixed40_costs_more_than_level():
    gap = m.run(strategy="fixed40")["total_tax"] - m.run(strategy="level")["total_tax"]
    assert close(gap, 69_190.47, 1)


# ------------------------------------------------------------- early withdrawal
def test_early_withdrawal_costs():
    assert close(m.early_withdrawal(50_000)["cost_rate"], 0.075, 1e-9)
    assert close(m.early_withdrawal(400_000)["cost_rate"], 0.205375, 1e-9)


def test_effective_early_penalty():
    for tau, pen in ((0.07, 0.085), (0.115, 0.1075), (0.22, 0.16), (0.24, 0.17)):
        assert close(m.effective_early_penalty(tau), pen, 1e-12)


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
