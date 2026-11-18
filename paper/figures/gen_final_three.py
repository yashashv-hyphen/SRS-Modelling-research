"""Regenerate Figure 7b, Figure 7c, and Figure 13 with exactly three strategies:
DP (main/slate), Level-drawdown (second/jade), $40,000 rule (third/clay, dashed) — no
fixed-at-start anywhere."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
import json

MAIN = "var(--c-main)"; SECOND = "var(--c-second)"; THIRD = "var(--c-third)"

# ===================== Figure 7b (volatile path, seed 17, oi=0) =====================
returns = [-0.0903, -0.1185, -0.2197, 0.2836, 0.1074, 0.1482, 0.021, 0.1589, 0.3215, 0.1352]
dp_w      = [102571, 104429, 86211, 62002, 77496, 82673, 102451, 90756, 91664, 162207]
level_w   = [123487, 104666, 85271, 59583, 75451, 80528, 90183, 86778, 100618, 153953]
rule40_w  = [40000]*10

x0, x1, y0, y1 = 58, 600, 220, 24
def X(i): return x0 + i*(x1-x0)/9
def Y(v): return y0 - v/170000*(y0-y1)

s = ['<svg viewBox="0 0 650 280" role="img" aria-label="Year-by-year SRS withdrawal under dynamic programming, level drawdown, and the forty thousand dollar rule, over a ten year window with an early market downturn followed by a strong recovery">']
xshade0, xshade1 = X(-0.5), X(2.5)
s.append(f'<rect x="{xshade0:.1f}" y="{y1}" width="{xshade1-xshade0:.1f}" height="{y0-y1}" fill="var(--c-third)" opacity="0.08"/>')
s.append(f'<text x="{(xshade0+xshade1)/2:.1f}" y="{y1+12}" text-anchor="middle" class="axis-label" fill="var(--c-third)">market down years</text>')
for v in (0, 50_000, 100_000, 150_000):
    y = Y(v)
    s.append(f'<line class="grid-line" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    lbl = "$0" if v == 0 else f"${v//1000}k"
    s.append(f'<text x="{x0-6}" y="{y+3.2:.1f}" text-anchor="end" class="axis-label">{lbl}</text>')
s.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="baseline"/>')
s.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" class="baseline"/>')

def line(vals, color, titles, dash=None):
    d = " ".join(("M" if i==0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    out = [f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2"{dd}/>', f'<g fill="{color}">']
    for i, v in enumerate(vals):
        out.append(f'<circle class="pt" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.2"><title>{titles[i]}</title></circle>')
    out.append('</g>')
    return "".join(out)

s.append(line(rule40_w, THIRD, [f"Year {i+1}: $40,000 rule withdraws $40,000" for i in range(10)], dash="3 4"))
s.append(line(level_w, SECOND, [f"Year {i+1}: level drawdown withdraws ${v:,.0f} (market return this year {returns[i]*100:+.1f}%)" for i, v in enumerate(level_w)]))
s.append(line(dp_w, MAIN, [f"Year {i+1}: DP withdraws ${v:,.0f} (market return this year {returns[i]*100:+.1f}%)" for i, v in enumerate(dp_w)]))

s.append(f'<text x="{X(9):.1f}" y="{Y(162207)-8:.1f}" text-anchor="end" class="data-label" fill="{MAIN}">DP: $162k</text>')
s.append(f'<text x="{X(9):.1f}" y="{Y(153953)+14:.1f}" text-anchor="end" class="data-label" fill="{SECOND}">level: $154k</text>')

for i in range(10):
    s.append(f'<text x="{X(i):.1f}" y="{y0+15}" text-anchor="middle" class="axis-label">{i+1}</text>')
s.append(f'<text x="{(x0+x1)/2:.0f}" y="{y0+32}" text-anchor="middle" class="axis-title">Year of the 10-year withdrawal window</text>')
ym = (y0+y1)/2
s.append(f'<text x="14" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 14 {ym:.0f})">Withdrawal that year (S$)</text>')
s.append('</svg>')
fig7b = "".join(s)

# ===================== Figure 7c (flat market, oi=0) =====================
data = json.load(open(str(OUT / "flat_market_v2.json")))
level_f = data["level"]; dp_f = data["dp"]; rule40_f = data["rule40"]

s = ['<svg viewBox="0 0 650 280" role="img" aria-label="Year-by-year SRS withdrawal under the three strategies when the market return is flat at the five percent forecast every year, the control case for Figure 7b">']
s.append(f'<rect x="{x0}" y="{y1}" width="{x1-x0}" height="{y0-y1}" fill="var(--c-main)" opacity="0.04"/>')
s.append(f'<text x="{(x0+x1)/2:.1f}" y="{y1+12}" text-anchor="middle" class="axis-label" fill="var(--c-main)">market return held flat at 5% every year</text>')
for v in (0, 50_000, 100_000, 150_000):
    y = Y(v)
    s.append(f'<line class="grid-line" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    lbl = "$0" if v == 0 else f"${v//1000}k"
    s.append(f'<text x="{x0-6}" y="{y+3.2:.1f}" text-anchor="end" class="axis-label">{lbl}</text>')
s.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="baseline"/>')
s.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" class="baseline"/>')

s.append(line(rule40_f, THIRD, [f"Year {i+1}: $40,000 rule withdraws $40,000" for i in range(10)], dash="3 4"))
s.append(line(level_f, SECOND, [f"Year {i+1}: level drawdown withdraws ${v:,.0f} (closed form, flat market)" for i, v in enumerate(level_f)]))

# DP as diamond markers + dotted connector (grid-search noise around the level line)
d = " ".join(("M" if i==0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(dp_f))
s.append(f'<path d="{d}" fill="none" stroke="{MAIN}" stroke-width="1.2" stroke-dasharray="1 3" opacity="0.85"/>')
s.append(f'<g fill="var(--paper-raised)" stroke="{MAIN}" stroke-width="1.6">')
for i, v in enumerate(dp_f):
    cx, cy = X(i), Y(v)
    sz = 4.6
    s.append(f'<path d="M{cx:.1f},{cy-sz:.1f} L{cx+sz:.1f},{cy:.1f} L{cx:.1f},{cy+sz:.1f} L{cx-sz:.1f},{cy:.1f} Z"><title>Year {i+1}: DP grid-search withdraws ${v:,.0f} (flat market; noise around the $123,487 closed-form optimum)</title></path>')
s.append('</g>')

s.append(f'<text x="{X(9)-4:.1f}" y="{Y(123487)-10:.1f}" text-anchor="end" class="data-label" fill="{SECOND}">level: $123,487 every year</text>')
s.append(f'<text x="{X(9)-4:.1f}" y="{Y(40000)-10:.1f}" text-anchor="end" class="data-label" fill="{THIRD}">$40,000 rule leaves $1.05M to be dumped at close</text>')

for i in range(10):
    s.append(f'<text x="{X(i):.1f}" y="{y0+15}" text-anchor="middle" class="axis-label">{i+1}</text>')
s.append(f'<text x="{(x0+x1)/2:.0f}" y="{y0+32}" text-anchor="middle" class="axis-title">Year of the 10-year withdrawal window</text>')
s.append(f'<text x="14" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 14 {ym:.0f})">Withdrawal that year (S$)</text>')
s.append('</svg>')
fig7c = "".join(s)

# ===================== Figure 13 (6.5: level, DP, $40k across contribution years) =====================
D = json.load(open(str(OUT / "sweeps.json")))
rows = D["strategy_tax"]
x0b, x1b, y0b, y1b = 70, 670, 242, 22
def Xb(years): return x0b + (years-10)/(36-10)*(x1b-x0b)
def Yb(v): return y0b - v/190_000*(y0b-y1b)

s = ['<svg viewBox="0 0 690 290" role="img" aria-label="Total drawdown tax by contribution years: level drawdown and the DP grid solver track closely, while the forty thousand dollar rule grows far more expensive">']
for v in (0, 50_000, 100_000, 150_000):
    y = Yb(v)
    s.append(f'<line class="grid-line" x1="{x0b}" y1="{y:.1f}" x2="{x1b}" y2="{y:.1f}"/>')
    lbl = "$0" if v == 0 else f"${v//1000}k"
    s.append(f'<text x="{x0b-6}" y="{y+3.2:.1f}" text-anchor="end" class="axis-label">{lbl}</text>')
s.append(f'<line x1="{x0b}" y1="{y0b}" x2="{x1b}" y2="{y0b}" class="baseline"/>')

def line2(key, color, label_fn, dash=None, r=3.4):
    d = " ".join(("M" if i==0 else "L") + f"{Xb(r2['years']):.1f},{Yb(r2[key]):.1f}" for i, r2 in enumerate(rows))
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    out = [f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{dd}/>', f'<g fill="{color}">']
    for r2 in rows:
        out.append(f'<circle class="pt" cx="{Xb(r2["years"]):.1f}" cy="{Yb(r2[key]):.1f}" r="{r}"><title>{label_fn(r2)}</title></circle>')
    out.append("</g>")
    return "".join(out)

s.append(line2("fixed40_tax", THIRD, lambda r: f"{r['years']}y (pot ${r['pot']:,.0f}): $40k-rule tax ${r['fixed40_tax']:,.0f}", dash="3 4"))
s.append(line2("level_tax", SECOND, lambda r: f"{r['years']}y (pot ${r['pot']:,.0f}): level-drawdown tax ${r['level_tax']:,.0f}"))

# DP diamonds
dpts = [(Xb(r2["years"]), Yb(r2["dp_tax"])) for r2 in rows]
dline = " ".join(("M" if i==0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(dpts))
s.append(f'<path d="{dline}" fill="none" stroke="{MAIN}" stroke-width="1.2" stroke-dasharray="1 3" opacity="0.85"/>')
s.append(f'<g fill="var(--paper-raised)" stroke="{MAIN}" stroke-width="1.6">')
for r2 in rows:
    cx, cy = Xb(r2["years"]), Yb(r2["dp_tax"])
    sz = 4.4
    s.append(f'<path d="M{cx:.1f},{cy-sz:.1f} L{cx+sz:.1f},{cy:.1f} L{cx:.1f},{cy+sz:.1f} L{cx-sz:.1f},{cy:.1f} Z"><title>{r2["years"]}y (pot ${r2["pot"]:,.0f}): DP grid-solver tax ${r2["dp_tax"]:,.0f}</title></path>')
s.append('</g>')

for y in (10, 16, 22, 28, 34):
    s.append(f'<text x="{Xb(y):.1f}" y="{y0b+16}" text-anchor="middle" class="axis-label">{y}</text>')
s.append(f'<text x="{(x0b+x1b)/2:.0f}" y="{y0b+32}" text-anchor="middle" class="axis-title">Years of capped contributions (pot size grows with years)</text>')
ymb = (y0b+y1b)/2
s.append(f'<text x="12" y="{ymb:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 12 {ymb:.0f})">Total drawdown tax (S$)</text>')
last = rows[-1]
s.append(f'<text x="{Xb(last["years"])-4:.1f}" y="{Yb(last["fixed40_tax"])-6:.1f}" text-anchor="end" class="data-label" fill="{THIRD}">$40k rule: ${last["fixed40_tax"]:,.0f}</text>')
s.append(f'<text x="{Xb(last["years"])-4:.1f}" y="{Yb(last["dp_tax"])-10:.1f}" text-anchor="end" class="data-label" fill="{MAIN}">DP: ${last["dp_tax"]:,.0f}</text>')
s.append(f'<text x="{Xb(last["years"])-4:.1f}" y="{Yb(last["level_tax"])+16:.1f}" text-anchor="end" class="data-label" fill="{SECOND}">level: ${last["level_tax"]:,.0f}</text>')
s.append('</svg>')
fig13 = "".join(s)

json.dump({"fig7b": fig7b, "fig7c": fig7c, "fig13": fig13}, open(str(OUT / "final_three_charts.json"), "w"))
print("fig7b", len(fig7b), "fig7c", len(fig7c), "fig13", len(fig13))
