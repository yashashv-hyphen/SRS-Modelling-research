"""Base case for the from-scratch SRS model. Change values here only."""

SCHEDULE_CSV = "data/sg_resident_tax_schedules_YA2003_present.csv"
REGIME = "YA2024-present"
OUTPUT_DIR = "srs_basic/output"

I = 0.5            # taxable share of each qualifying SRS withdrawal
K = 10             # years the balance is withdrawn over (even split)
OTHER = 0          # other taxable income in each retirement year ($)
N = 20             # years from contribution to retirement
B = 1_000_000      # SRS balance at retirement ($), fixed-pot mode
C = 15_300         # annual contribution ($), fixed-contribution mode

TC_RANGE = (0.0, 0.24)   # x axis: tax rate saved on contribution
R_RANGE = (0.03, 0.12)   # y axis: annual return
TC_STEPS = 241           # 0.1% steps
R_STEPS = 91             # 0.1% steps
