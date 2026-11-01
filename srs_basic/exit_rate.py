#avg_exit_rate (B, k, other, I, schedule) and if B=0 return 0 
"""SRS exit tax rates (Model 1, formulas M1.2 and M1.7)."""

from srs_basic.tax import band_rate, tax


def avg_exit_rate(B, k, other, I, schedule):
    """M1.2: total tax on SRS withdrawals / total withdrawn.

    B        SRS balance at retirement ($)
    k        years the balance is withdrawn over (even split)
    other    other taxable income in each retirement year ($)
    I        share of each withdrawal that is taxable (0.5 for SRS)
    schedule tax bands from tax.load_schedule()
    """
    if B <= 0:
        return 0.0
    yearly_withdrawal = B / k
    taxable_from_srs = I * yearly_withdrawal
    extra_tax_per_year = tax(other + taxable_from_srs, schedule) - tax(other, schedule)
    return k * extra_tax_per_year / B
##exit rate = the price of withdrawing, lower than tax rate, since only 50% is taxed

def marginal_breakeven(B, k, other, I, schedule):
    """M1.7 (optional): tax on the last SRS dollar withdrawn, per dollar.

    = I x the band rate that each year's top dollar of taxable income falls in.
    """
    taxable_income = other + I * (B / k)
    return I * band_rate(taxable_income, schedule)


if __name__ == "__main__":
    from srs_basic.config import SCHEDULE_CSV, REGIME
    from srs_basic.tax import load_schedule

    schedule = load_schedule(SCHEDULE_CSV, REGIME)
    for B in [400_000, 1_000_000, 3_000_000]:
        print(f"B = ${B:,}: average exit rate {avg_exit_rate(B, 10, 0, 0.5, schedule):.2%}")
    print(f"B = $1M, lump sum: {avg_exit_rate(1_000_000, 1, 0, 0.5, schedule):.2%}")
    print(f"B = $1M, $30k other income: {avg_exit_rate(1_000_000, 10, 30_000, 0.5, schedule):.2%}")