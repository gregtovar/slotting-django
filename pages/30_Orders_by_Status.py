"""Streamlit page: Orders by Status."""
import streamlit as st
from app.config import ORDERS_BY_STATUS
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Orders by Status", page_icon="\U0001F4CB", layout="wide")
render_analysis_page(ORDERS_BY_STATUS)
