"""Data for Figure 7b and Table 3: the three strategies on one real S&P 500 block-bootstrap
path (seed 17), at four non-SRS income levels. gen_final_three.py hardcodes the oi=0 series
printed here."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
import srs_model as m
import srs_simulation as sim
import numpy as np

rng = np.random.default_rng(17)
ret_path = sim.historical_block_bootstrap_path(10, rng=rng)
pot = 953_537.0
brk = [None]*10

def with_deemed(res, oi):
    t = m.tax(oi + m.INCLUSION*res["residual"], None) - m.tax(oi, None)
    res["total_tax_incl"] = res["total_tax"] + t
    return res

print("return path:", [round(x, 4) for x in ret_path])
rows, paths = [], {}
for oi in (0, 40_000, 80_000, 160_000):
    level = with_deemed(sim.mpc_drawdown(pot, 10, ret_path, brk, other_income=oi, r_forecast=0.05, strategy="mpc", use_dp=False), oi)
    dp = with_deemed(sim.mpc_drawdown(pot, 10, ret_path, brk, other_income=oi, r_forecast=0.05, strategy="mpc", use_dp=True, grid_size=160), oi)
    rule40 = with_deemed(sim.mpc_drawdown(pot, 10, ret_path, brk, other_income=oi, r_forecast=0.05, strategy="rule40"), oi)
    if oi == 0:
        paths = {"level": level["withdrawals"], "dp": dp["withdrawals"], "rule40": rule40["withdrawals"]}
        for k, v in paths.items():
            print(f"withdrawals {k:7s}", [round(w) for w in v])
    row = {"other_income": oi,
           "level_tax": level["total_tax_incl"], "level_residual": level["residual"],
           "dp_tax": dp["total_tax_incl"], "dp_residual": dp["residual"],
           "rule40_tax": rule40["total_tax_incl"], "rule40_residual": rule40["residual"]}
    rows.append(row)
    print(oi, {k: round(v) for k, v in row.items() if k != "other_income"})

json.dump({"return_path": list(ret_path), "withdrawals_oi0": paths, "rows": rows, "pot": pot},
          open(OUT / "strategy3_v2.json", "w"), indent=1)
