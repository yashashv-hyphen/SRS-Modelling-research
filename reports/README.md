# Model report figures

Matplotlib figures for the Word reports on the three models:

| Script | Model | Figures |
|---|---|---|
| `model1_figures.py` | Model 1, `srs_model.py` (per-dollar core) | 1.1 to 1.5 |
| `model2_figures.py` | Model 2, `srs_simulation.py` (Monte Carlo, DP, early exit) | 2.1 to 2.6 |
| `model3_figures.py` | Model 3, `srs_tax_regime.py` (tax-regime history and projection) | 3.1 to 3.4 |

Each script imports the models from the repo root and writes PNGs to `figures/`. It also prints
the numbers quoted in the reports, so they can be checked against `docs/findings.md`.

```bash
.venv/bin/python reports/model1_figures.py
.venv/bin/python reports/model2_figures.py   # ~15 s (Monte Carlo + DP)
.venv/bin/python reports/model3_figures.py
```
