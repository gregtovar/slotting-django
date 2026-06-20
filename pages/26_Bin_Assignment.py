"""Streamlit page: Bin Assignment."""
import streamlit as st
from app.config import BIN_ASSIGNMENT
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Bin Assignment", page_icon="\U0001F4E6", layout="wide")
render_analysis_page(BIN_ASSIGNMENT)
