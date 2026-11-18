"""Data for Figure 7c: level drawdown vs DP vs $40k rule with the market held at exactly 5%."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
import srs_model as m
import srs_simulation as sim

pot = 953_537.0
flat = [0.05]*10
brk = [None]*10

level = sim.mpc_drawdown(pot, 10, flat, brk, other_income=0, r_forecast=0.05, strategy="mpc", use_dp=False)
dp = sim.mpc_drawdown(pot, 10, flat, brk, other_income=0, r_forecast=0.05, strategy="mpc", use_dp=True, grid_size=160)
rule40 = sim.mpc_drawdown(pot, 10, flat, brk, other_income=0, r_forecast=0.05, strategy="rule40")

def deemed(res):
    """Total tax including the deemed withdrawal of the residual at window close."""
    return res["total_tax"] + m.tax(m.INCLUSION*res["residual"], None)

for name, res in (("level", level), ("dp", dp), ("rule40", rule40)):
    print(f"{name:7s}", [round(w) for w in res["withdrawals"]], "residual", round(res["residual"]), "tax_incl", round(deemed(res)))

json.dump({
    "level": level["withdrawals"], "level_residual": level["residual"], "level_tax": deemed(level),
    "dp": dp["withdrawals"], "dp_residual": dp["residual"], "dp_tax": deemed(dp),
    "rule40": rule40["withdrawals"], "rule40_residual": rule40["residual"], "rule40_tax": deemed(rule40),
}, open(OUT / "flat_market_v2.json", "w"), indent=1)
