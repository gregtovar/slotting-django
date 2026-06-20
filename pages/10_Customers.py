"""Streamlit page: Customers (Data Management)."""
import streamlit as st
from app.config import CUSTOMERS_CONFIG
from app.web.tables import render_table_page

st.set_page_config(page_title="Customers", page_icon="\U0001F465", layout="wide")
render_table_page(CUSTOMERS_CONFIG)
