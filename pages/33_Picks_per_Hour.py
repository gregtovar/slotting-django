"""Streamlit page: Picks per Hour."""
import streamlit as st
from app.config import PICKS_PER_HOUR
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Picks per Hour", page_icon="\u23F1", layout="wide")
render_analysis_page(PICKS_PER_HOUR)
