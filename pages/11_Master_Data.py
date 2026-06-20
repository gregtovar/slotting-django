"""Streamlit page: Master Data (Data Management)."""
import streamlit as st
from app.config import MASTER_CONFIG
from app.web.tables import render_table_page

st.set_page_config(page_title="Master Data", page_icon="\U0001F4E6", layout="wide")
render_table_page(MASTER_CONFIG)
