import streamlit as st
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data', 'mediview.db'
)

st.set_page_config(
    page_title="MediView",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.markdown("## MediView")
st.sidebar.markdown("Medicare Advantage Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Select Module",
    options=[
        "Home",
        "Module 1 - Risk Adjustment",
        "Module 2 - HEDIS and Star Ratings",
        "Module 3 - Rate Development",
        "Module 4 - Compliance Tracker"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Plan FL-001 - Plan Year 2025/2026")


def run_module(filepath):
    code = open(filepath, encoding='utf-8').read()
    code = code.replace(
        r"DB_PATH = r'C:\Users\gtbru\MediView\data\mediview.db'",
        f"DB_PATH = r'{DB_PATH}'"
    )
    exec(code, {'__file__': filepath})


if page == "Home":
    st.title("MediView")
    st.subheader(
        "Medicare Advantage Analytics and Compliance Platform")
    st.markdown(
        "A portfolio project demonstrating end-to-end analytical "
        "capability across the four core financial domains of "
        "Medicare Advantage managed care."
    )
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Module 1 - Risk Adjustment")
        st.write(
            "HCC-based RAF score calculation using CMS V28 model. "
            "ICD-10 to HCC crosswalk, demographic scoring, "
            "capitation payment projection by county, and "
            "V24 vs V28 transition impact analysis."
        )
        st.markdown("### Module 3 - Rate Development")
        st.write(
            "Medical cost PMPM analysis by service category, "
            "trend factor application, MA bid construction with "
            "admin and margin loading, MLR compliance check, "
            "and interactive bid vs benchmark simulator."
        )
    with col2:
        st.markdown("### Module 2 - HEDIS and Star Ratings")
        st.write(
            "Four HEDIS measure calculations with denominator, "
            "numerator, and rate logic. Star Rating weighted "
            "average model, NCQA benchmark comparison, and "
            "interactive quality bonus payment simulator."
        )
        st.markdown("### Module 4 - Compliance Tracker")
        st.write(
            "CMS regulatory event tracker covering MA, Medicaid, "
            "and Part D. Rule type classification, financial "
            "impact rating, effective date monitoring, and "
            "required action items by module."
        )
    st.divider()
    tc1, tc2, tc3, tc4 = st.columns(4)
    tc1.info("Data Layer\nSQLite, 5 tables\n465 claims, 100 members")
    tc2.info("Processing\nPython, pandas, numpy")
    tc3.info("Visualization\nStreamlit, Plotly")
    tc4.info("Domain\nMedicare Advantage\nHEDIS, HCC, MLR")

elif page == "Module 1 - Risk Adjustment":
    run_module(os.path.join(
        os.path.dirname(__file__),
        'modules', 'module', 'module1_hcc', 'dashboard.py'
    ))

elif page == "Module 2 - HEDIS and Star Ratings":
    run_module(os.path.join(
        os.path.dirname(__file__),
        'modules', 'module', 'module2_hedis', 'dashboard_hedis.py'
    ))

elif page == "Module 3 - Rate Development":
    run_module(os.path.join(
        os.path.dirname(__file__),
        'modules', 'module', 'module3_rates', 'dashboard_rates.py'
    ))

elif page == "Module 4 - Compliance Tracker":
    run_module(os.path.join(
        os.path.dirname(__file__),
        'modules', 'module', 'module4_compliance',
        'dashboard_compliance.py'
    ))