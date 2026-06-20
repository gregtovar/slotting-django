"""
analysis.py (web)
--------------------
Generic Streamlit page for any AnalysisConfig (the 7 Slotting Analysis
modules and 5 of the 6 Reports & Dashboards - Warehouse Map gets its
own page, see warehouse_map.py). Mirrors the Tkinter app's
DateRangeDialog -> ResultsView flow: pick a date range (+ options),
run, see a chart + sortable grid, export to CSV.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.config import ORDERS_CONFIG, MASTER_CONFIG
from app.data_manager import DataManager
from app.analytics.common import parse_date, build_date_presets
from app.analytics.runner import run_analysis
from app.charting import render_chart_spec


def _build_presets(anchor: date, data_min: date, data_max: date):
    return build_date_presets(anchor, data_min, data_max)


@st.cache_data(ttl=60, show_spinner=False)
def _load_orders_and_master():
    orders_dm = DataManager(ORDERS_CONFIG)
    orders_dm.load()
    master_dm = DataManager(MASTER_CONFIG)
    master_dm.load()
    return orders_dm.all_rows(), master_dm.all_rows()


def _render_options_form(analysis_config):
    options = {}
    if not analysis_config.options:
        return options
    st.subheader("Options")
    for opt in analysis_config.options:
        widget_key = f"{analysis_config.key}_opt_{opt.name}"
        if opt.type == "choice" and opt.choices:
            default_index = opt.choices.index(opt.default) if opt.default in opt.choices else 0
            options[opt.name] = st.selectbox(
                opt.label, opt.choices, index=default_index, key=widget_key, help=opt.help or None,
            )
        elif opt.type == "int":
            default_val = int(float(opt.default)) if opt.default else 0
            options[opt.name] = st.number_input(
                opt.label, value=default_val, step=1, key=widget_key, help=opt.help or None,
            )
        elif opt.type == "float":
            default_val = float(opt.default) if opt.default else 0.0
            options[opt.name] = st.number_input(
                opt.label, value=default_val, key=widget_key, help=opt.help or None,
            )
        else:
            options[opt.name] = st.text_input(
                opt.label, value=opt.default, key=widget_key, help=opt.help or None,
            )
    return options


def render_analysis_page(analysis_config):
    st.title(f"{analysis_config.icon} {analysis_config.label}")
    if analysis_config.description:
        st.caption(analysis_config.description)

    order_rows, master_rows = _load_orders_and_master()

    dates = [d for d in (parse_date(r.get("order_date", "")) for r in order_rows) if d is not None]
    data_min = min(dates) if dates else date.today() - timedelta(days=365)
    data_max = max(dates) if dates else date.today()
    presets = _build_presets(data_max, data_min, data_max)
    preset_names = [p[0] for p in presets]

    preset_key = f"{analysis_config.key}_preset"
    start_key = f"{analysis_config.key}_start"
    end_key = f"{analysis_config.key}_end"

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
    st.caption(
        f"Data on file spans {data_min.isoformat()} to {data_max.isoformat()} "
        "(presets are anchored to the latest date in your data, not today's date)."
    )
    st.selectbox("Quick range", preset_names, key=preset_key, on_change=_apply_preset)

    col1, col2 = st.columns(2)
    start = col1.date_input("Start", key=start_key)
    end = col2.date_input("End", key=end_key)

    options = _render_options_form(analysis_config)

    run_clicked = st.button("\u25B6\uFE0F Run Analysis", type="primary", key=f"{analysis_config.key}_run")

    state_key = f"{analysis_config.key}_results"

    if run_clicked:
        if start > end:
            st.error("Start date must be on or before the end date.")
        else:
            with st.spinner(f"Running {analysis_config.label}..."):
                try:
                    results, summary, chart_spec = run_analysis(
                        analysis_config.key, order_rows, master_rows, start, end, options
                    )
                    st.session_state[state_key] = {
                        "results": results, "summary": summary, "chart_spec": chart_spec,
                        "start": start, "end": end, "error": None,
                    }
                except Exception as exc:  # noqa: BLE001
                    st.session_state[state_key] = {"error": str(exc)}

    if state_key in st.session_state:
        payload = st.session_state[state_key]
        if payload.get("error"):
            st.error(f"Something went wrong while running this analysis:\n\n{payload['error']}")
        else:
            results = payload["results"]
            st.success(payload["summary"])

            chart_spec = payload["chart_spec"]
            if chart_spec:
                fig = render_chart_spec(chart_spec)
                if fig:
                    show_chart = st.checkbox("Show chart", value=True, key=f"{analysis_config.key}_show_chart")
                    if show_chart:
                        st.plotly_chart(fig, width='stretch')

            if results:
                col_specs = analysis_config.result_columns
                col_names = [c.name for c in col_specs] if col_specs else list(results[0].keys())
                df = pd.DataFrame(results, columns=col_names)
                rename_map = {c.name: c.label for c in col_specs}

                search = st.text_input("Search results", key=f"{analysis_config.key}_search")
                display_df = df
                if search:
                    mask = df.astype(str).apply(lambda r: r.str.contains(search, case=False, na=False).any(), axis=1)
                    display_df = df[mask]

                st.dataframe(
                    display_df.rename(columns=rename_map),
                    width='stretch', hide_index=True, height=460,
                )
                st.caption(f"{len(display_df):,} of {len(df):,} rows shown")

                csv_bytes = display_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "\U0001F4BE Export to CSV", data=csv_bytes,
                    file_name=f"{analysis_config.key}_{payload['start']}_{payload['end']}.csv",
                    mime="text/csv", key=f"{analysis_config.key}_download",
                )
            else:
                st.info("No rows in this date range.")
