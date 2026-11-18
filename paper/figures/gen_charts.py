"""Generate the sensitivity-analysis SVG fragment for the SRS paper from sweeps.json."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]          # repository root (srs_model.py lives here)
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
import json

D = json.load(open(str(OUT / "sweeps.json")))

# ---------- tiny chart toolkit ----------
def sc(v, lo, hi, plo, phi):
    return plo + (v - lo) / (hi - lo) * (phi - plo)

def fmt_money(v):
    if v >= 1_000_000: return f"${v/1_000_000:.2f}M"
    if v >= 1_000: return f"${v/1_000:.0f}k"
    return f"${v:.0f}"

def fmt_pct(v, dp=1):
    return f"{v*100:.{dp}f}%"

class Panel:
    """One small-multiple panel. viewBox 0 0 W H with margins."""
    def __init__(self, W=380, H=250, ml=62, mr=16, mt=16, mb=44, aria=""):
        self.W, self.H = W, H
        self.ml, self.mr, self.mt, self.mb = ml, mr, mt, mb
        self.parts = []
        self.aria = aria
    @property
    def x0(self): return self.ml
    @property
    def x1(self): return self.W - self.mr
    @property
    def y0(self): return self.H - self.mb   # bottom (baseline)
    @property
    def y1(self): return self.mt            # top
    def X(self, v): return sc(v, self.xlo, self.xhi, self.x0, self.x1)
    def Y(self, v): return sc(v, self.ylo, self.yhi, self.y0, self.y1)
    def set_scales(self, xlo, xhi, ylo, yhi):
        self.xlo, self.xhi, self.ylo, self.yhi = xlo, xhi, ylo, yhi
    def gridlines_y(self, vals, fmt):
        g = ['<g class="grid-line">']
        lbl = []
        for v in vals:
            y = self.Y(v)
            g.append(f'<line x1="{self.x0}" y1="{y:.1f}" x2="{self.x1}" y2="{y:.1f}"/>')
            lbl.append(f'<text x="{self.x0-6}" y="{y+3.5:.1f}" text-anchor="end" class="axis-label">{fmt(v)}</text>')
        g.append('</g>')
        self.parts += g + lbl
    def baseline(self):
        self.parts.append(f'<line x1="{self.x0}" y1="{self.y0}" x2="{self.x1}" y2="{self.y0}" class="baseline"/>')
    def xticks(self, vals, fmt):
        for v in vals:
            x = self.X(v)
            self.parts.append(f'<text x="{x:.1f}" y="{self.y0+16}" text-anchor="middle" class="axis-label">{fmt(v)}</text>')
    def xtitle(self, t):
        self.parts.append(f'<text x="{(self.x0+self.x1)/2:.0f}" y="{self.H-6}" text-anchor="middle" class="axis-title">{t}</text>')
    def ytitle(self, t):
        ym = (self.y0 + self.y1) / 2
        self.parts.append(f'<text x="12" y="{ym:.0f}" text-anchor="middle" class="axis-title" transform="rotate(-90 12 {ym:.0f})">{t}</text>')
    def line(self, pts, color, width=2, dash=None, step=False):
        d = []
        for i, (x, y) in enumerate(pts):
            X, Y = self.X(x), self.Y(y)
            if i == 0:
                d.append(f"M{X:.1f},{Y:.1f}")
            elif step:
                d.append(f"H{X:.1f}")
                d.append(f"V{Y:.1f}")
            else:
                d.append(f"L{X:.1f},{Y:.1f}")
        dd = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{" ".join(d)}" fill="none" stroke="{color}" stroke-width="{width}"{dd}/>')
    def dots(self, pts, color, titles, r=3.4, every=1):
        g = [f'<g fill="{color}">']
        for i, (x, y) in enumerate(pts):
            if i % every: continue
            g.append(f'<circle class="pt" cx="{self.X(x):.1f}" cy="{self.Y(y):.1f}" r="{r}"><title>{titles[i]}</title></circle>')
        g.append('</g>')
        self.parts += g
    def label(self, x, y, text, color="var(--ink)", anchor="middle", dx=0, dy=0, cls="data-label"):
        self.parts.append(f'<text x="{self.X(x)+dx:.1f}" y="{self.Y(y)+dy:.1f}" text-anchor="{anchor}" class="{cls}" fill="{color}">{text}</text>')
    def raw(self, s): self.parts.append(s)
    def svg(self):
        return (f'<svg viewBox="0 0 {self.W} {self.H}" role="img" aria-label="{self.aria}">'
                + "".join(self.parts) + "</svg>")

MAIN = "var(--c-main)"; SECOND = "var(--c-second)"; THIRD = "var(--c-third)"

frags = []

# ========== Panel A: return -> advantage $ ==========
rows = D["by_return"]
p = Panel(aria="Dollar advantage of SRS rises steadily with assumed market return, from about 80 thousand dollars at 2 percent to 333 thousand at 9 percent")
p.set_scales(0.02, 0.09, 0, 350_000)
p.gridlines_y([0, 100_000, 200_000, 300_000], fmt_money)
p.baseline()
pts = [(r["r"], r["advantage"]) for r in rows]
p.line(pts, MAIN)
p.dots(pts, MAIN, [f"r = {fmt_pct(r['r'])}: advantage {fmt_money(r['advantage'])}" for r in rows], every=2)
p.xticks([0.02, 0.04, 0.06, 0.08], lambda v: fmt_pct(v, 0))
p.xtitle("Assumed annual return r")
p.ytitle("Advantage at 73 (S$)")
p.label(0.09, 332_540, "$333k", anchor="end", dy=-10)
p.label(0.02, 79_848, "$80k", anchor="start", dy=-10)
fragA = p.svg()

# ========== Panel B: return -> advantage % ==========
p = Panel(aria="Percentage advantage of SRS falls with market return, from 12.5 percent at a 2 percent return to 8.4 percent at 9 percent")
p.set_scales(0.02, 0.09, 0.07, 0.135)
p.gridlines_y([0.08, 0.10, 0.12], lambda v: fmt_pct(v, 0))
p.baseline()
pts = [(r["r"], r["advantage_pct"]) for r in rows]
p.line(pts, THIRD)
p.dots(pts, THIRD, [f"r = {fmt_pct(r['r'])}: advantage {fmt_pct(r['advantage_pct'])} of Route B" for r in rows], every=2)
p.xticks([0.02, 0.04, 0.06, 0.08], lambda v: fmt_pct(v, 0))
p.xtitle("Assumed annual return r")
p.ytitle("Advantage (% of Route B)")
p.label(0.02, 0.1247, "12.5%", anchor="start", dy=-9)
p.label(0.09, 0.0836, "8.4%", anchor="end", dy=16)
fragB = p.svg()

# ========== Panel C: income -> advantage $ ==========
rows = D["by_income"]
p = Panel(aria="Dollar advantage of SRS by chargeable income: near 20 thousand dollars at 40 thousand income, rising in steps to 331 thousand at 520 thousand income")
p.set_scales(40_000, 520_000, 0, 350_000)
p.gridlines_y([0, 100_000, 200_000, 300_000], fmt_money)
p.baseline()
pts = [(r["chargeable"], r["advantage"]) for r in rows]
p.line(pts, MAIN)
p.dots(pts, MAIN, [f"income {fmt_money(r['chargeable'])}: advantage {fmt_money(r['advantage'])} (relief rate {fmt_pct(r['relief_rate'])})" for r in rows], r=2.8, every=3)
p.xticks([100_000, 250_000, 400_000], lambda v: f"${v//1000}k")
p.xtitle("Chargeable income at contribution")
p.ytitle("Advantage at 73 (S$)")
p.label(520_000, 331_177, "$331k", anchor="end", dy=-10)
p.label(40_000, 20_230, "$20k", anchor="start", dy=-10)
fragC = p.svg()

# ========== Panel D: income -> relief rate (the staircase driver) ==========
p = Panel(aria="Relief rate by chargeable income is a staircase following the IRAS bands, from 3 percent at 40 thousand income to 23 percent at 520 thousand")
p.set_scales(40_000, 520_000, 0, 0.25)
p.gridlines_y([0, 0.10, 0.20], lambda v: fmt_pct(v, 0))
p.baseline()
pts = [(r["chargeable"], r["relief_rate"]) for r in rows]
p.line(pts, SECOND, step=False)
p.dots(pts, SECOND, [f"income {fmt_money(r['chargeable'])}: relief rate {fmt_pct(r['relief_rate'])}" for r in rows], r=2.8, every=3)
p.xticks([100_000, 250_000, 400_000], lambda v: f"${v//1000}k")
p.xtitle("Chargeable income at contribution")
p.ytitle("Relief rate t&#8347;")
p.label(520_000, 0.23, "23%", anchor="end", dy=-9)
fragD = p.svg()

# ========== Panel E: years -> advantage $ ==========
rows = D["by_years"]
p = Panel(aria="Dollar advantage of SRS grows with contribution years, from 16 thousand dollars after 5 years to 247 thousand after 40")
p.set_scales(5, 40, 0, 260_000)
p.gridlines_y([0, 100_000, 200_000], fmt_money)
p.baseline()
pts = [(r["years"], r["advantage"]) for r in rows]
p.line(pts, MAIN)
p.dots(pts, MAIN, [f"{r['years']} years: advantage {fmt_money(r['advantage'])}, pot {fmt_money(r['srs_at_retirement'])}" for r in rows], r=2.8, every=5)
p.xticks([10, 20, 30, 40], lambda v: str(int(v)))
p.xtitle("Years of capped contributions")
p.ytitle("Advantage at end (S$)")
p.label(40, 246_689, "$247k", anchor="end", dy=-10)
fragE = p.svg()

# ========== Panel F: other retirement income -> advantage ==========
rows = D["by_other_income"]
p = Panel(aria="Dollar advantage of the base case falls from 153 thousand dollars with no other retirement income to 70 thousand with 100 thousand of other income a year")
p.set_scales(0, 100_000, 0, 170_000)
p.gridlines_y([0, 50_000, 100_000, 150_000], fmt_money)
p.baseline()
pts = [(r["other"], r["advantage"]) for r in rows]
p.line(pts, MAIN)
p.dots(pts, MAIN, [f"other income {fmt_money(r['other'])}/yr: advantage {fmt_money(r['advantage'])}, avg exit rate {fmt_pct(r['average_exit_rate'])}" for r in rows], r=2.8, every=2)
p.xticks([0, 25_000, 50_000, 75_000, 100_000], lambda v: f"${v//1000}k")
p.xtitle("Other taxable income per drawdown year")
p.ytitle("Advantage at 73 (S$)")
p.label(0, 152_557, "$153k", anchor="start", dy=-10)
p.label(100_000, 70_275, "$70k", anchor="end", dy=-10)
fragF = p.svg()

# ========== Wide chart G: pot -> exit rates (staircase) ==========
rows = [r for r in D["by_pot"] if r["pot"] <= 16_000_000]
p = Panel(W=690, H=300, ml=66, mr=120, mt=18, mb=48,
          aria="Marginal exit rate is a staircase in pot size reaching its 24 percent cap near 15.4 million; the average exit rate rises smoothly and stays far below it; the breakeven relief rate is half the marginal rate and caps at 12 percent")
p.set_scales(0, 16_000_000, 0, 0.26)
p.gridlines_y([0, 0.06, 0.12, 0.18, 0.24], lambda v: fmt_pct(v, 0))
p.baseline()
mpts = [(r["pot"], r["marginal"]) for r in rows]
apts = [(r["pot"], r["average"]) for r in rows]
bpts = [(r["pot"], r["breakeven_tc"]) for r in rows]
p.line(mpts, MAIN, step=True)
p.line(bpts, SECOND, step=True, dash="5 4")
p.line(apts, THIRD)
# sparse hover dots on marginal
p.dots(mpts, MAIN, [f"pot {fmt_money(r['pot'])}: marginal exit {fmt_pct(r['marginal'])}" for r in rows], r=2.6, every=8)
p.dots(apts, THIRD, [f"pot {fmt_money(r['pot'])}: average exit {fmt_pct(r['average'])}" for r in rows], r=2.6, every=8)
# 12% cap reference
y12 = p.Y(0.12)
p.raw(f'<line x1="{p.x0}" y1="{y12:.1f}" x2="{p.x1}" y2="{y12:.1f}" class="ref-line" stroke="#999999"/>')
p.raw(f'<text x="{p.x1+6}" y="{y12+3.5:.1f}" class="axis-label">12% cap on breakeven</text>')
p.xticks([0, 4_000_000, 8_000_000, 12_000_000, 16_000_000], lambda v: f"${v/1_000_000:.0f}M")
p.xtitle("SRS pot at withdrawal age")
p.ytitle("Tax rate on withdrawal")
p.label(16_000_000, 0.24, "marginal 24%", anchor="end", dx=-4, dy=-8)
p.label(16_000_000, 0.1003, "average 10.0%", anchor="end", dx=-4, dy=16)
p.label(16_000_000, 0.12, "breakeven 12%", anchor="end", dx=-4, dy=-8)
fragG = p.svg()

# ========== Wide chart H: strategy tax vs years ==========
rows = D["strategy_tax"]
p = Panel(W=690, H=290, ml=70, mr=20, mt=18, mb=48,
          aria="Total drawdown tax by contribution years: the 40 thousand a year rule's tax grows far faster than level drawdown's, costing 135 thousand dollars more by 36 contribution years")
p.set_scales(10, 36, 0, 190_000)
p.gridlines_y([0, 50_000, 100_000, 150_000], fmt_money)
p.baseline()
lpts = [(r["years"], r["level_tax"]) for r in rows]
fpts = [(r["years"], r["fixed40_tax"]) for r in rows]
p.line(fpts, THIRD)
p.line(lpts, MAIN)
p.dots(fpts, THIRD, [f"{r['years']}y (pot {fmt_money(r['pot'])}): $40k-rule tax {fmt_money(r['fixed40_tax'])}" for r in rows])
p.dots(lpts, MAIN, [f"{r['years']}y (pot {fmt_money(r['pot'])}): level-drawdown tax {fmt_money(r['level_tax'])}" for r in rows])
p.xticks([10, 16, 22, 28, 34], lambda v: str(int(v)))
p.xtitle("Years of capped contributions (pot size grows with years)")
p.ytitle("Total drawdown tax (S$)")
p.label(36, 185_962, "$40k rule: $186k", anchor="end", dy=-10, color=THIRD)
p.label(36, 50_688, "level: $51k", anchor="end", dy=22, color=MAIN)
fragH = p.svg()

# ---------- assemble section ----------
section = f"""
  <!-- ============ 5 (sensitivity) ============ -->
  <section>
    <h2><span class="secnum">6.</span>Sensitivity Analysis: What Moves the Outcome, Factor by Factor</h2>
    <p>
      Each panel below varies <em>one</em> input of the base case (S$120,000 chargeable income,
      S$15,300 contributed for 29 years, 5% return, level 10-year drawdown) while holding every
      other input fixed, re-running <code>srs_model.run()</code> at each point. These are model
      outputs, not interpolations of the summary tables.
    </p>

    <h3>6.1&ensp;Market return</h3>
    <figure class="chart-fig">
      <div class="panel-grid">
        <div class="chart-frame"><p class="panel-title">(a)&ensp;Dollar advantage rises with return</p><div class="chart-svg-wrap">{fragA}</div></div>
        <div class="chart-frame"><p class="panel-title">(b)&ensp;Percentage advantage falls with return</p><div class="chart-svg-wrap">{fragB}</div></div>
      </div>
      <figcaption class="chart-cap"><span class="fig-num">Figure 12.</span>
        Return sensitivity, 15 model runs from r = 2% to 9%. The two panels move in opposite
        directions: a stronger market compounds the invested relief into more dollars (a), but the
        fixed 50% exemption covers a shrinking share of a faster-growing pot, so the relative
        edge thins from 12.5% to 8.4% (b). Hover any point for its exact value.
      </figcaption>
    </figure>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        Better markets make SRS worth more money but a smaller percentage. Either way the sign
        never flips — there is no return, high or low, at which the base-case saver regrets using
        SRS. The return decides how big the win is, never whether you win.
      </p>
    </div>

    <h3>6.2&ensp;Tax bracket at contribution</h3>
    <figure class="chart-fig">
      <div class="panel-grid">
        <div class="chart-frame"><p class="panel-title">(a)&ensp;Advantage by chargeable income</p><div class="chart-svg-wrap">{fragC}</div></div>
        <div class="chart-frame"><p class="panel-title">(b)&ensp;…driven by the relief-rate staircase</p><div class="chart-svg-wrap">{fragD}</div></div>
      </div>
      <figcaption class="chart-cap"><span class="fig-num">Figure 13.</span>
        Income sensitivity, 49 model runs from S$40k to S$520k chargeable income. The advantage
        (a) inherits the staircase of the IRAS schedule (b): flat within each band, jumping at
        band edges ($80k, $120k, $160k, $200k…), with blended rates where the S$15,300
        contribution straddles an edge. The advantage spans S$20k to S$331k — a 16× difference
        across incomes, versus roughly 4× across returns in Figure 9.
      </figcaption>
    </figure>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        Your tax bracket matters far more than the market. A top-bracket earner gets about
        sixteen times the benefit of a low earner from the identical contributions — because the
        whole scheme is a tax-rate trade, and the higher your bracket, the better your side of
        the trade. The steps in the chart are real: within a tax band, earning more changes
        nothing until your income crosses into the next band.
      </p>
    </div>

    <h3>6.3&ensp;Years of contributing</h3>
    <figure class="chart-fig">
      <div class="panel-grid">
        <div class="chart-frame"><p class="panel-title">(a)&ensp;Advantage by contribution years</p><div class="chart-svg-wrap">{fragE}</div></div>
        <div class="chart-frame"><p class="panel-title">(b)&ensp;Advantage by other retirement income</p><div class="chart-svg-wrap">{fragF}</div></div>
      </div>
      <figcaption class="chart-cap"><span class="fig-num">Figure 11.</span>
        (a) Horizon sensitivity, 36 runs from 5 to 40 contribution years: each extra year adds
        both a year's relief and a year's compounding, so the dollar advantage grows
        superlinearly early and almost linearly later. (b) Other-income sensitivity, 21 runs from
        S$0 to S$100k of other taxable income per drawdown year: outside income fills the low tax
        bands first, pushing the taxable half of each SRS withdrawal into higher bands — more
        than halving the advantage (S$153k → S$70k) by S$100k/year. CPF LIFE payouts are
        tax-exempt and do <em>not</em> have this effect.
      </figcaption>
    </figure>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        Starting earlier always helps — there's no age at which beginning SRS stops being
        worthwhile in the base case. But what you'll earn <em>in retirement</em> matters a lot:
        if you expect substantial taxable income then (rent, part-time work, a pension taxed as
        income), each SRS withdrawal gets taxed on top of it and the benefit shrinks fast.
        Government CPF LIFE payouts don't count — they're tax-free and leave your SRS benefit
        untouched.
      </p>
    </div>

    <h3>6.4&ensp;Pot size at withdrawal — the full exit-rate staircase</h3>
    <figure class="chart-fig">
      <div class="chart-frame">
        <div class="chart-svg-wrap">{fragG}</div>
        <div class="chart-legend">
          <span class="lg-item"><span class="lg-swatch" style="background:var(--c-main)"></span>Marginal exit rate (decides: keep contributing?)</span>
          <span class="lg-item"><span class="lg-dash" style="border-color:var(--c-second)"></span>Breakeven relief rate = &frac12; × marginal</span>
          <span class="lg-item"><span class="lg-swatch" style="background:var(--c-third)"></span>Average exit rate (evaluates: what did it cost?)</span>
        </div>
      </div>
      <figcaption class="chart-cap"><span class="fig-num">Figure 12.</span>
        Exit tax rates across 95 pot sizes from S$100k to S$16M (level 10-year drawdown at 5%,
        no other income). The marginal rate is a true staircase — it jumps only where the taxable
        half of the annual withdrawal crosses an IRAS band edge — and caps at 24%, bounding the
        breakeven relief rate at 12%. The average rate every saver actually pays rises smoothly
        and reaches only 10.0% even at S$16M. Confusing the two curves moved an earlier estimate
        of the 7%-bracket crossover from the correct $1.85M to a wrong $5M (docs/findings.md §13).
      </figcaption>
    </figure>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        Two different questions need two different curves. "Should I add one more dollar?" uses
        the staircase (the tax on your <em>next</em> withdrawn dollar). "Was the whole thing worth
        it?" uses the smooth curve (total tax over total withdrawn) — which stays remarkably low:
        even a S$16 million pot pays only about 10 cents per withdrawn dollar on average.
      </p>
    </div>

    <h3>6.5&ensp;Withdrawal strategy</h3>
    <figure class="chart-fig">
      <div class="chart-frame">
        <div class="chart-svg-wrap">{fragH}</div>
        <div class="chart-legend">
          <span class="lg-item"><span class="lg-swatch" style="background:var(--c-main)"></span>Level drawdown (optimal, deterministic case)</span>
          <span class="lg-item"><span class="lg-swatch" style="background:var(--c-third)"></span>"$40,000 a year" rule of thumb</span>
        </div>
      </div>
      <figcaption class="chart-cap"><span class="fig-num">Figure 13.</span>
        Total drawdown tax under the two strategies, 14 runs from 10 to 36 contribution years
        (the pot grows with years: S$192k at 10y to S$1.47M at 36y). Both pay zero while the pot
        is small enough for S$40k/year to drain. Beyond that, the rule of thumb leaves a growing
        residual that is deemed withdrawn — and taxed — in a single final year, costing
        S$135k more than level drawdown by 36 years.
      </figcaption>
    </figure>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        How you take the money out matters as much as how it grew. The popular "$40k a year is
        tax-free" habit is fine for small pots and increasingly expensive for big ones — the
        leftover gets dumped and taxed in one year at the end. Simply dividing your pot evenly
        across the ten years beats it at every size.
      </p>
    </div>

    <h3>6.6&ensp;Ranking the factors</h3>
    <div class="tablewrap">
    <table>
      <caption><span class="tab-num">Table 5.</span> Each factor's leverage on the base-case advantage, from Figures 9–13 (range swept → advantage range).</caption>
      <thead><tr><th>Factor</th><th>Swept over</th><th class="num">Advantage range</th><th class="num">Leverage</th></tr></thead>
      <tbody>
        <tr><td>Tax bracket at contribution</td><td>S$40k – S$520k income</td><td class="num">S$20k – S$331k</td><td class="num">≈ 16×</td></tr>
        <tr><td>Years of contributing</td><td>5 – 40 years</td><td class="num">S$16k – S$247k</td><td class="num">≈ 16×</td></tr>
        <tr><td>Market return</td><td>2% – 9% a year</td><td class="num">S$80k – S$333k</td><td class="num">≈ 4×</td></tr>
        <tr><td>Withdrawal strategy</td><td>level vs $40k rule, 36y pot</td><td class="num">S$135k of tax at stake</td><td class="num">—</td></tr>
        <tr><td>Other income in retirement</td><td>S$0 – S$100k / year</td><td class="num">S$153k – S$70k</td><td class="num">≈ 2× (inverse)</td></tr>
      </tbody>
    </table>
    </div>
    <p class="table-note">
      "Leverage" compares the largest to the smallest advantage across the swept range; it ranks
      sensitivity, holding everything else at base-case values, and is not additive across rows.
    </p>
    <div class="plain">
      <span class="tag">In plain English</span>
      <p>
        If you remember one chart from this paper, make it this ranking: <strong>who you are (your
        tax bracket) and when you start matter most; the market matters least.</strong> The two
        things fully under your control — starting early and withdrawing sensibly — are together
        worth more than the difference between a bad market and a great one.
      </p>
    </div>
  </section>
"""

open(str(OUT / "section6.html"), "w").write(section)
print("wrote section6.html,", len(section), "chars")
