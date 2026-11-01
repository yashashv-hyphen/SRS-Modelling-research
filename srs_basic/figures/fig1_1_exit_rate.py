"""Figure 1.1: average exit rate against SRS balance at retirement."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter

from srs_basic.config import REGIME, SCHEDULE_CSV
from srs_basic.exit_rate import avg_exit_rate
from srs_basic.tax import load_schedule

OUTPUT = Path("srs_basic/output")
K, OTHER, I = 10, 0, 0.5

# 1. Compute
schedule = load_schedule(SCHEDULE_CSV, REGIME)
balances = np.linspace(0, 4_000_000, 401)  # $0 to $4M in $10k steps
exit_rates = [avg_exit_rate(B, K, OTHER, I, schedule) for B in balances]

# 2. Save the numbers behind the figure
OUTPUT.mkdir(parents=True, exist_ok=True)
pd.DataFrame({"balance": balances, "avg_exit_rate": exit_rates}).to_csv(
    OUTPUT / "fig1_1_exit_rate.csv", index=False
)

# 3. Plot
fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(balances, exit_rates, linewidth=2)

# Mark the hand-checked values
for B, offset in [(400_000, (-62, 10)), (1_000_000, (8, -14)), (3_000_000, (8, -14))]:
    e = avg_exit_rate(B, K, OTHER, I, schedule)
    ax.plot(B, e, "o", color="black", markersize=5)
    ax.annotate(f"${B/1e6:g}M: {e:.2%}", (B, e), textcoords="offset points",
                xytext=offset, fontsize=9)

ax.set_xlabel("SRS balance at retirement")
ax.set_ylabel("Average exit rate (tax ÷ amount withdrawn)")
ax.set_title("Figure 1.1: SRS exit rate rises with balance\n"
             "10-year even withdrawal, no other income, YA2024 resident rates",
             fontsize=11)
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x/1e6:g}M"))
ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
ax.set_xlim(0, 4_000_000)
ax.set_ylim(bottom=0)
ax.grid(alpha=0.3)

fig.tight_layout()
fig.savefig(OUTPUT / "fig1_1_exit_rate.png", dpi=200)
print("Saved", OUTPUT / "fig1_1_exit_rate.png")