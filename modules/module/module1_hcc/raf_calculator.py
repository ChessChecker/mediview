import sqlite3
import pandas as pd
import os

# --------------------------------------------------------------------------
# raf_calculator.py
# Purpose: Calculate RAF scores for all members using HCC V28 and V24 models
# Concepts: ICD-10 → HCC crosswalk, coefficient summation, demographic factors
#           V24 vs V28 comparison, capitation payment projection
# --------------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)
# --------------------------------------------------------------------------
# STEP 1: Load all the data we need from the database
# Three tables, each serving a specific purpose
# --------------------------------------------------------------------------

# Members — demographics drive the base RAF score
members_df = pd.read_sql('''
    SELECT
        m.member_id,
        m.sex,
        m.medicaid_dual_flag,
        m.county_code,
        m.county_name,
        CAST(strftime('%Y', 'now') - strftime('%Y', m.date_of_birth) AS INTEGER)
            AS age,
        cb.benchmark_amount
    FROM members m
    LEFT JOIN county_benchmarks cb
        ON m.county_code = cb.county_code
        AND cb.plan_year = 2025
''', conn)

# Claims — diagnosis codes are what trigger HCC assignments
claims_df = pd.read_sql('''
    SELECT
        member_id,
        icd10_primary,
        icd10_secondary_1,
        icd10_secondary_2,
        icd10_secondary_3
    FROM claims
    WHERE date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
''', conn)

# HCC crosswalk — maps ICD-10 codes to HCC coefficients
crosswalk_df = pd.read_sql('''
    SELECT
        icd10_code,
        hcc_v28,
        hcc_v24,
        condition_category,
        coefficient_v28,
        coefficient_v24
    FROM hcc_crosswalk
    WHERE hcc_v28 IS NOT NULL   -- only rows that actually map to an HCC
''', conn)

conn.close()

print(f"  Loaded {len(members_df)} members")
print(f"  Loaded {len(claims_df)} claims")
print(f"  Loaded {len(crosswalk_df)} HCC crosswalk entries")

# --------------------------------------------------------------------------
# STEP 2: Reshape claims into one row per member per diagnosis code
# A claim can have up to 4 diagnosis codes — we need each one as its own row
# so we can join against the crosswalk
# --------------------------------------------------------------------------

# Stack all four ICD-10 columns into a single column
# This is called "melting" — turning wide data into long data
diag_cols = [
    'icd10_primary',
    'icd10_secondary_1',
    'icd10_secondary_2',
    'icd10_secondary_3'
]

diagnoses_long = pd.melt(
    claims_df,
    id_vars=['member_id'],
    value_vars=diag_cols,
    value_name='icd10_code'
).dropna(subset=['icd10_code'])   # remove rows where the ICD-10 field was empty

# Deduplicate — if a member has the same ICD-10 code on 10 different claims,
# it still only counts ONCE for RAF purposes in a given year
diagnoses_unique = (
    diagnoses_long[['member_id', 'icd10_code']]
    .drop_duplicates()
)

print(f"\n  Unique member-diagnosis pairs: {len(diagnoses_unique)}")

# --------------------------------------------------------------------------
# STEP 3: Join diagnoses to HCC crosswalk
# This is the core of risk adjustment — matching codes to HCC coefficients
# --------------------------------------------------------------------------

hcc_hits = diagnoses_unique.merge(
    crosswalk_df,
    on='icd10_code',
    how='inner'   # inner join = only keep diagnoses that map to an HCC
)

print(f"  Unique member-diagnosis pairs:    {len(diagnoses_unique)}")
print(f"  Diagnoses that mapped to an HCC:  {len(hcc_hits)}")
print(f"  Unique members with any HCC:      {hcc_hits['member_id'].nunique()}")
# --------------------------------------------------------------------------
# STEP 4: Apply HCC hierarchy
# If a member has both HCC 19 (diabetes simple) AND HCC 18 (diabetes complex),
# only HCC 18 counts — the hierarchy drops the lower-severity category
# --------------------------------------------------------------------------

# For each member, keep only the highest-severity HCC within each
# condition group. We approximate this by keeping the highest coefficient.
hcc_hits_v28 = (
    hcc_hits
    .sort_values('coefficient_v28', ascending=False)
    .drop_duplicates(subset=['member_id', 'hcc_v28'])
)

hcc_hits_v24 = (
    hcc_hits
    .sort_values('coefficient_v24', ascending=False)
    .drop_duplicates(subset=['member_id', 'hcc_v24'])
)

# --------------------------------------------------------------------------
# STEP 5: Sum HCC coefficients per member
# This produces the "disease burden" portion of the RAF score
# --------------------------------------------------------------------------

hcc_score_v28 = (
    hcc_hits_v28
    .groupby('member_id')['coefficient_v28']
    .sum()
    .reset_index()
    .rename(columns={'coefficient_v28': 'hcc_score_v28'})
)

hcc_score_v24 = (
    hcc_hits_v24
    .groupby('member_id')['coefficient_v24']
    .sum()
    .reset_index()
    .rename(columns={'coefficient_v24': 'hcc_score_v24'})
)

# --------------------------------------------------------------------------
# STEP 6: Add demographic base scores
# Age, sex, and dual-eligible status each carry their own coefficient
# These are CMS-published values from the V28 demographic rate segments
# --------------------------------------------------------------------------

def demographic_score(age, sex, dual_flag):
    '''
    Simplified demographic RAF component.
    Real CMS tables have ~50 age/sex/dual combinations.
    These approximations are directionally accurate.
    '''
    # Age score — increases with age
    if   age < 70: age_score = 0.35
    elif age < 75: age_score = 0.45
    elif age < 80: age_score = 0.55
    else:          age_score = 0.65

    # Sex adjustment — males slightly higher average cost
    sex_adj = 0.02 if sex == 'M' else 0.00

    # Dual-eligible adjustment — Medicaid dual members have higher acuity
    dual_adj = 0.19 if dual_flag == 1 else 0.00

    return round(age_score + sex_adj + dual_adj, 4)

members_df['demo_score'] = members_df.apply(
    lambda r: demographic_score(r['age'], r['sex'], r['medicaid_dual_flag']),
    axis=1
)

# --------------------------------------------------------------------------
# STEP 7: Combine demographic scores + HCC scores = final RAF scores
# --------------------------------------------------------------------------

raf_df = (
    members_df
    .merge(hcc_score_v28, on='member_id', how='left')
    .merge(hcc_score_v24, on='member_id', how='left')
)

# Members with no HCC-mapping diagnoses get 0 for their disease score
raf_df['hcc_score_v28'] = raf_df['hcc_score_v28'].fillna(0)
raf_df['hcc_score_v24'] = raf_df['hcc_score_v24'].fillna(0)

# Final RAF = demographic base + HCC disease burden
raf_df['raf_v28'] = (raf_df['demo_score'] + raf_df['hcc_score_v28']).round(4)
raf_df['raf_v24'] = (raf_df['demo_score'] + raf_df['hcc_score_v24']).round(4)

# --------------------------------------------------------------------------
# STEP 8: Calculate capitation payments
# Payment = county benchmark x RAF score
# --------------------------------------------------------------------------

raf_df['payment_v28'] = (
    raf_df['benchmark_amount'] * raf_df['raf_v28']
).round(2)

raf_df['payment_v24'] = (
    raf_df['benchmark_amount'] * raf_df['raf_v24']
).round(2)

# V24 to V28 transition impact — the revenue change per member
raf_df['v28_v24_raf_delta']     = (raf_df['raf_v28']     - raf_df['raf_v24']).round(4)
raf_df['v28_v24_payment_delta'] = (raf_df['payment_v28'] - raf_df['payment_v24']).round(2)

# --------------------------------------------------------------------------
# STEP 9: Print results
# --------------------------------------------------------------------------

print("\n" + "=" * 65)
print("  RAF SCORE REPORT — PLAN FL-001  |  PLAN YEAR 2025")
print("=" * 65)

# Sample: top 10 members by V28 RAF score
top10 = (
    raf_df
    .sort_values('raf_v28', ascending=False)
    .head(10)[['member_id', 'age', 'county_name',
               'raf_v28', 'raf_v24',
               'payment_v28', 'payment_v24']]
)
print("\n  TOP 10 MEMBERS BY V28 RAF SCORE")
print(top10.to_string(index=False))

# Plan-level summary
print("\n" + "-" * 65)
print("  PLAN-LEVEL SUMMARY")
print("-" * 65)
print(f"  Total members:              {len(raf_df)}")
print(f"  Members with any HCC:       "
      f"{(raf_df['hcc_score_v28'] > 0).sum()}")
print(f"  Avg RAF score (V28):        {raf_df['raf_v28'].mean():.4f}")
print(f"  Avg RAF score (V24):        {raf_df['raf_v24'].mean():.4f}")
print(f"  RAF delta V28 vs V24:       "
      f"{(raf_df['raf_v28'].mean() - raf_df['raf_v24'].mean()):+.4f}")
print(f"\n  Avg monthly payment (V28):  "
      f"${raf_df['payment_v28'].mean():>10,.2f}")
print(f"  Avg monthly payment (V24):  "
      f"${raf_df['payment_v24'].mean():>10,.2f}")
print(f"\n  Total monthly revenue (V28):${raf_df['payment_v28'].sum():>10,.2f}")
print(f"  Total monthly revenue (V24):${raf_df['payment_v24'].sum():>10,.2f}")
print(f"  Monthly revenue impact:     "
      f"${raf_df['v28_v24_payment_delta'].sum():>+10,.2f}")
print(f"  Annual revenue impact:      "
      f"${raf_df['v28_v24_payment_delta'].sum() * 12:>+10,.2f}")

# County breakdown
print("\n" + "-" * 65)
print("  REVENUE BY COUNTY")
print("-" * 65)
county_summary = (
    raf_df
    .groupby('county_name')
    .agg(
        members        = ('member_id',    'count'),
        avg_raf_v28    = ('raf_v28',      'mean'),
        total_pmpm_v28 = ('payment_v28',  'sum'),
        benchmark      = ('benchmark_amount', 'mean')
    )
    .round(2)
    .sort_values('total_pmpm_v28', ascending=False)
)
print(county_summary.to_string())
print("=" * 65)




