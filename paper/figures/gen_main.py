"""Compute and render the three supervisor-specified MAIN analyses as SVG/HTML."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
import json, sys
sys.path.insert(0, str(ROOT))
import srs_model as m
import srs_simulation as sim

MAIN = "var(--c-main)"; SECOND = "var(--c-second)"; THIRD = "var(--c-third)"
NEUT = "var(--c-neutral)"

def money(v):
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000: return f"${v/1_000:.0f}k"
    return f"${v:.0f}"

# ================================================================
# MAIN 1 — Model 1: advantage per dollar over (r x tc), 2x2 panels
# ================================================================
TCS = [0.0, 0.02, 0.035, 0.07, 0.115, 0.15, 0.18, 0.20, 0.22, 0.24]
RS  = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09]
PANELS1 = [  # (horizon n, ending balance)
    (10, 500_000), (30, 500_000),
    (10, 3_000_000), (30, 3_000_000),
]

def m1_panel(n, pot, pid):
    CW, CH = 46, 22
    x0, y0t = 50, 26
    W = x0 + CW*len(TCS) + 10
    H = y0t + CH*len(RS) + 44
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Advantage per dollar across relief rate and portfolio return, horizon {n} years, ending balance {money(pot)}">']
    s.append(f'<text x="{x0}" y="14" class="panel-head">horizon n = {n}y &nbsp;·&nbsp; ending balance {money(pot)}</text>')
    for ri, r in enumerate(RS):
        tw = m.marginal_exit_rate(pot, r=r, years=10)
        y = y0t + ri*CH
        s.append(f'<text x="{x0-6}" y="{y+CH/2+3.5}" text-anchor="end" class="axis-label">{r*100:.0f}%</text>')
        for ci, tc in enumerate(TCS):
            adv = m.per_dollar_ratio(tc, tw) - 1.0
            x = x0 + ci*CW
            if abs(adv) < 0.004:
                fill, op = NEUT, 0.6
            elif adv > 0:
                fill, op = MAIN, min(1.0, 0.18 + adv/0.30*0.82)
            else:
                fill, op = THIRD, min(1.0, 0.25 + (-adv)/0.12*0.75)
            s.append(f'<rect class="cell-mark" x="{x}" y="{y}" width="{CW-2}" height="{CH-2}" fill="{fill}" opacity="{op:.2f}">'
                     f'<title>t_c = {tc*100:g}%, r = {r*100:.0f}% (exit rate t_w = {tw*100:g}%): advantage {adv*100:+.2f}% per dollar</title></rect>')
            txt = f"{adv*100:+.0f}" if abs(adv) >= 0.0995 else f"{adv*100:+.1f}"
            cls = "cell-txt-inv" if (adv > 0.12) else "cell-txt"
            s.append(f'<text x="{x+(CW-2)/2}" y="{y+CH/2+3}" text-anchor="middle" class="{cls}">{txt}</text>')
    yb = y0t + len(RS)*CH
    for ci, tc in enumerate(TCS):
        lab = f"{tc*100:g}"
        s.append(f'<text x="{x0+ci*CW+(CW-2)/2}" y="{yb+14}" text-anchor="middle" class="axis-label">{lab}</text>')
    s.append(f'<text x="{x0 + CW*len(TCS)/2}" y="{yb+32}" text-anchor="middle" class="axis-title">Marginal tax rate at contribution, t&#8347; (%)</text>')
    s.append(f'<text x="14" y="{y0t + CH*len(RS)/2}" class="axis-title" transform="rotate(-90 14 {y0t + CH*len(RS)/2})" text-anchor="middle">Return r</text>')
    s.append('</svg>')
    return "".join(s)

m1_svgs = [m1_panel(n, pot, i) for i, (n, pot) in enumerate(PANELS1)]

# tw table for the caption
tw_notes = []
for pot in (500_000, 3_000_000):
    tws = sorted({round(m.marginal_exit_rate(pot, r=r, years=10)*100, 1) for r in RS})
    tw_notes.append((pot, tws))
print("MAIN1 exit rates:", tw_notes)

# ================================================================
# MAIN 2 — Model 2: DP policy grid, 4 income panels
# ================================================================
BALS = [2_000_000, 1_500_000, 1_000_000, 600_000, 300_000, 100_000]  # top to bottom
YEARS = list(range(10, 0, -1))  # x axis: 10 ... 1 years left
INCOMES = [0, 40_000, 80_000, 160_000]

def m2_panel(oi):
    CW, CH = 52, 24
    x0, y0t = 76, 26
    W = x0 + CW*len(YEARS) + 8
    H = y0t + CH*len(BALS) + 44
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Dynamic-programming recommended withdrawal by balance and years left, other income {money(oi)} per year">']
    s.append(f'<text x="{x0}" y="14" class="panel-head">other income = {money(oi)}/yr</text>')
    for bi, b in enumerate(BALS):
        y = y0t + bi*CH
        s.append(f'<text x="{x0-6}" y="{y+CH/2+3.5}" text-anchor="end" class="axis-label">{money(b)}</text>')
        for yi, yl in enumerate(YEARS):
            action, _tot = sim._dp_solve(b, yl, None, 0.05, other_income=oi, grid_size=120)
            frac = action / b if b else 0
            x = x0 + yi*CW
            op = min(1.0, 0.12 + min(frac, 1.0)*0.88)
            s.append(f'<rect class="cell-mark" x="{x}" y="{y}" width="{CW-2}" height="{CH-2}" fill="{MAIN}" opacity="{op:.2f}">'
                     f'<title>balance {money(b)}, {yl} years left, other income {money(oi)}: withdraw {money(action)} this year ({frac*100:.0f}% of balance)</title></rect>')
            txt = money(action).replace("$", "")
            cls = "cell-txt-inv" if op > 0.55 else "cell-txt"
            s.append(f'<text x="{x+(CW-2)/2}" y="{y+CH/2+3}" text-anchor="middle" class="{cls}">{txt}</text>')
    yb = y0t + len(BALS)*CH
    for yi, yl in enumerate(YEARS):
        s.append(f'<text x="{x0+yi*CW+(CW-2)/2}" y="{yb+14}" text-anchor="middle" class="axis-label">{yl}</text>')
    s.append(f'<text x="{x0 + CW*len(YEARS)/2}" y="{yb+32}" text-anchor="middle" class="axis-title">Years left in the 10-year window</text>')
    ym = y0t + CH*len(BALS)/2
    s.append(f'<text x="12" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 12 {ym:.0f})">SRS balance now</text>')
    s.append('</svg>')
    return "".join(s)

m2_svgs = [m2_panel(oi) for oi in INCOMES]
print("MAIN2 done")

# spot-check numbers for the caption
a0, _ = sim._dp_solve(1_000_000, 10, None, 0.05, other_income=0, grid_size=120)
a1, _ = sim._dp_solve(1_000_000, 10, None, 0.05, other_income=160_000, grid_size=120)
lvl = m.level_payment(1_000_000, 0.05, 10)
print("1M/10y: dp(oi=0) =", round(a0), " dp(oi=160k) =", round(a1), " level =", round(lvl))

# ================================================================
# MAIN 3 — Model 3: narrative table + projection table (data from results_tax_regime.json)
# ================================================================
hist = json.load(open(str(ROOT / "data") + "/tax_brackets_historical.json"))
rows3 = []
for h in hist["history"]:
    ya = h["year_of_assessment"]
    thru = h["effective_through"] or "today"
    top = h["brackets"][-1][1]*100
    nb = len(h["brackets"])
    rows3.append((ya, thru, top, nb))
print("MAIN3 history:", rows3)

json.dump({"m1": m1_svgs, "m2": m2_svgs}, open(str(OUT / "main_svgs.json"), "w"))
print("saved main_svgs.json")
