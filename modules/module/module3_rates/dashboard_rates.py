import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------
# dashboard_rates.py
# MediView Module 3 — Rate Development & MA Bid Simulator
# Models medical cost trends, bid construction, and benchmark
# comparison with interactive levers
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'

@st.cache_data
def load_rates_data():
    conn = sqlite3.connect(DB_PATH)

    pmpm = pd.read_sql('''
        SELECT
            place_of_service,
            COUNT(*)                      AS claims,
            SUM(allowed_amount)           AS total_allowed,
            SUM(allowed_amount) / 1200.0  AS base_pmpm
        FROM claims
        GROUP BY place_of_service
        ORDER BY base_pmpm DESC
    ''', conn)

    benchmarks = pd.read_sql('''
        SELECT county_name, benchmark_amount
        FROM county_benchmarks
        WHERE plan_year = 2025
        ORDER BY benchmark_amount DESC
    ''', conn)

    conn.close()
    return pmpm, benchmarks

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------

CATEGORY_MAP = {
    '21': 'Inpatient',
    '23': 'Emergency Room',
    '11': 'Office Visits',
    '19': 'Imaging',
    '81': 'Lab'
}

TREND_DEFAULTS = {
    'Inpatient':      {'unit_cost': 5.5, 'utilization': -2.0},
    'Emergency Room': {'unit_cost': 4.0, 'utilization':  1.0},
    'Office Visits':  {'unit_cost': 3.5, 'utilization':  0.5},
    'Imaging':        {'unit_cost': 2.5, 'utilization': -1.0},
    'Lab':            {'unit_cost': 1.5, 'utilization':  0.5},
}

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------

st.set_page_config(
    page_title="MediView - Rate Development",
    page_icon="📊",
    layout="wide"
)

st.title("MediView - Module 3: Rate Development & MA Bid Simulator")
st.caption("Plan FL-001  ·  Plan Year 2026 Bid  ·  Medicare Advantage")

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------

pmpm_df, benchmarks = load_rates_data()
pmpm_df['category'] = pmpm_df['place_of_service'].map(CATEGORY_MAP)

# ------------------------------------------------------------------
# SIDEBAR — TREND AND LOADING ASSUMPTIONS
# ------------------------------------------------------------------

st.sidebar.header("Trend Assumptions")
st.sidebar.caption("Adjust to model different market scenarios")

trend_inputs = {}
for cat in CATEGORY_MAP.values():
    st.sidebar.subheader(cat)
    uc = st.sidebar.slider(
        f"Unit cost trend (%)",
        -5.0, 15.0,
        TREND_DEFAULTS[cat]['unit_cost'],
        0.5,
        key=f"uc_{cat}"
    )
    ut = st.sidebar.slider(
        f"Utilization trend (%)",
        -10.0, 10.0,
        TREND_DEFAULTS[cat]['utilization'],
        0.5,
        key=f"ut_{cat}"
    )
    trend_inputs[cat] = {'unit_cost': uc/100, 'utilization': ut/100}

st.sidebar.divider()
st.sidebar.header("Plan Loading Factors")
admin_pct   = st.sidebar.slider("Admin expense (%)",   5.0, 15.0, 8.5, 0.5)
margin_pct  = st.sidebar.slider("Profit margin (%)",   0.0, 10.0, 3.0, 0.5)
quality_pct = st.sidebar.slider("Quality investment (%)", 0.0, 5.0, 1.5, 0.5)

st.sidebar.divider()
st.sidebar.header("Cost Reduction Levers")
provider_reduction = st.sidebar.slider(
    "Provider rate reduction (%)", 0.0, 20.0, 0.0, 0.5)
util_mgmt_savings  = st.sidebar.slider(
    "Utilization mgmt savings (%)", 0.0, 20.0, 0.0, 0.5)

# ------------------------------------------------------------------
# CALCULATE PROJECTED PMPMs
# ------------------------------------------------------------------

pmpm_df['combined_trend'] = pmpm_df['category'].apply(
    lambda c: (1 + trend_inputs[c]['unit_cost']) *
              (1 + trend_inputs[c]['utilization']) - 1
)

pmpm_df['projected_pmpm'] = (
    pmpm_df['base_pmpm'] *
    (1 + pmpm_df['combined_trend']) *
    (1 - provider_reduction/100) *
    (1 - util_mgmt_savings/100)
).round(2)

total_medical  = pmpm_df['projected_pmpm'].sum()
admin_pmpm     = round(total_medical * admin_pct/100,   2)
margin_pmpm    = round(total_medical * margin_pct/100,  2)
quality_pmpm   = round(total_medical * quality_pct/100, 2)
total_bid      = round(total_medical + admin_pmpm +
                       margin_pmpm + quality_pmpm, 2)
mlr            = round(total_medical / total_bid * 100, 1)

# ------------------------------------------------------------------
# BENCHMARK COMPARISON
# ------------------------------------------------------------------

benchmarks['bid']        = total_bid
benchmarks['difference'] = (
    benchmarks['bid'] - benchmarks['benchmark_amount']
).round(2)
benchmarks['rebate']     = benchmarks.apply(
    lambda r: round((r['benchmark_amount'] - r['bid']) * 0.25, 2)
    if r['bid'] < r['benchmark_amount'] else 0, axis=1)
benchmarks['premium']    = benchmarks.apply(
    lambda r: round(r['bid'] - r['benchmark_amount'], 2)
    if r['bid'] > r['benchmark_amount'] else 0, axis=1)
benchmarks['status']     = benchmarks.apply(
    lambda r: 'Rebate' if r['bid'] < r['benchmark_amount']
              else 'Premium', axis=1)
benchmarks['annual_rebate'] = benchmarks['rebate'] * 12

# ------------------------------------------------------------------
# ROW 1 — KEY METRICS
# ------------------------------------------------------------------

st.subheader("Bid Summary")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Bid PMPM",      f"${total_bid:,.2f}")
c2.metric("Medical Cost PMPM",   f"${total_medical:,.2f}")
c3.metric("MLR",
          f"{mlr:.1f}%",
          delta="Compliant" if mlr >= 85 else "NON-COMPLIANT")
c4.metric("Counties with Rebate",
          f"{(benchmarks['status']=='Rebate').sum()} / "
          f"{len(benchmarks)}")
c5.metric("Max Annual Rebate",
          f"${benchmarks['annual_rebate'].max():,.0f}")

st.divider()

# ------------------------------------------------------------------
# ROW 2 — PMPM WATERFALL + BID VS BENCHMARK
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Medical PMPM by Service Category")

    colors = {
        'Inpatient':      '#1B3A5C',
        'Emergency Room': '#E8593C',
        'Office Visits':  '#1A7A6E',
        'Imaging':        '#534AB7',
        'Lab':            '#BA7517'
    }

    fig_pmpm = go.Figure()
    fig_pmpm.add_trace(go.Bar(
        name='Base PMPM',
        x=pmpm_df['category'],
        y=pmpm_df['base_pmpm'],
        marker_color='#B4B2A9',
        text=pmpm_df['base_pmpm'].apply(lambda x: f'${x:,.2f}'),
        textposition='outside'
    ))
    fig_pmpm.add_trace(go.Bar(
        name='Projected PMPM',
        x=pmpm_df['category'],
        y=pmpm_df['projected_pmpm'],
        marker_color=[colors[c] for c in pmpm_df['category']],
        text=pmpm_df['projected_pmpm'].apply(lambda x: f'${x:,.2f}'),
        textposition='outside'
    ))
    fig_pmpm.update_layout(
        barmode='group',
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.1),
        yaxis_title='PMPM ($)'
    )
    st.plotly_chart(fig_pmpm, width='stretch')

with col_right:
    st.subheader("Bid vs County Benchmark")

    fig_bench = go.Figure()

    fig_bench.add_trace(go.Bar(
        name='Benchmark',
        x=benchmarks['county_name'],
        y=benchmarks['benchmark_amount'],
        marker_color='#B5D4F4',
        text=benchmarks['benchmark_amount'].apply(
            lambda x: f'${x:,.0f}'),
        textposition='outside'
    ))
    fig_bench.add_trace(go.Scatter(
        name='Plan Bid',
        x=benchmarks['county_name'],
        y=benchmarks['bid'],
        mode='lines+markers',
        line=dict(color='#E8593C', width=2.5),
        marker=dict(size=10)
    ))
    fig_bench.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.1),
        yaxis_title='PMPM ($)'
    )
    st.plotly_chart(fig_bench, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 3 — BID CONSTRUCTION WATERFALL
# ------------------------------------------------------------------

st.subheader("Bid Construction")

col_left2, col_right2 = st.columns(2)

with col_left2:
    waterfall_labels = [
        'Medical costs', 'Admin', 'Quality', 'Margin', 'Total bid'
    ]
    waterfall_values = [
        total_medical, admin_pmpm, quality_pmpm,
        margin_pmpm, total_bid
    ]
    waterfall_measure = [
        'absolute', 'relative', 'relative', 'relative', 'total'
    ]
    waterfall_colors = [
        '#1A7A6E', '#534AB7', '#1A7A6E', '#BA7517', '#1B3A5C'
    ]

    fig_waterfall = go.Figure(go.Waterfall(
        name='Bid components',
        orientation='v',
        measure=waterfall_measure,
        x=waterfall_labels,
        y=waterfall_values,
        connector=dict(line=dict(color='#888', width=0.8)),
        decreasing=dict(marker_color='#1A7A6E'),
        increasing=dict(marker_color='#534AB7'),
        totals=dict(marker_color='#1B3A5C'),
        text=[f'${v:,.2f}' for v in waterfall_values],
        textposition='outside'
    ))
    fig_waterfall.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title='PMPM ($)',
        showlegend=False
    )
    st.plotly_chart(fig_waterfall, width='stretch')

with col_right2:
    st.subheader("County Rebate Summary")

    rebate_display = benchmarks[[
        'county_name', 'benchmark_amount',
        'bid', 'difference', 'rebate', 'status'
    ]].rename(columns={
        'county_name':      'County',
        'benchmark_amount': 'Benchmark',
        'bid':              'Bid',
        'difference':       'Difference',
        'rebate':           'Rebate PMPM',
        'status':           'Status'
    })

    st.dataframe(rebate_display, hide_index=True, width='stretch')

    st.caption(
        "Rebate = 25% of (Benchmark - Bid) when Bid < Benchmark. "
        "Rebate funds supplemental benefits."
    )

st.divider()

# ------------------------------------------------------------------
# ROW 4 — TREND DETAIL TABLE
# ------------------------------------------------------------------

st.subheader("Trend Development Detail")

trend_display = pmpm_df[[
    'category', 'base_pmpm', 'combined_trend', 'projected_pmpm'
]].copy()
trend_display['combined_trend'] = (
    trend_display['combined_trend'] * 100).round(2)
trend_display['pmpm_change'] = (
    trend_display['projected_pmpm'] -
    trend_display['base_pmpm']
).round(2)

trend_display = trend_display.rename(columns={
    'category':       'Service Category',
    'base_pmpm':      'Base PMPM',
    'combined_trend': 'Combined Trend (%)',
    'projected_pmpm': 'Projected PMPM',
    'pmpm_change':    'Change'
})

st.dataframe(trend_display, hide_index=True, width='stretch')