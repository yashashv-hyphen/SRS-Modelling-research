"""SRS exit tax rates (Model 1, formulas M1.2 and M1.7)."""

from srs_basic.tax import band_rate, tax


def _check_years(k):
    if k < 1 or int(k) != k:
        raise ValueError(f"k must be a whole number of years >= 1, got {k}")


def avg_exit_rate(B, k, other, I, schedule):
    """M1.2: total tax on SRS withdrawals / total withdrawn (whole balance).

    B        SRS balance at retirement ($)
    k        years the balance is withdrawn over (even split)
    other    other taxable income in each retirement year ($)
    I        share of each withdrawal that is taxable (0.5 for SRS)
    schedule tax bands from tax.load_schedule()
    """
    _check_years(k)
    if B <= 0:
        return 0.0
    yearly_withdrawal = B / k
    taxable_from_srs = I * yearly_withdrawal
    extra_tax_per_year = tax(other + taxable_from_srs, schedule) - tax(other, schedule)
    return k * extra_tax_per_year / B


def marginal_breakeven(B, k, other, I, schedule):
    """M1.7 (optional): tax on the last SRS dollar withdrawn, per dollar.

    = I x the band rate of each year's last dollar of taxable income.
    Use for "add one more dollar?" decisions, not for the whole balance.
    """
    _check_years(k)
    taxable_income = other + I * (B / k)
    return I * band_rate(taxable_income, schedule)


if __name__ == "__main__":
    from srs_basic.config import I as INCL, K, OTHER, REGIME, SCHEDULE_CSV
    from srs_basic.tax import load_schedule

    schedule = load_schedule(SCHEDULE_CSV, REGIME)
    for bal in [400_000, 1_000_000, 3_000_000]:
        print(f"B = ${bal:,}: average exit rate "
              f"{avg_exit_rate(bal, K, OTHER, INCL, schedule):.2%}")
