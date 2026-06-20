"""Streamlit page: Cube Movement."""
import streamlit as st
from app.config import CUBE_MOVEMENT
from app.web.analysis import render_analysis_page

st.set_page_config(page_title="Cube Movement", page_icon="\U0001F4D0", layout="wide")
render_analysis_page(CUBE_MOVEMENT)
