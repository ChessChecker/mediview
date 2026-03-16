import sqlite3
import pandas as pd
import numpy as np
import os

# ------------------------------------------------------------------
# rate_development.py
# Purpose: Project medical costs forward using trend factors,
#          build MA bid, compare to CMS county benchmarks
# Concepts: PMPM analysis, trend development, bid mechanics,
#           MLR, rebate calculation
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)

# ------------------------------------------------------------------
# STEP 1: Load base period PMPMs from claims data
# ------------------------------------------------------------------

base_pmpm = pd.read_sql('''
    SELECT
        place_of_service                    AS pos,
        COUNT(*)                            AS claim_count,
        SUM(allowed_amount)                 AS total_allowed,
        SUM(allowed_amount) / 1200.0        AS base_pmpm
    FROM claims
    WHERE date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY place_of_service
    ORDER BY base_pmpm DESC
''', conn)

# Load county benchmarks
benchmarks = pd.read_sql('''
    SELECT county_name, benchmark_amount
    FROM county_benchmarks
    WHERE plan_year = 2025
    ORDER BY benchmark_amount DESC
''', conn)

# Load member count for MLR calculation
member_count = pd.read_sql('''
    SELECT COUNT(*) AS members FROM members
''', conn).iloc[0, 0]

conn.close()

# ------------------------------------------------------------------
# STEP 2: Map service categories and apply trend factors
# Trend = (1 + unit_cost_trend) x (1 + utilization_trend) - 1
# ------------------------------------------------------------------

category_map = {
    '21': 'Inpatient',
    '23': 'Emergency Room',
    '11': 'Office Visits',
    '19': 'Imaging',
    '81': 'Lab'
}

# Trend assumptions — 2025 to 2026 projection
# Based on current market conditions and CMS rate environment
trend_assumptions = {
    'Inpatient':      {'unit_cost': 0.055, 'utilization': -0.020},
    'Emergency Room': {'unit_cost': 0.040, 'utilization':  0.010},
    'Office Visits':  {'unit_cost': 0.035, 'utilization':  0.005},
    'Imaging':        {'unit_cost': 0.025, 'utilization': -0.010},
    'Lab':            {'unit_cost': 0.015, 'utilization':  0.005},
}

base_pmpm['category'] = base_pmpm['pos'].map(category_map)

def combined_trend(unit_cost, utilization):
    return round((1 + unit_cost) * (1 + utilization) - 1, 4)

base_pmpm['unit_cost_trend']  = base_pmpm['category'].map(
    lambda c: trend_assumptions.get(c, {}).get('unit_cost', 0.03))
base_pmpm['util_trend']       = base_pmpm['category'].map(
    lambda c: trend_assumptions.get(c, {}).get('utilization', 0.0))
base_pmpm['combined_trend']   = base_pmpm.apply(
    lambda r: combined_trend(r['unit_cost_trend'], r['util_trend']),
    axis=1)
base_pmpm['projected_pmpm']   = (
    base_pmpm['base_pmpm'] * (1 + base_pmpm['combined_trend'])
).round(2)

# ------------------------------------------------------------------
# STEP 3: Build the bid
# Projected medical PMPM + admin loading + margin loading
# ------------------------------------------------------------------

total_medical_pmpm     = base_pmpm['projected_pmpm'].sum()

# Standard MA plan loading factors
admin_load_pct         = 0.085   # 8.5% administrative expense
margin_load_pct        = 0.030   # 3.0% profit margin
quality_invest_pct     = 0.015   # 1.5% quality improvement investment

admin_pmpm             = round(total_medical_pmpm * admin_load_pct,  2)
margin_pmpm            = round(total_medical_pmpm * margin_load_pct, 2)
quality_pmpm           = round(total_medical_pmpm * quality_invest_pct, 2)

total_bid_pmpm         = round(
    total_medical_pmpm + admin_pmpm + margin_pmpm + quality_pmpm, 2)

# MLR = medical costs / (medical costs + admin + margin)
# Must be >= 85% per federal law
mlr = round(total_medical_pmpm / total_bid_pmpm * 100, 1)

# ------------------------------------------------------------------
# STEP 4: Compare bid to county benchmarks
# If bid < benchmark: plan earns rebate (25% of difference)
# If bid > benchmark: members pay premium (bid - benchmark)
# ------------------------------------------------------------------

benchmarks['bid_pmpm']        = total_bid_pmpm
benchmarks['bid_vs_benchmark'] = (
    benchmarks['bid_pmpm'] - benchmarks['benchmark_amount']
).round(2)
benchmarks['rebate_pmpm']     = benchmarks.apply(
    lambda r: round((r['benchmark_amount'] - r['bid_pmpm']) * 0.25, 2)
    if r['bid_pmpm'] < r['benchmark_amount'] else 0, axis=1)
benchmarks['member_premium']  = benchmarks.apply(
    lambda r: round(r['bid_pmpm'] - r['benchmark_amount'], 2)
    if r['bid_pmpm'] > r['benchmark_amount'] else 0, axis=1)
benchmarks['status']          = benchmarks.apply(
    lambda r: 'Rebate' if r['bid_pmpm'] < r['benchmark_amount']
              else 'Premium', axis=1)

# ------------------------------------------------------------------
# STEP 5: Print rate development report
# ------------------------------------------------------------------

print("=" * 65)
print("  RATE DEVELOPMENT REPORT — PLAN FL-001  |  PY 2026 BID")
print("=" * 65)

print("\n  STEP 1 & 2 — BASE PERIOD PMPMs AND TREND PROJECTION")
print(f"  {'Category':<18} {'Base PMPM':>10} {'Trend':>7} "
      f"{'Proj PMPM':>10}")
print("  " + "-" * 48)

for _, row in base_pmpm.iterrows():
    print(f"  {row['category']:<18} "
          f"${row['base_pmpm']:>9.2f} "
          f"{row['combined_trend']*100:>6.2f}% "
          f"${row['projected_pmpm']:>9.2f}")

print("  " + "-" * 48)
print(f"  {'Total Medical':<18} "
      f"${base_pmpm['base_pmpm'].sum():>9.2f} "
      f"{'':>7} "
      f"${total_medical_pmpm:>9.2f}")

print(f"\n  STEP 3 — BID CONSTRUCTION")
print("  " + "-" * 48)
print(f"  {'Total medical PMPM':<30} ${total_medical_pmpm:>10.2f}")
print(f"  {'Admin loading (8.5%)':<30} ${admin_pmpm:>10.2f}")
print(f"  {'Quality investment (1.5%)':<30} ${quality_pmpm:>10.2f}")
print(f"  {'Profit margin (3.0%)':<30} ${margin_pmpm:>10.2f}")
print("  " + "-" * 48)
print(f"  {'TOTAL BID PMPM':<30} ${total_bid_pmpm:>10.2f}")
print(f"  {'Medical Loss Ratio':<30} {mlr:>10.1f}%")
print(f"  {'MLR Requirement':<30} {'>=85.0%':>10}")
print(f"  {'MLR Status':<30} "
      f"{'COMPLIANT' if mlr >= 85 else 'NON-COMPLIANT':>10}")

print(f"\n  STEP 4 — BID vs COUNTY BENCHMARK")
print("  " + "-" * 65)
print(f"  {'County':<25} {'Benchmark':>10} {'Bid':>10} "
      f"{'Difference':>11} {'Rebate PMPM':>12} {'Status':>8}")
print("  " + "-" * 65)

for _, row in benchmarks.iterrows():
    print(f"  {row['county_name']:<25} "
          f"${row['benchmark_amount']:>9.2f} "
          f"${row['bid_pmpm']:>9.2f} "
          f"${row['bid_vs_benchmark']:>+10.2f} "
          f"${row['rebate_pmpm']:>11.2f} "
          f"{row['status']:>8}")

print("=" * 65)