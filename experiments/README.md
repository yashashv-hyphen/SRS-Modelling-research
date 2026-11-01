# experiments/

Ad hoc explorations, not part of the three built models (`srs_model.py`,
`srs_simulation.py`, `srs_tax_regime.py`) or their test suites. Nothing outside
this folder imports anything in it, and nothing in this folder modifies or
depends on `docs/findings.md`, `docs/open-tasks.md`, or `CLAUDE.md`. No
stability guarantees — these are scratch investigations, not pinned results.

## radial_vs_parallel_frontier.py

Resolves a question raised in the 2026-10-17 WhatsApp discussion of Model 1a
(the not-yet-built investment-universe/leverage extension): does the SRS tax
wedge shift the efficient frontier *parallel* (flat additive annualized bump,
same at every risk level) or *radially* (scaled from the origin, measurably
steeper at higher risk)?

Run: `python experiments/radial_vs_parallel_frontier.py` (writes
`radial_vs_parallel_results.json` and, if matplotlib is installed,
`radial_vs_parallel_frontier.png`, both gitignored scratch output).

**Finding:** the exact relationship is genuinely radial — but from
`(sigma=0, mu=-100%)` in net-return space, not from `(0, 0)`. At the small
annualized wedge sizes this project's tax math actually produces (~0.24-0.26%/yr
for the base case and the WhatsApp example), that is numerically
indistinguishable from a flat parallel shift: the exact transform and the
parallel approximation agree to within ~0.01-0.02 percentage points across a
0-20%/yr risk range. Reading "radial from the origin" literally — scaling the
chart's annualized axes by the *raw* (un-annualized) terminal-wealth multiplier
instead of the annualized delta — overstates the effect by roughly an order of
magnitude.

Practical upshot for when Model 1a actually gets built: the cheap parallel-shift
approximation is safe to use; the radial-vs-parallel distinction is real but not
worth the extra complexity at these wedge sizes. The toy frontier used for
comparison is illustrative only (not calibrated to real SRS-eligible vs.
general-universe asset data) — that calibration is still open Model 1a work.
