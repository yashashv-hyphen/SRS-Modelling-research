"""Parameter sweeps over srs_model.py for the paper's sensitivity figures."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
import json, sys
sys.path.insert(0, str(ROOT))
import srs_model as m

out = {}

# S1: advantage ($ and %) vs market return, base case otherwise
out["by_return"] = [
    {"r": r/1000,
     **{k: v for k, v in m.run(r=r/1000).items()
        if k in ("advantage", "advantage_pct", "srs_at_retirement", "average_exit_rate")}}
    for r in range(20, 91, 5)  # 2.0% .. 9.0% step 0.5pp
]

# S2: advantage vs chargeable income (tax bracket), 5% return
out["by_income"] = [
    {"chargeable": ci,
     **{k: v for k, v in m.run(chargeable=ci).items()
        if k in ("advantage", "advantage_pct", "relief_rate")}}
    for ci in range(40_000, 520_001, 10_000)
]

# S3: pot at 64 + advantage vs contribution years, 5%
out["by_years"] = [
    {"years": y,
     **{k: v for k, v in m.run(contrib_years=y).items()
        if k in ("advantage", "advantage_pct", "srs_at_retirement")}}
    for y in range(5, 41, 1)
]

# S4: exit-rate staircase vs pot size (marginal + average + breakeven tc)
pots = list(range(100_000, 2_000_001, 50_000)) + list(range(2_250_000, 16_000_001, 250_000))
out["by_pot"] = [
    {"pot": p,
     "marginal": m.marginal_exit_rate(p),
     "average": m.average_exit_rate(p),
     "breakeven_tc": m.breakeven_tc(p)}
    for p in pots
]

# S5: other retirement income vs average exit rate and advantage, base pot
out["by_other_income"] = [
    {"other": oi,
     **{k: v for k, v in m.run(other_retirement_income=oi).items()
        if k in ("advantage", "advantage_pct", "average_exit_rate", "total_tax")}}
    for oi in range(0, 100_001, 5_000)
]

# S6: strategy comparison across contribution years (level vs fixed40 total tax)
out["strategy_tax"] = [
    {"years": y,
     "pot": m.run(contrib_years=y)["srs_at_retirement"],
     "level_tax": m.run(contrib_years=y, strategy="level")["total_tax"],
     "fixed40_tax": m.run(contrib_years=y, strategy="fixed40")["total_tax"]}
    for y in range(10, 37, 2)
]

json.dump(out, open(str(OUT / "sweeps.json"), "w"), indent=1)
# compact preview
for k, rows in out.items():
    print(k, len(rows), "rows; first:", {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in rows[0].items()})
    print("   last:", {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in rows[-1].items()})
