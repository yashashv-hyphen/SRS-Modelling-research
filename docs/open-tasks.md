# Open tasks

In priority order. T1 is the project's stated deliverable; T2 was flagged at the supervisor meeting
as the section most likely to need historical simulation and dynamic programming. Each task says
what "done" looks like so progress can be checked against the tests.

Supervisor notes this list comes from (paraphrased): model the withdrawal strategy with historical
simulation and possibly DP; inputs are marginal tax rate, horizon, return and tax-rate creep; the
unit of decision is a single dollar invested at a point in time; explore when early withdrawal is
worth it when outside opportunities arrive at random; keep a source next to every point.

---

## T1 — Participation-region map (core deliverable)

Draw the boundary between "use SRS" and "don't".

- Axes: relief rate `tc` against pot size at withdrawal age (and a second view with contribution
  years and return, since pot = f(years, r)).
- Boundary uses the **marginal** exit rate: `breakeven_tc(pot)`. Shade the evaluation surface
  (advantage %) using the **average** exit rate from `run()`. Never swap them.
- Check the boundary against the closed form `pot* = 2·L·a(10, r)` in `docs/findings.md` §7.
- Render the staircase honestly — plateaus at band edges are the result, not noise.
- Produce the same map for the foreigner cap ($35,700).

Decision to raise with the supervisor before finalising: is the unit the whole annual contribution
(use the *average* relief rate on the block, which `relief_value` gives) or the literal marginal
dollar (use the rate at `chargeable − contributed so far`)? They differ whenever the contribution
straddles a band edge, e.g. $88k chargeable gives a 9.35% block rate but a 7% last-dollar rate.

Done when: grid CSVs + figures exist, the boundary matches the closed form, and a test asserts it.

## T2 — Withdrawal strategy under uncertainty

a. **Deterministic check.** Optimise ten withdrawal amounts directly (e.g. `scipy.optimize` or an LP
   with piecewise-linear tax) and confirm it returns level drawdown. Add a test.
b. **Stochastic returns.** Monte Carlo (start lognormal). Compare level, $40k/yr, front-loaded, and
   "fill to the top of a bracket" rules on expected terminal wealth and on CRRA certainty
   equivalent.
c. **Historical simulation.** Block-bootstrap a long return series to capture sequence risk.
   Preferred source: Dimson–Marsh–Staunton via NTU library (confirm access); fallback is a public
   US series, stated as a limitation.
   **Done (fallback path, supervisor-approved):** `sim.historical_block_bootstrap_path()` splices
   real consecutive-year blocks from `data/sp500_annual_returns.json` (S&P 500 total returns,
   1928-2025, Damodaran/NYU Stern — see the file for the full citation). Selectable in the
   dashboard via "Model the market using" → "Real market history", alongside (not replacing) the
   original parametric mode. Raised with the supervisor whether a single-country US series is
   defensible for a Singapore-domiciled SRS portfolio — confirmed acceptable; no need to pursue
   Dimson–Marsh–Staunton/NTU library access further for this project.
d. **Dynamic programming.** State = (balance, years left in window, other income); control = this
   year's withdrawal; terminal condition = deemed withdrawal of the residual in one year (a kink).
   Discretise the balance grid, solve backwards, compare the optimal policy to level drawdown and
   **report the gap** — that gap is itself a finding.

Literature anchors (full refs in `docs/literature-review.md`): Ragsdale, Seila & Little (1994);
Horan (2006) on progressive brackets; DiLellio & Ostrov; the 2025 MPC arXiv preprint
(https://arxiv.org/pdf/2507.10603, not peer-reviewed). None models a terminal deadline — SRS's is
a forced-liquidation date, not a US-style minimum-distribution floor.

Done when: a, b and d each have code, figures and at least one test; c is done if data access works.

## T3 — Annuity versus the 10-year drain (large pots)

Rules in `docs/srs-rules.md` → "The annuity clause". Model a fraction φ of the pot at withdrawal
age buying a life annuity paying `p` dollars per year per dollar of premium, with the rest drained
over ten years.

- During the window, annuity payments land in the SRS account untaxed unless withdrawn; after the
  account is closed or deemed closed, 50% of each payment is taxable every year for life.
- `p` is the unknown. Take it as a parameter first; then either source insurer quotes or derive it
  actuarially from SingStat complete life tables plus a discount rate and loading. Compare the
  implied money's worth with the CPF LIFE paper in `docs/literature-review.md` (Stream 2).
- Output: for each pot size, the break-even payout rate `p*` above which partial annuitisation beats
  draining. Report with and without a longevity-insurance value (utility-based).

Unresolved rule questions (flag, don't assume): must the annuity be bought before the window
starts; exact treatment of payments withdrawn during the window; fixed-term annuity treatment
(forum-sourced only).

## T4 — Tax-rate creep

Every function takes `brackets`, so schedules are swappable.

- Scenario A: thresholds frozen in nominal terms while incomes grow → bracket creep.
- Scenario B: parallel rate shift (±x percentage points) at withdrawal time only.
- Scenario C: stochastic schedule in the spirit of Brown, Cederburg & O'Doherty (2017, JFE,
  https://repository.arizona.edu/bitstream/handle/10150/627841/RothTaxUncertainty_CopyEditVersion.pdf).
  Singapore has no Roth-style account, so the only hedge is the ordinary account, which is already
  close to tax-free — note that asymmetry.
- Output: how the T1 frontier moves under each scenario.

**Done (historical foundation, Model 3):** `srs_tax_regime.py` loads six real IRAS resident-rate
schedules YA2003-2024 (`data/tax_brackets_historical.json`, Data.gov.sg/IRAS, primary/official —
see `docs/findings.md` #12) and calibrates both a discrete-jump and a smooth 50-year projection
from the real revision history (confirms Scenario A's frozen-threshold assumption is actually
what happened, not a simplification; supplies real calibration for Scenario B's "±x points"
instead of an arbitrary x). Shows the T1 11.5%-relief crossover only exists from the YA2024
reform onward — it didn't exist from YA2007-2023.

Still open:
- Scenario C (stochastic schedule) — `random_policy_shift_path` in `srs_simulation.py` is a
  Poisson-shock version of this but isn't calibrated against the real 3-revisions-in-17-years
  history the way the discrete/smooth projections now are.
- The inflation/GDP correlation extension (Oxford Economics / Capital Economics / SingStat /
  BIS) — explicitly deferred, not attempted in this pass.
- Only 6 waypoints (YA2003, 2006, 2007, 2012, 2017, 2024) are confirmed from a primary
  government source (Data.gov.sg dataset `d_f73055c69144d2e7734c28811d3982aa`, attributed to
  IRAS); no `[VERIFY]` flags were needed since every number came from that one dataset, but a
  second primary source (IRAS Annual Report / Budget Statement) has not been cross-checked.

## T5 — Early withdrawal as a real option

Investor has money locked in SRS. Outside opportunities (private equity, property, a business)
arrive as a Poisson process with rate λ and random excess return. Breaking the lock-up costs 5%
plus tax on 100% instead of 50%; versus a later qualifying withdrawal the extra cost is
`effective_early_penalty(τ) = 0.05 + 0.5τ` (8.5%–17%).

**Done:** `early_exit_breakeven_excess(balance, years_to_lock, r_forecast, other_income,
brackets)` in `srs_simulation.py` gives the threshold excess return (over just staying invested)
an outside opportunity must clear to be worth breaking the lock-up for — by bracket (via
`other_income`) and by time remaining (`years_to_lock`), exactly as asked. `early_exit_threshold_by_bracket`
sweeps both axes at once: at a $1m pot, 5 years to lock, the bar rises from 6.5% (no other income)
to 7.3% ($500k other income) — confirming the dispute settles in favour of "it depends on the
income in the withdrawal year", not a flat yes/no. The bar falls as years-to-lock rises (more time
for a smaller annual excess to compound into the same catch-up), consistent intuition, test-pinned.

The Poisson-arrival process itself is modelled by `poisson_opportunity_counts` (opportunities/year,
rate λ) and `draw_excess_returns` (each arriving opportunity's excess return, exponential, mean
set by the caller); `simulate_early_exit_path`/`simulate_early_exit_portfolio` run many simulated
lifetimes and report the fraction that ever see a good-enough offer before the natural unlock, and
how early. Base case (λ=0.2/yr, mean excess 5%, $1m-ish pot): ~50% of simulated lifetimes take an
early exit at some point, median in year 2 of the 10-year window if it happens at all. 8 tests in
`tests/test_srs_simulation.py`.

**Still open:** `λ` and the excess-return distribution (exponential, mean 5%) are illustrative
placeholders, not calibrated to real private-equity/property/small-business deal flow or return
data for a Singapore-resident investor — no such base-rate source was identified this pass.
Treat the *shape* of the result (the bar depends on income and on time-to-lock) as the finding;
treat the *specific* 50% headline figure as sensitive to those two placeholder assumptions.

- Nearest literature: Beshears et al., "Optimal Illiquidity" (JFE 2025,
  https://www.nber.org/papers/w27459). No paper found models this exact problem.

## T6 — Foreigner extension

$35,700 cap; withholding on withdrawal with a concessionary 15% rate where the year's withdrawals are
under $200,000 and there is no other income ([VERIFY] in `docs/srs-rules.md`); full withdrawal after
the 10-year parking period is 50% taxable with no penalty. Add a probability of retiring in
Singapore and mix resident/non-resident exit treatment. Note: 40 years at 7% on $35,700 reaches
about $7.1m — close to the 11.5%-bracket plateau, so the frontier genuinely binds for this group.

## T7 — Other retirement income

`run(other_retirement_income=...)` already stacks it under the taxable half. Sweep rental or
part-time income from $0 to $100k and show how the average exit rate and the frontier move. CPF LIFE
payouts are exempt and must NOT be added here.

## T8 — Verification backlog (not code)

- Resolve every **[VERIFY]** in `docs/srs-rules.md` against IRAS/MOF primary pages.
- Complete the Scopus / Web of Science search behind the "no peer-reviewed SRS literature" claim.
- Find out whether MOF's ~15% average marginal rate (Jan 2019) was measured on assessable or
  chargeable income.
- Replace the SmartWealth idle-cash estimate (21%, ~S$5.0bn) with primary MOF data if possible.

## Not modelled yet (state as limitations)

The $80,000 overall relief cap; foreign-dividend withholding tax on the ordinary account; inflation
and real returns; fees inside SRS; mortality during the drawdown.
