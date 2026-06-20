"""Streamlit page: Orders by Zone."""
import streamlit as st
from app.config import ORDERS_BY_ZONE
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Orders by Zone", page_icon="\U0001F5FA", layout="wide")
render_analysis_page(ORDERS_BY_ZONE)
