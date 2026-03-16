import sqlite3
import random
import os
from datetime import date, timedelta

# ------------------------------------------------------------------
# add_clinical_table.py
# Adds clinical values table for blood pressure readings
# Required for Controlling Blood Pressure HEDIS measure
# ------------------------------------------------------------------

random.seed(99)

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create clinical_values table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS clinical_values (
        reading_id        TEXT PRIMARY KEY,
        member_id         TEXT,
        reading_date      TEXT,
        reading_type      TEXT,   -- BP, BMI, HBA1C, etc.
        value_numeric_1   REAL,   -- systolic for BP, value for others
        value_numeric_2   REAL,   -- diastolic for BP, null for others
        data_source       TEXT,   -- EHR, claim, supplemental
        FOREIGN KEY (member_id) REFERENCES members(member_id)
    )
''')

# Load members to generate readings for
cursor.execute('SELECT member_id FROM members')
all_members = [row[0] for row in cursor.fetchall()]

# Load hypertensive members for targeted BP readings
cursor.execute('''
    SELECT DISTINCT c.member_id
    FROM claims c
    JOIN hcc_crosswalk h
        ON c.icd10_primary = h.icd10_code
        OR c.icd10_secondary_1 = h.icd10_code
    WHERE h.hcc_v28 IN (85, 18, 19)
''')
high_risk_members = [row[0] for row in cursor.fetchall()]

readings = []
reading_counter = 1

for member_id in all_members:
    # Everyone gets 1-2 BP readings during the year
    num_readings = random.randint(1, 2)

    for _ in range(num_readings):
        dos_offset  = random.randint(0, 364)
        reading_date = str(date(2025, 1, 1) + timedelta(days=dos_offset))

        # High risk members skew toward higher BP — realistic
        if member_id in high_risk_members:
            systolic  = random.randint(118, 158)
            diastolic = random.randint(72, 98)
        else:
            systolic  = random.randint(108, 145)
            diastolic = random.randint(65, 92)

        readings.append((
            f'BP{reading_counter:06d}',
            member_id,
            reading_date,
            'BP',
            float(systolic),
            float(diastolic),
            'EHR'
        ))
        reading_counter += 1

cursor.executemany('''
    INSERT OR REPLACE INTO clinical_values
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', readings)

conn.commit()

# Verify
cursor.execute('SELECT COUNT(*) FROM clinical_values')
count = cursor.fetchone()[0]

cursor.execute('''
    SELECT
        AVG(value_numeric_1) AS avg_systolic,
        AVG(value_numeric_2) AS avg_diastolic,
        SUM(CASE WHEN value_numeric_1 < 140
                 AND value_numeric_2 < 90
                 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS pct_controlled
    FROM clinical_values
    WHERE reading_type = 'BP'
''')
bp_stats = cursor.fetchone()

conn.close()

print("=" * 45)
print("  CLINICAL VALUES TABLE ADDED")
print("=" * 45)
print(f"  BP readings inserted:  {count}")
print(f"  Avg systolic:          {bp_stats[0]:.1f}")
print(f"  Avg diastolic:         {bp_stats[1]:.1f}")
print(f"  Pct BP controlled:     {bp_stats[2]:.1f}%")
print("=" * 45)