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

## 12. Model 3 — tax regime: real history and 50-year projection

Six real IRAS resident-rate schedules, YA2003-2024 (Data.gov.sg/IRAS, "Tax Rates for Individual
Income Tax" open dataset, https://data.gov.sg/dataset/tax-rates-for-individual-income-tax,
resource_id `d_f73055c69144d2e7734c28811d3982aa` — see `data/tax_brackets_historical.json`),
loaded and projected by `srs_tax_regime.py` (`test_srs_tax_regime.py`).

**Thresholds never move.** The $20,000 / $30,000 / $40,000 / $80,000 band edges are identical
across every schedule from YA2003 to YA2024 — 21+ years. Bracket creep in this project
(`bracket_creep_income` in `srs_simulation.py`) is modelling the *observed* mechanism, not an
assumption. (`test_thresholds_up_to_80k_never_moved`)

**Only three real revisions since the schedule settled (YA2007):** YA2012 (restructure, top
rate unchanged at 20%), YA2017 (+2pp, top rate to 22%), YA2024 (+2pp, top rate to 24%) — one
every ~5.7 years on average, average step +1.33pp including the zero. (`test_calibration_facts`)

**The 11.5%-relief crossover (docs/findings.md #7) did not exist before 2024.** Under every
schedule from YA2007 to YA2023 the top rate (20-22%) never exceeded 2 × 11.5% = 23%, so there
was no pot size at which an 11.5%-bracket saver should stop contributing — contributing was
*always* worth it. The YA2024 reform (top rate to 24%) created the plateau for the first time,
at the same $15,443,470 this project's closed form gives today. (`test_historical_frontier_matches_findings_closed_form`)

**The 7%-relief crossover moved around before settling.** YA2003-2006: $1,235,478 (first band
exceeding 14% was the $320k edge at 19-20%). The 2007 rate cut pushed the >14% threshold up to
the (then) top band, moving the crossover to $2,470,955 — the single highest the 7% crossover
has ever been. The 2012 restructuring (new $120k band) brought it back down to $1,853,216,
where it has stayed through YA2024. (`test_tc_seven_percent_doubled_from_2003_to_2007`)

**50-year projection, two scenarios calibrated to the same long-run total.** `project_discrete`
applies the historical average step (+1.33pp) every historical average interval (5.7 years);
`project_smooth` applies +0.235pp/year continuously — chosen so both reach (almost) the same
cumulative drift by year 50, isolating the actual question (lumpy vs. continuous) from
magnitude. At tc = 11.5%, the $15,443,470 crossover created by the 2024 reform erodes as the
regime drifts up — by +50 years, discrete gives $1,853,216, smooth gives $1,235,478 (discrete
lags smooth because its first jump hasn't landed until year 6). (`test_projection_crossover_falls_as_regime_drifts_up`)

**Not modelled (deliberately out of scope for this pass):** inflation/GDP correlation
(Oxford Economics / SingStat / BIS) — see `docs/open-tasks.md` T4. **Flag for the
supervisor:** the finding that thresholds are nominally frozen in real history *supports*
rather than conflicts with the project's existing nominal-SGD-no-inflation convention, so no
convention change is proposed here — noting this explicitly since Model 3 was the item most
likely to require one.

## 13. Discrepancies with earlier documents

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

## 14. Early withdrawal as a real option (T5)

`srs_simulation.py`'s `early_exit_breakeven_excess(balance, years_to_lock, r_forecast,
other_income, brackets)` gives the excess return (over just staying invested) an outside
opportunity must offer to justify breaking the lock-up now rather than waiting for the natural,
penalty-free unlock. At a $953,537 pot (the base case's pot at 64, docs/findings.md §3), 5 years
to lock, r_forecast = 5%:

| Other income in the exit year | Breakeven excess return needed |
|---|---|
| $0 | 6.5% |
| $100,000 | 6.7% |
| $300,000 | 7.1% |
| $500,000 | 7.3% |

(`test_early_exit_threshold_rises_with_other_income`) **This settles the Investment Moats /
commenter dispute (docs/open-tasks.md T5) in favour of "it depends"**: the bar a high-bracket
saver's outside opportunity must clear is measurably higher than a saver with no other income,
because the early withdrawal is 100%-taxable (not 50%) and lands on top of whatever else they
earned that year. Neither side of the practitioner argument is simply right or wrong — each is
describing a different point on this table.

The bar also falls as more years remain before the natural unlock (`test_early_exit_threshold_falls_with_more_years_to_lock`):
with only 1 year left, the outside opportunity has to beat a much higher bar than with 9 years
left, because a smaller annual edge has longer to compound into the same catch-up.

**Simulated arrival** (`poisson_opportunity_counts`, `draw_excess_returns`,
`simulate_early_exit_portfolio`): opportunities arrive at rate λ/year, each offering a random
excess return (exponential, mean set by the caller). At λ = 0.2/yr and mean excess 5%, roughly
**half of simulated 10-year windows see at least one offer good enough to trigger an early
exit**, typically by year 2 of the window if it happens at all. λ and the 5% mean are illustrative
placeholders — no base-rate source for how often a Singapore-resident SRS saver actually
encounters a genuine outside deal was identified this pass, so the *shape* of the result (the
bar depends on income and on time-to-lock; a non-trivial fraction of lifetimes see a good enough
offer) is the finding; the specific 50% headline is sensitive to those placeholders and
shouldn't be quoted on its own.

## 15. Tax changes vs. the macro backdrop (T4 extension, backward-looking)

`srs_tax_regime.py`'s `macro_correlation_facts` / `macro_by_direction`, run against
`data/sg_macro_tax_history_2003_2025.csv` (annual CPI inflation and real/nominal GDP growth
alongside a tax-change flag, 2003-2025 — **[VERIFY]** primary source, presumably SingStat for
the macro figures). 5 of the 23 years had a tax change: cuts in 2006, 2007, 2012; rises in 2017,
2024 (`test_five_change_years_match_the_bracket_history`, consistent with the revision years
already established in `data/tax_brackets_historical.json`).

**Pooled correlation is near zero** — whether a change happened at all, against the prior
year's GDP growth or inflation, is essentially uncorrelated (±0.1,
`test_pooled_change_correlation_is_weak`). That's expected: cuts and rises pull in opposite
directions and cancel out when lumped together as just "changed".

**Splitting by direction shows a real pattern:**

| Direction | Years | Avg prior-year real GDP growth |
|---|---|---|
| Cut | 2006, 2007, 2012 | 7.53% |
| Rise | 2017, 2024 | 2.68% |

(`test_cuts_followed_stronger_growth_than_rises`) Every cut followed a year of strong growth
(7.4%, 9.0%, 6.2%); both rises followed markedly weaker growth (3.9%, 1.5%) — consistent with
Singapore cutting personal tax rates when the economy can afford it and raising them once growth
has slowed. **Caveat stated plainly:** 5 events in 23 years is a small sample — this is a real
pattern in the actual data, not a statistically decisive test, and shouldn't be presented as
more than that.

**What this does not do:** turn `project_discrete`/`project_smooth` into a macro-driven
forecast. That would require a *projected* (not actuals-only) inflation/GDP series — the
original ask was Oxford Economics / Capital Economics / SingStat / BIS forecasts — which this
CSV doesn't contain (2003-2025 is all realised history). The 50-year projections still drift at
the fixed calibrated rate from finding #12; this finding explains part of *why* past changes
happened, it doesn't yet predict *when* future ones will.
