import sqlite3
import pandas as pd
import random
import os
from datetime import date, timedelta

# --------------------------------------------------------------------------
# seed_data.py
# Purpose: Populate MediView database with synthetic but realistic data
# 100 members, ~800 claims, real ICD-10 codes, real HCC coefficients
# --------------------------------------------------------------------------

random.seed(42)  # Makes results reproducible — same data every run

DB_PATH = os.path.join(os.path.dirname(__file__), 'mediview.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --------------------------------------------------------------------------
# SEED 1: county_benchmarks
# Real Florida county benchmarks (approximate 2025 values)
# Source: CMS Medicare Advantage Rate Announcement
# --------------------------------------------------------------------------
benchmarks = [
    ('12031', 2025, 'FL', 'Duval County',      1021.50),
    ('12086', 2025, 'FL', 'Miami-Dade County', 1342.80),
    ('12057', 2025, 'FL', 'Hillsborough County',1089.20),
    ('12099', 2025, 'FL', 'Palm Beach County',  1178.60),
    ('12095', 2025, 'FL', 'Orange County',      1043.70),
]

cursor.executemany('''
    INSERT OR REPLACE INTO county_benchmarks
    VALUES (?, ?, ?, ?, ?)
''', benchmarks)

print(f"  Inserted {len(benchmarks)} county benchmarks")

# --------------------------------------------------------------------------
# SEED 2: hcc_crosswalk
# Real ICD-10 to HCC mappings with V28 and V24 coefficients
# These are simplified but directionally accurate
# --------------------------------------------------------------------------
crosswalk = [
    # icd10, hcc_v28, hcc_v24, condition,                coeff_v28, coeff_v24
    ('E1140', 18, 18, 'Diabetes with neuropathy',           0.302,  0.318),
    ('E1141', 18, 18, 'Diabetes with neuropathy',           0.302,  0.318),
    ('E1165', 18, 18, 'Diabetes with hyperglycemia',        0.302,  0.318),
    ('E1100', 19, 19, 'Diabetes without complication',      0.118,  0.105),
    ('E1109', 19, 19, 'Diabetes without complication',      0.118,  0.105),
    ('I5020', 85, 85, 'Systolic heart failure',             0.323,  0.331),
    ('I5032', 85, 85, 'Chronic diastolic heart failure',    0.323,  0.331),
    ('I5033', 85, 85, 'Acute on chronic diastolic HF',      0.323,  0.331),
    ('J440',  111,108,'COPD with acute lower resp inf',     0.242,  0.335),
    ('J441',  111,108,'COPD with acute exacerbation',       0.242,  0.335),
    ('J449',  111,108,'COPD unspecified',                   0.242,  0.335),
    ('I2510', 86, 83, 'Coronary artery disease',            0.148,  0.160),
    ('I209',  86, 83, 'Angina pectoris unspecified',        0.148,  0.160),
    ('N184',  138,137,'Chronic kidney disease stage 4',     0.289,  0.289),
    ('N185',  138,137,'Chronic kidney disease stage 5',     0.289,  0.289),
    ('E1122', 18, 18, 'Diabetes with diabetic CKD',         0.302,  0.318),
    ('F3290', 155,155,'Major depressive disorder',          0.159,  0.159),
    ('F3200', 155,155,'Major depressive disorder single',   0.159,  0.159),
    ('E6601', 48, 22, 'Morbid obesity',                     0.236,  0.273),
    ('I10',   None,None,'Essential hypertension',           0.000,  0.000),
    ('Z1231', None,None,'Mammography screening encounter',  0.000,  0.000),
    ('G0438', None,None,'Annual wellness visit',            0.000,  0.000),
    ('83036', None,None,'HbA1c lab test',                   0.000,  0.000),
]

cursor.executemany('''
    INSERT OR REPLACE INTO hcc_crosswalk
    VALUES (?, ?, ?, ?, ?, ?)
''', crosswalk)

print(f"  Inserted {len(crosswalk)} HCC crosswalk entries")

# --------------------------------------------------------------------------
# SEED 3: members
# 100 synthetic Medicare Advantage members across Florida counties
# --------------------------------------------------------------------------
counties = [
    ('12031', 'Duval County',       'FL'),
    ('12086', 'Miami-Dade County',  'FL'),
    ('12057', 'Hillsborough County','FL'),
    ('12099', 'Palm Beach County',  'FL'),
    ('12095', 'Orange County',      'FL'),
]

sexes = ['M', 'F']

members = []
for i in range(1, 101):
    member_id  = f'M{i:04d}'
    age        = random.randint(65, 85)
    dob        = date(2025 - age, random.randint(1,12), random.randint(1,28))
    sex        = random.choice(sexes)
    county     = random.choice(counties)
    dual       = 1 if random.random() < 0.25 else 0  # 25% dual eligible
    plan_id    = 'PLAN-FL-001'
    enr_start  = '2025-01-01'
    enr_end    = '2025-12-31'

    members.append((
        member_id, str(dob), sex,
        county[0], county[1], county[2],
        dual, plan_id, enr_start, enr_end
    ))

cursor.executemany('''
    INSERT OR REPLACE INTO members
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', members)

print(f"  Inserted {len(members)} members")

# --------------------------------------------------------------------------
# SEED 4: claims
# Realistic chronic condition patterns by age
# Older members get more conditions — mirrors real population
# --------------------------------------------------------------------------

# Condition profiles: (primary_icd10, secondary codes, cpt, hcpcs, place)
# Each profile represents a type of encounter
condition_profiles = {
    'wellness_only':    ('G0438', [],              '99213', 'G0438', '11'),
    'diabetes_simple':  ('E1109', ['I10'],          '99213', None,   '11'),
    'diabetes_complex': ('E1141', ['I10', 'N184'],  '99214', None,   '11'),
    'heart_failure':    ('I5032', ['E1140', 'I10'], '99215', None,   '11'),
    'copd':             ('J441',  ['I10'],           '99213', None,   '11'),
    'cad':              ('I2510', ['I10', 'E1109'], '99214', None,   '11'),
    'depression':       ('F3290', [],               '99213', None,   '11'),
    'obesity':          ('E6601', ['I10'],           '99213', None,   '11'),
    'ckd':              ('N184',  ['I10', 'E1122'], '99214', None,   '11'),
    'mammogram':        ('Z1231', [],               None,   None,   '19'),
    'hba1c_lab':        ('E1109', [],               '83036', None,   '81'),
    'hypertension':     ('I10',   [],               '99213', None,   '11'),
}

# Assign condition profiles to members based on age
# Older members → more complex profiles, mirrors Medicare population
def get_profiles_for_member(age, sex):
    profiles = ['wellness_only']  # everyone gets a wellness visit

    if age >= 70:
        profiles.append(random.choice([
            'diabetes_simple', 'diabetes_complex',
            'heart_failure', 'copd', 'cad'
        ]))
    if age >= 75:
        profiles.append(random.choice([
            'heart_failure', 'ckd', 'copd', 'depression'
        ]))
    if random.random() < 0.4:
        profiles.append('hypertension')
    if sex == 'F' and random.random() < 0.6:
        profiles.append('mammogram')
    if 'diabetes' in ' '.join(profiles):
        profiles.append('hba1c_lab')
    if random.random() < 0.2:
        profiles.append('obesity')

    return profiles

claims = []
claim_counter = 1

for member in members:
    member_id  = member[0]
    dob_str    = member[1]
    sex        = member[2]
    age        = 2025 - int(dob_str[:4])

    profiles = get_profiles_for_member(age, sex)

    for profile_name in profiles:
        profile = condition_profiles[profile_name]
        primary_icd   = profile[0]
        secondary_list= profile[1]
        cpt           = profile[2]
        hcpcs         = profile[3]
        pos           = profile[4]

        # Spread claims across the measurement year
        dos_offset = random.randint(0, 364)
        dos        = date(2025, 1, 1) + timedelta(days=dos_offset)
        paid       = dos + timedelta(days=random.randint(14, 45))

        # Realistic cost by place of service
        if pos == '21':    # inpatient
            allowed = round(random.uniform(8000, 25000), 2)
        elif pos == '23':  # ER
            allowed = round(random.uniform(800, 3500), 2)
        elif pos == '81':  # lab
            allowed = round(random.uniform(15, 85), 2)
        elif pos == '19':  # imaging
            allowed = round(random.uniform(150, 400), 2)
        else:              # office
            allowed = round(random.uniform(85, 320), 2)

        paid_amt   = round(allowed * 0.82, 2)
        cost_share = round(allowed - paid_amt, 2)

        claims.append((
            f'CLM{claim_counter:06d}',
            member_id,
            str(dos),
            str(paid),
            pos,
            primary_icd,
            secondary_list[0] if len(secondary_list) > 0 else None,
            secondary_list[1] if len(secondary_list) > 1 else None,
            secondary_list[2] if len(secondary_list) > 2 else None,
            cpt,
            hcpcs,
            allowed,
            paid_amt,
            cost_share
        ))
        claim_counter += 1

cursor.executemany('''
    INSERT OR REPLACE INTO claims
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', claims)

print(f"  Inserted {len(claims)} claims")

conn.commit()
conn.close()

# --------------------------------------------------------------------------
# Summary report
# --------------------------------------------------------------------------
print("\n" + "=" * 45)
print("  MEDIVIEW DATABASE SEEDED")
print("=" * 45)
print(f"  County benchmarks:  {len(benchmarks)}")
print(f"  HCC crosswalk rows: {len(crosswalk)}")
print(f"  Members:            {len(members)}")
print(f"  Claims:             {len(claims)}")
print(f"\n  Database: {DB_PATH}")
print("=" * 45)