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

Running a file by its path (`python srs_basic/figures/fig1_2_base.py`) fails
with `ModuleNotFoundError`, because the repo root is then not on Python's path.

## Conventions

- All base-case values live in `config.py`.
- Exit rates are average rates (whole-balance evaluation). The marginal
  "next dollar" breakeven is `exit_rate.marginal_breakeven`.
- Fixed-B figures show advantage per $1 invested at year 0; fixed-C figures
  show advantage per $1 contributed.
- Figures and CSVs are written to `srs_basic/output/`; CSVs are not committed.
