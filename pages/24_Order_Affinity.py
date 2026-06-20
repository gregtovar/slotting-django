"""Streamlit page: Order Affinity."""
import streamlit as st
from app.config import ORDER_AFFINITY
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Order Affinity", page_icon="\U0001F517", layout="wide")
render_analysis_page(ORDER_AFFINITY)
