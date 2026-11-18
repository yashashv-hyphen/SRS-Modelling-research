"""Adds the DP grid-solver's total tax (dp_tax) to sweeps.json's strategy_tax rows, for
Figure 13 and Table 6. Run after sweeps.py."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(ROOT))
import srs_simulation as sim

D = json.load(open(OUT / "sweeps.json"))
flat = [0.05]*10
brk = [None]*10
for r in D["strategy_tax"]:
    res = sim.mpc_drawdown(r["pot"], 10, flat, brk, other_income=0, r_forecast=0.05,
                           strategy="mpc", use_dp=True, grid_size=160)
    r["dp_tax"] = res["total_tax"]
    print(r["years"], round(r["pot"]), "level=", round(r["level_tax"]), "dp=", round(r["dp_tax"]))
json.dump(D, open(OUT / "sweeps.json", "w"), indent=1)
