"""Streamlit page: Warehouse Map / Picking Heat Map."""
import streamlit as st
from app.config import WAREHOUSE_MAP
from app.web.warehouse_map import render_warehouse_map_page

st.set_page_config(page_title="Warehouse Map", page_icon="\U0001F525", layout="wide")
render_warehouse_map_page(WAREHOUSE_MAP)
