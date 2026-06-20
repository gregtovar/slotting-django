"""
streamlit_app.py
------------------
Home page of the Streamlit version of Slotting Optimizer. Run with:

    streamlit run streamlit_app.py

Every other screen lives under pages/ and is auto-discovered by
Streamlit into the sidebar navigation.
"""

import streamlit as st

from app.config import ALL_TABLES, ALL_ANALYSES, ALL_REPORTS, APP_NAME, APP_SUBTITLE
from app.data_manager import DataManager

st.set_page_config(page_title=APP_NAME, page_icon="\U0001F4E6", layout="wide")

st.title(f"\U0001F4E6 {APP_NAME}")
st.caption(APP_SUBTITLE.upper())
st.markdown(
    "Analyze order history and SKU attributes to recommend optimal storage "
    "locations - reducing travel time and lowering pick costs."
)

st.divider()
st.subheader("Data on file")
cols = st.columns(len(ALL_TABLES))
for col, table_cfg in zip(cols, ALL_TABLES):
    dm = DataManager(table_cfg)
    dm.load()
    col.metric(f"{table_cfg.icon} {table_cfg.label}", f"{dm.row_count():,}")

st.divider()
st.subheader("Slotting Analysis & Optimization")
st.caption("Use the sidebar to open any module. Every one starts with a date-range picker.")
cols = st.columns(3)
for i, a in enumerate(ALL_ANALYSES):
    with cols[i % 3]:
        st.markdown(f"**{a.icon} {a.label}**")
        st.caption(a.description)

st.subheader("Reports & Dashboards")
cols = st.columns(3)
for i, r in enumerate(ALL_REPORTS):
    with cols[i % 3]:
        st.markdown(f"**{r.icon} {r.label}**")
        st.caption(r.description)

st.divider()
st.caption("Data files are read from / written to the local `data/` folder - a timestamped backup is kept on every save.")
