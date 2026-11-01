"""Build the Model 1 Excel workbook from the same inputs as the Python model.

Every grid cell is a live Excel formula, so the workbook recalculates when the
Inputs sheet changes. Base-case values come from config.py and the tax bands
from the schedule CSV, so the workbook always starts from what the code uses.

Run from the repo root: python -m srs_basic.make_excel
"""

import math
from pathlib import Path

from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.utils import get_column_letter as L

from srs_basic import config
from srs_basic.tax import load_schedule

FILE_NAME = "SRS_Model1_grids.xlsx"
TOP_EDGE = 1e12  # stands in for "no upper limit" in Excel

# Sweeps shown in the workbook (same as the Python figures)
SWEEP_N = (10, 20, 30, 40)
SWEEP_B = (500_000, 1_000_000, 2_000_000, 3_000_000)
SWEEP_OTHER = (0, 30_000, 60_000)
CURVE_LEVELS = (0, 0.25, 0.5, 1, 2)
SUMMARY_OTHER = (0, 30_000, 60_000, 90_000)


def build_workbook(path=None):
    """Write the workbook and return its path."""
    path = Path(path) if path else Path(config.OUTPUT_DIR) / FILE_NAME
    wb = Workbook()
    _build(wb)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def _build(wb):
    F = "Arial"
    BLUE = Font(name=F, color="0000FF")
    GREEN = Font(name=F, color="008000")
    BLACK = Font(name=F)
    BOLD = Font(name=F, bold=True)
    TITLE = Font(name=F, bold=True, size=13)
    HDR_FILL = PatternFill("solid", fgColor="D9E1F2")
    KEY_FILL = PatternFill("solid", fgColor="FFFF00")
    thin = Side(style="thin", color="BFBFBF")
    BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
    PCT0, PCT2 = "0%", "0.00%"
    USD = '$#,##0;($#,##0);"-"'
    ADV = '0.00;[Red]-0.00;0.00'

    def name(n, ref):
        wb.defined_names[n] = DefinedName(n, attr_text=ref)

    def cell(ws, ref, value, font=BLACK, fmt=None, fill=None):
        c = ws[ref]
        c.value = value
        c.font = font
        if fmt: c.number_format = fmt
        if fill: c.fill = fill
        return c

    def TAX(x):
        x = f"({x})"
        return (f"SUMPRODUCT(({x}>TaxLower)*((({x}<TaxUpper)*{x})+(({x}>=TaxUpper)*TaxUpper)-TaxLower)*TaxRate)")

    def EXIT(b, other, k="In_K", i="In_I"):
        return f"IF({b}<=0,0,{k}*({TAX(f'{other}+{i}*{b}/{k}')}-{TAX(other)})/{b})"

    TC = [t / 100 for t in range(0, 25)]          # 0%..24%
    RS = [r / 100 for r in range(3, 13)]          # 3%..12%
    RS_FINE = [round(0.03 + 0.005 * i, 4) for i in range(19)]  # 3%..12% step 0.5%

    def scale(ws, rng):
        ws.conditional_formatting.add(rng, ColorScaleRule(
            start_type="min", start_color="F8696B", mid_type="num", mid_value=0,
            mid_color="FFFFFF", end_type="max", end_color="5A8AC6"))

    def widths(ws, first=22, rest=8, ncols=30):
        ws.column_dimensions["A"].width = first
        for c in range(2, ncols + 1):
            ws.column_dimensions[L(c)].width = rest

    # ---------------- Guide ----------------
    g = wb.active
    g.title = "Guide"
    g.column_dimensions["A"].width = 24
    g.column_dimensions["B"].width = 100
    rows = [
        ("SRS vs non-SRS: Model 1 workbook", None),
        ("", None),
        ("What it shows", "Whether investing a pre-tax dollar in SRS beats investing it outside SRS, across tax rates (tc, x axis) and returns (r, y axis), changing one parameter at a time."),
        ("Advantage", "SRS after-tax wealth minus non-SRS after-tax wealth. Positive (blue) = SRS wins, negative (red) = outside SRS wins."),
        ("Breakeven", "Where the advantage is 0: tc = average exit rate. Whole-balance evaluation (average rate), not a next-dollar decision."),
        ("", None),
        ("Sheets", None),
        ("Inputs", "Base case. Change the blue cells here and every sheet updates."),
        ("Tax_Schedule", f"{config.REGIME} resident income tax bands (IRAS). Edit to test another schedule (Model 3)."),
        ("Fig1_1_ExitRate", "Average exit rate against balance at retirement, with chart."),
        ("Fig1_2_Base", "Base grid: advantage per $1 invested at year 0, N and B from Inputs."),
        ("Fig1_2_Curves", "Indifference curves on the tc-r plane: combinations giving the same advantage (0 = breakeven)."),
        ("Fig1_3_Horizon", "Grids for N = 10, 20, 30, 40 years (B from Inputs)."),
        ("Fig1_4_Balance", "Grids for B = $0.5M, $1M, $2M, $3M (N from Inputs)."),
        ("Fig1_5_OtherInc", "Grids for other retirement income = $0, $30k, $60k."),
        ("Fig1_6_7_Variant", "Fixed annual contribution C instead of fixed B: advantage per $1 contributed, N = 10 to 40."),
        ("Fig1_7_Curves", "Breakeven tc against r for a fixed contribution, one curve per N: the 'don't earn too high a return in SRS' result."),
        ("Breakeven_Summary", "Two-way table: breakeven tc by balance and other income, with chart."),
        ("", None),
        ("Formulas", None),
        ("Tax T(x)", "Each band's slice taxed at that band's rate: SUMPRODUCT over Tax_Schedule."),
        ("Exit rate", "K x [T(other + I x B/K) - T(other)] / B: total tax on withdrawals / total withdrawn."),
        ("Fixed B grid", "(1 + r)^N x (tc - exit rate)."),
        ("Fixed C grid", "Pot x (tc - exit rate) / (C x N), where Pot = C x ((1 + r)^N - 1) / r (end-of-year contributions)."),
        ("Curves", "Fixed B: tc = exit rate + A / (1 + r)^N for advantage level A."),
        ("", None),
        ("Colour code", "Blue text = input you can change. Black = formula. Green = link to Inputs."),
        ("Assumptions", "Resident; 50% of each withdrawal taxable; even withdrawals over K years; same return inside and outside SRS; no tax on non-SRS returns."),
        ("Source", f"Tax bands: IRAS resident rates, {config.REGIME}, loaded from {config.SCHEDULE_CSV}. Workbook generated by srs_basic/make_excel.py."),
    ]
    for i, (a, b) in enumerate(rows, start=1):
        g.cell(i, 1, a).font = TITLE if i == 1 else (BOLD if b is None and a else BOLD)
        if b:
            c = g.cell(i, 2, b); c.font = BLACK; c.alignment = Alignment(wrap_text=True, vertical="top")
        g.cell(i, 1).alignment = Alignment(vertical="top")

    # ---------------- Inputs ----------------
    inp = wb.create_sheet("Inputs")
    inp.column_dimensions["A"].width = 38; inp.column_dimensions["B"].width = 14; inp.column_dimensions["C"].width = 60
    cell(inp, "A1", "Base case inputs", TITLE)
    cell(inp, "A2", "Blue cells are inputs. Every sheet reads from here.", Font(name=F, italic=True))
    items = [
        ("Horizon N (years to retirement)", config.N, "0", "In_N", "Base case horizon"),
        ("Balance at retirement B ($)", config.B, USD, "In_B", "Fixed-pot mode"),
        ("Withdrawal years K", config.K, "0", "In_K", "Even split; SRS allows up to 10 years"),
        ("Other taxable income per retirement year ($)", config.OTHER, USD, "In_Other", "Income besides SRS in each withdrawal year"),
        ("Taxable share of withdrawals I", config.I, "0%", "In_I", "SRS rule: 50% of qualifying withdrawals taxable"),
        ("Annual contribution C ($)", config.C, USD, "In_C", "Fixed-contribution variant; SRS cap for citizens and PRs"),
    ]
    for i, (lab, val, fmt, nm, note) in enumerate(items, start=4):
        cell(inp, f"A{i}", lab)
        cell(inp, f"B{i}", val, BLUE, fmt, KEY_FILL)
        cell(inp, f"C{i}", note, Font(name=F, color="595959"))
        name(nm, f"Inputs!$B${i}")
    rules = [
        ("B4", "whole", "between", 1, 60, "N must be a whole number of years from 1 to 60."),
        ("B5", "decimal", "greaterThanOrEqual", 0, None, "B cannot be negative."),
        ("B6", "whole", "between", 1, 10, "SRS withdrawals can be spread over 1 to 10 years."),
        ("B7", "decimal", "greaterThanOrEqual", 0, None, "Other income cannot be negative."),
        ("B8", "decimal", "between", 0, 1, "Enter a share between 0% and 100%."),
        ("B9", "decimal", "greaterThan", 0, None, "C must be above 0."),
    ]
    for ref, kind, op, lo, hi, msg in rules:
        dv = DataValidation(type=kind, operator=op, formula1=str(lo),
                            formula2=None if hi is None else str(hi),
                            showErrorMessage=True, errorTitle="Invalid input", error=msg)
        inp.add_data_validation(dv)
        dv.add(ref)

    # ---------------- Tax schedule ----------------
    tx = wb.create_sheet("Tax_Schedule")
    for col, w in zip("ABCD", (16, 16, 12, 50)):
        tx.column_dimensions[col].width = w
    cell(tx, "A1", f"Resident income tax bands, {config.REGIME}", TITLE)
    cell(tx, "A2", f"Source: IRAS resident tax rates, loaded from {config.SCHEDULE_CSV}. Top band upper edge set to 1E+12 to mean 'no limit'.", Font(name=F, italic=True))
    for c, h in zip("ABC", ("Lower ($)", "Upper ($)", "Rate")):
        x = cell(tx, f"{c}4", h, BOLD, fill=HDR_FILL)
    schedule = load_schedule(config.SCHEDULE_CSV, config.REGIME)
    bands, lower = [], 0.0
    for upper, rate in schedule:
        bands.append((lower, TOP_EDGE if math.isinf(upper) else upper, rate))
        lower = upper
    for i, (lo, up, rt) in enumerate(bands, start=5):
        cell(tx, f"A{i}", lo, BLUE, USD)
        cell(tx, f"B{i}", up, BLUE, USD if up < TOP_EDGE else "0.0E+00")
        cell(tx, f"C{i}", rt, BLUE, "0.0%")
    last = 4 + len(bands)
    name("TaxLower", f"Tax_Schedule!$A$5:$A${last}")
    name("TaxUpper", f"Tax_Schedule!$B$5:$B${last}")
    name("TaxRate", f"Tax_Schedule!$C$5:$C${last}")
    cell(tx, "D4", "Check: tax on income", BOLD, fill=HDR_FILL)
    for i, inc in enumerate([50_000, 100_000, 500_000], start=5):
        cell(tx, f"D{i}", f'="Tax on ${inc:,}: $"&TEXT({TAX(str(inc))},"#,##0")')
    cell(tx, "D8", "Expected: $1,250 / $5,650 / $84,150", Font(name=F, color="595959"))

    # ---------------- Fig 1.1 exit rate ----------------
    f1 = wb.create_sheet("Fig1_1_ExitRate")
    widths(f1, 26, 14, 4)
    cell(f1, "A1", "Figure 1.1: average exit rate against balance at retirement", TITLE)
    cell(f1, "A2", "Uses K, I and other income from Inputs.", Font(name=F, italic=True))
    cell(f1, "A4", "Balance B ($)", BOLD, fill=HDR_FILL); cell(f1, "B4", "Exit rate", BOLD, fill=HDR_FILL)
    for i, b in enumerate(range(0, 4_000_001, 100_000), start=5):
        cell(f1, f"A{i}", b, BLUE, USD)
        cell(f1, f"B{i}", "=" + EXIT(f"A{i}", "In_Other"), BLACK, PCT2)
    end1 = 4 + 41
    ch = ScatterChart(); ch.title = "Average exit rate vs balance"; ch.style = 13
    ch.x_axis.title = "Balance at retirement ($)"; ch.y_axis.title = "Exit rate"
    ch.y_axis.number_format = "0%"; ch.x_axis.number_format = '$#,##0'
    s = Series(Reference(f1, min_col=2, min_row=5, max_row=end1), Reference(f1, min_col=1, min_row=5, max_row=end1), title="Exit rate")
    s.marker.symbol = "none"; ch.series.append(s); ch.legend = None
    ch.x_axis.delete = False; ch.y_axis.delete = False
    ch.height, ch.width = 9, 16
    f1.add_chart(ch, "D4")

    # ---------------- grid helpers ----------------
    def fixed_b_block(ws, top, title, n, b, other):
        """n, b, other: (value, is_link). Returns exit-rate cell ref."""
        cell(ws, f"A{top}", title, BOLD)
        cell(ws, f"A{top+1}", "Horizon N")
        cell(ws, f"B{top+1}", n[0], GREEN if n[1] else BLUE, "0")
        cell(ws, f"D{top+1}", "Balance B")
        cell(ws, f"F{top+1}", b[0], GREEN if b[1] else BLUE, USD)
        cell(ws, f"H{top+1}", "Other income")
        cell(ws, f"J{top+1}", other[0], GREEN if other[1] else BLUE, USD)
        cell(ws, f"L{top+1}", "Exit rate = breakeven tc")
        ew = f"$P${top+1}"
        cell(ws, f"P{top+1}", "=" + EXIT(f"$F${top+1}", f"$J${top+1}"), BOLD, PCT2, KEY_FILL)
        hdr = top + 2
        cell(ws, f"A{hdr}", "r (down) \\ tc (across)", BOLD, fill=HDR_FILL)
        for j, t in enumerate(TC, start=2):
            cell(ws, f"{L(j)}{hdr}", t, BLUE, PCT0, HDR_FILL)
        for i, r in enumerate(RS, start=hdr + 1):
            cell(ws, f"A{i}", r, BLUE, PCT0, HDR_FILL)
            for j in range(2, 2 + len(TC)):
                cl = L(j)
                cell(ws, f"{cl}{i}", f"=(1+$A{i})^$B${top+1}*({cl}${hdr}-{ew})", BLACK, ADV)
        scale(ws, f"B{hdr+1}:{L(1+len(TC))}{hdr+len(RS)}")
        return top + len(RS) + 4

    def sheet_header(ws, title, note):
        widths(ws, 22, 7.5, 30)
        cell(ws, "A1", title, TITLE)
        cell(ws, "A2", note, Font(name=F, italic=True))
        ws.freeze_panes = "B3"

    # Fig 1.2 base
    f2 = wb.create_sheet("Fig1_2_Base")
    sheet_header(f2, "Figure 1.2: base grid, SRS advantage per $1 of pre-tax income invested at year 0",
                 "Blue = SRS wins, red = outside SRS wins. N, B and other income link to Inputs.")
    fixed_b_block(f2, 4, "Base case", ("=In_N", 1), ("=In_B", 1), ("=In_Other", 1))

    # Fig 1.3 horizon
    f3 = wb.create_sheet("Fig1_3_Horizon")
    sheet_header(f3, "Figure 1.3: varying the horizon N", "B and other income link to Inputs. Breakeven does not move; only the size of the advantage does.")
    top = 4
    for n in SWEEP_N:
        top = fixed_b_block(f3, top, f"N = {n} years", (n, 0), ("=In_B", 1), ("=In_Other", 1))

    # Fig 1.4 balance
    f4 = wb.create_sheet("Fig1_4_Balance")
    sheet_header(f4, "Figure 1.4: varying the balance at retirement B", "N and other income link to Inputs. Breakeven moves right as B rises.")
    top = 4
    for b in SWEEP_B:
        top = fixed_b_block(f4, top, f"B = ${b/1e6:g}M", ("=In_N", 1), (b, 0), ("=In_Other", 1))

    # Fig 1.5 other income
    f5 = wb.create_sheet("Fig1_5_OtherInc")
    sheet_header(f5, "Figure 1.5: varying other retirement income", "N and B link to Inputs. Breakeven moves right as other income fills the low bands.")
    top = 4
    for y in SWEEP_OTHER:
        top = fixed_b_block(f5, top, f"Other income = ${y:,}", ("=In_N", 1), ("=In_B", 1), (y, 0))

    # Fig 1.6/1.7 variant
    f6 = wb.create_sheet("Fig1_6_7_Variant")
    widths(f6, 18, 7.5, 30)
    f6.column_dimensions["B"].width = 14; f6.column_dimensions["C"].width = 12
    cell(f6, "A1", "Figures 1.6-1.7: fixed annual contribution, SRS advantage per $1 contributed", TITLE)
    cell(f6, "A2", "The pot now depends on r, so the breakeven tc changes with r (column C). C and other income link to Inputs.", Font(name=F, italic=True))
    f6.freeze_panes = "D3"
    top = 4
    for n in SWEEP_N:
        cell(f6, f"A{top}", f"N = {n} years", BOLD)
        cell(f6, f"A{top+1}", "Horizon N"); cell(f6, f"B{top+1}", n, BLUE, "0")
        cell(f6, f"D{top+1}", "Contribution C"); cell(f6, f"G{top+1}", "=In_C", GREEN, USD)
        cell(f6, f"I{top+1}", "Other income"); cell(f6, f"L{top+1}", "=In_Other", GREEN, USD)
        hdr = top + 2
        for c, h in zip("ABC", ("r (down) \\ tc", "Pot at retirement ($)", "Breakeven tc")):
            cell(f6, f"{c}{hdr}", h, BOLD, fill=HDR_FILL)
        for j, t in enumerate(TC, start=4):
            cell(f6, f"{L(j)}{hdr}", t, BLUE, PCT0, HDR_FILL)
        for i, r in enumerate(RS, start=hdr + 1):
            cell(f6, f"A{i}", r, BLUE, PCT0, HDR_FILL)
            cell(f6, f"B{i}", f"=IF($A{i}=0,$G${top+1}*$B${top+1},$G${top+1}*((1+$A{i})^$B${top+1}-1)/$A{i})", BLACK, USD)
            cell(f6, f"C{i}", "=" + EXIT(f"$B{i}", f"$L${top+1}"), BOLD, PCT2, KEY_FILL)
            for j in range(4, 4 + len(TC)):
                cl = L(j)
                cell(f6, f"{cl}{i}", f"=$B{i}*({cl}${hdr}-$C{i})/($G${top+1}*$B${top+1})", BLACK, ADV)
        scale(f6, f"D{hdr+1}:{L(3+len(TC))}{hdr+len(RS)}")
        top = top + len(RS) + 4

    # Fig 1.2 curves
    fc = wb.create_sheet("Fig1_2_Curves")
    widths(fc, 26, 12, 8)
    cell(fc, "A1", "Indifference curves, fixed balance: tc needed for a given advantage at each return", TITLE)
    cell(fc, "A2", "tc = exit rate + A / (1 + r)^N. Points beyond tc = 24% fall off the chart (no one can save more than the top rate).", Font(name=F, italic=True))
    cell(fc, "A4", "Horizon N"); cell(fc, "B4", "=In_N", GREEN, "0")
    cell(fc, "A5", "Balance B"); cell(fc, "B5", "=In_B", GREEN, USD)
    cell(fc, "A6", "Other income"); cell(fc, "B6", "=In_Other", GREEN, USD)
    cell(fc, "A7", "Exit rate"); cell(fc, "B7", "=" + EXIT("$B$5", "$B$6"), BOLD, PCT2, KEY_FILL)
    cell(fc, "A9", "Advantage level A ($ per $1)", BOLD, fill=HDR_FILL)
    levels = list(CURVE_LEVELS)
    for j, a in enumerate(levels, start=2):
        cell(fc, f"{L(j)}9", a, BLUE, "0.00", HDR_FILL)
    cell(fc, "A10", "r (down) / tc needed (across)", BOLD, fill=HDR_FILL)
    for i, r in enumerate(RS_FINE, start=11):
        cell(fc, f"A{i}", r, BLUE, "0.0%", HDR_FILL)
        for j in range(2, 2 + len(levels)):
            cl = L(j)
            cell(fc, f"{cl}{i}", f"=$B$7+{cl}$9/(1+$A{i})^$B$4", BLACK, PCT2)
    endc = 10 + len(RS_FINE)
    ch = ScatterChart(); ch.title = "Indifference curves (fixed balance)"; ch.style = 13
    ch.x_axis.title = "Tax rate saved on contribution, tc"; ch.y_axis.title = "Annual return, r"
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 0, 0.24
    ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0.03, 0.12
    ch.x_axis.number_format = "0%"; ch.y_axis.number_format = "0%"
    ch.x_axis.delete = False; ch.y_axis.delete = False
    for j, a in enumerate(levels, start=2):
        s = Series(Reference(fc, min_col=1, min_row=11, max_row=endc),
                   Reference(fc, min_col=j, min_row=11, max_row=endc),
                   title=("Breakeven (A = 0)" if a == 0 else f"A = +${a:g}"))
        s.marker.symbol = "none"; s.smooth = False
        if a == 0: s.graphicalProperties.line.width = 38100
        ch.series.append(s)
    ch.height, ch.width = 10, 18
    fc.add_chart(ch, "H4")

    # Fig 1.7 curves
    f7 = wb.create_sheet("Fig1_7_Curves")
    widths(f7, 16, 13, 10)
    cell(f7, "A1", "Breakeven tc against return, fixed annual contribution (one curve per horizon)", TITLE)
    cell(f7, "A2", "SRS wins to the right of each curve. Curves lean right at high r: a higher return builds a bigger pot, taxed in higher bands at exit.", Font(name=F, italic=True))
    cell(f7, "A4", "Contribution C"); cell(f7, "B4", "=In_C", GREEN, USD)
    cell(f7, "A5", "Other income"); cell(f7, "B5", "=In_Other", GREEN, USD)
    NS = SWEEP_N
    cell(f7, "A7", "Horizon N", BOLD, fill=HDR_FILL)
    cell(f7, "A8", "r", BOLD, fill=HDR_FILL)
    for k, n in enumerate(NS):
        pc, ec = 2 + 2 * k, 3 + 2 * k
        cell(f7, f"{L(pc)}7", n, BLUE, "0", HDR_FILL); cell(f7, f"{L(ec)}7", f"={L(pc)}7", BLACK, "0", HDR_FILL)
        cell(f7, f"{L(pc)}8", "Pot ($)", BOLD, fill=HDR_FILL); cell(f7, f"{L(ec)}8", "Breakeven tc", BOLD, fill=HDR_FILL)
    for i, r in enumerate(RS_FINE, start=9):
        cell(f7, f"A{i}", r, BLUE, "0.0%", HDR_FILL)
        for k in range(len(NS)):
            pc, ec = L(2 + 2 * k), L(3 + 2 * k)
            cell(f7, f"{pc}{i}", f"=IF($A{i}=0,$B$4*{pc}$7,$B$4*((1+$A{i})^{pc}$7-1)/$A{i})", BLACK, USD)
            cell(f7, f"{ec}{i}", "=" + EXIT(f"{pc}{i}", "$B$5"), BLACK, PCT2)
    end7 = 8 + len(RS_FINE)
    ch = ScatterChart(); ch.title = "Breakeven tc vs return (fixed contribution)"; ch.style = 13
    ch.x_axis.title = "Breakeven tax rate on contribution, tc"; ch.y_axis.title = "Annual return, r"
    ch.x_axis.scaling.min = 0; ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0.03, 0.12
    ch.x_axis.number_format = "0%"; ch.y_axis.number_format = "0%"
    ch.x_axis.delete = False; ch.y_axis.delete = False
    for k, n in enumerate(NS):
        s = Series(Reference(f7, min_col=1, min_row=9, max_row=end7),
                   Reference(f7, min_col=3 + 2 * k, min_row=9, max_row=end7), title=f"N = {n}")
        s.marker.symbol = "none"; ch.series.append(s)
    ch.height, ch.width = 10, 18
    f7.add_chart(ch, "K4")

    # Breakeven summary
    bs = wb.create_sheet("Breakeven_Summary")
    widths(bs, 20, 14, 6)
    cell(bs, "A1", "Breakeven tc (= exit rate) by balance and other retirement income, fixed-balance mode", TITLE)
    cell(bs, "A2", "SRS wins whenever your tax rate saved on contribution is above the value shown. N does not affect it.", Font(name=F, italic=True))
    cell(bs, "A4", "Balance B ($) \\ other income", BOLD, fill=HDR_FILL)
    others = list(SUMMARY_OTHER)
    for j, y in enumerate(others, start=2):
        cell(bs, f"{L(j)}4", y, BLUE, USD, HDR_FILL)
    bal = list(range(250_000, 4_000_001, 250_000))
    for i, b in enumerate(bal, start=5):
        cell(bs, f"A{i}", b, BLUE, USD, HDR_FILL)
        for j in range(2, 2 + len(others)):
            cl = L(j)
            cell(bs, f"{cl}{i}", "=" + EXIT(f"$A{i}", f"{cl}$4"), BLACK, PCT2)
    endb = 4 + len(bal)
    ch = ScatterChart(); ch.title = "Breakeven tc vs balance"; ch.style = 13
    ch.x_axis.title = "Balance at retirement ($)"; ch.y_axis.title = "Breakeven tc"
    ch.x_axis.number_format = '$#,##0'; ch.y_axis.number_format = "0%"
    ch.x_axis.delete = False; ch.y_axis.delete = False
    for j, y in enumerate(others, start=2):
        s = Series(Reference(bs, min_col=j, min_row=5, max_row=endb),
                   Reference(bs, min_col=1, min_row=5, max_row=endb), title=f"Other income ${y/1000:g}k")
        s.marker.symbol = "circle"; s.marker.size = 4; ch.series.append(s)
    ch.height, ch.width = 10, 18
    bs.add_chart(ch, "G4")



if __name__ == "__main__":
    print("Saved", build_workbook())
