"""
tables.py (web)
------------------
Generic Streamlit page for any TableConfig (Customers / Master / Orders):
a read-only search preview, plus a full editable grid (add/edit/delete
rows directly in the grid) saved in one validated batch via
DataManager.replace_all().
"""

import pandas as pd
import streamlit as st

from app.data_manager import DataManager, ValidationError


def _column_config_for(field_spec):
    if field_spec.type == "choice" and field_spec.choices:
        return st.column_config.SelectboxColumn(
            field_spec.label, options=field_spec.choices, required=field_spec.required,
            help=field_spec.help or None,
        )
    if field_spec.type == "int":
        return st.column_config.NumberColumn(
            field_spec.label, required=field_spec.required, format="%d", help=field_spec.help or None,
        )
    if field_spec.type == "float":
        return st.column_config.NumberColumn(
            field_spec.label, required=field_spec.required, help=field_spec.help or None,
        )
    if field_spec.type == "date":
        return st.column_config.TextColumn(
            field_spec.label, required=field_spec.required, help=field_spec.help or "YYYY-MM-DD",
        )
    if field_spec.type == "datetime":
        return st.column_config.TextColumn(
            field_spec.label, required=field_spec.required, help=field_spec.help or "YYYY-MM-DD HH:MM",
        )
    return st.column_config.TextColumn(
        field_spec.label, required=field_spec.required, help=field_spec.help or None,
    )


def render_table_page(table_config):
    st.title(f"{table_config.icon} {table_config.label}")
    if table_config.description:
        st.caption(table_config.description)

    dm = DataManager(table_config)
    dm.load()
    columns = table_config.column_names()
    df = pd.DataFrame(dm.all_rows(), columns=columns)

    st.metric("Records on file", f"{len(df):,}")

    with st.expander("\U0001F50D Search (read-only preview)"):
        search_text = st.text_input("Search", key=f"search_{table_config.key}", label_visibility="collapsed",
                                    placeholder="Search all columns...")
        if search_text:
            mask = df.apply(lambda r: r.astype(str).str.contains(search_text, case=False, na=False).any(), axis=1)
            st.dataframe(df[mask], width='stretch', hide_index=True)
            st.caption(f"{int(mask.sum())} of {len(df)} rows match")

    st.subheader("Edit records")
    st.caption(
        "Add rows with the **+** row at the bottom, delete with the row checkbox + trash icon, "
        "or edit any cell directly. Click **Save Changes** when done - nothing is written to disk until then."
    )

    column_config = {f.name: _column_config_for(f) for f in table_config.fields}

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        width='stretch',
        height=480,
        column_config=column_config,
        key=f"editor_{table_config.key}",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        save_clicked = st.button("\U0001F4BE Save Changes", type="primary", key=f"save_{table_config.key}")

    if save_clicked:
        new_rows = edited_df.fillna("").astype(str).to_dict("records")
        try:
            n = dm.replace_all(new_rows)
            st.cache_data.clear()  # analysis pages cache Orders/Master - invalidate now, not after ttl
            st.success(f"Saved {n:,} records to {table_config.csv_path.name}. A backup of the previous version was kept.")
            st.rerun()
        except ValidationError as e:
            st.error("Couldn't save - please fix the following and try again:\n\n" + str(e))
