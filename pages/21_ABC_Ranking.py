"""Streamlit page: ABC Ranking."""
import streamlit as st
from app.config import ABC_RANKING
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="ABC Ranking", page_icon="\U0001F3C6", layout="wide")
render_analysis_page(ABC_RANKING)
