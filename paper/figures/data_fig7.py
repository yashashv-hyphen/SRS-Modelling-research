"""Data for Figure 7: the optimal (level) withdrawal per (balance, years left) cell, and the
marginal rate it faces at each non-SRS income level."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
import srs_model as m
import srs_simulation as sim

r = 0.05
I = 0.5
BALS = [2_000_000, 1_500_000, 1_000_000, 600_000, 300_000, 100_000]
YEARS = list(range(10, 0, -1))
INCOMES = [0, 40_000, 80_000, 160_000]

def level_w(B, k):
    return B * r / (1 - (1+r)**(-k)) if k > 0 else 0.0

rows = []
for b in BALS:
    for k in YEARS:
        w = level_w(b, k)
        marg = {oi: m.marginal_rate(oi + I*w, None) for oi in INCOMES}
        rows.append({"B": b, "k": k, "w": w, "marginal_by_income": marg})

spot = [row for row in rows if row["B"] == 1_000_000 and row["k"] == 10][0]
print("B=$1,000,000, k=10: w* =", round(spot["w"]))
for oi, rate in spot["marginal_by_income"].items():
    print(f"  Yo=${oi:,}: marginal rate {rate*100:.1f}%")

json.dump({"rows": rows, "BALS": BALS, "YEARS": YEARS, "INCOMES": INCOMES},
          open(OUT / "fig7_corrected.json", "w"))
