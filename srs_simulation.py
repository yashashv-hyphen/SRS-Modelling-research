"""
SRS Monte Carlo simulation engine — extends srs_model.py, does not modify it.

Adds four things srs_model.py doesn't have:
  1. Random year-to-year portfolio growth (instead of one fixed return for the whole horizon).
  2. Random year-to-year tax-bracket drift: nominal bracket creep (income grows, thresholds
     don't) plus rare random policy-rate shocks. Both feed into srs_model's existing
     `brackets=` argument — no change needed there.
  3. A Model Predictive Control (MPC) withdrawal strategy: each year, solve a small backward
     dynamic-programming problem ("if I knew the future, how would I split what's left?"),
     take only *this* year's action, then re-solve next year once the real return and real
     tax schedule for that year are known. This is open task T2d in docs/open-tasks.md.
  4. Two "what happens after the SRS window closes" comparisons (spend-to-zero vs. bequest),
     and the external return needed to justify breaking the lock-up early (open task T5).

Every function here takes plain numbers/arrays in and out — no classes, no hidden state — so
each piece can be tested and read on its own. Run `python srs_simulation.py` for a demo across
the same income grid used in docs/findings.md; it writes results_simulation.json and
docs/simulation-walkthrough.md.
"""
import json
import os

import numpy as np

import srs_model as m

DEFAULT_INCOME_GRID = (60_000, 80_000, 100_000, 120_000, 160_000, 200_000, 320_000, 500_000)
DEFAULT_DEATH_AGE = 85          # age used for the "what's left after the window closes" comparison
RETIREMENT_AGE = 63             # age the SRS window opens (matches CLAUDE.md / srs-rules.md schedule)

_HERE = os.path.dirname(os.path.abspath(__file__))
_HISTORICAL_PATH = os.path.join(_HERE, "data", "sp500_annual_returns.json")


def load_historical_returns(path=_HISTORICAL_PATH):
    """S&P 500 annual total returns, 1928-2025 (see the file for the citation). The
    docs/open-tasks.md T2c "public US series" fallback: a single-country nominal equity
    series, not a calibration to SRS-eligible instruments or the Singapore market."""
    with open(path) as f:
        raw = json.load(f)["returns"]
    return [float(r) for _, r in raw]


HISTORICAL_RETURNS = load_historical_returns()
HISTORICAL_MEAN = float(np.mean(HISTORICAL_RETURNS))
HISTORICAL_VOL = float(np.std(HISTORICAL_RETURNS))


# --------------------------------------------------------------------- 1. random growth
def random_return_path(years, mean=0.05, vol=0.15, rng=None):
    """
    One random sequence of `years` yearly returns, lognormally distributed so a return of
    -100% is impossible. `mean`/`vol` are the *arithmetic* mean and stdev you'd quote out loud
    ("5% a year, plus or minus 15%") — converted internally to the lognormal's own parameters.
    This is an approximation (exact only for small vol) — fine for illustrative simulation,
    not a calibrated market model.
    """
    rng = rng or np.random.default_rng()
    sigma = vol
    mu = np.log1p(mean) - 0.5 * sigma ** 2
    draws = rng.normal(mu, sigma, size=years)
    return np.exp(draws) - 1.0


def historical_block_bootstrap_path(years, series=None, block_size=5, rng=None):
    """
    One random sequence of `years` yearly returns, built by splicing together contiguous
    blocks of `block_size` *real* consecutive years from `series` (default: the S&P 500,
    1928-2025 - see load_historical_returns). This is docs/open-tasks.md T2c's "block-bootstrap
    a long return series to capture sequence risk": sampling single years independently would
    erase the clustering that makes sequence risk real (a bad year is more likely to be
    followed by another bad year than the unconditional average suggests, e.g. 2008-2009).
    Keeping blocks intact preserves that clustering; only where one block ends and the next
    (unrelated) one begins is an artificial seam introduced.

    Blocks wrap around the end of the series (a "circular" block bootstrap) so every real
    year, including ones near the end of the dataset, has an equal chance of starting a block.
    """
    series = series if series is not None else HISTORICAL_RETURNS
    rng = rng or np.random.default_rng()
    n = len(series)
    path = []
    while len(path) < years:
        start = rng.integers(0, n)
        block = [series[(start + i) % n] for i in range(block_size)]
        path.extend(block)
    return path[:years]


# ------------------------------------------------------------- 2. random tax-bracket drift
def shifted_brackets(base_brackets, shift):
    """Apply a parallel rate shift to every band, clamped to a sane [0%, 30%] range."""
    return [(upper, min(0.30, max(0.0, rate + shift))) for upper, rate in base_brackets]


def random_policy_shift_path(years, shock_prob=0.03, shock_size_range=(0.01, 0.03), rng=None):
    """
    One random sequence of `years` cumulative rate shifts. Each year there's `shock_prob`
    chance of a policy change (like the YA2024 top-rate rise the literature review notes);
    when it happens the shift moves by a random +/- amount and *stays* there until the next
    shock, because real tax changes don't revert on their own.
    """
    rng = rng or np.random.default_rng()
    shift = 0.0
    path = []
    for _ in range(years):
        if rng.random() < shock_prob:
            direction = rng.choice([-1.0, 1.0])
            magnitude = rng.uniform(*shock_size_range)
            shift += direction * magnitude
        path.append(shift)
    return path


def bracket_creep_income(base_income, wage_growth, year_index):
    """
    Bracket creep isn't a change to the brackets — Singapore's thresholds are nominal and
    don't move. It's the person's own income drifting upward in nominal terms while the bands
    stay put, so the same real income slides into a higher band over the decades.
    """
    return base_income * (1.0 + wage_growth) ** year_index


# ------------------------------------------------------ 3. MPC withdrawal (backward DP core)
def _dp_solve(balance, years_left, brackets_forecast, r_forecast, other_income=0.0, grid_size=80):
    """
    Backward dynamic program over a discretised balance grid (open task T2d).

    State: (years_left, balance). Terminal value (years_left == 0) is the tax on deemed
    withdrawal of whatever remains — the actual SRS rule for the end of the 10-year window.
    Each step back, for every balance on the grid, try withdrawing every amount on the grid
    up to that balance and keep the one that minimises this year's tax plus the best possible
    future cost, given the balance grows at `r_forecast` in between withdrawals.

    Returns the *first* action only — the amount to withdraw this year — plus the plan's
    expected total tax (nominal, not future-valued) if the forecast holds exactly (it won't;
    that's why we re-solve every year instead of trusting this plan for all `years_left` years).

    The DP internally minimises the *future-value-compounded* tax, not the plain nominal sum.
    That distinction matters: ending wealth = FV(gross withdrawn) − FV(tax paid), and
    FV(gross withdrawn) is fixed by the depletion requirement regardless of the withdrawal
    schedule chosen, so maximising ending wealth is exactly equivalent to minimising the
    *compounded* tax — a dollar of tax paid early forgoes more years of growth than a dollar
    paid late, so it must be weighted more heavily. Minimising the plain nominal sum instead
    (an easy mistake) systematically biases the plan away from the true optimum — this is
    exactly what docs/findings.md #9 means by "equal slices minimise it": equal *marginal
    rates* in future-value terms, which for a flat schedule works out to equal dollar amounts.
    """
    if years_left <= 0:
        return 0.0, 0.0

    b_max = balance * (1.0 + r_forecast) ** years_left * 1.05 + 1.0
    grid = np.linspace(0.0, b_max, grid_size)

    # V[n][i] = best achievable FUTURE-VALUE (at window close) of tax, starting with balance
    # grid[i] and n years left. Nominal tax paid with n years left is compounded by (n-1)
    # more years to bring it to the same terminal point as V[n-1]'s own future-valued costs.
    # The window forces exact depletion by its last year (whatever remains is deemed
    # withdrawn as part of that same final withdrawal here, not left over as a separate
    # "free" low-tax year) — so V[1] is a forced full payout, not a free choice.
    V = np.zeros((years_left + 1, grid_size))
    policy0 = np.zeros((years_left + 1, grid_size))  # policy0[n][i] = optimal withdrawal
    brackets_1 = brackets_forecast[years_left - 1] if brackets_forecast else None
    grown_1 = grid * (1.0 + r_forecast)
    V[1] = [m.tax(other_income + m.INCLUSION * g, brackets_1) for g in grown_1]
    policy0[1] = grown_1

    for n in range(2, years_left + 1):
        brackets_n = brackets_forecast[years_left - n] if brackets_forecast else None
        compounding = (1.0 + r_forecast) ** (n - 1)
        grown = grid * (1.0 + r_forecast)
        best_cost = np.full(grid_size, np.inf)
        best_w = np.zeros(grid_size)
        for w in grid:
            remaining = np.maximum(grown - w, 0.0)  # can't withdraw more than what's there
            feasible = grown >= w
            this_tax_fv = m.tax(other_income + m.INCLUSION * w, brackets_n) * compounding
            future = np.interp(remaining, grid, V[n - 1])
            cost = np.where(feasible, this_tax_fv + future, np.inf)
            better = cost < best_cost
            best_cost = np.where(better, cost, best_cost)
            best_w = np.where(better, w, best_w)
        V[n] = best_cost
        policy0[n] = best_w

    # Read off the action for the actual (possibly off-grid) starting balance. No clamp
    # against `balance` here — the action is a withdrawal taken *after* this year's growth,
    # so it can legitimately exceed the pre-growth balance (mpc_drawdown clamps against the
    # post-growth amount once the actual realised return is known).
    action = float(np.interp(balance, grid, policy0[years_left]))
    expected_fv_tax = float(np.interp(balance, grid, V[years_left]))  # future-valued, not nominal
    return action, expected_fv_tax


def mpc_drawdown(srs_at_retirement, draw_years, return_path, brackets_path, other_income=0.0,
                  r_forecast=0.05, use_dp=False, grid_size=80, strategy="mpc", fixed_amount=None):
    """
    `strategy` selects how much to withdraw each year:
      "mpc"          re-plan every year from the CURRENT balance under a flat forecast — the
                     level payment that would drain what's left over the years remaining (or,
                     with use_dp=True, the exact backward-DP solve of the same flat forecast).
                     This is the only strategy that reacts to the balance actually realised.
      "static_level" the level payment computed ONCE in the first year and never revised, even
                     though the real balance will drift away from the forecast.
      "rule40"       $40,000 a year, every year (docs/findings.md pitfall #4 / srs_model.run's
                     'fixed40' route) — on a pot too big to drain that way in `draw_years`, the
                     leftover is simply the returned `residual`, exactly like every other
                     strategy here; the caller deems it withdrawn, same as it would for "mpc".
      "fixed"        `fixed_amount` a year (defaults to $40,000 if not given), same rule.

    The MPC loop: at the start of each of `draw_years`, plan against *today's* known tax
    schedule assumed to hold for the rest of the window (the standard "best guess from the
    latest observation" MPC forecast), take only this year's withdrawal, then apply the
    *actual* random return for the year (which the plan could not have known) and move on.
    Re-planning every year — reacting to whatever the market and the tax schedule actually
    did — is what makes "mpc" MPC rather than a single fixed plan solved once at the start;
    "static_level" is the same starting plan with the re-planning switched off, kept as a
    strategy of its own so the dashboard can show what re-planning is actually worth.

    Because the forecast is flat (same brackets and same assumed return for every remaining
    year), the within-year planning problem for "mpc" has a known closed-form answer: the level
    payment that exactly drains the balance over the remaining years (docs/findings.md #9
    proves level drawdown is optimal for a flat schedule). Using that closed form here —
    instead of re-running the grid search fresh every single year of every simulated path — is
    what makes a multi-thousand-path Monte Carlo sweep fast. Set `use_dp=True` to instead solve
    each year's action with the general backward-DP grid search in `_dp_solve` (open task T2d);
    `test_srs_simulation.py` checks the two agree, and a single showcase path can afford the
    slower exact solve even though a full Monte Carlo sweep cannot.
    """
    static_amount = m.level_payment(srs_at_retirement, r_forecast, draw_years) if strategy == "static_level" else None

    balance = srs_at_retirement
    withdrawals, taxes, balance_path, marginal_rate_path = [], [], [], []
    for year in range(draw_years):
        years_left = draw_years - year
        current_brackets = brackets_path[year]
        if strategy == "mpc":
            if use_dp:
                forecast_brackets = [current_brackets] * years_left
                w, _ = _dp_solve(balance, years_left, forecast_brackets, r_forecast, other_income, grid_size)
            else:
                w = m.level_payment(balance, r_forecast, years_left)
        elif strategy == "static_level":
            w = static_amount
        else:  # "rule40" / "fixed" — the same flat amount every year, no exception for the last
            w = fixed_amount if (strategy == "fixed" and fixed_amount is not None) else 40_000.0
        # The plan above is based on today's balance and the *forecast* return; what can
        # actually be withdrawn is bounded by what's there after the *actual* realised
        # growth for the year, which the plan could not have known in advance.
        grown_actual = balance * (1.0 + return_path[year])
        w = min(max(w, 0.0), grown_actual)
        tax_due = m.tax(other_income + m.INCLUSION * w, current_brackets) - m.tax(other_income, current_brackets)
        withdrawals.append(w)
        taxes.append(tax_due)
        balance = max(0.0, grown_actual - w)
        balance_path.append(balance)
        marginal_rate_path.append(m.marginal_rate(other_income + m.INCLUSION * w, current_brackets))
    return {"withdrawals": withdrawals, "taxes": taxes, "residual": balance,
            "total_withdrawn": sum(withdrawals), "total_tax": sum(taxes),
            "balance_path": balance_path, "marginal_rate_path": marginal_rate_path,
            "strategy": strategy}


# --------------------------------------------------- 4. after-the-window & early-exit maths
def spend_to_zero_vs_bequest(lump_sum_at_window_close, r, extra_years):
    """
    Two honest endpoints for "what happens to the money after the window closes", both
    starting from the same lump sum and the same return assumption:
      A. spend_to_zero — a level annuity that exactly exhausts the lump sum by death.
      B. bequest — never touch it; report what's left at death.
    """
    if extra_years <= 0:
        return {"spend_to_zero_annual": lump_sum_at_window_close, "bequest_if_untouched": lump_sum_at_window_close}
    annual = m.level_payment(lump_sum_at_window_close, r, extra_years)
    bequest = lump_sum_at_window_close * (1.0 + r) ** extra_years
    return {"spend_to_zero_annual": annual, "bequest_if_untouched": bequest}


def bequest_after_spending(lump_sum_at_window_close, r, extra_years, annual_spend):
    """
    Generalises spend_to_zero_vs_bequest's two endpoints to any level annual spend in between:
    what's left at death after spending `annual_spend` a year for `extra_years` years, the
    balance still growing at `r` between withdrawals. `annual_spend=0` reproduces
    bequest_if_untouched; `annual_spend=spend_to_zero_annual` reproduces exactly 0 (to
    floating-point noise) - the relationship is linear in `annual_spend` (grown lump sum minus
    the future value of the spending annuity), so every point strictly between "spend nothing"
    and "spend it all" is a straight-line trade-off, not something requiring its own search.
    """
    if extra_years <= 0:
        return lump_sum_at_window_close
    return (lump_sum_at_window_close * (1.0 + r) ** extra_years
            - m.fv_annuity(annual_spend, r, extra_years))


def early_exit_breakeven_return(balance_now, years_to_lock, r_forecast, other_income=0.0, brackets=None):
    """
    Solve for the external annual return `x` at which breaking the lock-up right now and
    investing the net proceeds elsewhere for `years_to_lock` years ties with just leaving the
    money in SRS to keep compounding untouched until the locked-in age. Closed form because
    both sides are single lump sums compounding at a constant rate to the same future date —
    no tax is paid a second time on the "stay" side because it isn't withdrawn at the lock date,
    only accumulated.
    """
    if years_to_lock <= 0:
        return None
    net_if_broken = m.early_withdrawal(balance_now, other_income, brackets)["net"]
    stay_value = balance_now * (1.0 + r_forecast) ** years_to_lock
    if net_if_broken <= 0:
        return float("inf")
    return (stay_value / net_if_broken) ** (1.0 / years_to_lock) - 1.0


def early_exit_breakeven_excess(balance_now, years_to_lock, r_forecast, other_income=0.0, brackets=None):
    """
    `early_exit_breakeven_return` gives the breakeven ABSOLUTE external return. Outside
    opportunities in T5 (private equity, property, a business) are naturally described by how
    much EXTRA they pay over just staying invested in the market at `r_forecast` -- this is
    that number: breakeven_return - r_forecast. None/inf propagate unchanged (no time left to
    lock, or the early-exit penalty already consumes the whole balance).
    """
    thr = early_exit_breakeven_return(balance_now, years_to_lock, r_forecast, other_income, brackets)
    if thr is None or thr == float("inf"):
        return thr
    return thr - r_forecast


# --------------------------------------------- 5. early exit as a real option (open task T5)
# docs/open-tasks.md T5: outside opportunities (PE, property, a business) arrive as a Poisson
# process with rate lambda and a random excess return; breaking the SRS lock-up to take one
# costs 5% plus tax on 100% instead of 50% (early_exit_breakeven_excess, above, is the
# per-event payoff this section's random arrivals get compared against).
def poisson_opportunity_counts(years, lam=0.2, rng=None):
    """How many outside investment opportunities arrive in each of `years` years, as
    independent Poisson(lam) draws. `lam` is opportunities per year -- most years draw 0; it's
    the rate parameter T5 asks for, not a probability, so values above 1 are legitimate (more
    than one opportunity can arrive in the same year)."""
    rng = rng or np.random.default_rng()
    return rng.poisson(lam, size=years).tolist()


def draw_excess_returns(n, mean_excess=0.05, rng=None):
    """The excess return (over just staying in the market) offered by each of `n` arriving
    opportunities, drawn from an exponential distribution: always positive -- nobody chases an
    outside deal that pays worse than staying invested -- occasionally large, with mean
    `mean_excess`. This is T5's 'random excess return'."""
    rng = rng or np.random.default_rng()
    if n == 0:
        return []
    return rng.exponential(mean_excess, size=n).tolist()


def simulate_early_exit_path(balance_path, r_forecast, other_income_path=None, brackets_path=None,
                              lam=0.2, mean_excess=0.05, rng=None):
    """
    One simulated lifetime's worth of early-exit temptation, year by year, for as long as
    `balance_path` (the SRS balance at the start of each remaining year before the natural
    unlock) still has years left to run.

    Each year, `years_to_lock` years still separate the saver from the natural, penalty-free
    unlock. Opportunities arrive per `poisson_opportunity_counts`; if one or more arrive, the
    BEST excess return on offer that year (`draw_excess_returns`) is compared against
    `early_exit_breakeven_excess` for that balance/years_to_lock/income/tax-schedule combination.
    The first year an offer clears that bar, the lock-up is broken and the simulated lifetime
    stops there (the money has left SRS); a lifetime that never sees a good-enough offer simply
    runs out the years_to_lock clock with the decision never triggered -- matching T5's "explore
    WHEN early withdrawal is worth it", not "assume it always/never happens".

    Returns one row per simulated year up to and including an exit (if any).
    """
    rng = rng or np.random.default_rng()
    n_years = len(balance_path) - 1
    rows = []
    for year in range(n_years):
        years_to_lock = n_years - year
        balance = balance_path[year]
        oi = other_income_path[year] if other_income_path else 0.0
        brackets = brackets_path[year] if brackets_path else None
        threshold = early_exit_breakeven_excess(balance, years_to_lock, r_forecast, oi, brackets)
        count = poisson_opportunity_counts(1, lam, rng)[0]
        offers = draw_excess_returns(count, mean_excess, rng)
        best_offer = max(offers) if offers else None
        exited = (best_offer is not None and threshold is not None
                  and threshold != float("inf") and best_offer >= threshold)
        rows.append({"year": year, "years_to_lock": years_to_lock, "balance": balance,
                     "opportunities_seen": count, "best_excess_offer": best_offer,
                     "breakeven_excess_return": threshold, "exited": exited})
        if exited:
            break
    return rows


def simulate_early_exit_portfolio(balance_path, r_forecast, other_income_path=None, brackets_path=None,
                                   lam=0.2, mean_excess=0.05, n_paths=500, seed=None):
    """
    Run `simulate_early_exit_path` `n_paths` times over the SAME balance/income/tax path --
    only the opportunity arrivals and their sizes are random -- and summarise: across many
    plausible futures, how often does a good-enough outside opportunity ever actually show up
    before the money unlocks naturally, and how early? This is the honest "will this happen"
    answer T5 asks for, as odds rather than a single deterministic breakeven number.
    """
    rng = np.random.default_rng(seed)
    paths = [simulate_early_exit_path(balance_path, r_forecast, other_income_path, brackets_path,
                                       lam, mean_excess, rng) for _ in range(n_paths)]
    exited = [p for p in paths if p and p[-1]["exited"]]
    exit_years = [p[-1]["year"] for p in exited]
    return {
        "n_paths": n_paths, "lam": lam, "mean_excess": mean_excess,
        "fraction_that_ever_exit_early": len(exited) / n_paths,
        "exit_year_given_exit": {
            "median": float(np.median(exit_years)) if exit_years else None,
            "p10": float(np.percentile(exit_years, 10)) if exit_years else None,
            "p90": float(np.percentile(exit_years, 90)) if exit_years else None,
        } if exit_years else None,
        "breakeven_excess_return_by_year": [row["breakeven_excess_return"] for row in paths[0]],
    }


def early_exit_threshold_by_bracket(balance, years_to_lock_grid=(1, 3, 5, 9),
                                     incomes=DEFAULT_INCOME_GRID, r_forecast=0.05, brackets=None):
    """
    How the breakeven excess return (the bar an outside opportunity must clear to justify
    breaking the lock-up) moves with the saver's OTHER income in the exit year and with how
    many years are left before the money would have unlocked naturally anyway.

    This settles T5's practitioner dispute computationally: Investment Moats argues early
    withdrawal can pay for high-bracket savers; a commenter disputes it. Both are right about
    different incomes -- this table is the actual dependence on income the open task asked the
    model to show, rather than a yes/no answer.
    """
    rows = []
    for income in incomes:
        for ytl in years_to_lock_grid:
            thr = early_exit_breakeven_excess(balance, ytl, r_forecast, other_income=income, brackets=brackets)
            rows.append({"other_income": income, "years_to_lock": ytl, "breakeven_excess_return": thr})
    return rows


# ------------------------------------------------------------- putting it together per path
def simulate_one_path(chargeable, contribution=m.CAP_CITIZEN, contrib_years=29, draw_years=10,
                       mean_return=0.05, vol=0.15, wage_growth=0.02, shock_prob=0.03,
                       shock_size_range=(0.01, 0.03), death_extra_years=DEFAULT_DEATH_AGE - (RETIREMENT_AGE + 10),
                       other_income=0.0, rng=None, base_brackets=None, drawdown_strategy="mpc",
                       drawdown_fixed_amount=None, use_dp=False, return_mode="parametric",
                       historical_series=None, historical_block_size=5):
    """
    One simulated lifetime: 29 years of contributions (each year's relief computed against
    that year's drifted/shocked brackets and drifted income), then a 10-year drawdown run
    under `drawdown_strategy` (see `mpc_drawdown`), then the after-window comparison and, for
    every contribution year, what an outside opportunity would have needed to pay to beat
    staying in SRS.

    `base_brackets` overrides the IRAS YA2026 schedule as the starting point that wage-growth
    creep and policy shocks then drift away from — lets a caller explore "what if the brackets
    themselves were different" independently of "what if they also drift over time".

    `return_mode`: "parametric" (default) draws each year's return from the lognormal model
    (`random_return_path`, `mean_return`/`vol`). "historical" instead splices together real
    consecutive years from `historical_series` (default: S&P 500, 1928-2025) via
    `historical_block_bootstrap_path` — `mean_return`/`vol` are then ignored for the draw
    itself (they still set the forecast pot used for the marginal participation question).
    """
    rng = rng or np.random.default_rng()
    total_years = contrib_years + draw_years
    if return_mode == "historical":
        returns = historical_block_bootstrap_path(total_years, historical_series,
                                                   historical_block_size, rng)
    elif return_mode == "parametric":
        returns = random_return_path(total_years, mean_return, vol, rng)
    else:
        raise ValueError(f"unknown return_mode {return_mode!r}")
    policy_shifts = random_policy_shift_path(total_years, shock_prob, shock_size_range, rng)
    start_brackets = base_brackets if base_brackets is not None else m.BRACKETS
    brackets_by_year = [shifted_brackets(start_brackets, s) for s in policy_shifts]

    # The marginal question each contribution year ("is this dollar still worth it?") is
    # judged against the FULL eventual pot from the whole 29-year contribution plan, not just
    # the balance accumulated so far — a dollar added in year 1 pushes on the same eventual
    # withdrawal bracket as a dollar added in year 29. Only the *tax schedule* used to read
    # that pot's marginal exit rate changes year to year (if a policy shock hits); the
    # forecast pot size itself is a fixed planning assumption under the mean-return forecast.
    projected_total_pot = m.fv_annuity(contribution, mean_return, contrib_years)

    # --- contribution phase ---
    # Track two balances side by side under the SAME market returns:
    #   balance        the SRS account (full contribution goes in)
    #   nosrs_balance  the "didn't use SRS" account: only the out-of-pocket cash (contribution
    #                  minus the tax you saved) is invested normally. No capital-gains tax in
    #                  Singapore, so it grows untaxed. This is the honest apples-to-apples
    #                  alternative — same money out of your pocket either way.
    balance = 0.0
    nosrs_balance = 0.0
    yearly = []
    for y in range(contrib_years):
        drifted_income = bracket_creep_income(chargeable, wage_growth, y)
        brackets_y = brackets_by_year[y]
        relief = m.relief_value(drifted_income, contribution, brackets_y)
        relief_rate = relief / contribution if contribution else 0.0
        out_of_pocket = contribution - relief
        balance = balance * (1.0 + returns[y]) + contribution
        nosrs_balance = nosrs_balance * (1.0 + returns[y]) + out_of_pocket

        marg_exit = m.marginal_exit_rate(projected_total_pot, mean_return, draw_years, other_income, brackets_y)
        breakeven_tc = m.INCLUSION * marg_exit
        still_worth_it = relief_rate > breakeven_tc

        breakeven_x = early_exit_breakeven_return(
            balance, contrib_years - 1 - y, mean_return, other_income, brackets_y)

        yearly.append({
            "year": y + 1, "drifted_income": drifted_income, "relief_rate": relief_rate,
            "relief_dollars": relief, "marginal_exit_rate_forecast": marg_exit,
            "breakeven_tc": breakeven_tc, "still_worth_contributing": still_worth_it,
            "balance": balance, "nosrs_balance": nosrs_balance,
            "top_marginal_rate": m.marginal_rate(drifted_income, brackets_y),
            "early_exit_breakeven_return": breakeven_x,
        })

    srs_at_retirement = balance
    nosrs_at_retirement = nosrs_balance

    # --- drawdown phase: the chosen strategy re-solves (or doesn't) every year against the
    # realised returns/brackets. The "$40k/yr" rule is always ALSO computed on the identical
    # realised path (docs/findings.md pitfall #4: a tax-free threshold people wrongly cite as a
    # strategy) so the dashboard can show an honest apples-to-apples comparison regardless of
    # which strategy the user picked as their actual plan.
    draw_returns = returns[contrib_years:]
    draw_brackets = brackets_by_year[contrib_years:]
    drawdown = mpc_drawdown(srs_at_retirement, draw_years, draw_returns, draw_brackets,
                             other_income, mean_return, use_dp=use_dp,
                             strategy=drawdown_strategy, fixed_amount=drawdown_fixed_amount)
    rule40 = (drawdown if drawdown_strategy == "rule40" else
              mpc_drawdown(srs_at_retirement, draw_years, draw_returns, draw_brackets,
                           other_income, mean_return, strategy="rule40"))

    # Whatever a plan leaves standing is deemed-withdrawn (50% taxable) at window close — the
    # real end-of-window rule. In the zero-noise base case the level plan drains it to exactly
    # 0, so this is a no-op there; under real (stochastic) returns any plan can miss its target.
    def _close_out(dd):
        resid = dd["residual"]
        resid_tax = (m.tax(other_income + m.INCLUSION * resid, draw_brackets[-1])
                     - m.tax(other_income, draw_brackets[-1]))
        return dd["total_tax"] + resid_tax, resid, resid_tax

    mpc_total_tax, residual, residual_tax = _close_out(drawdown)
    rule40_tax, _, _ = _close_out(rule40)
    residual_net = residual - residual_tax

    # --- SRS wealth over time (endA at window close): net-of-tax withdrawals reinvested in an
    # ordinary account at the realised returns (no capital-gains tax) as they're received, plus
    # whatever's still sitting in SRS. Forward recurrence `outside = outside*(1+r) + nf` is the
    # standard FV-of-a-cashflow-series identity — algebraically identical to (and simpler and
    # faster than) compounding each flow separately to the end — and, as a side effect, gives
    # the running total at every year instead of only the final one, for the wealth-over-time
    # chart.
    net_flows = [w - t for w, t in zip(drawdown["withdrawals"], drawdown["taxes"])]
    outside, wealth_with_srs_drawdown = 0.0, []
    for i in range(draw_years):
        outside = outside * (1.0 + draw_returns[i]) + net_flows[i]
        still_in_srs = residual_net if i == draw_years - 1 else drawdown["balance_path"][i]
        wealth_with_srs_drawdown.append(outside + still_in_srs)
    endA = wealth_with_srs_drawdown[-1]

    # --- no-SRS wealth over time (endB at window close): the same out-of-pocket cash in an
    # ordinary account, grown at the same realised returns straight through to window close —
    # nothing is withdrawn from this side, so it's a running product.
    running, wealth_without_srs_drawdown = nosrs_at_retirement, []
    for y in range(draw_years):
        running *= (1.0 + draw_returns[y])
        wealth_without_srs_drawdown.append(running)
    endB = wealth_without_srs_drawdown[-1]

    after_window = spend_to_zero_vs_bequest(endA, mean_return, death_extra_years)
    total_relief_received = sum(y["relief_dollars"] for y in yearly)
    flip_years = [y["year"] for y in yearly if not y["still_worth_contributing"]]

    return {
        "chargeable": chargeable, "mean_return": mean_return, "vol": vol,
        "yearly_contributions": yearly,
        "srs_at_retirement": srs_at_retirement,
        "nosrs_at_retirement": nosrs_at_retirement,
        "total_relief_received": total_relief_received,
        "first_year_not_worth_contributing": flip_years[0] if flip_years else None,
        "draw_returns": list(draw_returns), "draw_brackets": draw_brackets,
        "drawdown_strategy": drawdown_strategy,
        "mpc_drawdown": drawdown,
        "rule40_drawdown": rule40,
        "mpc_total_tax": mpc_total_tax,
        "rule40_total_tax": rule40_tax,
        "smart_vs_rule40_tax_gap": rule40_tax - mpc_total_tax,
        "wealth_with_srs": endA,
        "wealth_without_srs": endB,
        "wealth_with_srs_path": [y["balance"] for y in yearly] + wealth_with_srs_drawdown,
        "wealth_without_srs_path": [y["nosrs_balance"] for y in yearly] + wealth_without_srs_drawdown,
        "advantage": endA - endB,
        "advantage_pct": (endA / endB - 1.0) if endB else 0.0,
        "after_window": after_window,
    }


def simulate_portfolio(chargeable, n_paths=200, seed=None, **kwargs):
    """Run `n_paths` simulated lifetimes for one income level and summarise the spread."""
    rng = np.random.default_rng(seed)
    paths = [simulate_one_path(chargeable, rng=rng, **kwargs) for _ in range(n_paths)]

    def pct(key_fn, p):
        vals = sorted(key_fn(path) for path in paths)
        idx = min(len(vals) - 1, int(p * (len(vals) - 1)))
        return vals[idx]

    flip_count = sum(1 for p in paths if p["first_year_not_worth_contributing"] is not None)
    win_count = sum(1 for p in paths if p["advantage"] > 0)

    def band(key_fn):
        return {"p10": pct(key_fn, 0.10), "median": pct(key_fn, 0.50), "p90": pct(key_fn, 0.90)}

    def path_band(key):
        # Per-year p10/median/p90 across all paths — the raw material for a wealth-over-time
        # fan chart. Every path shares the same length (contrib_years + draw_years), so this is
        # a plain array op, not a per-year re-sort.
        arr = np.asarray([p[key] for p in paths])
        return {"p10": np.percentile(arr, 10, axis=0).tolist(),
                "median": np.percentile(arr, 50, axis=0).tolist(),
                "p90": np.percentile(arr, 90, axis=0).tolist()}

    summary = {
        "chargeable": chargeable, "n_paths": n_paths,
        # the headline: how much better (or worse) off SRS leaves you vs not using it.
        "advantage": band(lambda p: p["advantage"]),
        "advantage_pct": band(lambda p: p["advantage_pct"]),
        "wealth_with_srs": band(lambda p: p["wealth_with_srs"]),
        "wealth_without_srs": band(lambda p: p["wealth_without_srs"]),
        "total_relief_received": band(lambda p: p["total_relief_received"]),
        "smart_vs_rule40_tax_gap": band(lambda p: p["smart_vs_rule40_tax_gap"]),
        "srs_at_retirement": band(lambda p: p["srs_at_retirement"]),
        "bequest_if_untouched": band(lambda p: p["after_window"]["bequest_if_untouched"]),
        "spend_to_zero_annual": band(lambda p: p["after_window"]["spend_to_zero_annual"]),
        "fraction_of_paths_where_contributing_ever_stops_paying": flip_count / n_paths,
        # the fraction of simulated futures in which SRS actually comes out ahead — the closest
        # honest answer to "will SRS give a good yield", stated as odds rather than a promise.
        "prob_srs_wins": win_count / n_paths,
        "wealth_with_srs_path": path_band("wealth_with_srs_path"),
        "wealth_without_srs_path": path_band("wealth_without_srs_path"),
    }
    # Pick the median-*advantage* path as the representative story (the headline metric).
    median_idx = sorted(range(n_paths), key=lambda i: paths[i]["advantage"])[n_paths // 2]
    return {"summary": summary, "median_path": paths[median_idx]}


# ------------------------------------------------------------------ sweeps across the axes
# The whole question is comparative: how does SRS's advantage change as income, market return,
# and the tax regime change? These run the Monte Carlo once per point on each axis and return
# the advantage band (p10/median/p90) at each — the raw material for the comparison charts.

DEFAULT_RETURN_GRID = (0.03, 0.04, 0.05, 0.06, 0.07, 0.08)


def advantage_by_income(incomes=DEFAULT_INCOME_GRID, n_paths=200, seed=None, **kwargs):
    """Advantage band at each income level, holding market and tax settings fixed."""
    rows = []
    for inc in incomes:
        s = simulate_portfolio(inc, n_paths=n_paths, seed=seed, **kwargs)["summary"]
        rows.append({"income": inc, "advantage": s["advantage"],
                     "total_relief_received": s["total_relief_received"]})
    return rows


def advantage_by_return(return_grid=DEFAULT_RETURN_GRID, chargeable=120_000, n_paths=200,
                        seed=None, **kwargs):
    """Advantage band at each average market return, holding income and tax settings fixed.
    Shows both the dollar advantage (grows with return) and the % edge (shrinks) — findings.md §5."""
    kwargs.pop("mean_return", None)
    rows = []
    for r in return_grid:
        s = simulate_portfolio(chargeable, n_paths=n_paths, seed=seed, mean_return=r, **kwargs)["summary"]
        rows.append({"mean_return": r, "advantage": s["advantage"],
                     "advantage_pct": s["advantage_pct"]})
    return rows


def advantage_by_tax_regime(chargeable=120_000, wage_growth=0.02, shock_prob=0.03,
                            n_paths=200, seed=None, **kwargs):
    """Advantage band under three tax futures: brackets frozen forever; bracket creep as a
    rising salary drifts into higher bands; and creep plus random rate-change shocks."""
    kwargs.pop("wage_growth", None)
    kwargs.pop("shock_prob", None)
    regimes = [
        ("Brackets frozen forever", 0.0, 0.0),
        ("Bracket creep (pay rises)", wage_growth, 0.0),
        ("Creep + rate-change shocks", wage_growth, shock_prob),
    ]
    rows = []
    for name, wg, sp in regimes:
        s = simulate_portfolio(chargeable, n_paths=n_paths, seed=seed,
                               wage_growth=wg, shock_prob=sp, **kwargs)["summary"]
        rows.append({"regime": name, "advantage": s["advantage"]})
    return rows


if __name__ == "__main__":
    grid_results = {str(income): simulate_portfolio(income, n_paths=200, seed=42)
                     for income in DEFAULT_INCOME_GRID}
    with open("results_simulation.json", "w") as f:
        json.dump(grid_results, f, indent=1, default=float)
    print("wrote results_simulation.json")

    return_rows = advantage_by_return(chargeable=120_000, n_paths=200, seed=42)
    tax_rows = advantage_by_tax_regime(chargeable=120_000, n_paths=200, seed=42)

    from srs_walkthrough import write_walkthrough
    write_walkthrough(grid_results, "docs/simulation-walkthrough.md",
                      return_rows=return_rows, tax_rows=tax_rows)
    print("wrote docs/simulation-walkthrough.md")

    # T5: early exit as a real option. Base case balance path = the base-case SRS balance at
    # each year of the 10-year window (docs/findings.md base case), lam=0.2 opportunities/year,
    # mean 5% excess return on offer when one arrives.
    base_run = m.run()
    pot = base_run["srs_at_retirement"]
    draw_years = 10
    balance_path_demo = [pot * (1 - i / draw_years) for i in range(draw_years + 1)]
    portfolio = simulate_early_exit_portfolio(balance_path_demo, r_forecast=0.05,
                                              lam=0.2, mean_excess=0.05, n_paths=2000, seed=42)
    threshold_table = early_exit_threshold_by_bracket(pot, r_forecast=0.05)
    with open("results_early_exit.json", "w") as f:
        json.dump({"portfolio": portfolio, "threshold_by_bracket": threshold_table},
                 f, indent=1, default=float)
    print("\nT5 -- early exit as a real option (base-case pot, lam=0.2/yr, mean excess 5%):")
    print(f"  fraction of simulated lifetimes that ever take an early exit: "
         f"{portfolio['fraction_that_ever_exit_early']:.1%}")
    if portfolio["exit_year_given_exit"]:
        print(f"  given an exit happens, year (of {draw_years}): "
             f"p10={portfolio['exit_year_given_exit']['p10']:.1f}  "
             f"median={portfolio['exit_year_given_exit']['median']:.1f}  "
             f"p90={portfolio['exit_year_given_exit']['p90']:.1f}")
    print("  breakeven excess return needed, by other income (years_to_lock=5):")
    for row in threshold_table:
        if row["years_to_lock"] == 5:
            thr = row["breakeven_excess_return"]
            thr_s = f"{thr:.1%}" if isinstance(thr, float) and thr != float("inf") else str(thr)
            print(f"    other_income=${row['other_income']:>9,}   breakeven={thr_s}")
    print("wrote results_early_exit.json")
