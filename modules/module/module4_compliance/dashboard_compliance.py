import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------
# dashboard_compliance.py
# MediView Module 4 — CMS Compliance & Policy Tracker
# Tracks regulatory events, effective dates, financial impact,
# and operational action items across MA, Medicaid, and Part D
# ------------------------------------------------------------------

DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'

@st.cache_data
def load_compliance_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('''
        SELECT * FROM regulatory_events
        ORDER BY effective_date DESC
    ''', conn)
    conn.close()
    return df

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------

st.set_page_config(
    page_title="MediView - Compliance Tracker",
    page_icon="📋",
    layout="wide"
)

st.title("MediView - Module 4: CMS Compliance & Policy Tracker")
st.caption(
    "Regulatory intelligence across Medicare Advantage, "
    "Medicaid, and Part D  ·  Updated through Q1 2026"
)

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------

events = load_compliance_data()

date_cols = [
    'proposed_date', 'final_date',
    'effective_date', 'comment_deadline'
]
for col in date_cols:
    events[col] = pd.to_datetime(
        events[col], errors='coerce'
    ).dt.strftime('%m/%d/%Y').fillna('—')

# ------------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------------

st.sidebar.header("Filter Events")

programs = ['All'] + sorted(events['program'].unique().tolist())
selected_program = st.sidebar.selectbox("Program", programs)

impacts = ['All'] + sorted(
    events['financial_impact'].unique().tolist())
selected_impact = st.sidebar.selectbox(
    "Financial Impact", impacts)

rule_types = ['All'] + sorted(
    events['rule_type'].unique().tolist())
selected_type = st.sidebar.selectbox("Rule Type", rule_types)

modules = ['All'] + sorted(
    events['affected_module'].unique().tolist())
selected_module = st.sidebar.selectbox(
    "Affected Module", modules)

filtered = events.copy()
if selected_program != 'All':
    filtered = filtered[
        filtered['program'] == selected_program]
if selected_impact != 'All':
    filtered = filtered[
        filtered['financial_impact'] == selected_impact]
if selected_type != 'All':
    filtered = filtered[
        filtered['rule_type'] == selected_type]
if selected_module != 'All':
    filtered = filtered[
        filtered['affected_module'] == selected_module]

# ------------------------------------------------------------------
# ROW 1 — KEY METRICS
# ------------------------------------------------------------------

st.subheader("Regulatory Landscape Summary")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Events Tracked",
          f"{len(events)}")
c2.metric("High Impact Events",
          f"{(events['financial_impact']=='High').sum()}")
c3.metric("Negative Impact Events",
          f"{(events['impact_direction']=='Negative').sum()}")
c4.metric("Open Comment Periods",
          f"{(events['comment_deadline']!='—').sum()}")
c5.metric("Events Filtered",
          f"{len(filtered)}")

st.divider()

# ------------------------------------------------------------------
# ROW 2 — CHARTS
# ------------------------------------------------------------------

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Events by Program and Impact")

    impact_summary = (
        events.groupby(['program', 'financial_impact'])
        .size()
        .reset_index(name='count')
    )

    color_map = {
        'High':   '#E24B4A',
        'Medium': '#EF9F27',
        'Low':    '#1A7A6E'
    }

    fig_impact = px.bar(
        impact_summary,
        x='program',
        y='count',
        color='financial_impact',
        color_discrete_map=color_map,
        labels={
            'program':          'Program',
            'count':            'Events',
            'financial_impact': 'Impact Level'
        },
        text='count',
        barmode='stack'
    )
    fig_impact.update_traces(textposition='inside')
    fig_impact.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig_impact, width='stretch')

with col_right:
    st.subheader("Events by Direction and Module")

    direction_summary = (
        events.groupby(['affected_module', 'impact_direction'])
        .size()
        .reset_index(name='count')
    )

    dir_color_map = {
        'Negative': '#E24B4A',
        'Neutral':  '#888780',
        'Positive': '#1A7A6E'
    }

    fig_direction = px.bar(
        direction_summary,
        x='affected_module',
        y='count',
        color='impact_direction',
        color_discrete_map=dir_color_map,
        labels={
            'affected_module':  'Module',
            'count':            'Events',
            'impact_direction': 'Direction'
        },
        text='count',
        barmode='stack'
    )
    fig_direction.update_traces(textposition='inside')
    fig_direction.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation='h', y=1.1)
    )
    st.plotly_chart(fig_direction, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 3 — EVENT CARDS
# ------------------------------------------------------------------

st.subheader(f"Regulatory Events ({len(filtered)} shown)")

direction_icons = {
    'Negative': 'Revenue Impact: Negative',
    'Positive': 'Revenue Impact: Positive',
    'Neutral':  'Revenue Impact: Neutral'
}

for _, row in filtered.iterrows():
    d_icon = direction_icons.get(row['impact_direction'], '')

    with st.expander(
        f"{row['rule_type']}  |  {row['program']}  |  "
        f"{row['title'][:70]}..."
        if len(row['title']) > 70 else
        f"{row['rule_type']}  |  {row['program']}  |  "
        f"{row['title']}"
    ):
        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"**Proposed:** {row['proposed_date']}")
        m2.markdown(f"**Finalized:** {row['final_date']}")
        m3.markdown(f"**Effective:** {row['effective_date']}")
        m4.markdown(
            f"**Comment Deadline:** {row['comment_deadline']}")

        st.markdown("---")

        col_a, col_b = st.columns([2, 1])

        with col_a:
            st.markdown("**Summary**")
            st.write(row['summary'])
            st.markdown("**Required Action**")
            st.info(row['action_required'])

        with col_b:
            st.markdown("**Classification**")
            st.markdown(f"**Program:** {row['program']}")
            st.markdown(f"**Rule Type:** {row['rule_type']}")
            st.markdown(
                f"**Affected Module:** {row['affected_module']}")
            st.markdown(
                f"**Financial Impact:** "
                f"{row['financial_impact']}")
            st.markdown(f"**{d_icon}**")
            st.markdown(f"**Citation:** `{row['citation']}`")

st.divider()

# ------------------------------------------------------------------
# ROW 4 — ACTION ITEMS TABLE
# ------------------------------------------------------------------

st.subheader("Compliance Action Items")
st.caption(
    "Required actions derived from regulatory events — "
    "prioritized by financial impact"
)

action_df = (
    filtered[[
        'title', 'program', 'financial_impact',
        'impact_direction', 'effective_date',
        'affected_module', 'action_required'
    ]]
    .sort_values(
        'financial_impact',
        key=lambda x: x.map(
            {'High': 0, 'Medium': 1, 'Low': 2}))
    .rename(columns={
        'title':            'Rule',
        'program':          'Program',
        'financial_impact': 'Impact',
        'impact_direction': 'Direction',
        'effective_date':   'Effective',
        'affected_module':  'Module',
        'action_required':  'Action Required'
    })
)

st.dataframe(action_df, hide_index=True, width='stretch')

st.divider()

# ------------------------------------------------------------------
# ROW 5 — RULEMAKING PROCESS REFERENCE
# ------------------------------------------------------------------

st.subheader("CMS Rulemaking Process Reference")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**ANPRM**")
    st.caption("Advance Notice of Proposed Rulemaking")
    st.write(
        "Earliest regulatory signal. CMS solicits public "
        "input before drafting formal proposals. No binding "
        "changes. Monitor for strategic direction."
    )

with col2:
    st.markdown("**NPRM**")
    st.caption("Notice of Proposed Rulemaking")
    st.write(
        "Formal proposed rule published in Federal Register. "
        "60-day public comment period opens. Submit comments "
        "to influence final rule. Begin impact modeling."
    )

with col3:
    st.markdown("**Final Rule**")
    st.caption("Binding Regulation")
    st.write(
        "CMS publishes final binding rule after reviewing "
        "comments. Effective date typically 60 days after "
        "publication. Compliance required by effective date."
    )

with col4:
    st.markdown("**Sub-regulatory**")
    st.caption("HPMS Memos and Guidance")
    st.write(
        "Operational guidance issued outside formal "
        "rulemaking. Immediately effective. Monitor HPMS "
        "and CMS.gov regularly for new memos affecting "
        "plan operations."
    )