import streamlit as st

# ------------------------------------------------------------------
# app.py
# MediView — Medicare & Medicaid Analytics Platform
# Unified entry point connecting all four modules
# ------------------------------------------------------------------

st.set_page_config(
    page_title="MediView",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ------------------------------------------------------------------

st.sidebar.image(
    "https://via.placeholder.com/280x60/1B3A5C/FFFFFF"
    "?text=MediView",
    use_container_width=True
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")

page = st.sidebar.radio(
    "Select Module",
    options=[
        "Home",
        "Module 1 — Risk Adjustment",
        "Module 2 — HEDIS & Star Ratings",
        "Module 3 — Rate Development",
        "Module 4 — Compliance Tracker"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Plan FL-001  ·  Plan Year 2025/2026\n\n"
    "Medicare Advantage Analytics Portfolio"
)

# ------------------------------------------------------------------
# PAGE ROUTING
# ------------------------------------------------------------------

if page == "Home":

    st.title("MediView")
    st.subheader(
        "Medicare Advantage Analytics & Compliance Platform")
    st.markdown(
        "A portfolio project demonstrating end-to-end analytical "
        "capability across the four core financial domains of "
        "Medicare Advantage managed care."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Module 1 — Risk Adjustment")
        st.write(
            "HCC-based RAF score calculation using CMS V28 model. "
            "ICD-10 to HCC crosswalk, demographic scoring, "
            "capitation payment projection by county, and "
            "V24 vs V28 transition impact analysis."
        )
        if st.button("Open Module 1"):
            st.switch_page("pages/module1.py")

        st.markdown("### Module 3 — Rate Development")
        st.write(
            "Medical cost PMPM analysis by service category, "
            "trend factor application, MA bid construction with "
            "admin and margin loading, MLR compliance check, "
            "and interactive bid vs benchmark simulator."
        )
        if st.button("Open Module 3"):
            st.switch_page("pages/module3.py")

    with col2:
        st.markdown("### Module 2 — HEDIS & Star Ratings")
        st.write(
            "Four HEDIS measure calculations with denominator, "
            "numerator, and rate logic. Star Rating weighted "
            "average model, NCQA benchmark comparison, and "
            "interactive quality bonus payment simulator."
        )
        if st.button("Open Module 2"):
            st.switch_page("pages/module2.py")

        st.markdown("### Module 4 — Compliance Tracker")
        st.write(
            "CMS regulatory event tracker covering MA, Medicaid, "
            "and Part D. Rule type classification, financial "
            "impact rating, effective date monitoring, and "
            "required action items by module."
        )
        if st.button("Open Module 4"):
            st.switch_page("pages/module4.py")

    st.divider()

    st.markdown("### Technical Stack")
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.info("**Data Layer**\nSQLite · 5 tables\n465 claims\n100 members")
    tc2.info("**Processing**\nPython 3.14\npandas · numpy\nSQLite3")
    tc3.info("**Visualization**\nStreamlit\nPlotly\nInteractive charts")
    tc4.info("**Domain**\nMedicare Advantage\nHEDIS · HCC · MLR\nCMS Compliance")

elif page == "Module 1 — Risk Adjustment":
    exec(open(
        r'C:\Users\gtbru\MediView\modules\module\module1_hcc'
        r'\dashboard.py',
        encoding='utf-8'
    ).read())

elif page == "Module 2 — HEDIS & Star Ratings":
    exec(open(
        r'C:\Users\gtbru\MediView\modules\module\module2_hedis'
        r'\dashboard_hedis.py',
        encoding='utf-8'
    ).read())

elif page == "Module 3 — Rate Development":
    exec(open(
        r'C:\Users\gtbru\MediView\modules\module\module3_rates'
        r'\dashboard_rates.py',
        encoding='utf-8'
    ).read())

elif page == "Module 4 — Compliance Tracker":
    exec(open(
        r'C:\Users\gtbru\MediView\modules\module\module4_compliance'
        r'\dashboard_compliance.py',
        encoding='utf-8'
    ).read())