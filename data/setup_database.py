import sqlite3
import pandas as pd
import os

# --------------------------------------------------------------------------
# setup_database.py
# Purpose: Create the MediView SQLite database and core tables
# This schema is the foundation for all four MediView modules
# --------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), 'mediview.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --------------------------------------------------------------------------
# TABLE 1: members
# Who is enrolled in the plan and when
# Used by: all four modules
# --------------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS members (
        member_id           TEXT PRIMARY KEY,
        date_of_birth       TEXT,
        sex                 TEXT,
        county_code         TEXT,
        county_name         TEXT,
        state               TEXT,
        medicaid_dual_flag  INTEGER,  -- 1 = dual eligible, 0 = not
        plan_id             TEXT,
        enrollment_start    TEXT,
        enrollment_end      TEXT
    )
''')

# --------------------------------------------------------------------------
# TABLE 2: claims
# Every service rendered to every member
# Used by: Module 1 (diagnosis codes), Module 2 (procedure codes),
#          Module 3 (allowed amounts)
# --------------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS claims (
        claim_id            TEXT PRIMARY KEY,
        member_id           TEXT,
        date_of_service     TEXT,
        date_paid           TEXT,
        place_of_service    TEXT,  -- 11=office, 21=inpatient, 23=ER
        icd10_primary       TEXT,
        icd10_secondary_1   TEXT,
        icd10_secondary_2   TEXT,
        icd10_secondary_3   TEXT,
        cpt_code            TEXT,
        hcpcs_code          TEXT,
        allowed_amount      REAL,
        paid_amount         REAL,
        member_cost_share   REAL,
        FOREIGN KEY (member_id) REFERENCES members(member_id)
    )
''')

# --------------------------------------------------------------------------
# TABLE 3: hcc_crosswalk
# Maps ICD-10 codes to HCC categories under V24 and V28 models
# Used by: Module 1 (RAF score calculation)
# --------------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS hcc_crosswalk (
        icd10_code          TEXT PRIMARY KEY,
        hcc_v28             INTEGER,
        hcc_v24             INTEGER,
        condition_category  TEXT,
        coefficient_v28     REAL,
        coefficient_v24     REAL
    )
''')

# --------------------------------------------------------------------------
# TABLE 4: county_benchmarks
# CMS published benchmark rates by county and plan year
# Used by: Module 1 (payment calculation), Module 3 (rate development)
# --------------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE IF NOT EXISTS county_benchmarks (
        county_code         TEXT,
        plan_year           INTEGER,
        state               TEXT,
        county_name         TEXT,
        benchmark_amount    REAL,
        PRIMARY KEY (county_code, plan_year)
    )
''')

conn.commit()

# --------------------------------------------------------------------------
# Verify: print all tables created
# --------------------------------------------------------------------------
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 45)
print("  MEDIVIEW DATABASE INITIALIZED")
print("=" * 45)
for table in tables:
    cursor.execute(f"PRAGMA table_info({table[0]})")
    columns = cursor.fetchall()
    print(f"\n  {table[0].upper()} ({len(columns)} columns)")
    for col in columns:
        print(f"    {col[1]:<22} {col[2]}")
print("\n" + "=" * 45)
print(f"  Database saved to: {DB_PATH}")
print("=" * 45)

conn.close()