"""Streamlit page: SKU Velocity."""
import streamlit as st
from app.config import SKU_VELOCITY
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="SKU Velocity", page_icon="\U0001F680", layout="wide")
render_analysis_page(SKU_VELOCITY)
