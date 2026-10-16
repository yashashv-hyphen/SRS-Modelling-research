# Verified findings

Every number below was regenerated from `srs_model.py` on 21 Sep 2026. Where a test pins it, the
test name is given. Base case throughout unless stated: chargeable income $120,000 before relief,
$15,300 contributed a year for 29 years (ages 35–63), 5% return, level drawdown over ages 64–73
with the balance still invested, no other retirement income, net proceeds reinvested at 5%,
measured at age 73. Tax rules and their sources are in `docs/srs-rules.md`.

## 1. The per-dollar condition

One pre-tax dollar, return `r`, horizon `n`, relief rate `tc` at contribution, marginal rate `tw`
on the taxable half at withdrawal. No capital gains tax, so the ordinary account has no drag:

```
SRS:       (1+r)^n × (1 − 0.5·tw)
Ordinary:  (1 − tc) × (1+r)^n
SRS wins  ⇔  tc > 0.5·tw         — independent of r and n
```

The ratio `(1 − 0.5·tw)/(1 − tc)` is 1.0903955 for tc = 11.5%, tw = 7%, identical for every
r ∈ {3,5,7}% and n ∈ {10,29,40}. (`test_per_dollar_growth_cancels`)

**Contributions are separable, withdrawals are not.** Progressive brackets make `tw` a function of
the accumulated pot, so each extra dollar raises the exit rate on every withdrawn dollar. The
participation decision is therefore marginal: contribute while `tc > 0.5 × marginal exit rate`.

## 2. The advantage is one subtraction

```
advantage = FV(relief received and invested) − FV(tax paid on withdrawal)
```

Holds exactly (to 1e-6) across returns, incomes and strategies. (`test_advantage_identity`)
Equivalent form: advantage ≈ (average relief rate − average exit rate) × grown pot.

## 3. Base case

| Item | Value |
|---|---|
| Relief per year | $1,759.50 (11.5%) |
| Cash out of pocket per year | $13,540.50 |
| SRS pot at 64 | $953,537 |
| Level withdrawal per year | $123,487 |
| Tax per year / total tax | $2,072 / $20,721 |
| Average exit rate | 1.68% |
| Marginal exit rate on the taxable half | 7.0% |
| **Route A (SRS) at 73** | **$1,527,150** |
| **Route B (ordinary account, same out-of-pocket) at 73** | **$1,374,593** |
| **Advantage** | **$152,557 (11.10%)** |
| FV relief invested / FV tax paid | $178,619 / $26,062 |

(`test_base_case_regression`)

## 4. By income (5% return)

| Chargeable income | Relief on $15,300 | Relief rate | Advantage at 73 |
|---|---|---|---|
| $60,000 | $1,071.00 | 7.00% | $82,663 (5.72%) |
| $80,000 | $1,071.00 | 7.00% | $82,663 (5.72%) |
| $100,000 | $1,759.50 | 11.50% | $152,557 (11.10%) |
| $120,000 | $1,759.50 | 11.50% | $152,557 (11.10%) |
| $160,000 | $2,295.00 | 15.00% | $206,920 (15.67%) |
| $200,000 | $2,754.00 | 18.00% | $253,516 (19.90%) |
| $250,000 | $2,957.00 | 19.33% (straddles $240k edge) | — |
| $320,000 | $3,060.00 | 20.00% | $284,580 (22.90%) |
| $500,000 | $3,366.00 | 22.00% | $315,644 (26.05%) |

A gross salary of $100,000 is roughly $79,800 chargeable after employee CPF relief (~$19,200,
assuming the $8,000/month ordinary wage ceiling) and $1,000 earned income relief — the 7% band,
relief $1,071, advantage $82,663. (`test_relief_gross_vs_chargeable`)

## 5. By return — higher returns shrink the percentage edge

| Return | Pot at 64 | Average exit rate | Advantage | % |
|---|---|---|---|---|
| 3% | $691,848 | 0.73% | $100,177 | 12.17% |
| 5% | $953,537 | 1.68% | $152,557 | 11.10% |
| 7% | $1,336,402 | 2.68% | $231,988 | 9.97% |

Mechanism: the 50% exemption is fixed, but the growth share of the pot rises with return. Over
29 years of contributions, growth is 25.2% of the pot at 2%, 35.9% at 3%, 45.2% at 4%, 53.5% at
5%, 60.6% at 6%, 66.8% at 7%, 72.1% at 8%. It crosses 50% at **r = 4.56%**; below that the
tax-free half covers all the growth. (`test_higher_return_lowers_pct_advantage`)

## 6. Exit rates by pot — marginal, average, breakeven

Level drawdown over 10 years at 5%, no other income.

| Pot at withdrawal age | Withdrawal / yr | Tax / yr | Average exit | Marginal exit | Breakeven tc |
|---|---|---|---|---|---|
| $200,000 | $25,901 | $0 | 0.00% | 0.0% | 0.00% |
| $400,000 | $51,802 | $118 | 0.23% | 2.0% | 1.00% |
| $1,000,000 | $129,505 | $2,283 | 1.76% | 7.0% | 3.50% |
| $2,000,000 | $259,009 | $9,376 | 3.62% | 15.0% | 7.50% |
| $3,000,000 | $388,514 | $20,116 | 5.18% | 18.0% | 9.00% |
| $5,000,000 | $647,523 | $45,378 | 7.01% | 22.0% | 11.00% |
| $8,000,000 | $1,036,037 | $88,294 | 8.52% | 23.0% | 11.50% |
| $50,000,000 | $6,475,229 | $736,177 | 11.37% | 24.0% | 12.00% |

**The cap:** top rate 24% × 50% inclusion = 12%. The breakeven reaches exactly 12% in the top band
and never exceeds it; the average approaches 12% but never reaches it.
(`test_exit_rate_cap_is_twelve_percent`)

## 7. Participation crossovers — closed form

The next dollar stops paying once the breakeven exceeds `tc`. Because the breakeven only moves at
band edges, the crossover pot is exactly:

```
pot* = 2 × L × a(10, r),   a(10, 5%) = (1 − 1.05^−10)/0.05 = 7.721735
```

where `L` is the lower edge of the first band whose rate exceeds `2·tc`.

| Relief rate tc | L | Crossover pot | Years of max contribution needed |
|---|---|---|---|
| 0% | $20,000 | $308,869 | 15y at 5%, 13y at 7% |
| 2% | $40,000 | $617,739 | 23y at 5%, 20y at 7% |
| 3.5% | $80,000 | $1,235,478 | 34y at 5%, 28y at 7% |
| 7% | $120,000 | $1,853,216 | 41y at 5%, 34y at 7% |
| 11.5% | $1,000,000 | $15,443,470 | beyond 60 years |
| ≥ 15% | — | never | exit rate caps at 12% |

(`test_participation_crossovers`) Note the 0% crossover equals the $40k/yr drain capacity: both are
"taxable half first exceeds $20,000".

**Plateaus:** the 11.5% bracket is exactly indifferent from ~$8m (breakeven hits 11.5% in the 23%
band) until $15.44m (24% band). The frontier is a staircase. (`test_frontier_is_a_step_function`)

## 8. Size of the loss when tc < breakeven (per marginal dollar)

`per_dollar_ratio(tc, tw) − 1`, where tw is the marginal rate on the taxable half:

| Relief tc | tw = 7% | 15% | 20% | 24% |
|---|---|---|---|---|
| 0% | −3.50% | −7.50% | −10.00% | −12.00% |
| 3.5% | 0.00% | −4.15% | −6.74% | −8.81% |
| 7% | +3.76% | −0.54% | −3.23% | −5.38% |
| 11.5% | +9.04% | +4.52% | +1.69% | −0.56% |

Asymmetry: best case (tc 22%, tw ≈ 0) is +28.2% per dollar; worst case (tc 0%, tw 24%) is −12.0%.
Crossing the frontier affects only the *next* dollar — the existing balance stays profitable, so
the implication is "stop adding", not "withdraw".

## 9. Drawdown strategy

Deterministic argument: money compounds at the same rate inside and outside SRS, so terminal wealth
= grown pot − compounded tax. The only job is minimising tax, and with a convex (progressive)
schedule equal slices minimise it. **Level drawdown is optimal in the deterministic case.** DP only
adds value with stochastic returns (see T2 in `docs/open-tasks.md`).

The "$40,000 a year, tax-free" figure drains at most **$308,869** at 5% in ten years
(`test_fixed40_capacity`). Above that, the residual is deemed withdrawn in one year:

| Contribution years | Pot at 64 | Total tax: level | Total tax: $40k/yr | Cost of the rule of thumb |
|---|---|---|---|---|
| 10 | $192,442 | $0 | $0 | $0 |
| 18 | $430,425 | $1,574 | $5,535 | $3,961 |
| 24 | $680,881 | $8,362 | $41,147 | $32,785 |
| 29 | $953,537 | $20,721 | $89,911 | **$69,190** |
| 34 | $1,301,524 | $38,418 | $155,097 | $116,679 |

(`test_fixed40_costs_more_than_level`)

On a $3,000,000 pot, value at 73: everything in year one $4,363,654; $40,000 a year $4,401,506;
level drawdown **$4,633,664**; gross before any tax $4,886,684.

Withdrawing in kind changes none of these numbers — the tax is fixed at the transfer-date market
value, and later sale of transferred assets is untaxed (no capital gains tax). It saves transaction
costs and forced selling, but the tax falls due in cash while the withdrawal arrives as securities.

## 10. Early withdrawal

Whole balance withdrawn before the locked-in age, no other income that year:

| Balance | 5% penalty | Tax on 100% | Total cost |
|---|---|---|---|
| $50,000 | $2,500 | $1,250 | 7.50% |
| $100,000 | $5,000 | $5,650 | 10.65% |
| $200,000 | $10,000 | $21,150 | 15.57% |
| $400,000 | $20,000 | $62,150 | 20.54% |

(`test_early_withdrawal_costs`)

Extra cost versus a qualifying withdrawal at the same marginal rate τ is `0.05 + 0.5τ`: 8.5% at 7%,
10.75% at 11.5%, 16% at 22%, 17% at 24% (`test_effective_early_penalty`). Beshears et al., "Optimal
Illiquidity" (JFE 2025, https://www.nber.org/papers/w27459) put the socially optimal penalty at
about 10%, which Singapore's effective range brackets.

## 11. Idle cash

$15,300 a year for 29 years: **$446,820** at 0.05% versus **$953,537** at 5%. The gap (~$507k) is
roughly ten times the undiscounted lifetime relief (29 × $1,759.50 = $51,026).

## 12. Discrepancies with earlier documents

The earlier dossier, slide deck and chat answers contain these small errors. The model and this
file are authoritative.

| Earlier figure | Correct | Note |
|---|---|---|
| Route A $1,527,062 / Route B $1,374,505 | $1,527,150 / $1,374,593 | both off by $88; advantage unchanged |
| Advantage at $320k: +22.6% | +22.90% | |
| 7% crossover "$5m" | $1,853,216 | $5m used the *average* exit rate |
| 7% crossover $1,852,775 | $1,853,216 | earlier bisection imprecision |
| 0% / 2% / 3.5% crossovers $307,325 / $616,415 / $1,233,933 | $308,869 / $617,739 / $1,235,478 | now closed form |
| 11.5% crossover "~$8m" | indifferent from ~$8m, loses above $15,443,470 | plateau, not a crossing |
| Exemption covers growth below "~4.7%" | 4.56% | |
| "12% cap makes breaking the lock-up tractable" | early-withdrawal extra cost up to ~17% | cap only applies to qualifying withdrawals |
