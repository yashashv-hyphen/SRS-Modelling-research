# Methodology: equations, assumptions, and data

Companion to `docs/findings.md` (results) and `docs/srs-rules.md` (scheme rules). This file exists
to make every assumption embedded in the code **explicit and citable**, the way a methodology
section in a paper would, rather than leaving assumptions implicit in docstrings. Every equation
below is implemented exactly as shown — none are presented in a simplified form that differs from
`srs_model.py` / `srs_simulation.py` / `srs_tax_regime.py`.

Notation: `t_c` relief rate; `t_w` marginal withdrawal tax rate; `r` return; `n` horizon (years);
`τ` marginal rate at a withdrawal; `λ` Poisson arrival rate; `I` inclusion rate (0.5 — the taxable
share of a qualifying withdrawal); `a(n,r) = (1-(1+r)^-n)/r` the n-year annuity factor.

## 1. General assumptions (apply to all three models)

| # | Assumption | Justification / where it's relaxed |
|---|---|---|
| A1 | Nominal SGD, no inflation adjustment | `CLAUDE.md` convention; Model 3's finding that band thresholds haven't moved in 21+ years supports treating the frozen-threshold convention as realistic, not a simplification needing correction |
| A2 | Contributions occur at year-end, not continuously | `CLAUDE.md` convention; matches how `fv_annuity`/`level_payment` treat cash flows (ordinary annuity) |
| A3 | Tax is a pure step function of chargeable income, no credits beyond the modelled reliefs | Matches IRAS resident-rate structure; the $80,000 overall personal relief cap (A6) is the one documented exception not modelled |
| A4 | The ordinary (non-SRS) account has **zero** ongoing tax drag | Singapore has no capital gains tax and exempts one-tier dividends for individuals — stated in `CLAUDE.md`, not assumed casually |
| A5 | Foreign-dividend withholding tax is not modelled | Stated limitation (`docs/open-tasks.md`, "Not modelled yet") |
| A6 | The $80,000 overall personal income tax relief cap is not modelled | Each contribution's relief is computed in isolation; stated limitation |
| A7 | No fees or expense ratios inside either account | Stated limitation |
| A8 | No mortality risk during the drawdown window | The member is assumed to survive to spend or bequeath; CPF LIFE-style longevity pooling is out of scope |

## 2. Model 1 — the per-dollar core (`srs_model.py`)

**Purpose.** Establishes, for one pre-tax dollar, whether routing it through SRS beats an ordinary
account, as a function of the relief rate obtained now and the marginal tax rate paid later.

### 2.1 Model-specific assumptions

| # | Assumption | Why it's reasonable here |
|---|---|---|
| B1 | A single constant return `r` holds for the entire horizon — no path dependence | Isolates the tax-arbitrage question from market-timing; relaxed in Model 2 |
| B2 | The annual contribution is constant (the chosen cap), not a variable savings schedule | Matches how the SRS cap is actually used in practice by a saver maximising relief each year |
| B3 | The pot's growth is deterministic (expected-value case, no variance) | The certainty-equivalent benchmark Model 2 is compared against |
| B4 | During drawdown, undrawn capital keeps earning `r` | `run()`'s balance update: `balance = balance*(1+r) - pmt` |
| B5 | "Other income" in the withdrawal years is held constant across the window | Simplifies the exit-rate calculation; Model 2 can vary it per path |
| B6 | The relief rate used is the chargeable-income band rate at the moment of contribution, assumed stationary | Model 3 relaxes this via real historical/projected schedules |

### 2.2 Equations, assumptions invoked, data, and interpretation

| Eq. | Formula | Assumptions invoked | Parameters / data | What it tells us |
|---|---|---|---|---|
| (1) | `tax(x) = Σᵢ (min(x,Uᵢ) − Uᵢ₋₁)·rateᵢ` | A3 | `data/tax_brackets_ya2026.json` (IRAS, live) | Singapore resident tax on chargeable income x |
| (2) | `relief = tax(x) − tax(x − contribution)` | A3, A6 | Band table above | Cash tax saved by one year's SRS contribution — a blended rate if it straddles a band edge |
| (3) | `FV = payment·[(1+r)ⁿ−1]/r` | B1, B2 | user-chosen `r`, `n` | Future value of the contribution stream |
| (4) | `payment = PV·r/[1−(1+r)⁻ⁿ]` | B1, B4 | user-chosen `r`, draw-window `n` | The level annual withdrawal that exactly drains a pot |
| (5) | `marginal_exit(pot) = marginal_rate(I·level_payment(pot,r,n) + other_income)` | A4, B4, B5 | `I = 0.5` | The rate on the **next** withdrawn dollar — for the participation decision |
| (6) | `t_c^break(pot) = I·marginal_exit(pot)` | same as (5) | — | The relief rate at which one more contributed dollar is exactly indifferent |
| (7) | `pot* = 2·(L − other_income)·a(n,r)` | B1, B5, B6 | band edges `Uᵢ` | Closed-form pot size at which contributing stops paying off, at a given relief rate |
| (8) | `avg_exit(pot) = [tax(oi+I·pmt)−tax(oi)]/pmt` | A4, B4 | — | Total-tax-over-total-withdrawn — for **evaluating** a completed plan, never for participation |
| (9) | `penalty(τ) = 0.05 + (1−I)τ` | scheme rule (5% penalty, 100% inclusion if early) | `docs/srs-rules.md` | Extra cost of breaking the lock-up vs. a qualifying withdrawal |
| (10) | `k(t_c,t_w) = (1 − I·t_w)/(1 − t_c)` | A1, A4, B1 | — | SRS ÷ ordinary terminal wealth for one dollar — independent of `r`, `n` |
| (11) | `SRS wins ⟺ t_c > I·t_w` | A4, B1 | — | The entire participation decision collapses to comparing two rates |
| (12) | `endA = Σᵢ(pmtᵢ−taxᵢ)(1+r)ⁿ⁻¹⁻ⁱ + residual − residual_tax` | A4, B1, B4 | chosen strategy (`level`/`fixed40`) | Terminal wealth, SRS route |
| (13) | `advantage = FV(relief invested) − FV(tax paid)` | A4 | — | Exact decomposition of the dollar advantage (identity, not an approximation) |
| (14) | `cost_rate = [0.05·balance + tax(x+balance)−tax(x)] / balance` | scheme rule | — | All-in cost of a full early withdrawal, as a rate |

## 3. Model 2 — Monte Carlo, dynamic-programming drawdown, early exit (`srs_simulation.py`)

**Purpose.** Relaxes B1 (constant return) and B6 (stationary tax rate) into explicit stochastic
processes, and solves for the withdrawal policy and the early-exit decision under that
uncertainty, rather than assuming a single deterministic path.

### 3.1 Model-specific assumptions

| # | Assumption | Why / caveat |
|---|---|---|
| C1 | Returns are i.i.d. lognormal per year **or** block-bootstrapped from real history (S&P 500, 1928–2025), 5-year blocks | Block bootstrap preserves sequence-risk clustering a single-year i.i.d. draw would erase. **Supervisor-approved caveat:** single-country US data, not calibrated to the Singapore market or SRS-eligible instruments specifically |
| C2 | Tax-bracket drift = nominal bracket creep (wage growth, frozen thresholds) **+** independent Poisson-style policy shocks | Thresholds-frozen part is empirically supported (Model 3, finding #12); the shock process itself is illustrative, not calibrated to the real 3-revisions-in-17-years cadence (that calibration is Model 3's discrete/smooth projections, used separately) |
| C3 | The DP/MPC withdrawal planner uses a **fixed** return forecast for all remaining years at each re-planning step | **Supervisor-approved simplification** — the forecast does not itself update over time as a state variable |
| C4 | Outside opportunities (the early-exit real option) arrive as a Poisson process, rate `λ`, with i.i.d. exponential excess returns | `λ` and the mean excess return are illustrative placeholders — no base-rate data source was identified (`docs/open-tasks.md` T5) |
| C5 | "Other income" during drawdown is held constant across years within a path | Represents a fixed post-retirement income stream (e.g. CPF LIFE, rental) |
| C6 | The DP's balance grid is discretised (80 points by default); off-grid values are linearly interpolated | Numerical approximation; not separately error-bounded |

### 3.2 Equations, assumptions invoked, data, and interpretation

| Eq. | Formula | Assumptions invoked | Parameters / data | What it tells us |
|---|---|---|---|---|
| (15) | `σ=vol; μ=ln(1+mean)-½σ²; rₜ=e^N(μ,σ²)-1` | C1 (parametric branch) | user-chosen mean/vol | One lognormal-draw return path |
| (16) | `rate′=clip(rate+shift,0,0.30); incomeᵥ=income₀(1+g)ʸ` | C2 | `wage_growth` | Nominal bracket creep |
| (17) | `shiftₜ=shiftₜ₋₁+𝟙[U<p]·(±1)·V, V~Uniform(a,b)` | C2 | `shock_prob`, `shock_size_range` | A random, permanent policy-rate shock path |
| (18) | `V₁(b)=tax(I·b(1+r)); Vₖ(b)=min_w{tax(I·w)(1+r)ᵏ⁻¹+Vₖ₋₁(b(1+r)−w)}` | A4, C3, C6 | balance grid | Backward-DP optimal withdrawal, minimising future-value-compounded tax |
| (19) | `spend_to_zero=level_payment(lump,r,m); bequest=lump(1+r)ᵘ−FV(spend,r,m)` | B1-style (fixed r post-window) | `death_extra_years` | What's left after the 10-year window closes, under any spending rule |
| (20) | `x* = [balance(1+r_fc)ᵏ / net_if_broken]^(1/k) − 1` | scheme rule (early-withdrawal cost) | — | Absolute breakeven external return for breaking the lock-up now |
| (21) | `x*_excess = x* − r_forecast` | C3 | — | Breakeven **excess** return — the bar an outside deal's edge must clear |
| (22) | `N_year ~ Poisson(λ)` | C4 | user-chosen `λ` | How many outside opportunities arrive in a year |
| (23) | `X ~ Exponential(mean=mean_excess)` | C4 | user-chosen mean | The excess return each arriving opportunity offers |
| (24) | `outsideᵢ = outsideᵢ₋₁(1+rᵢ) + net_flowᵢ` | A4 | realised path | Running reinvested-withdrawal wealth (FV-of-cashflow-series identity) |
| (25) | `band = {p10,median,p90} = percentile(values,{10,50,90})` | — | `n_paths` simulated lifetimes | The spread of outcomes, not a single point estimate |
| (26) | `blockᵢ = series[(start+i) mod N], start~Uniform{0,…,N−1}` | C1 (historical branch) | `data/sp500_annual_returns.json` | Circular block bootstrap draw |

## 4. Model 3 — tax-regime history and projection (`srs_tax_regime.py`)

**Purpose.** Replaces Model 1/2's stationary-tax-rate assumption (B6) with the real historical
Singapore schedule, and extrapolates it 50 years forward two ways; separately checks whether the
historical rate changes correlate with the macroeconomic backdrop.

### 4.1 Model-specific assumptions

| # | Assumption | Why / caveat |
|---|---|---|
| D1 | Only six discrete historical schedules are ground truth (YA2003, 2006, 2007, 2012, 2017, 2024); intervening years hold the most recent schedule | Matches how IRAS actually publishes rate schedules — rates are stable between Budget changes, not interpolated |
| D2 | The 50-year discrete and smooth projections are **calibrated to the same historical magnitude** (same total drift by year 50) | Isolates the actual question (lumpy vs. continuous arrival) from magnitude, per the task's own framing |
| D3 | Band thresholds stay frozen in nominal terms for the full 50-year projection | Extrapolates 21+ years of observed history; the single largest assumption in Model 3 if real policy ever indexes thresholds |
| D4 | The tax-change/macro correlation is backward-looking only — a historical pattern, not assumed to generalise forward without a *projected* (not actuals) macro series | Only 5 change events in 23 years; stated explicitly as suggestive, not decisive |
| D5 | Tax-bracket data is primary (Data.gov.sg/IRAS); the macro CSV's source is unverified | `[VERIFY]` flagged rather than silently treated as confirmed |

### 4.2 Equations, assumptions invoked, data, and interpretation

| Eq. | Formula | Assumptions invoked | Parameters / data | What it tells us |
|---|---|---|---|---|
| (27) | `avg_interval=Σintervals/count; avg_step=Σsteps/count; drift/yr=(rate_end−rate_start)/years` | D1 | six real schedules | The empirical cadence and size of past revisions |
| (28) | `shift(y) = avg_step · ⌊y/avg_interval⌋` | D2, D3 | Eq. (27) outputs | Discrete-jump 50-year projection |
| (29) | `shift(y) = drift_per_year · y` | D2, D3 | Eq. (27) outputs | Smooth 50-year projection, same total drift |
| (30) | `ρ = Σ(xᵢ−x̄)(yᵢ−ȳ) / [√Σ(xᵢ−x̄)²·√Σ(yᵢ−ȳ)²]` | D4, D5 | `data/sg_macro_tax_history_2003_2025.csv` | Correlation between a tax change (x) and the prior year's CPI/GDP growth (y) |

## 5. Side experiment — radial vs. parallel frontier shift (`experiments/radial_vs_parallel_frontier.py`)

Not one of the three models; resolves a scoping question for the not-yet-built Model 1a
(investment-universe/leverage extension).

| Eq. | Formula | Assumptions invoked | Data | What it tells us |
|---|---|---|---|---|
| (31) | `(1+δ)ⁿ=k; δ=k^(1/n)−1; μ′=(1+δ)(1+μ)−1; σ′=(1+δ)σ` | A1, B1 | Eq. (10)'s `k` at this project's actual `t_c`,`t_w` | The SRS tax wedge is technically a radial transform centred at (σ=0, μ=−100%), numerically indistinguishable from a flat parallel shift at these wedge sizes |

## 6. Data sources

| Dataset | Content | Coverage | Provider | Confidence | Used by |
|---|---|---|---|---|---|
| `data/tax_brackets_ya2026.json` | Current IRAS resident rates | YA2026 | IRAS | Primary | Models 1, 2 (default) |
| `data/tax_brackets_historical.json` | Six real resident-rate schedules | YA2003–2024 | Data.gov.sg / IRAS (`d_f73055c69144d2e7734c28811d3982aa`) | Primary | Model 3 |
| `data/sp500_annual_returns.json` | Annual total returns (incl. dividends) | 1928–2025 | Damodaran Online, NYU Stern | Primary (public), single-country stand-in — supervisor-approved | Model 2 (historical return mode) |
| `data/sg_macro_tax_history_2003_2025.csv` | Annual CPI inflation, real/nominal GDP growth, tax-change flag | 2003–2025 | **[VERIFY]** — user-supplied, presumed SingStat | Unconfirmed | Model 3 (macro correlation) |
| `docs/srs-rules.md` | Scheme rules: caps, inclusion rate, penalty, lock-in age schedule, 10-year window | current | MOF / IRAS, with some forum-sourced items flagged `[VERIFY]` | Mixed — see file for item-by-item sourcing | All three models |

## 7. Limitations, in one place

Everything in §1–§4's assumption tables is a scoping decision, not an oversight — but collected
here because a methodology section should let a reader see the full set at once: A5, A6, A7, A8
(§1); C1's single-country return series and C4's uncalibrated arrival-rate/excess-return
parameters (§3); D3's frozen-threshold extrapolation and D4's small-sample macro correlation
(§4). None of these are hidden inside a docstring only the author would find.

## 8. Planned MAIN analyses (visualisation specifications, supervisor-set)

Each model's underlying equations (§2–§4) are implemented and tested. The supervisor separately
specified one **MAIN analysis** output per model — a specific figure, not just a working formula.
Honest status of each, so the gap between "the maths works" and "the figure exists" is explicit:

| Model | Specification (supervisor's words, condensed) | Maps to | Status |
|---|---|---|---|
| 1 | Portfolio return `r` (y) × marginal tax rate `t_c` (x), horizon and ending balance fixed, reasonable withdrawal-phase regime assumed → indifference-curve heatmap. Repeat across a 2×2 grid of (horizon, ending balance). | Eq. (10), (11), (13) | **Not built.** Every function it needs exists (`per_dollar_ratio`, `run`); this is an unbuilt sweep-and-plot, not new modelling. |
| 2 | SRS portfolio size (y) × years left (x), non-SRS income and tax regime fixed → DP-recommended withdrawal per cell. Repeat across ~4 income levels. | Eq. (18) | **Not built, but the data already exists internally.** `_dp_solve`'s `policy0[years_left][balance_i]` grid *is* this heatmap for one income level — computed, then discarded after returning a single action. |
| 3 | Narrative timeline of historical regimes ("in year XXXX, the regime was…"), then a simple (e.g. linear) 10/20/30/40/50-year forward projection. | Eq. (27)–(29) | **Closest to done.** `HISTORY`, `project_discrete`, `project_smooth` already produce this data; only the literal narrative/table rendering is missing. |

None of these three require new equations — §2–§4 already cover the maths each needs. What's
missing in all three cases is the specific output artifact (a saved figure/table), which is
implementation work, not research work.

## 9. Extension models (new, not yet started)

Two further models were specified separately from Models 1–3, explicitly as extensions to take up
once the core three are in a presentable state.

**Model 1a — investment universe inside vs. outside SRS.** SRS's eligible investments
(`docs/srs-rules.md`) are a strict subset of what's available outside, and SRS disallows leverage.
Hypothesis to test: ignoring tax, the wider outside universe (+ leverage) gives a strictly better
efficient frontier — more return per unit of risk, less risk per unit of return. The supervisor's
own framing: *is this true*, and *what is the impact for a fully rational actor with a specified
risk tolerance* — growth outside could be higher with leverage, but at correspondingly higher risk.
**Not the same question as this document's §5 experiment**, which held the investment universe
fixed and only asked how the *tax wedge* shifts a frontier (finding: negligibly). Model 1a asks
whether the universe/leverage *restriction itself* shrinks the frontier, independent of tax —
unanswered. Would need a real efficient-frontier construction (constrained vs. unconstrained asset
sets, with/without leverage) plus a utility framework for the risk-tolerance question.

**Model 4 — lifecycle personas.** Once Models 1–3 (and ideally T5/T9) are complete, map several
personas (e.g. a 30-year-old on $80k, a 45-year-old on $250k) through their SRS journey as a
narrative built on those models' outputs — explicitly suited to a URECA poster or news-style
write-up, per the supervisor's own note. Not started; depends on the above.

**Already satisfied — interactive dashboard.** The supervisor separately asked for an interactive
website, good for a poster presentation. `srs_dashboard.py` already is this, live on Streamlit
Community Cloud, built over Models 1 and 2.

## 10. Practitioner literature: does "too much SRS, too much tax" circulate as a lay argument?

Separate task, separate standard of evidence — not peer-reviewed, included because the project's
own Model 1 finding (a real participation plateau/ceiling, `docs/findings.md` §7) has a lay echo in
Singapore personal-finance commentary, and the supervisor asked for it documented even if "not well
researched." Full writeup with quotes: `docs/literature-review.md`, Stream 11. Three sources found:
Seedly's "Does SRS ever not make sense?" (archived, fully accessible, two informal but numerically
worked rebuttals), Investment Moats' "Is it Always Better to Contribute to SRS Account?" (archived,
accessible), and a HardwareZone Forums thread found but **not independently verified** — it sits
behind an age-verification wall and the archived screenshot captured only an ad, not the posts.
Screenshots: `docs/literature-screenshots/`.
