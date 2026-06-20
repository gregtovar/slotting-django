"""Streamlit page: Orders Trend."""
import streamlit as st
from app.config import ORDERS_TREND_BY_DAY
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Orders Trend", page_icon="\U0001F4C8", layout="wide")
render_analysis_page(ORDERS_TREND_BY_DAY)
