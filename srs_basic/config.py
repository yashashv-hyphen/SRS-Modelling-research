"""Base case for the from-scratch SRS model. Change values here only."""

SCHEDULE_CSV = "data/sg_resident_tax_schedules_YA2003_present.csv"
REGIME = "YA2024-present"
OUTPUT_DIR = "srs_basic/output"

# Model 1
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

# --- Model 2: withdrawal model ---
R2 = 0.05                    # base return during the withdrawal period
B_MAX = 4_000_000            # top of the balance grid ($)
DB = 5_000                  # balance grid step ($)
B_PLOT_MAX = 3_000_000       # top of the y axis in Model 2 figures ($)
YO_PANELS = (0, 20_000, 50_000, 100_000)   # other taxable income panels ($)
DISCOUNT = True              # True: minimise PV of tax; False: total nominal tax
DEEMED_SEPARATE = False      # True: leftover balance taxed in its own (11th) year

# --- Model 3: tax regime (history and projection) ---
ANCHOR_YA = 2007             # first YA of the settled schedule; revisions counted from here
PROJECTION_YEARS = 50        # how far ahead the projected schedules run
TOP_BAND_FROM = 160_000      # "top-band" scenario: only bands starting at or above this move
                             # (the YA2017 and YA2024 rises only touched bands above $160k)
JUMP_YEAR = 5                # Model 2 in-window jump: a revision lands this many years in
