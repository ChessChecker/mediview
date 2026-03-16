import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------
# dashboard_hedis.py
# MediView Module 2 — HEDIS & Star Ratings Dashboard
# Displays measure performance, Star scores, quality bonus impact
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'

@st.cache_data
def load_measures():
    conn = sqlite3.connect(DB_PATH)

    # All four measure calculations consolidated
    queries = {
        'DAH_denom': '''
            SELECT COUNT(DISTINCT c.member_id)
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
        ''',
        'DAH_numer': '''
            SELECT COUNT(DISTINCT c.member_id)
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
        ''',
        'BCS_denom': '''
            SELECT COUNT(DISTINCT m.member_id)
            FROM members m
            WHERE m.sex = 'F'
            AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
                      BETWEEN 67 AND 74
            AND   m.enrollment_start <= '2025-12-31'
            AND   m.enrollment_end   >= '2025-01-01'
        ''',
        'BCS_numer': '''
            SELECT COUNT(DISTINCT m.member_id)
            FROM members m
            JOIN claims c ON m.member_id = c.member_id
            WHERE m.sex = 'F'
            AND   (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
                      BETWEEN 67 AND 74
            AND   m.enrollment_start <= '2025-12-31'
            AND   m.enrollment_end   >= '2025-01-01'
            AND   c.icd10_primary = 'Z1231'
            AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
        ''',
        'CBP_denom': '''
            SELECT COUNT(DISTINCT c.member_id)
            FROM claims c
            JOIN members m ON c.member_id = m.member_id
            WHERE (strftime('%Y','now') - strftime('%Y', m.date_of_birth))
                      BETWEEN 18 AND 85
            AND   (c.icd10_primary     = 'I10'
                   OR c.icd10_secondary_1 = 'I10'
                   OR c.icd10_secondary_2 = 'I10')
            AND   c.place_of_service = '11'
            AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
        ''',
        'CBP_numer': '''
            SELECT COUNT(DISTINCT denom.member_id)
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
                SELECT member_id,
                       value_numeric_1 AS systolic,
                       value_numeric_2 AS diastolic,
                       ROW_NUMBER() OVER (
                           PARTITION BY member_id
                           ORDER BY reading_date DESC
                       ) AS rn
                FROM clinical_values
                WHERE reading_type = 'BP'
                AND   reading_date BETWEEN '2025-01-01' AND '2025-12-31'
            ) bp ON denom.member_id = bp.member_id
                AND bp.rn = 1
                AND bp.systolic  < 140
                AND bp.diastolic < 90
        ''',
        'AWV_denom': '''
            SELECT COUNT(DISTINCT member_id)
            FROM members
            WHERE enrollment_start <= '2025-01-01'
            AND   enrollment_end   >= '2025-12-31'
        ''',
        'AWV_numer': '''
            SELECT COUNT(DISTINCT m.member_id)
            FROM members m
            JOIN claims c ON m.member_id = c.member_id
            WHERE m.enrollment_start <= '2025-01-01'
            AND   m.enrollment_end   >= '2025-12-31'
            AND   (c.hcpcs_code = 'G0438'
                   OR c.hcpcs_code = 'G0439'
                   OR c.cpt_code  = 'G0438')
            AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
        '''
    }

    results = {}
    for key, sql in queries.items():
        results[key] = pd.read_sql(sql, conn).iloc[0, 0]

    conn.close()
    return results

# ------------------------------------------------------------------
# STAR RATING LOGIC
# ------------------------------------------------------------------

CUT_POINTS = {
    'DAH': [0, 72, 80, 86, 92],
    'BCS': [0, 52, 62, 70, 78],
    'CBP': [0, 55, 63, 70, 78],
    'AWV': [0, 40, 55, 68, 78],
}

NCQA_BENCHMARKS = {
    'DAH': 82.0,
    'BCS': 65.0,
    'CBP': 64.0,
    'AWV': 62.0,
}

def assign_stars(measure_id, rate):
    cuts = CUT_POINTS[measure_id]
    if   rate >= cuts[4]: return 5
    elif rate >= cuts[3]: return 4
    elif rate >= cuts[2]: return 3
    elif rate >= cuts[1]: return 2
    else:                 return 1

def star_color(stars):
    return {1:'#E24B4A', 2:'#EF9F27', 3:'#EF9F27',
            4:'#1A7A6E', 5:'#1A7A6E'}.get(stars, '#888')

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------

st.set_page_config(
    page_title="MediView — HEDIS & Stars",
    page_icon="⭐",
    layout="wide"
)

st.title("MediView — Module 2: HEDIS & Star Ratings")
st.caption("Plan FL-001  ·  Plan Year 2025  ·  Medicare Advantage")

# ------------------------------------------------------------------
# LOAD DATA AND BUILD MEASURES DATAFRAME
# ------------------------------------------------------------------

raw = load_measures()

def rate(n, d):
    return round(n / d * 100, 1) if d > 0 else 0.0

measures = pd.DataFrame([
    {'id':'DAH', 'name':'Diabetes Care — HbA1c Testing',
     'weight':3, 'denom':raw['DAH_denom'], 'numer':raw['DAH_numer'],
     'rate':rate(raw['DAH_numer'], raw['DAH_denom']),
     'benchmark':NCQA_BENCHMARKS['DAH']},
    {'id':'BCS', 'name':'Breast Cancer Screening',
     'weight':1, 'denom':raw['BCS_denom'], 'numer':raw['BCS_numer'],
     'rate':rate(raw['BCS_numer'], raw['BCS_denom']),
     'benchmark':NCQA_BENCHMARKS['BCS']},
    {'id':'CBP', 'name':'Controlling Blood Pressure',
     'weight':3, 'denom':raw['CBP_denom'], 'numer':raw['CBP_numer'],
     'rate':rate(raw['CBP_numer'], raw['CBP_denom']),
     'benchmark':NCQA_BENCHMARKS['CBP']},
    {'id':'AWV', 'name':'Annual Wellness Visit',
     'weight':1, 'denom':raw['AWV_denom'], 'numer':raw['AWV_numer'],
     'rate':rate(raw['AWV_numer'], raw['AWV_denom']),
     'benchmark':NCQA_BENCHMARKS['AWV']},
])

measures['stars']          = measures.apply(
    lambda r: assign_stars(r['id'], r['rate']), axis=1)
measures['weighted_score'] = measures['stars'] * measures['weight']
measures['gap_to_4star']   = measures.apply(
    lambda r: max(0, CUT_POINTS[r['id']][3] - r['rate']), axis=1)
measures['vs_benchmark']   = (
    measures['rate'] - measures['benchmark']).round(1)

total_stars  = round(
    measures['weighted_score'].sum() / measures['weight'].sum(), 2)
bonus_eligible = total_stars >= 4.0
avg_benchmark  = 1115.0
total_members  = 100

# ------------------------------------------------------------------
# ROW 1 — KEY METRICS
# ------------------------------------------------------------------

st.subheader("Star Ratings Summary")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Overall Star Rating",   f"{total_stars:.2f} ⭐")
c2.metric("Quality Bonus",
          "Eligible ✓" if bonus_eligible else "Not Eligible ✗",
          delta="5% benchmark bonus" if bonus_eligible else
                f"{4.0 - total_stars:.2f} Stars to threshold")
c3.metric("Est. Annual Bonus",
          f"${avg_benchmark * 0.05 * total_members * 12:,.0f}"
          if bonus_eligible else "$0",)
c4.metric("Measures Tracked",      f"{len(measures)}")
c5.metric("Measures at 4+ Stars",
          f"{(measures['stars'] >= 4).sum()} / {len(measures)}")

st.divider()

# ------------------------------------------------------------------
# ROW 2 — MEASURE PERFORMANCE vs BENCHMARK
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Measure Rates vs NCQA Benchmark")

    fig_rates = go.Figure()

    fig_rates.add_trace(go.Bar(
        name='Plan Rate',
        x=measures['id'],
        y=measures['rate'],
        marker_color=[star_color(s) for s in measures['stars']],
        text=measures['rate'].apply(lambda x: f'{x}%'),
        textposition='outside'
    ))

    fig_rates.add_trace(go.Scatter(
        name='NCQA Benchmark',
        x=measures['id'],
        y=measures['benchmark'],
        mode='markers',
        marker=dict(symbol='diamond', size=12, color='#534AB7'),
    ))

    fig_rates.add_trace(go.Scatter(
        name='4-Star Cut Point',
        x=measures['id'],
        y=[CUT_POINTS[m][3] for m in measures['id']],
        mode='lines+markers',
        line=dict(dash='dash', color='#1A7A6E', width=1.5),
        marker=dict(size=6)
    ))

    fig_rates.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.12),
        yaxis=dict(title='Rate (%)', range=[0, 110])
    )
    st.plotly_chart(fig_rates, width='stretch')

with col_right:
    st.subheader("Star Score by Measure")

    fig_stars = go.Figure()

    for _, row in measures.iterrows():
        fig_stars.add_trace(go.Bar(
            name=row['name'],
            x=[row['id']],
            y=[row['stars']],
            marker_color=star_color(row['stars']),
            text=f"{row['stars']}★  (weight {row['weight']}x)",
            textposition='outside',
            width=0.5
        ))

    fig_stars.add_hline(
        y=4.0,
        line_dash='dash',
        line_color='#1A7A6E',
        annotation_text='4-Star bonus threshold',
        annotation_position='right'
    )

    fig_stars.update_layout(
        height=380,
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(title='Star Score', range=[0, 6]),
        bargap=0.4
    )
    st.plotly_chart(fig_stars, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 3 — GAP TO 4-STAR + WEIGHTED STAR WATERFALL
# ------------------------------------------------------------------

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Gap to 4-Star Cut Point")

    gap_df = measures[measures['gap_to_4star'] > 0].copy()

    if len(gap_df) > 0:
        fig_gap = px.bar(
            gap_df,
            x='gap_to_4star',
            y='name',
            orientation='h',
            color='weight',
            color_continuous_scale='Reds',
            labels={'gap_to_4star':'Percentage Points Needed',
                    'name':'Measure',
                    'weight':'Star Weight'},
            text=gap_df['gap_to_4star'].apply(lambda x: f'{x:.1f} pts')
        )
        fig_gap.update_traces(textposition='outside')
        fig_gap.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_gap, width='stretch')
    else:
        st.success("All measures at or above 4-Star cut points.")

with col_right2:
    st.subheader("Performance vs NCQA Benchmark")

    fig_bench = px.bar(
        measures,
        x='id',
        y='vs_benchmark',
        color='vs_benchmark',
        color_continuous_scale='RdYlGn',
        labels={'id':'Measure', 'vs_benchmark':'vs Benchmark (pp)'},
        text=measures['vs_benchmark'].apply(
            lambda x: f'{x:+.1f}pp')
    )
    fig_bench.add_hline(y=0, line_dash='solid',
                        line_color='#888', line_width=1)
    fig_bench.update_traces(textposition='outside')
    fig_bench.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_bench, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 4 — QUALITY BONUS SIMULATOR
# ------------------------------------------------------------------

st.subheader("Quality Bonus Payment Simulator")
st.caption("Adjust measure rates to model the financial impact "
           "of quality improvement programs")

sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)

with sim_col1:
    sim_dah = st.slider("DAH rate (%)", 0, 100,
                        int(measures.loc[measures['id']=='DAH',
                                         'rate'].iloc[0]))
with sim_col2:
    sim_bcs = st.slider("BCS rate (%)", 0, 100,
                        int(measures.loc[measures['id']=='BCS',
                                         'rate'].iloc[0]))
with sim_col3:
    sim_cbp = st.slider("CBP rate (%)", 0, 100,
                        int(measures.loc[measures['id']=='CBP',
                                         'rate'].iloc[0]))
with sim_col4:
    sim_awv = st.slider("AWV rate (%)", 0, 100,
                        int(measures.loc[measures['id']=='AWV',
                                         'rate'].iloc[0]))

sim_rates = {'DAH': sim_dah, 'BCS': sim_bcs,
             'CBP': sim_cbp, 'AWV': sim_awv}

sim_stars = {m: assign_stars(m, r) for m, r in sim_rates.items()}
sim_weighted = sum(
    sim_stars[m] * measures.loc[measures['id']==m,
                                 'weight'].iloc[0]
    for m in sim_rates
)
sim_overall = round(
    sim_weighted / measures['weight'].sum(), 2)
sim_bonus   = sim_overall >= 4.0
sim_revenue = (avg_benchmark * 0.05 * total_members * 12
               if sim_bonus else 0)

r1, r2, r3 = st.columns(3)
r1.metric("Simulated Star Rating", f"{sim_overall:.2f} ⭐")
r2.metric("Bonus Status",
          "Eligible ✓" if sim_bonus else "Not Eligible ✗")
r3.metric("Estimated Annual Bonus", f"${sim_revenue:,.0f}")

st.divider()

# ------------------------------------------------------------------
# ROW 5 — MEASURE DETAIL TABLE
# ------------------------------------------------------------------

st.subheader("Measure Detail")

display = measures[[
    'name','weight','denom','numer',
    'rate','benchmark','vs_benchmark','stars','gap_to_4star'
]].rename(columns={
    'name':         'Measure',
    'weight':       'Weight',
    'denom':        'Denominator',
    'numer':        'Numerator',
    'rate':         'Rate (%)',
    'benchmark':    'NCQA Benchmark',
    'vs_benchmark': 'vs Benchmark',
    'stars':        'Stars',
    'gap_to_4star': 'Gap to 4-Star'
})

st.dataframe(display, hide_index=True, width='stretch')