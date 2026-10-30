# SRS research model — URECA NBS26004

Undergraduate research project at NTU, supervised by Assoc Prof Nelson Lau (Nanyang Business
School): *A Lifecycle and Tax-Arbitrage Analysis of Singapore's Supplementary Retirement Scheme:
Indifference Curves and Optimal Participation Regions*. The goal is a map of who should use SRS
(Singapore's voluntary tax-deferred retirement account) and who shouldn't, plus the drawdown
strategy that goes with it. Next supervisor meeting: 25 September 2026.

## Layout

```
CLAUDE.md                     this file
srs_model.py                  core model: tax, relief, exit rates, drawdown routes
srs_simulation.py             Monte Carlo engine: random returns/tax-creep, MPC drawdown,
                               after-window and early-exit comparisons (extends srs_model.py)
srs_walkthrough.py            renders srs_simulation.py's output as plain-language Markdown
srs_dashboard.py              interactive Streamlit UI over srs_simulation.py
srs_tax_regime.py             Model 3: real historical IRAS brackets (YA2003-2024) + calibrated
                               50-year discrete/smooth projections, plus a backward-looking
                               tax-change-vs-macro correlation check (extends srs_model.py /
                               srs_simulation.py)
data/tax_brackets_ya2026.json IRAS resident rates — the only place *current* brackets live
data/tax_brackets_historical.json six real historical schedules, Data.gov.sg/IRAS, with source
data/sg_macro_tax_history_2003_2025.csv annual CPI/GDP + tax-change flag, 2003-2025 — [VERIFY]
                               primary source
tests/test_srs_model.py       21 regression tests pinning every verified number
tests/test_srs_simulation.py  47 tests for the simulation engine (zero-noise mode must
                               reproduce the exact base case in test_srs_model.py; 8 cover
                               the T5 early-exit-as-a-real-option Poisson model)
tests/test_srs_tax_regime.py  15 tests for the tax-regime model, cross-checked against the
                               closed-form crossover in docs/findings.md #7; 4 cover the
                               macro-correlation extension
docs/srs-rules.md             scheme rules incl. the annuity clause, with sources
docs/findings.md              verified results and where each number comes from
docs/open-tasks.md            what to build next, in priority order
docs/literature-review.md     literature review (10 streams) for positioning
docs/simulation-walkthrough.md generated report from srs_simulation.py — regenerate, don't edit
```

## Commands

```
python tests/test_srs_model.py       # no pytest needed; or: python -m pytest tests/
python tests/test_srs_simulation.py  # simulation engine tests
python tests/test_srs_tax_regime.py  # tax-regime model tests
python srs_model.py                  # base case, writes results.json to the current dir
python srs_simulation.py             # Monte Carlo grid, writes results_simulation.json
                                      # and docs/simulation-walkthrough.md
python srs_tax_regime.py             # historical + 50-year projections, writes
                                      # results_tax_regime.json
streamlit run srs_dashboard.py       # interactive dashboard, opens in a browser
```

Run the tests before and after any change to `srs_model.py` or `srs_simulation.py`.

## Read before you touch things

- Changing tax or withdrawal logic → read `docs/srs-rules.md` first.
- Quoting any number → check `docs/findings.md`; most have been verified and some were wrong
  in earlier documents.
- Choosing what to build → `docs/open-tasks.md`.

## Conventions

- Rates are IRAS resident rates, YA2026, loaded from the JSON. Every function takes an optional
  `brackets` argument so alternative schedules (tax-rate creep) can be passed in. Don't hardcode
  rates anywhere else.
- Nominal SGD, no inflation adjustment, contributions at year end, unless a task says otherwise.
- Relief is `tax(before) − tax(after)`, never `contribution × marginal rate`. A contribution can
  straddle a band edge and earn a blended rate ($88k chargeable → $1,431, i.e. 9.35%, not 11.5%).
- Any written output (reports, notes, memos) puts the source URL or citation **inline, right next
  to the claim it supports**, not only in a closing list. This is a supervisor instruction.
- Singapore has no capital gains tax and exempts one-tier dividends for individuals, so the
  ordinary (non-SRS) account is modelled with zero tax drag. Foreign-dividend withholding tax is
  the one real leak and is not yet modelled.

## Pitfalls — mistakes already made once in this project

1. **Marginal vs average exit rate.** Use the *marginal* rate for participation ("should I add a
   dollar?") and the *average* rate for evaluation ("what did it cost overall?"). Mixing them
   moved the 7%-bracket crossover from the correct ~$1.85m to a wrong ~$5m.
2. **The 12% cap only applies to qualifying withdrawals.** Top rate 24% × 50% inclusion = 12%.
   Breaking the lock-up early is 100% taxable plus 5%, so its *extra* cost is `0.05 + 0.5τ`,
   up to ~17%. Don't cite the 12% cap for early withdrawal.
3. **Gross vs chargeable income.** "$100k income" as gross salary is ~$79,800 chargeable after
   employee CPF relief (~$19,200, assuming the $8,000/month ordinary wage ceiling) and $1,000 earned
   income relief — that's the 7% band, not 11.5%.
4. **The "$40,000 a year tax-free" rule** only drains a pot of ≤ $308,869 at 5% in ten years. It is
   a threshold, not a strategy. Level drawdown beat it by $69,190 of tax on a ~$954k pot.
5. **The participation frontier is a staircase.** Wide bands create flat plateaus (the 11.5% bracket
   is indifferent from ~$8m to ~$15.4m of pot). Plateaus are real, not bugs.
6. **MOF's "average marginal tax rate of about 15%"** (Jan 2019 parliamentary reply) is a group
   average for contributors with assessable income > $80k, possibly measured on assessable rather
   than chargeable income, and seven years old. Treat as an upper-bound anchor, not an input.
7. **Earlier documents quote $1,527,062 / $1,374,505** at age 73. The model gives $1,527,150 /
   $1,374,593. Both were off by the same $88, so the $152,557 advantage stands. Use the model.
8. **Fixed-term annuity treatment is unverified.** Only *life* annuities are confirmed exempt from
   the 10-year window (IRAS). The claim that fixed-term annuities are taxed on surrender value at
   deemed closure comes from a forum post.

## Do not

- Change a test's expected value to make it pass. Each one is documented in `docs/findings.md`;
  if one breaks, the code is wrong or the finding needs re-deriving with a stated reason.
- Present the model's outputs as financial advice. This is research on stated assumptions.
