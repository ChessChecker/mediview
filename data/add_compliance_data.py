import sqlite3
import os

# ------------------------------------------------------------------
# add_compliance_data.py
# Purpose: Add regulatory events table and populate with real
#          CMS actions affecting Medicare Advantage and Medicaid
# Source: Federal Register, CMS.gov, HPMS memos (public)
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create regulatory events table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS regulatory_events (
        event_id            TEXT PRIMARY KEY,
        program             TEXT,    -- MA, Medicaid, Part D, All
        rule_type           TEXT,    -- Final Rule, NPRM, ANPRM, Guidance
        title               TEXT,
        summary             TEXT,
        proposed_date       TEXT,
        final_date          TEXT,
        effective_date      TEXT,
        comment_deadline    TEXT,
        financial_impact    TEXT,    -- High, Medium, Low
        impact_direction    TEXT,    -- Positive, Negative, Neutral
        affected_module     TEXT,    -- Module 1,2,3,4 or Multiple
        action_required     TEXT,
        citation            TEXT
    )
''')

events = [
    # ----------------------------------------------------------
    # MEDICARE ADVANTAGE
    # ----------------------------------------------------------
    (
        'REG001',
        'Medicare Advantage',
        'Final Rule',
        'CMS-4201-F: MA and Part D Rule — HCC Model V28 Transition',
        'Phases in the new HCC risk adjustment model V28 over three '
        'years (2024-2026). V28 recalibrates coefficients based on '
        'ICD-10 coding patterns, reducing average RAF scores industry-'
        'wide. Plans with high proportions of soft-coded HCCs face '
        'the largest revenue reductions.',
        '2023-02-01',
        '2023-04-05',
        '2024-01-01',
        None,
        'High',
        'Negative',
        'Module 1',
        'Model dual V24/V28 RAF scores. Identify members where V28 '
        'coefficient is significantly lower than V24. Prioritize '
        'gap closure on conditions with largest coefficient deltas.',
        'CMS-4201-F, 88 FR 22120'
    ),
    (
        'REG002',
        'Medicare Advantage',
        'Final Rule',
        'RADV Final Rule: 100% Extrapolation Methodology',
        'CMS finalizes risk adjustment data validation audit '
        'methodology requiring extrapolation of audit findings '
        'across the full contract population. Plans must repay '
        '100% of projected overpayments identified in random '
        'sample audits. Eliminates the fee-for-service adjuster '
        'that previously reduced repayment amounts.',
        '2022-12-14',
        '2023-01-30',
        '2023-01-30',
        None,
        'High',
        'Negative',
        'Module 1',
        'Conduct immediate retrospective coding audit. Validate '
        'all HCC submissions against medical record documentation. '
        'Establish repayment reserve. Tighten prospective coding '
        'standards and vendor oversight.',
        'CMS-4199-F, 88 FR 6643'
    ),
    (
        'REG003',
        'Medicare Advantage',
        'Rate Announcement',
        '2026 Medicare Advantage Rate Announcement',
        'CMS publishes final 2026 county benchmark rates and '
        'risk score normalization factors. Average effective '
        'growth rate of 5.06% nationally. Florida county '
        'benchmarks reflect updated FFS expenditure data. '
        'Star Rating quality bonus payment percentages '
        'unchanged at 5% for 4-Star plans.',
        '2025-02-21',
        '2025-04-07',
        '2026-01-01',
        None,
        'High',
        'Positive',
        'Module 3',
        'Re-run bid model with 2026 county benchmarks. '
        'Identify counties where benchmark increase improves '
        'rebate position. Adjust supplemental benefit design '
        'to reflect updated rebate dollars available.',
        'CMS Rate Announcement 2026'
    ),
    (
        'REG004',
        'Medicare Advantage',
        'Final Rule',
        'CMS-4201-F: MA Marketing and Communications Rule',
        'Significant restrictions on MA marketing practices '
        'including third-party marketing organizations (TPMOs). '
        'Requires prominent display of plan limitations. '
        'Restricts use of Medicare name and logo in marketing. '
        'Mandates new enrollment verification requirements.',
        '2022-12-14',
        '2023-04-05',
        '2024-10-01',
        None,
        'Medium',
        'Neutral',
        'Module 4',
        'Review all marketing materials for compliance. '
        'Audit TPMO contracts and oversight procedures. '
        'Update enrollment verification workflows. '
        'Train sales staff on new restrictions.',
        'CMS-4201-F, 88 FR 22120'
    ),
    (
        'REG005',
        'Medicare Advantage',
        'Final Rule',
        'CMS-4201-F: Star Ratings Methodology Updates',
        'Updates Star Ratings methodology including new '
        'guardrails preventing significant year-over-year '
        'measure cut point changes. Adds Health Equity Index '
        'reward factor for plans serving high proportions of '
        'low-income and dual-eligible members. Triple-weighted '
        'measures unchanged.',
        '2023-02-01',
        '2023-04-05',
        '2024-01-01',
        None,
        'High',
        'Positive',
        'Module 2',
        'Model Health Equity Index impact on Star Rating. '
        'Identify dual-eligible population proportion. '
        'Assess eligibility for equity reward factor. '
        'Prioritize quality improvement in LIS member segments.',
        'CMS-4201-F, 88 FR 22120'
    ),
    (
        'REG006',
        'Part D',
        'Final Rule',
        'IRA 2022: Part D Redesign — $2,000 OOP Cap',
        'Inflation Reduction Act restructures Part D benefit '
        'design effective 2025. $2,000 annual out-of-pocket cap '
        'eliminates catastrophic coverage phase for most members. '
        'Manufacturer discount program replaces coverage gap '
        'discount. Plans assume greater liability in catastrophic '
        'phase. Significant impact on MA-PD bid construction.',
        '2022-08-16',
        '2022-08-16',
        '2025-01-01',
        None,
        'High',
        'Negative',
        'Module 3',
        'Remodel Part D bid with new benefit structure. '
        'Assess catastrophic phase liability exposure. '
        'Review formulary design for high-cost specialty drugs. '
        'Model member OOP impact for retention analysis.',
        'IRA 2022, PL 117-169'
    ),
    (
        'REG007',
        'Medicaid',
        'Final Rule',
        'CMS-2439-F: Medicaid Managed Care Access, '
        'Finance and Quality Rule',
        'Most comprehensive update to Medicaid managed care '
        'regulations in decades. Establishes new network '
        'adequacy standards, medical loss ratio requirements '
        'of 85% for Medicaid MCOs, directed payment program '
        'standards, and quality rating system for Medicaid '
        'managed care plans.',
        '2023-05-03',
        '2024-04-22',
        '2024-07-09',
        None,
        'High',
        'Neutral',
        'Module 4',
        'Assess MLR compliance under new 85% Medicaid '
        'requirement. Review network adequacy against new '
        'standards. Evaluate directed payment program '
        'participation. Prepare for Medicaid quality '
        'rating system reporting.',
        'CMS-2439-F, 89 FR 41002'
    ),
    (
        'REG008',
        'Medicaid',
        'Guidance',
        'Medicaid Unwinding: Post-PHE Enrollment Transitions',
        'Following end of COVID-19 public health emergency '
        'continuous enrollment requirement, states began '
        'Medicaid redeterminations in April 2023. Estimated '
        '20+ million disenrollments nationally through 2024. '
        'Significant impact on Medicaid MCO membership and '
        'revenue. Many disenrolled members transitioned to '
        'ACA marketplace or MA plans.',
        '2023-03-31',
        '2023-03-31',
        '2023-04-01',
        None,
        'High',
        'Negative',
        'Module 3',
        'Monitor dual-eligible membership for disenrollment '
        'patterns. Identify members losing Medicaid who may '
        'lose dual-eligible status and RAF demographic bonus. '
        'Assess revenue impact of dual-eligible RAF reduction.',
        'CIB 2023-03-31'
    ),
    (
        'REG009',
        'Medicare Advantage',
        'NPRM',
        'CMS-4208-P: MA and Part D Proposed Rule 2026',
        'Proposed rule covering plan year 2027 operations. '
        'Key proposals include additional prior authorization '
        'restrictions, expanded behavioral health network '
        'adequacy requirements, new supplemental benefit '
        'reporting requirements, and updates to the '
        'Star Ratings methodology.',
        '2025-11-20',
        None,
        '2027-01-01',
        '2026-01-20',
        'Medium',
        'Neutral',
        'Multiple',
        'Submit public comments by deadline. Model impact '
        'of prior authorization restrictions on utilization '
        'and medical PMPM. Assess behavioral health network '
        'adequacy gaps. Prepare supplemental benefit '
        'reporting infrastructure.',
        'CMS-4208-P'
    ),
    (
        'REG010',
        'Medicare Advantage',
        'Guidance',
        'HPMS Memo: 2026 Star Ratings Preview Methodology',
        'CMS releases preview of 2026 Star Ratings methodology '
        'including updated measure cut points and weights. '
        'Controlling Blood Pressure cut points adjusted '
        'upward reflecting improved national performance. '
        'Transition assistance provided for measures with '
        'significant cut point changes.',
        '2025-07-15',
        '2025-07-15',
        '2026-01-01',
        None,
        'Medium',
        'Negative',
        'Module 2',
        'Re-run Star Rating model with updated cut points. '
        'Identify measures where plan performance falls '
        'below new cut points. Prioritize quality improvement '
        'programs for affected measures before year end.',
        'HPMS Memo July 2025'
    ),
]

cursor.executemany('''
    INSERT OR REPLACE INTO regulatory_events VALUES
    (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
''', events)

conn.commit()

cursor.execute('SELECT COUNT(*) FROM regulatory_events')
count = cursor.fetchone()[0]

print("=" * 55)
print("  REGULATORY EVENTS TABLE POPULATED")
print("=" * 55)
print(f"  Events inserted:    {count}")
print(f"\n  Programs covered:")
cursor.execute('''
    SELECT program, COUNT(*) as events
    FROM regulatory_events
    GROUP BY program
    ORDER BY events DESC
''')
for row in cursor.fetchall():
    print(f"    {row[0]:<30} {row[1]} events")

print(f"\n  Impact levels:")
cursor.execute('''
    SELECT financial_impact, COUNT(*) as events
    FROM regulatory_events
    GROUP BY financial_impact
    ORDER BY events DESC
''')
for row in cursor.fetchall():
    print(f"    {row[0]:<30} {row[1]} events")

print("=" * 55)
conn.close()