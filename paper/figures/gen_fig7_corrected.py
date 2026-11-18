"""Corrected Figure 7: the optimal withdrawal amount is identical across all four income
panels (proven in Model 2's writeup); what actually varies is the marginal rate it's taxed
at. Each panel shows the same dollar grid, shaded by that panel's marginal rate."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
import json

d = json.load(open(str(OUT / "fig7_corrected.json")))
BALS, YEARS, INCOMES = d["BALS"], d["YEARS"], d["INCOMES"]
rows = {(r["B"], r["k"]): r for r in d["rows"]}

MAIN = "var(--c-main)"

def money(v):
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000: return f"${v/1_000:.0f}k"
    return f"${v:.0f}"

def panel(oi):
    CW, CH = 52, 24
    x0, y0t = 76, 26
    W = x0 + CW*len(YEARS) + 8
    H = y0t + CH*len(BALS) + 44
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Optimal withdrawal by balance and years left; the dollar amount is identical at every income level, shaded here by the marginal tax rate it faces at other income {money(oi)} per year">']
    s.append(f'<text x="{x0}" y="14" class="panel-head">other income = {money(oi)}/yr</text>')
    for b in BALS:
        bi = BALS.index(b)
        y = y0t + bi*CH
        s.append(f'<text x="{x0-6}" y="{y+CH/2+3.5}" text-anchor="end" class="axis-label">{money(b)}</text>')
        for yl in YEARS:
            yi = YEARS.index(yl)
            cell = rows[(b, yl)]
            w = cell["w"]
            rate = cell["marginal_by_income"][str(oi)] if str(oi) in cell["marginal_by_income"] else cell["marginal_by_income"][oi]
            x = x0 + yi*CW
            op = min(1.0, 0.12 + rate/0.24*0.88)
            s.append(f'<rect class="cell-mark" x="{x}" y="{y}" width="{CW-2}" height="{CH-2}" fill="{MAIN}" opacity="{op:.2f}">'
                     f'<title>balance {money(b)}, {yl} years left: withdraw {money(w)} this year, taxed at {rate*100:.1f}% marginal (other income {money(oi)})</title></rect>')
            txt = money(w).replace("$", "")
            cls = "cell-txt-inv" if op > 0.55 else "cell-txt"
            s.append(f'<text x="{x+(CW-2)/2}" y="{y+CH/2+3}" text-anchor="middle" class="{cls}">{txt}</text>')
    yb = y0t + len(BALS)*CH
    for yl in YEARS:
        yi = YEARS.index(yl)
        s.append(f'<text x="{x0+yi*CW+(CW-2)/2}" y="{yb+14}" text-anchor="middle" class="axis-label">{yl}</text>')
    s.append(f'<text x="{x0 + CW*len(YEARS)/2}" y="{yb+32}" text-anchor="middle" class="axis-title">Years left in the 10-year window</text>')
    ym = y0t + CH*len(BALS)/2
    s.append(f'<text x="12" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 12 {ym:.0f})">SRS balance now</text>')
    s.append('</svg>')
    return "".join(s)

svgs = [panel(oi) for oi in INCOMES]
json.dump({"m1": [], "m2": svgs}, open(str(OUT / "fig7_new_svgs.json"), "w"))
print("regenerated 4 corrected panels")
