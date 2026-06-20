"""
warehouse_map.py (web)
-------------------------
The Warehouse Map / Heat Map of Picking Activity page. Unlike the
Tkinter version's custom click-to-drill HeatGrid, this uses a Plotly
icicle chart (built by the shared app.charting.build_warehouse_map_figure,
also used by the Django UI): the full Zone -> Aisle -> Rack -> Shelf ->
Bin hierarchy renders at once, color-coded by picking activity, and
clicking any segment zooms in - that's native Plotly.js behavior, no
custom click-handling code needed.
"""

from datetime import date, timedelta

import streamlit as st

from app.analytics.common import parse_date
from app.analytics.warehouse_map import build_activity_tree
from app.charting import build_warehouse_map_figure, warehouse_map_rows_for_export
from app.web.analysis import _build_presets, _load_orders_and_master


def render_warehouse_map_page(analysis_config):
    st.title(f"{analysis_config.icon} {analysis_config.label}")
    if analysis_config.description:
        st.caption(analysis_config.description)
    st.caption(
        "Click any segment to zoom in; click the center label to zoom back out. "
        "Color = picking activity in the date range below."
    )

    order_rows, master_rows = _load_orders_and_master()

    dates = [d for d in (parse_date(r.get("order_date", "")) for r in order_rows) if d is not None]
    data_min = min(dates) if dates else date.today() - timedelta(days=365)
    data_max = max(dates) if dates else date.today()
    presets = _build_presets(data_max, data_min, data_max)
    preset_names = [p[0] for p in presets]

    preset_key = "warehouse_map_preset"
    start_key = "warehouse_map_start"
    end_key = "warehouse_map_end"

    def _apply_preset():
        chosen = st.session_state[preset_key]
        for name, s, e in presets:
            if name == chosen:
                st.session_state[start_key] = s
                st.session_state[end_key] = e
                return

    if preset_key not in st.session_state:
        st.session_state[preset_key] = "All Time"
        _apply_preset()

    st.subheader("Date Range")
    st.selectbox("Quick range", preset_names, key=preset_key, on_change=_apply_preset)
    col1, col2, col3 = st.columns(3)
    start = col1.date_input("Start", key=start_key)
    end = col2.date_input("End", key=end_key)
    metric = col3.selectbox("Color by", ["order_lines", "units"], key="warehouse_map_metric")

    if start > end:
        st.error("Start date must be on or before the end date.")
        return

    counts = build_activity_tree(order_rows, start, end)
    if not counts:
        st.info("No picking activity recorded in this date range.")
        return

    fig = build_warehouse_map_figure(counts, master_rows, metric)
    st.plotly_chart(fig, width='stretch')

    metric_label = "Order Lines" if metric == "order_lines" else "Units"
    st.caption(f"Coloring by {metric_label}. Leaf-level (Bin) segments show which SKU is homed there on hover.")

    export_rows = warehouse_map_rows_for_export(counts)
    with st.expander("\U0001F4BE Export full activity breakdown to CSV"):
        st.dataframe(export_rows, width='stretch', hide_index=True, height=300)
        import csv
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["location_path", "code", "order_lines", "units"])
        writer.writeheader()
        writer.writerows(export_rows)
        st.download_button(
            "Download CSV", data=buf.getvalue().encode("utf-8"),
            file_name=f"warehouse_map_{start}_{end}.csv", mime="text/csv",
            key="warehouse_map_download",
        )
