import sqlite3
import random
import os
from datetime import date, timedelta

# ------------------------------------------------------------------
# add_inpatient_claims.py
# Purpose: Add inpatient and ER claims to make PMPM analysis
#          realistic for Medicare Advantage rate development
# In a real plan these come from facility claim feeds
# ------------------------------------------------------------------

random.seed(77)

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get current claim count so new IDs don't collide
cursor.execute('SELECT COUNT(*) FROM claims')
existing_claims = cursor.fetchone()[0]
claim_counter = existing_claims + 1

# Get all members
cursor.execute('SELECT member_id, date_of_birth FROM members')
members = cursor.fetchall()

# Get high-risk members — more likely to have inpatient stays
cursor.execute('''
    SELECT DISTINCT c.member_id
    FROM claims c
    JOIN hcc_crosswalk h
        ON c.icd10_primary = h.icd10_code
        OR c.icd10_secondary_1 = h.icd10_code
    WHERE h.hcc_v28 IN (85, 111, 138)
''')
high_risk = [row[0] for row in cursor.fetchall()]

new_claims = []

for member_id, dob in members:
    age = 2025 - int(dob[:4])

    # ----------------------------------------------------------
    # INPATIENT ADMISSIONS (POS 21)
    # Probability increases with age and risk
    # Average MA plan: ~250 inpatient admissions per 1000 members
    # ----------------------------------------------------------
    base_ip_prob = 0.25  # 25% of members have at least one admission
    if member_id in high_risk:
        base_ip_prob += 0.20
    if age >= 80:
        base_ip_prob += 0.15

    if random.random() < base_ip_prob:
        # Number of admissions this year
        num_admits = random.choices([1, 2, 3], weights=[70, 22, 8])[0]

        for _ in range(num_admits):
            dos_offset  = random.randint(0, 340)
            dos         = date(2025, 1, 1) + timedelta(days=dos_offset)
            paid_date   = dos + timedelta(days=random.randint(30, 60))
            los         = random.randint(2, 8)  # length of stay days

            # Inpatient cost driven by length of stay
            # Average MA inpatient cost ~$12,000-$18,000
            allowed = round(random.uniform(8000, 22000) +
                           (los * random.uniform(500, 1200)), 2)
            paid    = round(allowed * 0.85, 2)
            cost_share = round(allowed - paid, 2)

            # Primary diagnosis based on risk profile
            if member_id in high_risk:
                primary_icd = random.choice([
                    'I5032',  # CHF
                    'J441',   # COPD exacerbation
                    'E1141',  # Diabetes complication
                    'N184'    # CKD
                ])
            else:
                primary_icd = random.choice([
                    'I10',    # Hypertension
                    'E1109',  # Diabetes
                    'J449'    # COPD
                ])

            new_claims.append((
                f'CLM{claim_counter:06d}',
                member_id,
                str(dos),
                str(paid_date),
                '21',           # inpatient
                primary_icd,
                'I10',          # hypertension almost always secondary
                None,
                None,
                '99223',        # initial hospital care CPT
                None,
                allowed,
                paid,
                cost_share
            ))
            claim_counter += 1

    # ----------------------------------------------------------
    # EMERGENCY ROOM VISITS (POS 23)
    # Average MA plan: ~400 ER visits per 1000 members
    # ----------------------------------------------------------
    er_prob = 0.35
    if member_id in high_risk:
        er_prob += 0.15
    if age >= 75:
        er_prob += 0.10

    if random.random() < er_prob:
        num_er = random.choices([1, 2], weights=[75, 25])[0]

        for _ in range(num_er):
            dos_offset  = random.randint(0, 364)
            dos         = date(2025, 1, 1) + timedelta(days=dos_offset)
            paid_date   = dos + timedelta(days=random.randint(14, 30))

            # ER cost range $800-$4,500
            allowed    = round(random.uniform(800, 4500), 2)
            paid       = round(allowed * 0.80, 2)
            cost_share = round(allowed - paid, 2)

            primary_icd = random.choice([
                'I5032', 'J441', 'E1141',
                'I10',   'E1109', 'F3290'
            ])

            new_claims.append((
                f'CLM{claim_counter:06d}',
                member_id,
                str(dos),
                str(paid_date),
                '23',           # ER
                primary_icd,
                'I10',
                None,
                None,
                '99285',        # high complexity ER visit CPT
                None,
                allowed,
                paid,
                cost_share
            ))
            claim_counter += 1

cursor.executemany('''
    INSERT OR REPLACE INTO claims
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', new_claims)

conn.commit()

# ----------------------------------------------------------
# Verify updated PMPM
# ----------------------------------------------------------
cursor.execute('''
    SELECT
        place_of_service,
        COUNT(*)                     AS claim_count,
        SUM(allowed_amount)          AS total_allowed,
        SUM(allowed_amount) / 1200.0 AS pmpm
    FROM claims
    GROUP BY place_of_service
    ORDER BY pmpm DESC
''')

rows = cursor.fetchall()

print("=" * 55)
print("  UPDATED PMPM BY SERVICE CATEGORY")
print("=" * 55)
print(f"  {'POS':<6} {'Claims':>8} {'Total Allowed':>14} {'PMPM':>10}")
print("  " + "-" * 43)

total_pmpm = 0
for row in rows:
    pos_label = {
        '21': 'Inpatient',
        '23': 'ER',
        '11': 'Office',
        '19': 'Imaging',
        '81': 'Lab'
    }.get(row[0], row[0])

    print(f"  {pos_label:<10} {row[1]:>8,} "
          f"{row[2]:>14,.2f} "
          f"{row[3]:>10.2f}")
    total_pmpm += row[3]

print("  " + "-" * 43)
print(f"  {'TOTAL':<10} {'':>8} {'':>14} "
      f"{total_pmpm:>10.2f}")
print(f"\n  New claims added:  {len(new_claims)}")
print(f"  Total claims now:  {existing_claims + len(new_claims)}")
print("=" * 55)

conn.close()