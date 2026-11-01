"""The Excel workbook must start from the same inputs as the Python model,
and (where LibreOffice is installed) give the same numbers."""

import math
import shutil
import subprocess

import pytest
from openpyxl import load_workbook

from srs_basic import config
from srs_basic.make_excel import build_workbook
from srs_basic.model1 import grid
from srs_basic.tax import load_schedule

S = load_schedule(config.SCHEDULE_CSV, config.REGIME)


@pytest.fixture(scope="module")
def workbook_path(tmp_path_factory):
    return build_workbook(tmp_path_factory.mktemp("xl") / "model1.xlsx")


def test_inputs_match_config(workbook_path):
    ws = load_workbook(workbook_path)["Inputs"]
    expected = [config.N, config.B, config.K, config.OTHER, config.I, config.C]
    assert [ws[f"B{r}"].value for r in range(4, 10)] == expected


def test_tax_bands_match_csv(workbook_path):
    ws = load_workbook(workbook_path)["Tax_Schedule"]
    for row, (upper, rate) in enumerate(S, start=5):
        assert ws[f"C{row}"].value == pytest.approx(rate)
        if not math.isinf(upper):
            assert ws[f"B{row}"].value == upper


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice not installed")
def test_excel_numbers_match_python(workbook_path, tmp_path):
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx",
                    "--outdir", str(tmp_path), str(workbook_path)],
                   check=True, capture_output=True, timeout=180)
    wb = load_workbook(tmp_path / workbook_path.name, data_only=True)

    # Base grid: exit rate cell and one grid point (r = 4%, tc = 7%)
    base = wb["Fig1_2_Base"]
    _, _, ew, a = grid([0.07], [0.04], config.N, S, B=config.B,
                       k=config.K, other=config.OTHER, I=config.I)
    assert base["P5"].value == pytest.approx(ew[0, 0])
    assert base["I8"].value == pytest.approx(a[0, 0])

    # Fixed contribution, N = 40, r = 12%: breakeven column
    var = wb["Fig1_6_7_Variant"]
    _, _, ew, _ = grid([0.0], [0.12], 40, S, C=config.C,
                       k=config.K, other=config.OTHER, I=config.I)
    assert var["C58"].value == pytest.approx(ew[0, 0])

def test_inputs_have_validation(workbook_path):
    ws = load_workbook(workbook_path)["Inputs"]
    rules = {str(dv.sqref): dv for dv in ws.data_validations.dataValidation}
    k_rule = rules["B6"]
    assert (k_rule.type, k_rule.formula1, k_rule.formula2) == ("whole", "1", "10")
    assert rules["B9"].operator == "greaterThan"


def test_pot_formulas_handle_zero_return(workbook_path):
    wb = load_workbook(workbook_path)
    assert wb["Fig1_6_7_Variant"]["B7"].value.startswith("=IF($A7=0,")
    assert wb["Fig1_7_Curves"]["B9"].value.startswith("=IF($A9=0,")