"""Generate the SRS-vs-ordinary indifference boundary line charts for each Figure 6 panel.
x-axis = marginal tax rate t_c, y-axis = portfolio expected return r — same axes as the Figure 6
heatmap itself, so this is the literal indifference curve the heatmap's colors are shading."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)

MAIN = "var(--c-main)"; THIRD = "var(--c-third)"

def sc(v, lo, hi, plo, phi):
    return plo + (v - lo) / (hi - lo) * (phi - plo)

# breakeven_tc(r) computed from srs_model.marginal_exit_rate — see gen_crossover_lines run log
BOUNDARIES = {
    500_000: [(0.02, 0.01), (0.04, 0.0175), (0.09, 0.0175)],       # steps at r=0.04
    3_000_000: [(0.02, 0.09), (0.06, 0.095), (0.09, 0.095)],       # steps at r=0.06
}

def make_chart(n, pot):
    x0, x1, y0, y1 = 58, 330, 196, 22
    xlo, xhi = 0.0, 0.24
    ylo, yhi = 0.02, 0.09
    def X(v): return sc(v, xlo, xhi, x0, x1)
    def Y(v): return sc(v, ylo, yhi, y0, y1)

    bnd = BOUNDARIES[pot]

    s = [f'<svg viewBox="0 0 346 236" role="img" aria-label="Indifference boundary between SRS and the ordinary account, marginal tax rate on x-axis, portfolio return on y-axis, horizon {n} years, ending balance S${pot:,}">']
    label_bal = "${:,.1f}M".format(pot/1e6) if pot >= 1e6 else "${:,.0f}k".format(pot/1e3)
    s.append(f'<text x="{x0}" y="14" class="panel-head">horizon n = {n}y &nbsp;·&nbsp; ending balance {label_bal}</text>')

    # y gridlines (return)
    for v in (0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09):
        y = Y(v)
        s.append(f'<line class="grid-line" x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
        if round(v*100) % 2 == 0:
            s.append(f'<text x="{x0-6}" y="{y+3.2:.1f}" text-anchor="end" class="axis-label">{v*100:.0f}%</text>')
    s.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="baseline"/>')
    s.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" class="baseline"/>')

    # shaded regions either side of the boundary, built from the step points
    # left polygon (ordinary wins): from x0 up to the boundary, right polygon (SRS wins): boundary to x1
    left_pts = [(x0, y0)]
    for r, tc in bnd:
        left_pts.append((X(tc), Y(r)))
    left_pts.append((x0, y1))
    left_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left_pts) + " Z"
    s.append(f'<path d="{left_d}" fill="{THIRD}" opacity="0.14"/>')

    right_pts = [(x1, y0)]
    for r, tc in bnd:
        right_pts.append((X(tc), Y(r)))
    right_pts.append((x1, y1))
    right_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in right_pts) + " Z"
    s.append(f'<path d="{right_d}" fill="{MAIN}" opacity="0.14"/>')

    # boundary line itself (step)
    d = "M" + " L".join(f"{X(tc):.1f},{Y(r):.1f}" for r, tc in bnd)
    s.append(f'<path d="{d}" fill="none" stroke="var(--ink)" stroke-width="2.4"/>')
    for r, tc in bnd:
        s.append(f'<circle cx="{X(tc):.1f}" cy="{Y(r):.1f}" r="3" fill="var(--ink)"><title>r={r*100:.0f}%: breakeven t_c={tc*100:.3g}%</title></circle>')

    # region labels
    s.append(f'<text x="{X(0.01):.1f}" y="{Y(0.08):.1f}" text-anchor="middle" class="data-label" fill="{THIRD}">Ordinary wins</text>')
    s.append(f'<text x="{X(0.19):.1f}" y="{Y(0.08):.1f}" text-anchor="middle" class="data-label" fill="{MAIN}">SRS wins</text>')

    for tc in (0, 0.07, 0.115, 0.18, 0.24):
        s.append(f'<text x="{X(tc):.1f}" y="{y0+15}" text-anchor="middle" class="axis-label">{tc*100:.0f}%</text>')
    s.append(f'<text x="{(x0+x1)/2:.0f}" y="{y0+32}" text-anchor="middle" class="axis-title">Marginal tax rate at contribution, t&#8347;</text>')
    ym = (y0+y1)/2
    s.append(f'<text x="14" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 14 {ym:.0f})">Portfolio expected return r</text>')
    s.append('</svg>')
    return "".join(s)

panels = [(10, 500_000), (30, 500_000), (10, 3_000_000), (30, 3_000_000)]
svgs = [make_chart(n, pot) for n, pot in panels]

import json
json.dump(svgs, open(str(OUT / "crossover_svgs.json"), "w"))
print("wrote", len(svgs), "crossover charts")
