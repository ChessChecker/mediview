import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ------------------------------------------------------------------
# dashboard.py
# MediView Module 1 — Risk Adjustment & HCC Dashboard
# Displays RAF scores, county revenue, member risk distribution,
# and top HCC conditions for Plan FL-001
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'

@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)

    # Members with benchmark
    members_df = pd.read_sql('''
        SELECT
            m.member_id,
            m.sex,
            m.medicaid_dual_flag,
            m.county_name,
            m.county_code,
            (CAST(strftime('%Y','now') AS INTEGER) - CAST(strftime('%Y', m.date_of_birth) AS INTEGER)) AS age,
            cb.benchmark_amount
        FROM members m
        LEFT JOIN county_benchmarks cb
            ON m.county_code = cb.county_code
            AND cb.plan_year = 2025
    ''', conn)

    # HCC hits across all diagnosis columns
    hcc_hits_df = pd.read_sql('''
        SELECT
            c.member_id,
            h.hcc_v28,
            h.hcc_v24,
            h.condition_category,
            h.coefficient_v28,
            h.coefficient_v24
        FROM claims c
        JOIN hcc_crosswalk h
            ON  c.icd10_primary     = h.icd10_code
            OR  c.icd10_secondary_1 = h.icd10_code
            OR  c.icd10_secondary_2 = h.icd10_code
            OR  c.icd10_secondary_3 = h.icd10_code
        WHERE h.hcc_v28 IS NOT NULL
        AND   c.date_of_service BETWEEN '2025-01-01' AND '2025-12-31'
    ''', conn)

    conn.close()
    return members_df, hcc_hits_df

def calculate_raf(members_df, hcc_hits_df):

    def demo_score(age, sex, dual):
        if   age < 70: base = 0.35
        elif age < 75: base = 0.45
        elif age < 80: base = 0.55
        else:          base = 0.65
        return round(base + (0.02 if sex=='M' else 0)
                           + (0.19 if dual==1  else 0), 4)

    members_df['demo_score'] = members_df.apply(
        lambda r: demo_score(r['age'], r['sex'], r['medicaid_dual_flag']),
        axis=1
    )

    # Deduplicate and sum HCC coefficients
    v28 = (hcc_hits_df.sort_values('coefficient_v28', ascending=False)
           .drop_duplicates(subset=['member_id','hcc_v28'])
           .groupby('member_id')['coefficient_v28'].sum()
           .reset_index().rename(columns={'coefficient_v28':'hcc_v28_score'}))

    v24 = (hcc_hits_df.sort_values('coefficient_v24', ascending=False)
           .drop_duplicates(subset=['member_id','hcc_v24'])
           .groupby('member_id')['coefficient_v24'].sum()
           .reset_index().rename(columns={'coefficient_v24':'hcc_v24_score'}))

    raf = (members_df
           .merge(v28, on='member_id', how='left')
           .merge(v24, on='member_id', how='left'))

    raf['hcc_v28_score'] = raf['hcc_v28_score'].fillna(0)
    raf['hcc_v24_score'] = raf['hcc_v24_score'].fillna(0)
    raf['raf_v28']       = (raf['demo_score'] + raf['hcc_v28_score']).round(4)
    raf['raf_v24']       = (raf['demo_score'] + raf['hcc_v24_score']).round(4)
    raf['payment_v28']   = (raf['benchmark_amount'] * raf['raf_v28']).round(2)
    raf['payment_v24']   = (raf['benchmark_amount'] * raf['raf_v24']).round(2)
    raf['payment_delta'] = (raf['payment_v28'] - raf['payment_v24']).round(2)

    return raf

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="MediView — Risk Adjustment",
    page_icon="🏥",
    layout="wide"
)

st.title("MediView — Module 1: Risk Adjustment & HCC Analysis")
st.caption("Plan FL-001  ·  Plan Year 2025  ·  Medicare Advantage")

# ------------------------------------------------------------------
# LOAD AND CALCULATE
# ------------------------------------------------------------------
members_df, hcc_hits_df = load_data()
raf = calculate_raf(members_df, hcc_hits_df)

# ------------------------------------------------------------------
# ROW 1 — KEY METRICS
# ------------------------------------------------------------------
st.subheader("Plan-Level Summary")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Total Members",        f"{len(raf):,}")
c2.metric("Members with HCC",     f"{(raf['hcc_v28_score']>0).sum()}")
c3.metric("Avg RAF (V28)",         f"{raf['raf_v28'].mean():.4f}")
c4.metric("Avg RAF (V24)",         f"{raf['raf_v24'].mean():.4f}",
          delta=f"{(raf['raf_v28'].mean()-raf['raf_v24'].mean()):+.4f}")
c5.metric("Annual V28 Impact",
          f"${raf['payment_delta'].sum()*12:,.0f}")

st.divider()

# ------------------------------------------------------------------
# ROW 2 — COUNTY REVENUE + RAF DISTRIBUTION
# ------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Monthly Revenue by County")
    county = (raf.groupby('county_name')
              .agg(members       =('member_id',   'count'),
                   avg_raf       =('raf_v28',      'mean'),
                   total_revenue =('payment_v28',  'sum'),
                   benchmark     =('benchmark_amount','mean'))
              .reset_index()
              .sort_values('total_revenue', ascending=True))

    county['revenue_pmpm'] = (
        county['total_revenue'] / county['members']
    ).round(2)

    fig_county = px.bar(
        county,
        x='total_revenue',
        y='county_name',
        orientation='h',
        color='avg_raf',
        color_continuous_scale='Teal',
        hover_data={
            'members':      True,
            'avg_raf':      ':.4f',
            'revenue_pmpm': ':$,.2f',
            'benchmark':    ':$,.2f'
        },
        labels={'total_revenue':'Monthly Revenue ($)',
                'county_name':'County',
                'avg_raf':'Avg RAF',
                'revenue_pmpm':'Revenue PMPM'},
        text=county['total_revenue'].apply(lambda x: f'${x:,.0f}')
    )
    fig_county.update_traces(textposition='outside')
    fig_county.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=True
    )
st.plotly_chart(fig_county, width='stretch')

with col_right:
    st.subheader("Member RAF Score Distribution")
    fig_hist = px.histogram(
        raf,
        x='raf_v28',
        nbins=20,
        color_discrete_sequence=['#1A7A6E'],
        labels={'raf_v28':'RAF Score (V28)', 'count':'Members'}
    )
    fig_hist.add_vline(
        x=raf['raf_v28'].mean(),
        line_dash='dash',
        line_color='#E8593C',
        annotation_text=f"Plan avg: {raf['raf_v28'].mean():.2f}",
        annotation_position='top right'
    )
    fig_hist.add_vline(
        x=1.0,
        line_dash='dot',
        line_color='#888',
        annotation_text="CMS avg: 1.00",
        annotation_position='top left'
    )
    fig_hist.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_hist, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 3 — TOP HCC CONDITIONS + V28 vs V24 COMPARISON
# ------------------------------------------------------------------
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader("Top HCC Conditions by Prevalence")
    top_hcc = (hcc_hits_df
               .drop_duplicates(subset=['member_id','hcc_v28'])
               .groupby('condition_category')
               .agg(member_count  =('member_id',      'nunique'),
                    avg_coefficient=('coefficient_v28','mean'))
               .reset_index()
               .sort_values('member_count', ascending=False)
               .head(10))

    top_hcc['prevalence_pct'] = (
        top_hcc['member_count'] / len(raf) * 100
    ).round(1)

    fig_hcc = px.bar(
        top_hcc,
        x='member_count',
        y='condition_category',
        orientation='h',
        color='avg_coefficient',
        color_continuous_scale='Blues',
        labels={'member_count':'Members with HCC',
                'condition_category':'Condition',
                'avg_coefficient':'RAF Coefficient'},
        text=top_hcc['prevalence_pct'].apply(lambda x: f'{x}%')
    )
    fig_hcc.update_traces(textposition='outside')
    fig_hcc.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig_hcc, width='stretch')

with col_right2:
    st.subheader("V28 vs V24 Revenue Impact by County")
    v_compare = (raf.groupby('county_name')
                 .agg(revenue_v28=('payment_v28','sum'),
                      revenue_v24=('payment_v24','sum'))
                 .reset_index())
    v_compare['delta'] = v_compare['revenue_v28'] - v_compare['revenue_v24']

    fig_compare = go.Figure()
    fig_compare.add_trace(go.Bar(
        name='V24 Revenue',
        x=v_compare['county_name'],
        y=v_compare['revenue_v24'],
        marker_color='#B5D4F4'
    ))
    fig_compare.add_trace(go.Bar(
        name='V28 Revenue',
        x=v_compare['county_name'],
        y=v_compare['revenue_v28'],
        marker_color='#1A7A6E'
    ))
    fig_compare.update_layout(
        barmode='group',
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.1),
        yaxis_title='Monthly Revenue ($)'
    )
    st.plotly_chart(fig_compare, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 4 — MEMBER DETAIL TABLE
# ------------------------------------------------------------------
st.subheader("Member-Level RAF Detail")

display_cols = ['member_id','age','sex','county_name',
                'raf_v28','raf_v24','payment_v28','payment_delta']

st.dataframe(
    raf[display_cols]
    .sort_values('raf_v28', ascending=False)
    .rename(columns={
        'member_id':    'Member',
        'age':          'Age',
        'sex':          'Sex',
        'county_name':  'County',
        'raf_v28':      'RAF V28',
        'raf_v24':      'RAF V24',
        'payment_v28':  'Monthly Payment',
        'payment_delta':'V28 Impact'
    }),
    width='stretch',
    hide_index=True
)
