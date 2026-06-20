"""Streamlit page: Top Customers."""
import streamlit as st
from app.config import ORDERS_BY_CUSTOMER_TOP10
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Top Customers", page_icon="\U0001F465", layout="wide")
render_analysis_page(ORDERS_BY_CUSTOMER_TOP10)
