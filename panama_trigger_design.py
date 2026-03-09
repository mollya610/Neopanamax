#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insurance trigger design: low lake level (82 ft, 80 ft) vs 3-month total precipitation.
Uses DAILY lake level for triggers; 3-month precip from ERA5.
Checks: (1) how many days lake ≤ 82 / ≤ 80, (2) lag between low 3m precip and low lake.
"""

import xarray as xr
import numpy as np
import pandas as pd
import glob
import os
import matplotlib
if "DISPLAY" not in os.environ and os.environ.get("MPLBACKEND", "").lower() != "agg":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = "/Users/aficca/panama_trigger_design_figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

LAKE_CSV = "/Users/aficca/Downloads/Download_Gatun_Lake_Water_Level_History.csv"
MAX_FILES = 1200
ERA5_DIR = "/Users/aficca/Documents/era5_panama"

# Trigger thresholds (feet) – daily lake level
LAKE_TRIGGER_82_FT = 82.0
LAKE_TRIGGER_80_FT = 80.0

# 3-month precip threshold (mm) – e.g. trigger when 3m total ≤ this
PRECIP_3M_THRESHOLD_MM = 200.0  # change to test 200, 250, 300, etc.

# =====================================
# DAILY LAKE LEVEL – trigger counts
# =====================================

lake = pd.read_csv(LAKE_CSV)
lake["date"] = pd.to_datetime(lake["DATE_LOG"])
level_col = [c for c in lake.columns if "GATUN" in c.upper() or "LEVEL" in c.upper()][0]
lake = lake[["date", level_col]].rename(columns={level_col: "level_ft"})
lake = lake.set_index("date").sort_index()

# Daily triggers
below_82 = (lake["level_ft"] <= LAKE_TRIGGER_82_FT)
below_80 = (lake["level_ft"] <= LAKE_TRIGGER_80_FT)

n_days_82 = below_82.sum()
n_days_80 = below_80.sum()
print("Daily lake level triggers (full record):")
print(f"  Days with level ≤ {LAKE_TRIGGER_82_FT} ft: {int(n_days_82)}")
print(f"  Days with level ≤ {LAKE_TRIGGER_80_FT} ft: {int(n_days_80)}")

# Distinct spells (consecutive runs of days below threshold)
def count_spells(series):
    s = series.astype(int)
    diff = s.diff()
    # spell starts where we go from 0 to 1
    starts = (diff == 1).sum()
    if s.iloc[0] == 1:
        starts += 1
    return int(starts)

spells_82 = count_spells(below_82)
spells_80 = count_spells(below_80)
print(f"  Spells (episodes) ≤ {LAKE_TRIGGER_82_FT} ft: {spells_82}")
print(f"  Spells (episodes) ≤ {LAKE_TRIGGER_80_FT} ft: {spells_80}")

# =====================================
# 3-MONTH TOTAL PRECIP (ERA5, monthly)
# =====================================

monthly_files = sorted(glob.glob(os.path.join(ERA5_DIR, "*.nc")))
if len(monthly_files) > MAX_FILES:
    monthly_files = monthly_files[-MAX_FILES:]

ds = xr.open_mfdataset(
    monthly_files,
    combine="by_coords",
    parallel=False,
    chunks={"time": 1000},
    join="outer",
)
if "valid_time" in ds:
    ds = ds.rename({"valid_time": "time"})

rain = ds["tp"] * 1000
rain_mean = rain.mean(dim=["latitude", "longitude"])
monthly_rain = rain_mean.resample(time="1ME").sum()
rain_series = monthly_rain.to_series().dropna()
ds.close()

# 3-month total = rolling sum of last 3 months
precip_3m = rain_series.rolling(3, min_periods=3).sum()
precip_3m.name = "precip_3m_mm"

# =====================================
# MONTHLY LAKE SUMMARY (from daily, month-end to match ERA5)
# =====================================
# For each month: min level, and whether any day was ≤ 82 / ≤ 80

lake_monthly = lake.resample("ME").agg(
    min_level_ft=("level_ft", "min"),
    any_below_82=("level_ft", lambda x: (x <= LAKE_TRIGGER_82_FT).any()),
    any_below_80=("level_ft", lambda x: (x <= LAKE_TRIGGER_80_FT).any()),
)

# Align: inner join on month-end so we have both precip and lake
df = pd.DataFrame({"precip_3m_mm": precip_3m}).join(lake_monthly, how="inner")
df = df.dropna(subset=["precip_3m_mm", "min_level_ft"])
df["any_below_82"] = df["any_below_82"].fillna(False)
df["any_below_80"] = df["any_below_80"].fillna(False)
print(f"\nAligned monthly data: {len(df)} months from {df.index.min()} to {df.index.max()}")

# =====================================
# LAG: When 3-month precip is low, does lake go low 0 / 3 / 6 months later?
# =====================================
# "Low precip" = 3m total ≤ PRECIP_3M_THRESHOLD_MM

low_precip = df["precip_3m_mm"] <= PRECIP_3M_THRESHOLD_MM
n_low_precip = low_precip.sum()
print(f"\n3-month precip threshold: ≤ {PRECIP_3M_THRESHOLD_MM} mm")
print(f"  Months with 3m precip ≤ {PRECIP_3M_THRESHOLD_MM} mm: {int(n_low_precip)}")

# Lag 0: in the same month (low precip month, did lake trigger that month?)
# Lag 3: 3 months after the low-precip month, did lake trigger?
# Lag 6: 6 months after the low-precip month, did lake trigger?

def count_triggers_at_lag(low_precip_series, trigger_series, lag_months):
    """Months where precip was low and trigger happened `lag_months` later."""
    if lag_months == 0:
        return (low_precip_series & trigger_series).sum()
    # trigger_series shifted back: trigger at t corresponds to precip at t-lag
    trigger_lag = trigger_series.shift(-lag_months)
    return (low_precip_series & trigger_lag).sum()

results = []
for lag in [0, 3, 6]:
    n_82 = count_triggers_at_lag(low_precip, df["any_below_82"], lag)
    n_80 = count_triggers_at_lag(low_precip, df["any_below_80"], lag)
    pct_82 = 100 * n_82 / n_low_precip if n_low_precip else 0
    pct_80 = 100 * n_80 / n_low_precip if n_low_precip else 0
    results.append({"lag_months": lag, "lake_leq_82_count": n_82, "lake_leq_80_count": n_80, "pct_82": pct_82, "pct_80": pct_80})

results_df = pd.DataFrame(results)
print("\nWhen 3-month precip ≤ {} mm:".format(PRECIP_3M_THRESHOLD_MM))
print("  Lag 0 mo: lake ≤ 82 ft in same month: {} times ({:.1f}% of low-precip months)".format(int(results_df.iloc[0]["lake_leq_82_count"]), results_df.iloc[0]["pct_82"]))
print("  Lag 3 mo: lake ≤ 82 ft 3 months later: {} times ({:.1f}%)".format(int(results_df.iloc[1]["lake_leq_82_count"]), results_df.iloc[1]["pct_82"]))
print("  Lag 6 mo: lake ≤ 82 ft 6 months later: {} times ({:.1f}%)".format(int(results_df.iloc[2]["lake_leq_82_count"]), results_df.iloc[2]["pct_82"]))
print("  (Same for ≤ 80 ft: lag0={}, lag3={}, lag6={})".format(int(results_df.iloc[0]["lake_leq_80_count"]), int(results_df.iloc[1]["lake_leq_80_count"]), int(results_df.iloc[2]["lake_leq_80_count"])))

results_df.to_csv(os.path.join(OUTPUT_DIR, "trigger_lag_counts.csv"), index=False)

# =====================================
# REVERSE: When lake ≤ 82 ft (or ≤ 80), what was 3m precip at lag 0, 3, 6 months before?
# =====================================

lake_trigger_82_months = df.index[df["any_below_82"]]
lake_trigger_80_months = df.index[df["any_below_80"]]

def precip_at_lag_before(trigger_dates, precip_series, lag_months):
    # For each trigger month t, precip at t - lag
    vals = []
    for t in trigger_dates:
        t_prev = t - pd.DateOffset(months=lag_months)
        if t_prev in precip_series.index:
            vals.append(precip_series.loc[t_prev])
    return np.array(vals)

print("\nWhen lake level ≤ 82 ft (that month), 3-month precip BEFORE that:")
for lag in [0, 3, 6]:
    v = precip_at_lag_before(lake_trigger_82_months, df["precip_3m_mm"], lag)
    if len(v):
        print("  {} months before: mean 3m precip = {:.1f} mm, min = {:.1f}, max = {:.1f}".format(lag, v.mean(), v.min(), v.max()))

# =====================================
# SUMMARY TABLE: multiple precip thresholds
# =====================================

thresholds_mm = [150, 200, 250, 300, 350]
table = []
for thresh in thresholds_mm:
    low = df["precip_3m_mm"] <= thresh
    n_low = low.sum()
    row = {"precip_3m_threshold_mm": thresh, "n_months_low_precip": int(n_low)}
    for lag in [0, 3, 6]:
        n82 = count_triggers_at_lag(low, df["any_below_82"], lag)
        n80 = count_triggers_at_lag(low, df["any_below_80"], lag)
        row["lag{}_lake_leq82".format(lag)] = int(n82)
        row["lag{}_lake_leq80".format(lag)] = int(n80)
    table.append(row)

threshold_table = pd.DataFrame(table)
threshold_table.to_csv(os.path.join(OUTPUT_DIR, "trigger_by_precip_threshold.csv"), index=False)
print("\nSaved trigger_by_precip_threshold.csv (thresholds 150–350 mm, lags 0,3,6)")

# =====================================
# MATRIX: "When one happens, does the other follow?" (lag 0, 3, 6)
# =====================================
# Direction 1: When PRECIP is low (3m ≤ threshold) → does LAKE follow (0, 3, 6 mo later)?
# Direction 2: When LAKE is low (≤82 or ≤80 ft) → does PRECIP follow (0, 3, 6 mo later)?

def count_B_follows_A(trigger_A, trigger_B, lag_months):
    """Count months where A happens and B happens lag_months later (B follows A)."""
    if lag_months == 0:
        return (trigger_A & trigger_B).sum()
    B_later = trigger_B.shift(-lag_months)
    return (trigger_A & B_later).sum()

thresholds_matrix = [200, 250, 300]
follow_rows = []

for thresh in thresholds_matrix:
    low_precip = df["precip_3m_mm"] <= thresh
    n_precip = int(low_precip.sum())
    n_lake82 = int(df["any_below_82"].sum())
    n_lake80 = int(df["any_below_80"].sum())

    # When PRECIP low → does LAKE follow (at 0, 3, 6 mo)?
    p_then_l82_0 = int(count_B_follows_A(low_precip, df["any_below_82"], 0))
    p_then_l82_3 = int(count_B_follows_A(low_precip, df["any_below_82"], 3))
    p_then_l82_6 = int(count_B_follows_A(low_precip, df["any_below_82"], 6))
    p_then_l80_0 = int(count_B_follows_A(low_precip, df["any_below_80"], 0))
    p_then_l80_3 = int(count_B_follows_A(low_precip, df["any_below_80"], 3))
    p_then_l80_6 = int(count_B_follows_A(low_precip, df["any_below_80"], 6))

    # When LAKE low → does PRECIP follow (at 0, 3, 6 mo)?
    l82_then_p_0 = int(count_B_follows_A(df["any_below_82"], low_precip, 0))
    l82_then_p_3 = int(count_B_follows_A(df["any_below_82"], low_precip, 3))
    l82_then_p_6 = int(count_B_follows_A(df["any_below_82"], low_precip, 6))
    l80_then_p_0 = int(count_B_follows_A(df["any_below_80"], low_precip, 0))
    l80_then_p_3 = int(count_B_follows_A(df["any_below_80"], low_precip, 3))
    l80_then_p_6 = int(count_B_follows_A(df["any_below_80"], low_precip, 6))

    follow_rows.append({
        "precip_threshold_mm": thresh,
        "n_months_low_precip": n_precip,
        "n_months_lake_leq82": n_lake82,
        "n_months_lake_leq80": n_lake80,
        "precip_then_lake82_lag0": p_then_l82_0,
        "precip_then_lake82_lag3": p_then_l82_3,
        "precip_then_lake82_lag6": p_then_l82_6,
        "precip_then_lake80_lag0": p_then_l80_0,
        "precip_then_lake80_lag3": p_then_l80_3,
        "precip_then_lake80_lag6": p_then_l80_6,
        "lake82_then_precip_lag0": l82_then_p_0,
        "lake82_then_precip_lag3": l82_then_p_3,
        "lake82_then_precip_lag6": l82_then_p_6,
        "lake80_then_precip_lag0": l80_then_p_0,
        "lake80_then_precip_lag3": l80_then_p_3,
        "lake80_then_precip_lag6": l80_then_p_6,
    })

follow_df = pd.DataFrame(follow_rows)
follow_df.to_csv(os.path.join(OUTPUT_DIR, "matrix_one_then_other_follow_200_250_300.csv"), index=False)

print("\n--- MATRIX: When one happens, does the other follow? (lag 0, 3, 6 months) ---")
print("Precip threshold = 3-month total (mm). Lag = months until the other trigger.")
for _, r in follow_df.iterrows():
    print("\nThreshold {} mm:".format(int(r["precip_threshold_mm"])))
    print("  When PRECIP low (n={}) → lake ≤82 ft follows: lag0={}, lag3={}, lag6={}".format(
        int(r["n_months_low_precip"]), int(r["precip_then_lake82_lag0"]), int(r["precip_then_lake82_lag3"]), int(r["precip_then_lake82_lag6"])))
    print("  When PRECIP low → lake ≤80 ft follows: lag0={}, lag3={}, lag6={}".format(
        int(r["precip_then_lake80_lag0"]), int(r["precip_then_lake80_lag3"]), int(r["precip_then_lake80_lag6"])))
    print("  When LAKE ≤82 ft (n={}) → precip low follows: lag0={}, lag3={}, lag6={}".format(
        int(r["n_months_lake_leq82"]), int(r["lake82_then_precip_lag0"]), int(r["lake82_then_precip_lag3"]), int(r["lake82_then_precip_lag6"])))
    print("  When LAKE ≤80 ft (n={}) → precip low follows: lag0={}, lag3={}, lag6={}".format(
        int(r["n_months_lake_leq80"]), int(r["lake80_then_precip_lag0"]), int(r["lake80_then_precip_lag3"]), int(r["lake80_then_precip_lag6"])))
print("\nSaved matrix_one_then_other_follow_200_250_300.csv")

# Plot: two-panel matrix (precip→lake and lake→precip)
fig_m, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))

# Panel 1: When PRECIP low → Lake follows (rows=threshold, cols=lag 0,3,6 for ≤82 and ≤80)
M1 = follow_df[["precip_then_lake82_lag0", "precip_then_lake82_lag3", "precip_then_lake82_lag6",
                "precip_then_lake80_lag0", "precip_then_lake80_lag3", "precip_then_lake80_lag6"]].values
im1 = ax1.imshow(M1, cmap="Blues", aspect="auto", vmin=0)
ax1.set_xticks(range(6))
ax1.set_xticklabels(["Lake≤82\nlag0", "lag3", "lag6", "Lake≤80\nlag0", "lag3", "lag6"])
ax1.set_yticks(range(3))
ax1.set_yticklabels(["200 mm", "250 mm", "300 mm"])
ax1.set_ylabel("Precip threshold")
ax1.set_title("When PRECIP is low → does LAKE follow? (count of months)")
for i in range(3):
    for j in range(6):
        ax1.text(j, i, int(M1[i, j]), ha="center", va="center", color="black", fontsize=10)
fig_m.colorbar(im1, ax=ax1, label="Count", shrink=0.8)

# Panel 2: When LAKE low → Precip follows
M2 = follow_df[["lake82_then_precip_lag0", "lake82_then_precip_lag3", "lake82_then_precip_lag6",
                "lake80_then_precip_lag0", "lake80_then_precip_lag3", "lake80_then_precip_lag6"]].values
im2 = ax2.imshow(M2, cmap="Greens", aspect="auto", vmin=0)
ax2.set_xticks(range(6))
ax2.set_xticklabels(["Precip≤thresh\nlag0", "lag3", "lag6", "Precip≤thresh\nlag0", "lag3", "lag6"])
ax2.set_yticks(range(3))
ax2.set_yticklabels(["200 mm", "250 mm", "300 mm"])
ax2.set_ylabel("Precip threshold (for 'precip follows')")
ax2.set_title("When LAKE is low → does PRECIP follow? (count of months)")
for i in range(3):
    for j in range(6):
        ax2.text(j, i, int(M2[i, j]), ha="center", va="center", color="black", fontsize=10)
fig_m.colorbar(im2, ax=ax2, label="Count", shrink=0.8)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "matrix_one_then_other_follow_200_250_300.png"), dpi=150, bbox_inches="tight")
plt.show()

# =====================================
# PLOT: Trigger counts at 82 ft and 80 ft vs lag (for precip ≤ 200 mm)
# =====================================

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar([r - 0.2 for r in range(3)], results_df["lake_leq_82_count"], width=0.35, label=f"Lake ≤ {LAKE_TRIGGER_82_FT} ft", color="C0")
ax.bar([r + 0.2 for r in range(3)], results_df["lake_leq_80_count"], width=0.35, label=f"Lake ≤ {LAKE_TRIGGER_80_FT} ft", color="C1")
ax.set_xticks([0, 1, 2])
ax.set_xticklabels(["Lag 0 mo", "Lag 3 mo", "Lag 6 mo"])
ax.set_ylabel("Number of months")
ax.set_title("When 3-month precip ≤ {} mm: how often did lake trigger (0/3/6 mo later?)".format(PRECIP_3M_THRESHOLD_MM))
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "trigger_lag_bars.png"), dpi=150, bbox_inches="tight")
plt.show()

# =====================================
# PLOT: Distribution of 3m precip when lake ≤ 82 ft (lag 0, 3, 6 months before)
# =====================================

fig2, ax = plt.subplots(figsize=(7, 4))
for lag, label in [(0, "Same month"), (3, "3 mo before"), (6, "6 mo before")]:
    v = precip_at_lag_before(lake_trigger_82_months, df["precip_3m_mm"], lag)
    if len(v):
        ax.hist(v, bins=20, alpha=0.5, label="{} (n={}, mean={:.0f} mm)".format(label, len(v), v.mean()))
ax.axvline(PRECIP_3M_THRESHOLD_MM, color="red", linestyle="--", label="Precip threshold {} mm".format(PRECIP_3M_THRESHOLD_MM))
ax.set_xlabel("3-month total precip (mm)")
ax.set_ylabel("Count of months")
ax.set_title("When lake ≤ 82 ft: distribution of 3m precip (0, 3, 6 months before)")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "precip_when_lake_triggered_82ft.png"), dpi=150, bbox_inches="tight")
plt.show()

# =====================================
# PLOT: 3-month sum + daily lake level, with shaded periods (3m < 250 mm, lake < 82 ft)
# =====================================
# Clarification: trigger analysis (250 mm → lake ≤82 often follows) = threshold events.
# Pearson correlation is weak because it's over the full continuous series; the link is in the low tail.

PRECIP_THRESHOLD_PLOT_MM = 250.0
t0, t1 = df.index.min(), df.index.max()

fig3, ax1 = plt.subplots(figsize=(14, 6))

# Shade months where 3-month sum < 250 mm
low_precip_months = df.index[df["precip_3m_mm"] < PRECIP_THRESHOLD_PLOT_MM]
for i, m in enumerate(low_precip_months):
    start = pd.Timestamp(m.year, m.month, 1)
    end = m + pd.Timedelta(days=1)
    ax1.axvspan(start, end, color="steelblue", alpha=0.25)

# Shade days where daily lake < 82 ft (contiguous runs)
lake_sub = lake.loc[t0:t1]
full_below = (lake_sub["level_ft"] <= LAKE_TRIGGER_82_FT)
runs = full_below.ne(full_below.shift()).cumsum()
for _, grp in full_below.groupby(runs):
    if grp.any():
        s, e = grp.index.min(), grp.index.max()
        ax1.axvspan(s, e + pd.Timedelta(days=1), color="darkred", alpha=0.2)

# Plot 3-month precip (monthly) on left axis
ax1.plot(df.index, df["precip_3m_mm"], color="steelblue", linewidth=1.2)
ax1.axhline(PRECIP_THRESHOLD_PLOT_MM, color="steelblue", linestyle="--", linewidth=0.8, alpha=0.8)
ax1.set_ylabel("3-month total precip (mm)", color="steelblue")
ax1.tick_params(axis="y", labelcolor="steelblue")
ax1.set_xlim(t0, t1)
ax1.set_xlabel("Year")
ax1.grid(True, alpha=0.3)

# Plot daily lake level on right axis
ax2 = ax1.twinx()
ax2.plot(lake_sub.index, lake_sub["level_ft"], color="darkgreen", linewidth=0.4, alpha=0.8, label="Daily lake level (ft)")
ax2.axhline(LAKE_TRIGGER_82_FT, color="darkgreen", linestyle="--", linewidth=0.8, alpha=0.8)
ax2.set_ylabel("Lake Gatun level (ft)", color="darkgreen")
ax2.tick_params(axis="y", labelcolor="darkgreen")
ax2.set_ylim(76, 92)

# Legend: shading + lines
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
leg_handles = [
    Line2D([0], [0], color="steelblue", lw=2, label="3-month total precip"),
    Line2D([0], [0], color="darkgreen", lw=2, label="Daily lake level"),
    Patch(facecolor="steelblue", alpha=0.25, label="3m precip < 250 mm"),
    Patch(facecolor="darkred", alpha=0.2, label="Lake < 82 ft (daily)"),
]
ax1.legend(handles=leg_handles, loc="upper left", fontsize=8)

plt.title("3-month total precip and daily lake level — shaded: 3m precip < 250 mm, lake < 82 ft")
fig3.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "plot_3m_precip_and_lake_shaded_250_82.png"), dpi=150, bbox_inches="tight")
plt.show()

print("\nDone. Outputs in", OUTPUT_DIR)
