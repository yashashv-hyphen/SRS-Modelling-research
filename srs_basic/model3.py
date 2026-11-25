"""Model 3: how the tax regime moves Models 1 and 2.

Two parts:
  1. History. Replay Model 1 and Model 2 under each real resident schedule
     since YA2003 (from the schedule CSV).
  2. Projection. Calibrate the pace of past revisions (YA2007 onward) and
     project the schedule forward, then let the withdrawal years in Model 1
     and Model 2 use the projected schedule for that year.

Projection scenarios (shift = cumulative change in percentage points):
  frozen    today's schedule forever
  discrete  +avg_step every avg_interval years (lumpy, like real Budgets)
  smooth    +drift every year, same long-run total as discrete
  top       smooth drift, but only on bands starting at config.TOP_BAND_FROM
            or above (the YA2017 and YA2024 rises only touched those bands)
In every scenario the band edges and the 0% band never move: neither has
changed once since YA2003.
"""

import math

import numpy as np
import pandas as pd

from srs_basic import config
from srs_basic.model2 import level_payment, withdrawal_tax
from srs_basic.tax import load_schedule, tax

SCENARIOS = ("frozen", "discrete", "smooth", "top")


# ----------------------------------------------------------------- history
def regimes(csv_path=config.SCHEDULE_CSV):
    """Regime names in date order with their first YA: [(name, ya_from), ...]."""
    df = pd.read_csv(csv_path)
    first = df.groupby("regime")["ya_from"].min().sort_values()
    return [(name, int(ya)) for name, ya in first.items()]


def all_schedules(csv_path=config.SCHEDULE_CSV):
    """{regime name: schedule} for every regime in the CSV, in date order."""
    return {name: load_schedule(csv_path, name) for name, _ in regimes(csv_path)}


def calibration(csv_path=config.SCHEDULE_CSV, anchor_ya=config.ANCHOR_YA):
    """Pace of real revisions from anchor_ya onward, measured on the top rate.

    Returns revision YAs, average gap between revisions (years), average
    top-rate step per revision and the smooth drift per year (both decimals),
    and whether the band edges up to $80k have ever moved.
    """
    regs = [(n, ya) for n, ya in regimes(csv_path) if ya >= anchor_ya]
    scheds = all_schedules(csv_path)
    yas = [ya for _, ya in regs]
    tops = [scheds[n][-1][1] for n, _ in regs]
    gaps = np.diff(yas)
    steps = np.diff(tops)
    edges = {tuple(u for u, _ in s[:4]) for s in scheds.values()}
    return {
        "revision_yas": yas[1:],
        "avg_interval": float(gaps.mean()),
        "avg_step": float(steps.mean()),
        "drift_per_year": float((tops[-1] - tops[0]) / (yas[-1] - yas[0])),
        "low_edges_frozen": edges == {(20_000.0, 30_000.0, 40_000.0, 80_000.0)},
    }


# -------------------------------------------------------------- projection
def shift_schedule(schedule, shift, from_edge=0.0):
    """Add `shift` to the rate of every band that taxes income (rate > 0) and
    starts at or above `from_edge`. Band edges and the 0% band stay put."""
    out, lower = [], 0.0
    for upper, rate in schedule:
        moves = rate > 0 and lower >= from_edge
        out.append((upper, min(1.0, max(0.0, rate + shift)) if moves else rate))
        lower = upper
    return out


def scenario_shift(year, scenario, calib):
    """Cumulative rate shift `year` years from today under a scenario."""
    if scenario == "frozen" or year <= 0:
        return 0.0
    if scenario == "discrete":
        return math.floor(year / calib["avg_interval"] + 1e-9) * calib["avg_step"]
    if scenario in ("smooth", "top"):
        return calib["drift_per_year"] * year
    raise ValueError(f"Unknown scenario {scenario!r}; use one of {SCENARIOS}")


def projected_schedule(base, year, scenario, calib):
    """The schedule in force `year` years from today."""
    from_edge = config.TOP_BAND_FROM if scenario == "top" else 0.0
    return shift_schedule(base, scenario_shift(year, scenario, calib), from_edge)


def window_schedules(base, start_year, k, scenario, calib):
    """Schedules for the k withdrawal years that begin `start_year` years from today."""
    return [projected_schedule(base, start_year + t, scenario, calib) for t in range(k)]


# ------------------------------------------------- Model 1 with a moving regime
def avg_exit_rate_tv(B, other, I, schedules):
    """Model 1's average exit rate when each withdrawal year has its own
    schedule: even split B/k over k = len(schedules) years, no growth.
    With the same schedule every year this equals exit_rate.avg_exit_rate."""
    if B <= 0:
        return 0.0
    w = I * B / len(schedules)
    return sum(tax(other + w, s) - tax(other, s) for s in schedules) / B


def breakeven_tc(B, N, scenario, base, calib, k=config.K, other=config.OTHER, I=config.I):
    """Model 1 breakeven tax rate saved (= average exit rate) for a dollar put
    in today and withdrawn evenly over years N .. N+k-1 of the projection."""
    return avg_exit_rate_tv(B, other, I, window_schedules(base, N, k, scenario, calib))


# ------------------------------------------------- Model 2 with a moving regime
def solve_tv(r, other, B_grid, schedules, I=0.5, discount=True):
    """Model 2's dynamic program when the schedule changes during the window.

    schedules[t] is the schedule in withdrawal year t (t = 0 .. K-1), known in
    advance. Row n of each output = n years left, i.e. year t = K - n.
    The leftover balance is taxed with the last year, as in model2.solve.
    Returns V, W like model2.solve (ties broken towards the level payment).
    """
    K = len(schedules)
    B = np.asarray(B_grid, dtype=float)
    rows = np.arange(len(B))
    d = 1 / (1 + r) if discount else 1.0

    W_mat = B[:, None] - B[None, :] / (1 + r)
    feasible = W_mat >= -1e-9
    W_mat = np.where(feasible, np.clip(W_mat, 0, None), np.nan)
    W_safe = np.nan_to_num(W_mat)

    V = np.full((K + 1, len(B)), np.nan)
    W = np.full((K + 1, len(B)), np.nan)
    V[1] = withdrawal_tax(B, other, I, schedules[K - 1])
    W[1] = B
    for n in range(2, K + 1):
        T_mat = np.where(feasible, withdrawal_tax(W_safe, other, I, schedules[K - n]), np.inf)
        cost = T_mat + d * V[n - 1][None, :]
        best = cost.min(axis=1)
        ok = cost <= best[:, None] + 0.01
        dist = np.where(ok, np.abs(W_mat - level_payment(B, n, r)[:, None]), np.inf)
        V[n] = best
        W[n] = W_mat[rows, dist.argmin(axis=1)]
    return V, W


def run_tv(rule, B0, r, other, schedules, I=0.5, discount=True):
    """Follow rule(B, n_left) from B0 with year-specific schedules."""
    K = len(schedules)
    d = 1 / (1 + r) if discount else 1.0
    B, ws, taxes = float(B0), [], []
    for t in range(K):
        n = K - t
        w = B if n == 1 else min(max(float(rule(B, n)), 0.0), B)
        ws.append(w)
        taxes.append(float(withdrawal_tax(w, other, I, schedules[t])))
        B = (B - w) * (1 + r)
    total = sum(x * d ** t for t, x in enumerate(taxes))
    return {"withdrawals": np.array(ws), "taxes": np.array(taxes),
            "total_tax": total, "exit_rate": total / B0 if B0 > 0 else 0.0}


def optimal_path(W, B_grid, B0, r, other, schedules, I=0.5, discount=True):
    """Follow the policy W from solve_tv starting at B0 (inside B_grid)."""
    if not B_grid[0] <= B0 <= B_grid[-1]:
        raise ValueError(f"Starting balance {B0:,.0f} is outside the solved grid")
    return run_tv(lambda b, n: np.interp(b, B_grid, W[n]), B0, r, other, schedules, I, discount)


def level_path(B0, r, other, schedules, I=0.5, discount=True):
    """Level-payment rule (Model 2's optimum under a fixed schedule)."""
    return run_tv(lambda b, n: level_payment(b, n, r), B0, r, other, schedules, I, discount)


def jump_schedules(base, k, jump_year, step):
    """Window schedules with one revision of `step` landing in year `jump_year`."""
    return [shift_schedule(base, step if t >= jump_year else 0.0) for t in range(k)]
