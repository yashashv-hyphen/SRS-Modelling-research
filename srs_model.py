"""
SRS model — Singapore Supplementary Retirement Scheme (URECA NBS26004).

Compares, on an identical out-of-pocket basis:
  Route A  contribute to SRS, invest inside, draw down over the 10-year window,
           pay tax on 50% of each withdrawal, reinvest the net outside
  Route B  skip SRS, invest the same net-of-relief cash in an ordinary account

Singapore has no capital gains tax and one-tier (exempt) domestic dividends, so an ordinary
account carries no ongoing tax drag for an individual. The SRS advantage is therefore
exactly FV(relief invested) - FV(tax paid on exit). See docs/findings.md.

Tax brackets live in data/tax_brackets_ya2026.json and every function accepts a `brackets`
argument, so alternative schedules (tax-rate creep scenarios) can be passed in.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BRACKETS_PATH = os.path.join(_HERE, "data", "tax_brackets_ya2026.json")


def load_brackets(path=DEFAULT_BRACKETS_PATH):
    with open(path) as f:
        raw = json.load(f)["brackets"]
    return [(float("inf") if upper is None else float(upper), float(rate)) for upper, rate in raw]


BRACKETS = load_brackets()

CAP_CITIZEN = 15_300        # SRS annual cap, Citizens/PRs (15% x $102,000)
CAP_FOREIGN = 35_700        # SRS annual cap, foreigners  (35% x $102,000)
IDLE_RATE = 0.0005          # interest on uninvested SRS cash
PENALTY = 0.05              # early-withdrawal penalty
INCLUSION = 0.5             # share of a qualifying withdrawal that is taxable

CPF_EMPLOYEE_RATE = 0.20        # employee CPF contribution rate on Ordinary Wages
CPF_OW_CEILING_MONTHLY = 8_000  # Ordinary Wage ceiling the employee rate applies up to
EARNED_INCOME_RELIEF = 1_000.0  # flat relief for a resident under 55 with earned income


# ----------------------------------------------------------------------------- tax
def chargeable_from_gross(gross_income, earned_income_relief=EARNED_INCOME_RELIEF):
    """
    Approximate chargeable income from gross annual salary, so callers hand in the number they
    actually know (gross pay) instead of a number they'd have to compute by hand first.
    Subtracts the employee CPF contribution relief -- 20% of Ordinary Wages, capped at the
    $8,000/month OW ceiling (so at most $19,200/year) -- and the flat $1,000 earned-income
    relief. This is the conversion CLAUDE.md pitfall #3 / docs/findings.md #4 already documents
    in prose ("$100k gross is ~$79,800 chargeable"); this makes it a function instead of a
    manual step every caller had to redo.

    Approximation, not a full personal-tax calculator: ignores the Additional Wage (bonus) CPF
    ceiling, and any other reliefs (spouse, parent, course fees, etc.) a real taxpayer might
    also claim. Chargeable income this produces is always an upper bound on the true figure.
    """
    cpf_relief = min(CPF_EMPLOYEE_RATE * gross_income,
                     CPF_EMPLOYEE_RATE * CPF_OW_CEILING_MONTHLY * 12)
    return max(0.0, gross_income - cpf_relief - earned_income_relief)
def tax(chargeable, brackets=None):
    """Singapore resident income tax on a chargeable income."""
    brackets = brackets or BRACKETS
    t, prev = 0.0, 0.0
    for upper, rate in brackets:
        if chargeable <= prev:
            break
        t += (min(chargeable, upper) - prev) * rate
        prev = upper
    return t


def marginal_rate(chargeable, brackets=None):
    """Rate on the next dollar. At an exact band edge, returns the lower band's rate."""
    brackets = brackets or BRACKETS
    for upper, rate in brackets:
        if chargeable <= upper:
            return rate
    return brackets[-1][1]


def relief_value(chargeable_before, contribution=CAP_CITIZEN, brackets=None):
    """
    Cash tax saved by an SRS contribution.
    Computed as tax(before) - tax(after), NOT contribution x marginal rate, because a
    contribution can straddle a band edge and earn a blended rate.
    """
    return tax(chargeable_before, brackets) - tax(max(0.0, chargeable_before - contribution), brackets)


# ---------------------------------------------------------------------- time value
def fv_annuity(payment, rate, years):
    """Future value of `years` end-of-period payments."""
    if rate == 0:
        return payment * years
    return payment * (((1 + rate) ** years - 1) / rate)


def level_payment(pv, rate, years):
    """Annual withdrawal that exactly exhausts a balance still earning `rate`."""
    if rate == 0:
        return pv / years
    return pv * rate / (1 - (1 + rate) ** -years)


# -------------------------------------------------------- exit rates: KEEP THESE APART
def marginal_exit_rate(pot, r=0.05, years=10, other_income=0.0, brackets=None):
    """
    Marginal tax rate on the taxable half of a level drawdown.
    USE FOR PARTICIPATION DECISIONS ('should I contribute one more dollar?').
    """
    half = INCLUSION * level_payment(pot, r, years) + other_income
    return marginal_rate(half, brackets)


def breakeven_tc(pot, r=0.05, years=10, other_income=0.0, brackets=None):
    """Relief rate at which the next contributed dollar is exactly indifferent: 0.5 x marginal."""
    return INCLUSION * marginal_exit_rate(pot, r, years, other_income, brackets)


def participation_crossover_pot(relief_rate, r=0.05, years=10, other_income=0.0, brackets=None):
    """
    The pot size at which contributing stops being worth it at `relief_rate` (docs/findings.md
    #7): below this pot, `relief_rate` beats `breakeven_tc(pot, ...)`; above it, breakeven_tc
    wins. Closed form (brackets are flat bands, so the crossing happens exactly at a band
    edge): pot* = 2 x (L - other_income) x a(years, r), where L is the lower edge of the first
    band whose rate exceeds 2 x relief_rate, and a(n, r) = (1 - (1+r)^-n) / r is the n-year
    annuity factor. Returns None if relief_rate is at least half the top band's rate — the next
    dollar is worth it at any pot size, so there is no stop-adding point.
    """
    brackets = brackets or BRACKETS
    threshold = 2 * relief_rate
    prev_upper, lower_edge = 0.0, None
    for upper, rate in brackets:
        if rate > threshold:
            lower_edge = prev_upper
            break
        prev_upper = upper
    if lower_edge is None:
        return None
    half = max(0.0, lower_edge - other_income)
    annuity_factor = years if r == 0 else (1 - (1 + r) ** -years) / r
    return 2 * half * annuity_factor


def average_exit_rate(pot, r=0.05, years=10, other_income=0.0, brackets=None):
    """
    Total tax / total withdrawn under a level drawdown.
    USE FOR EVALUATION ('what did the whole thing cost?'). Never for participation.
    """
    pmt = level_payment(pot, r, years)
    t = tax(other_income + INCLUSION * pmt, brackets) - tax(other_income, brackets)
    return t / pmt if pmt else 0.0


def effective_early_penalty(tau):
    """
    Extra cost of withdrawing early vs a qualifying withdrawal, per dollar, assuming the same
    marginal rate tau applies either way: 5% penalty + (100% - 50%) inclusion x tau.
    """
    return PENALTY + (1 - INCLUSION) * tau


def per_dollar_ratio(tc, tw):
    """
    SRS / ordinary-account terminal wealth for one pre-tax dollar. Growth cancels, so this
    is independent of return and horizon: (1 - 0.5 tw) / (1 - tc).
    """
    return (1 - INCLUSION * tw) / (1 - tc)


# -------------------------------------------------------------------------- routes
def run(chargeable=120_000, contribution=CAP_CITIZEN, r=0.05, contrib_years=29,
        draw_years=10, other_retirement_income=0.0, strategy="level", brackets=None):
    """
    strategy: 'level'   drain the balance evenly across the window
              'fixed40' withdraw 40k/yr, residual deemed withdrawn at the end in one year
    """
    relief = relief_value(chargeable, contribution, brackets)
    out_of_pocket = contribution - relief

    srs_at_ret = fv_annuity(contribution, r, contrib_years)
    idle_at_ret = fv_annuity(contribution, IDLE_RATE, contrib_years)
    taxable_at_ret = fv_annuity(out_of_pocket, r, contrib_years)

    oi = other_retirement_income
    withdrawals, taxes, net_flows = [], [], []
    balance = srs_at_ret
    residual_tax = 0.0
    if strategy == "level":
        pmt = level_payment(srs_at_ret, r, draw_years)
        for _ in range(draw_years):
            balance = balance * (1 + r) - pmt
            t = tax(oi + INCLUSION * pmt, brackets) - tax(oi, brackets)
            withdrawals.append(pmt); taxes.append(t); net_flows.append(pmt - t)
        residual = max(0.0, balance)
    elif strategy == "fixed40":
        for _ in range(draw_years):
            take = min(40_000.0, balance * (1 + r))
            balance = balance * (1 + r) - take
            t = tax(oi + INCLUSION * take, brackets) - tax(oi, brackets)
            withdrawals.append(take); taxes.append(t); net_flows.append(take - t)
        residual = max(0.0, balance)
        residual_tax = tax(oi + INCLUSION * residual, brackets) - tax(oi, brackets)
    else:
        raise ValueError(f"unknown strategy {strategy!r}")

    endA = sum(nf * (1 + r) ** (draw_years - 1 - i) for i, nf in enumerate(net_flows))
    endA += residual - residual_tax
    endB = taxable_at_ret * (1 + r) ** draw_years
    total_wd = sum(withdrawals) + residual
    total_tax = sum(taxes) + residual_tax

    return {
        "chargeable": chargeable, "r": r, "strategy": strategy,
        "relief_per_year": relief, "relief_rate": relief / contribution,
        "out_of_pocket": out_of_pocket,
        "srs_at_retirement": srs_at_ret, "idle_at_retirement": idle_at_ret,
        "taxable_at_retirement": taxable_at_ret,
        "annual_withdrawal": withdrawals[0], "annual_tax": taxes[0],
        "total_withdrawn": total_wd, "total_tax": total_tax,
        "average_exit_rate": total_tax / total_wd if total_wd else 0.0,
        "residual_deemed": residual, "residual_tax": residual_tax,
        "endA": endA, "endB": endB,
        "advantage": endA - endB,
        "advantage_pct": (endA / endB - 1) if endB else 0.0,
        "fv_relief_invested": fv_annuity(relief, r, contrib_years) * (1 + r) ** draw_years,
        "fv_taxes_paid": sum(t * (1 + r) ** (draw_years - 1 - i) for i, t in enumerate(taxes))
                         + residual_tax,
    }


def early_withdrawal(balance, chargeable_other=0.0, brackets=None):
    """Cost of taking the whole balance out before the prescribed retirement age."""
    pen = balance * PENALTY
    t = tax(chargeable_other + balance, brackets) - tax(chargeable_other, brackets)
    return {"balance": balance, "penalty": pen, "tax": t,
            "net": balance - pen - t, "cost_rate": (pen + t) / balance}


if __name__ == "__main__":
    base = run()
    out = {"base": base,
           "by_return": [run(r=x) for x in (0.03, 0.05, 0.07)],
           "by_income": [run(chargeable=c) for c in (60_000, 80_000, 100_000, 120_000,
                                                     160_000, 200_000, 320_000, 500_000)]}
    with open("results.json", "w") as f:
        json.dump(out, f, indent=1, default=float)
    for k in ("relief_per_year", "out_of_pocket", "srs_at_retirement", "annual_withdrawal",
              "annual_tax", "total_tax", "average_exit_rate", "endA", "endB", "advantage",
              "advantage_pct", "fv_relief_invested", "fv_taxes_paid"):
        print(f"{k:22} {base[k]:>16,.4f}")
    print("\nwrote results.json")
