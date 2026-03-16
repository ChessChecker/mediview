import pandas as pd
import numpy as np

# --------------------------------------------------------------------------
# hello_medicare.py
# Purpose: Verify environment and demonstrate basic capitation calculation
# Concepts: RAF score, county benchmark, monthly capitation payment
# --------------------------------------------------------------------------

# In Phase 1 this will come from a SQL database instead
members = pd.DataFrame({
    'member_id':        ['M001', 'M002', 'M003'],
    'age':              [67,     74,     71    ],
    'sex':              ['F',    'M',    'F'   ],
    'raf_score':        [0.72,   2.14,   1.35  ],
    'county_benchmark': [1020,   1020,   1020  ]
})

# Core capitation formula: payment = benchmark x RAF
members['monthly_payment'] = (
    members['county_benchmark'] * members['raf_score']
).round(2)

members['annual_payment'] = members['monthly_payment'] * 12

# --------------------------------------------------------------------------
# Summary statistics — this is what a CFO actually wants to see
# --------------------------------------------------------------------------
print("=" * 55)
print("  MEMBER-LEVEL CAPITATION REPORT")
print("=" * 55)
print(members[['member_id', 'age', 'raf_score',
               'monthly_payment', 'annual_payment']].to_string(index=False))

print("\n" + "-" * 55)
print(f"  Members:               {len(members)}")
print(f"  Avg RAF score:         {members['raf_score'].mean():.2f}")
print(f"  Total monthly revenue: ${members['monthly_payment'].sum():>10,.2f}")
print(f"  Total annual revenue:  ${members['annual_payment'].sum():>10,.2f}")
print(f"  Revenue per member:    ${members['monthly_payment'].mean():>10,.2f} / mo")
print("=" * 55)
