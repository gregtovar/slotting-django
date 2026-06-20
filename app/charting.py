"""
charting.py
------------
Converts the chart_spec dicts produced by app/analytics/* into Plotly
figures. Framework-agnostic - both the Streamlit UI (app/web/) and the
Django UI (slotting/) import from here, so chart support for every
analytics module works on any front end for free.

Deliberately does NOT import app.theme (which imports tkinter) - see
app/colors.py for why.
"""

import plotly.graph_objects as go

from app import colors as Palette

AXIS_GRID_COLOR = Palette.BORDER


def render_chart_spec(spec):
    """spec -> a plotly Figure, or None if spec is empty/unsupported."""
    if not spec or not spec.get("items"):
        return None

    chart_type = spec.get("type")
    title = spec.get("title", "")
    value_fmt = spec.get("value_fmt", "{:,.0f}")

    if chart_type == "hbar":
        return _hbar(spec["items"], title, value_fmt)
    if chart_type == "vbar":
        return _vbar(spec["items"], title, value_fmt)
    if chart_type == "line":
        return _line(spec["items"], title, value_fmt)
    if chart_type == "pareto":
        return _pareto(spec["items"], title)
    return None


def _base_layout(title, height):
    return dict(
        title=dict(text=title, font=dict(color=Palette.NAVY, size=16)),
        margin=dict(l=10, r=20, t=46, b=10),
        height=height,
        plot_bgcolor=Palette.PANEL,
        paper_bgcolor=Palette.PANEL,
        font=dict(color=Palette.TEXT),
        xaxis=dict(gridcolor=AXIS_GRID_COLOR),
        yaxis=dict(gridcolor=AXIS_GRID_COLOR),
    )


def _hbar(items, title, value_fmt):
    items = list(items)[::-1]  # reverse so the #1 item ends up on top
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    text = [value_fmt.format(v) for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=Palette.TEAL, text=text, textposition="outside",
    ))
    fig.update_layout(**_base_layout(title, max(280, 30 * len(items) + 60)))
    fig.update_yaxes(automargin=True)
    return fig


def _vbar(items, title, value_fmt):
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    text = [value_fmt.format(v) for v in values]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=Palette.TEAL, text=text, textposition="outside",
    ))
    fig.update_layout(**_base_layout(title, 380))
    return fig


def _line(items, title, value_fmt):
    labels = [str(label) for label, _ in items]
    values = [v for _, v in items]
    fig = go.Figure(go.Scatter(
        x=labels, y=values, mode="lines+markers", line=dict(color=Palette.TEAL, width=2),
        marker=dict(size=6),
    ))
    fig.update_layout(**_base_layout(title, 380))
    return fig


def _pareto(items, title):
    labels = [str(label) for label, _, _ in items]
    values = [v for _, v, _ in items]
    cum_pct = [c for _, _, c in items]
    fig = go.Figure()
    fig.add_bar(x=labels, y=values, name="Value", marker_color=Palette.TEAL)
    fig.add_trace(go.Scatter(
        x=labels, y=cum_pct, name="Cumulative %", yaxis="y2",
        line=dict(color=Palette.AMBER, width=2), mode="lines+markers",
    ))
    layout = _base_layout(title, 440)
    layout["yaxis2"] = dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105])
    layout["legend"] = dict(orientation="h", y=1.15)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Warehouse Map - shared icicle-chart builder (Streamlit and Django both
# call this with the same activity tree, and just embed the resulting
# Figure differently: st.plotly_chart(fig) vs fig.to_html(...)).
# ---------------------------------------------------------------------------
HEAT_SCALE = [Palette.BORDER, Palette.TEAL, Palette.AMBER, Palette.RED]


def build_warehouse_map_figure(counts, master_rows, metric="order_lines"):
    """
    counts: the dict returned by app.analytics.warehouse_map.build_activity_tree()
    master_rows: Master table rows (for the leaf-level "which SKU lives here" hover info)
    metric: "order_lines" or "units" - which count colors/sizes the chart
    Returns a Plotly Figure, or None if counts is empty.
    """
    import plotly.express as px
    from app.analytics.warehouse_map import skus_at_location, LEVELS

    if not counts:
        return None

    rows = []
    grand_total_lines = sum(v["order_lines"] for k, v in counts.items() if len(k) == 1)
    grand_total_units = sum(v["units"] for k, v in counts.items() if len(k) == 1)
    rows.append({
        "id": "", "parent": "", "label": "Warehouse",
        "order_lines": grand_total_lines, "units": grand_total_units, "info": "",
    })

    for path, vals in counts.items():
        node_id = "/".join(path)
        parent_id = "/".join(path[:-1])
        info = ""
        if len(path) == len(LEVELS):
            skus = skus_at_location(master_rows, path)
            if skus:
                info = ", ".join(f"{s['sku']} ({s['product_name']})" for s in skus[:3])
        rows.append({
            "id": node_id, "parent": parent_id, "label": path[-1],
            "order_lines": vals["order_lines"], "units": vals["units"], "info": info,
        })

    fig = px.icicle(
        rows, ids="id", parents="parent", names="label", values=metric,
        color=metric, color_continuous_scale=HEAT_SCALE, branchvalues="total",
        hover_data={"order_lines": True, "units": True, "info": True},
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=650)
    return fig


def warehouse_map_rows_for_export(counts):
    """Flat list of dicts (location_path, code, order_lines, units) for CSV export."""
    rows = []
    for path, vals in counts.items():
        rows.append({
            "location_path": "/".join(path),
            "code": path[-1],
            "order_lines": vals["order_lines"],
            "units": vals["units"],
        })
    rows.sort(key=lambda r: r["location_path"])
    return rows
