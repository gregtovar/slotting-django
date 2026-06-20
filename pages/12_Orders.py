"""Streamlit page: Orders (Data Management)."""
import streamlit as st
from app.config import ORDERS_CONFIG
from app.web.tables import render_table_page

st.set_page_config(page_title="Orders", page_icon="\U0001F9FE", layout="wide")
render_table_page(ORDERS_CONFIG)
