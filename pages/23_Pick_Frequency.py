"""Streamlit page: Pick Frequency."""
import streamlit as st
from app.config import PICK_FREQUENCY
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Pick Frequency", page_icon="\U0001F58F", layout="wide")
render_analysis_page(PICK_FREQUENCY)
