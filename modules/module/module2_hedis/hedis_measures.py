import sqlite3
import pandas as pd
import os

# ------------------------------------------------------------------
# hedis_measures.py
# Purpose: Calculate four HEDIS measures from MediView database
# Measures: DAH, BCS, CBP, AWV
# Output: Measure rates for Star Ratings calculation
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)

# ------------------------------------------------------------------
# MEASURE 1: Diabetes Care — HbA1c Testing (DAH)
# Denominator: Diabetic members aged 66-75
# Numerator:   Those with CPT 83036 during measurement year
# ------------------------------------------------------------------

dah_denom = pd.read_sql('''
    SELECT COUNT(DISTINCT c.member_id) AS denominator
    FROM claims c
    JOIN members m ON c.member_id = m.member_id
    JOIN hcc_crosswalk h
        ON  c.icd10_primary     = h.icd10_code
        OR  c.icd10_secondary_1 = h.icd10_code
        OR  c.icd10_secondary_2 = h.icd10_code
        OR  c.icd10_secondary_3 = h.icd10_code
    WHERE h.hcc_v28 IN (18, 19)
    AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
              BETWEEN 66 AND 75
    AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
''', conn).iloc[0,0]

dah_numer = pd.read_sql('''
    SELECT COUNT(DISTINCT c.member_id) AS numerator
    FROM claims c
    JOIN members m ON c.member_id = m.member_id
    JOIN hcc_crosswalk h
        ON  c.icd10_primary     = h.icd10_code
        OR  c.icd10_secondary_1 = h.icd10_code
        OR  c.icd10_secondary_2 = h.icd10_code
        OR  c.icd10_secondary_3 = h.icd10_code
    WHERE h.hcc_v28 IN (18, 19)
    AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
              BETWEEN 66 AND 75
    AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
    AND   c.cpt_code = '83036'
''', conn).iloc[0,0]

# ------------------------------------------------------------------
# MEASURE 2: Breast Cancer Screening (BCS)
# Denominator: Female members aged 67-74
# Numerator:   Those with mammography claim (Z1231)
# ------------------------------------------------------------------

bcs_denom = pd.read_sql('''
    SELECT COUNT(DISTINCT m.member_id) AS denominator
    FROM members m
    WHERE m.sex = 'F'
    AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
              BETWEEN 67 AND 74
    AND   m.enrollment_start <= '2025-12-31'
    AND   m.enrollment_end   >= '2025-01-01'
''', conn).iloc[0,0]

bcs_numer = pd.read_sql('''
    SELECT COUNT(DISTINCT m.member_id) AS numerator
    FROM members m
    JOIN claims c ON m.member_id = c.member_id
    WHERE m.sex = 'F'
    AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
              BETWEEN 67 AND 74
    AND   m.enrollment_start <= '2025-12-31'
    AND   m.enrollment_end   >= '2025-01-01'
    AND   c.icd10_primary = 'Z1231'
    AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
''', conn).iloc[0,0]

# ------------------------------------------------------------------
# MEASURE 3: Controlling Blood Pressure (CBP)
# Denominator: Members aged 18-85 with hypertension diagnosis
#              who had at least one outpatient visit
# Numerator:   Those whose most recent BP reading is controlled
#              (systolic < 140 AND diastolic < 90)
# ------------------------------------------------------------------

cbp_denom = pd.read_sql('''
    SELECT COUNT(DISTINCT c.member_id) AS denominator
    FROM claims c
    JOIN members m ON c.member_id = m.member_id
    WHERE (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
              BETWEEN 18 AND 85
    AND   (c.icd10_primary     = 'I10'
           OR c.icd10_secondary_1 = 'I10'
           OR c.icd10_secondary_2 = 'I10')
    AND   c.place_of_service = '11'
    AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
''', conn).iloc[0,0]

cbp_numer = pd.read_sql('''
    SELECT COUNT(DISTINCT denom.member_id) AS numerator
    FROM (
        SELECT DISTINCT c.member_id
        FROM claims c
        JOIN members m ON c.member_id = m.member_id
        WHERE (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
                  BETWEEN 18 AND 85
        AND   (c.icd10_primary     = 'I10'
               OR c.icd10_secondary_1 = 'I10'
               OR c.icd10_secondary_2 = 'I10')
        AND   c.place_of_service = '11'
        AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
    ) denom
    JOIN (
        SELECT
            member_id,
            value_numeric_1 AS systolic,
            value_numeric_2 AS diastolic,
            ROW_NUMBER() OVER (
                PARTITION BY member_id
                ORDER BY reading_date DESC
            ) AS rn
        FROM clinical_values
        WHERE reading_type = 'BP'
        AND   reading_date BETWEEN '2025-01-01' AND '2025-12-31'
    ) latest_bp
        ON  denom.member_id  = latest_bp.member_id
        AND latest_bp.rn     = 1
        AND latest_bp.systolic  < 140
        AND latest_bp.diastolic < 90
''', conn).iloc[0,0]

# ------------------------------------------------------------------
# MEASURE 4: Annual Wellness Visit (AWV)
# Denominator: All enrolled members
# Numerator:   Those with G0438 or G0439 during measurement year
# ------------------------------------------------------------------

awv_denom = pd.read_sql('''
    SELECT COUNT(DISTINCT member_id) AS denominator
    FROM members
    WHERE enrollment_start <= '2025-01-01'
    AND   enrollment_end   >= '2025-12-31'
''', conn).iloc[0,0]

awv_numer = pd.read_sql('''
    SELECT COUNT(DISTINCT m.member_id) AS numerator
    FROM members m
    JOIN claims c ON m.member_id = c.member_id
    WHERE m.enrollment_start <= '2025-01-01'
    AND   m.enrollment_end   >= '2025-12-31'
    AND   (c.hcpcs_code = 'G0438' OR c.hcpcs_code = 'G0439'
           OR c.cpt_code = 'G0438')
    AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
''', conn).iloc[0,0]

conn.close()

# ------------------------------------------------------------------
# COMPILE RESULTS
# ------------------------------------------------------------------

def rate(numer, denom):
    if denom == 0:
        return 0.0
    return round(numer / denom * 100, 1)

measures = pd.DataFrame([
    {
        'measure_id':   'DAH',
        'measure_name': 'Diabetes Care — HbA1c Testing',
        'star_weight':  3,
        'denominator':  dah_denom,
        'numerator':    dah_numer,
        'rate_pct':     rate(dah_numer, dah_denom)
    },
    {
        'measure_id':   'BCS',
        'measure_name': 'Breast Cancer Screening',
        'star_weight':  1,
        'denominator':  bcs_denom,
        'numerator':    bcs_numer,
        'rate_pct':     rate(bcs_numer, bcs_denom)
    },
    {
        'measure_id':   'CBP',
        'measure_name': 'Controlling Blood Pressure',
        'star_weight':  3,
        'denominator':  cbp_denom,
        'numerator':    cbp_numer,
        'rate_pct':     rate(cbp_numer, cbp_denom)
    },
    {
        'measure_id':   'AWV',
        'measure_name': 'Annual Wellness Visit',
        'star_weight':  1,
        'denominator':  awv_denom,
        'numerator':    awv_numer,
        'rate_pct':     rate(awv_numer, awv_denom)
    }
])

# ------------------------------------------------------------------
# NCQA STAR CUT POINTS (approximate 2025 values)
# Maps performance rate to 1-5 Star score per measure
# ------------------------------------------------------------------

cut_points = {
    'DAH': [0,  72,  80,  86,  92],
    'BCS': [0,  52,  62,  70,  78],
    'CBP': [0,  55,  63,  70,  78],
    'AWV': [0,  40,  55,  68,  78],
}

def assign_stars(measure_id, rate_pct):
    cuts = cut_points[measure_id]
    if   rate_pct >= cuts[4]: return 5
    elif rate_pct >= cuts[3]: return 4
    elif rate_pct >= cuts[2]: return 3
    elif rate_pct >= cuts[1]: return 2
    else:                     return 1

measures['star_score'] = measures.apply(
    lambda r: assign_stars(r['measure_id'], r['rate_pct']), axis=1
)

measures['weighted_score'] = (
    measures['star_score'] * measures['star_weight']
)

# Overall Star Rating = sum of weighted scores / sum of weights
total_weighted = measures['weighted_score'].sum()
total_weight   = measures['star_weight'].sum()
overall_stars  = round(total_weighted / total_weight, 2)

# ------------------------------------------------------------------
# PRINT REPORT
# ------------------------------------------------------------------

print("=" * 65)
print("  HEDIS MEASURE REPORT — PLAN FL-001  |  PLAN YEAR 2025")
print("=" * 65)
print(f"\n  {'Measure':<35} {'Denom':>6} {'Numer':>6} "
      f"{'Rate':>6} {'Stars':>6} {'Wt':>4}")
print("  " + "-" * 63)

for _, row in measures.iterrows():
    print(f"  {row['measure_name']:<35} "
          f"{row['denominator']:>6} "
          f"{row['numerator']:>6} "
          f"{row['rate_pct']:>5.1f}% "
          f"{row['star_score']:>6} "
          f"{row['star_weight']:>4}x")

print("  " + "-" * 63)
print(f"\n  Overall Star Rating (weighted avg):  {overall_stars:.2f}")
print(f"  Total weighted score:                {total_weighted}")
print(f"  Total weight:                        {total_weight}")

# Quality bonus assessment
print("\n" + "-" * 65)
if overall_stars >= 4.0:
    print(f"  QUALITY BONUS STATUS: ELIGIBLE (4+ Stars)")
    print(f"  Estimated 5% benchmark bonus applies")
else:
    gap = 4.0 - overall_stars
    print(f"  QUALITY BONUS STATUS: NOT ELIGIBLE")
    print(f"  Gap to 4-Star threshold: {gap:.2f} Stars")
print("=" * 65)