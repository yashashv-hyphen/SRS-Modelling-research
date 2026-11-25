# srs_basic: from-scratch SRS vs non-SRS model

A simple, one-change-at-a-time rebuild of the SRS comparison. It is
deliberately separate from `srs_model.py`: different withdrawal assumptions
(even split over K years, see `config.py`) and its own tax schedule CSV.

## Setup

    pip install -r requirements.txt

## Run (always from the repo root, with `python -m`)

    python -m pytest srs_basic/tests -q
    python -m srs_basic.figures.fig1_1_exit_rate
    python -m srs_basic.figures.fig1_2_base
    python -m srs_basic.figures.fig1_3_to_1_5_sweeps
    python -m srs_basic.figures.fig1_6_1_7_variant
    python -m srs_basic.make_excel

    # Model 2: optimal withdrawals (dynamic programming)
    python -m srs_basic.figures.fig2_1_to_2_3_policy
    python -m srs_basic.figures.fig2_4_exit_rates
    python -m srs_basic.figures.fig2_5_exit_rate_vs_return

    # Model 3: tax regime (history and 50-year projection)
    python -m srs_basic.figures.fig3_1_schedules
    python -m srs_basic.figures.fig3_2_history
    python -m srs_basic.figures.fig3_3_projection
    python -m srs_basic.figures.fig3_4_heatmaps
    python -m srs_basic.figures.fig3_5_window
    python -m srs_basic.figures.fig3_6_macro

Running a file by its path (`python srs_basic/figures/fig1_2_base.py`) fails
with `ModuleNotFoundError`, because the repo root is then not on Python's path.

## Conventions

- All base-case values live in `config.py`.
- Exit rates are average rates (whole-balance evaluation). The marginal
  "next dollar" breakeven is `exit_rate.marginal_breakeven`.
- Fixed-B figures show advantage per $1 invested at year 0; fixed-C figures
  show advantage per $1 contributed.
- Figures and CSVs are written to `srs_basic/output/`; CSVs are not committed.
- The Excel workbook takes its base case from `config.py` and its tax bands from the schedule CSV. `tests/test_make_excel.py` checks that, and, if LibreOffice is installed, that its numbers match `model1.grid`.
- Model 3 (`model3.py`) replays Models 1 and 2 under every schedule in the
  CSV and projects the schedule forward (frozen / discrete / smooth / top-band
  scenarios, calibrated to the YA2007 to YA2024 revisions). Band edges and the
  0% band never move in any scenario, matching history since YA2003.
