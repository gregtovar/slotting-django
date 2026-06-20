"""Streamlit page: Optimal Location."""
import streamlit as st
from app.config import OPTIMAL_LOCATION
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Optimal Location", page_icon="\U0001F3AF", layout="wide")
render_analysis_page(OPTIMAL_LOCATION)
