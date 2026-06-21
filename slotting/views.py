"""
views.py
----------
Every view here is thin: load data via DataManager, compute via
app/analytics/*, render. No business logic lives in this file - it's
all already shared with the Tkinter and Streamlit UIs.
"""

import csv
from datetime import date, timedelta

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from app.config import (
    ALL_TABLES, TABLES_BY_KEY, ANALYSES_BY_KEY, REPORTS_BY_KEY,
    ORDERS_CONFIG, MASTER_CONFIG, WAREHOUSE_MAP,
)
from app.data_manager import DataManager, ValidationError
from app.analytics.common import parse_date, build_date_presets
from app.analytics.runner import run_analysis
from app.analytics.warehouse_map import build_activity_tree
from app.charting import render_chart_spec, build_warehouse_map_figure, warehouse_map_rows_for_export

from .forms import build_record_form, build_run_form

CONFIGS_BY_KEY = {**ANALYSES_BY_KEY, **REPORTS_BY_KEY}
PAGE_SIZE = 50


def _resolve_options(cfg, cleaned_data):
    """
    Django form fields with required=False return None in cleaned_data
    when the field is simply absent from the submitted query string
    (e.g. a date-preset link that only sets start/end) - `initial=` does
    NOT supply a fallback in that case, only for rendering. Fall back to
    the AnalysisOption's configured default explicitly here.
    """
    options = {}
    for opt in cfg.options:
        val = cleaned_data.get(f"opt_{opt.name}")
        if val is None or val == "":
            val = opt.default
        options[opt.name] = val
    return options


# ---------------------------------------------------------------------------
def home(request):
    table_counts = []
    for cfg in ALL_TABLES:
        dm = DataManager(cfg)
        dm.load()
        table_counts.append((cfg, dm.row_count()))
    return render(request, "slotting/home.html", {"table_counts": table_counts})


# ---------------------------------------------------------------------------
# Data Management (CRUD)
# ---------------------------------------------------------------------------
def table_list(request, table_key):
    cfg = TABLES_BY_KEY.get(table_key)
    if not cfg:
        raise Http404("Unknown table")

    dm = DataManager(cfg)
    dm.load()
    rows = dm.all_rows()

    search = request.GET.get("q", "").strip()
    if search:
        rows = dm.search(search)

    sort_col = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "asc")
    if sort_col:
        field_spec = cfg.field_map().get(sort_col)
        field_type = field_spec.type if field_spec else "text"
        rows = DataManager.sort_rows(rows, sort_col, reverse=(sort_dir == "desc"), field_type=field_type)

    total = len(rows)
    try:
        page = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page = 1
    total_pages = max(1, -(-total // PAGE_SIZE))
    page = min(page, total_pages)
    start = (page - 1) * PAGE_SIZE
    page_rows = rows[start:start + PAGE_SIZE]

    grid_columns = [cfg.field_map()[name] for name in cfg.grid_fields]
    display_rows = []
    for row in page_rows:
        key_values = [row.get(k, "") for k in cfg.key_fields]
        values = [row.get(c.name, "") for c in grid_columns]
        display_rows.append({"key_values": key_values, "values": values})

    return render(request, "slotting/table_list.html", {
        "cfg": cfg, "rows": display_rows, "grid_columns": grid_columns,
        "search": search, "sort_col": sort_col, "sort_dir": sort_dir,
        "page": page, "total_pages": total_pages, "total": total,
        "row_count": dm.row_count(),
    })


def table_add(request, table_key):
    cfg = TABLES_BY_KEY.get(table_key)
    if not cfg:
        raise Http404("Unknown table")

    dm = DataManager(cfg)
    dm.load()
    FormClass = build_record_form(cfg)

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            try:
                dm.add_row(form.cleaned_data)
                messages.success(request, "Record added.")
                return redirect("table_list", table_key=table_key)
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        initial = {}
        if cfg.id_field and cfg.id_prefix:
            initial[cfg.id_field] = dm.suggest_next_id()
        form = FormClass(initial=initial)

    return render(request, "slotting/table_form.html", {"cfg": cfg, "form": form, "mode": "add"})


def table_edit(request, table_key):
    cfg = TABLES_BY_KEY.get(table_key)
    if not cfg:
        raise Http404("Unknown table")

    key_values = tuple(request.GET.getlist("key")) or tuple(request.POST.getlist("key"))
    if not key_values:
        raise Http404("Missing record key")

    dm = DataManager(cfg)
    dm.load()
    row = dm.get(key_values)
    if row is None:
        raise Http404("Record not found - it may have been deleted")

    FormClass = build_record_form(cfg)

    if request.method == "POST":
        form = FormClass(request.POST)
        if form.is_valid():
            try:
                dm.update_row(key_values, form.cleaned_data)
                messages.success(request, "Record updated.")
                return redirect("table_list", table_key=table_key)
            except ValidationError as e:
                form.add_error(None, str(e))
    else:
        form = FormClass(initial=row)

    return render(request, "slotting/table_form.html", {
        "cfg": cfg, "form": form, "mode": "edit", "key_values": key_values,
    })


def table_delete(request, table_key):
    cfg = TABLES_BY_KEY.get(table_key)
    if not cfg:
        raise Http404("Unknown table")

    key_values = tuple(request.GET.getlist("key")) or tuple(request.POST.getlist("key"))
    if not key_values:
        raise Http404("Missing record key")

    dm = DataManager(cfg)
    dm.load()
    row = dm.get(key_values)

    if request.method == "POST":
        if dm.delete_row(key_values):
            messages.success(request, "Record deleted.")
        else:
            messages.error(request, "Record not found - it may already have been deleted.")
        return redirect("table_list", table_key=table_key)

    return render(request, "slotting/table_confirm_delete.html", {
        "cfg": cfg, "row": row, "key_values": key_values,
    })


# ---------------------------------------------------------------------------
# Slotting Analysis & Reports
# ---------------------------------------------------------------------------
def _data_date_bounds(order_rows):
    dates = [d for d in (parse_date(r.get("order_date", "")) for r in order_rows) if d is not None]
    data_min = min(dates) if dates else date.today() - timedelta(days=365)
    data_max = max(dates) if dates else date.today()
    return data_min, data_max


def analysis_run(request, analysis_key):
    cfg = CONFIGS_BY_KEY.get(analysis_key)
    if not cfg or analysis_key == "warehouse_map":
        raise Http404("Unknown analysis")

    orders_dm = DataManager(ORDERS_CONFIG)
    orders_dm.load()
    master_dm = DataManager(MASTER_CONFIG)
    master_dm.load()
    order_rows, master_rows = orders_dm.all_rows(), master_dm.all_rows()

    data_min, data_max = _data_date_bounds(order_rows)
    presets = build_date_presets(data_max, data_min, data_max)

    FormClass = build_run_form(cfg)
    has_run = "start" in request.GET and "end" in request.GET

    results = summary = chart_html = error = None

    if has_run:
        form = FormClass(request.GET)
        if form.is_valid():
            start, end = form.cleaned_data["start"], form.cleaned_data["end"]
            if start > end:
                error = "Start date must be on or before the end date."
            else:
                options = _resolve_options(cfg, form.cleaned_data)
                try:
                    results, summary, chart_spec = run_analysis(
                        analysis_key, order_rows, master_rows, start, end, options
                    )
                    if chart_spec:
                        fig = render_chart_spec(chart_spec)
                        if fig:
                            chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn",
                                                     config={"displayModeBar": False, "responsive": True})
                except Exception as exc:  # noqa: BLE001
                    error = f"Something went wrong while running this analysis: {exc}"
        else:
            error = "Please correct the highlighted fields."
    else:
        form = FormClass(initial={"start": data_min, "end": data_max})

    search = request.GET.get("q", "").strip()
    display_results = results
    total_count = len(results) if results is not None else 0
    if results and search:
        needle = search.lower()
        display_results = [r for r in results if any(needle in str(v).lower() for v in r.values())]

    DISPLAY_CAP = 500
    truncated = display_results is not None and len(display_results) > DISPLAY_CAP
    if truncated:
        display_results = display_results[:DISPLAY_CAP]

    result_columns = cfg.result_columns
    display_rows = None
    if display_results is not None:
        if result_columns:
            display_rows = [[r.get(c.name, "") for c in result_columns] for r in display_results]
        else:
            result_columns = []
            display_rows = []

    return render(request, "slotting/analysis_run.html", {
        "cfg": cfg, "form": form, "presets": presets,
        "data_min": data_min, "data_max": data_max,
        "result_columns": result_columns, "display_rows": display_rows,
        "result_count": len(display_results) if display_results is not None else 0,
        "total_count": total_count, "truncated": truncated,
        "summary": summary, "chart_html": chart_html, "error": error,
        "search": search, "has_run": has_run,
        "export_query": request.GET.urlencode() if has_run else "",
    })


def analysis_export(request, analysis_key):
    cfg = CONFIGS_BY_KEY.get(analysis_key)
    if not cfg or analysis_key == "warehouse_map":
        raise Http404("Unknown analysis")

    orders_dm = DataManager(ORDERS_CONFIG)
    orders_dm.load()
    master_dm = DataManager(MASTER_CONFIG)
    master_dm.load()

    FormClass = build_run_form(cfg)
    form = FormClass(request.GET)
    if not form.is_valid():
        raise Http404("Invalid or missing date range")

    start, end = form.cleaned_data["start"], form.cleaned_data["end"]
    options = _resolve_options(cfg, form.cleaned_data)
    results, _summary, _chart_spec = run_analysis(
        analysis_key, orders_dm.all_rows(), master_dm.all_rows(), start, end, options
    )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{analysis_key}_{start}_{end}.csv"'
    writer = csv.writer(response)
    if cfg.result_columns:
        cols = [c.name for c in cfg.result_columns]
        writer.writerow([c.label for c in cfg.result_columns])
    else:
        cols = list(results[0].keys()) if results else []
        writer.writerow(cols)
    for row in results:
        writer.writerow([row.get(c, "") for c in cols])
    return response


def warehouse_map_view(request):
    cfg = WAREHOUSE_MAP
    orders_dm = DataManager(ORDERS_CONFIG)
    orders_dm.load()
    master_dm = DataManager(MASTER_CONFIG)
    master_dm.load()
    order_rows, master_rows = orders_dm.all_rows(), master_dm.all_rows()

    data_min, data_max = _data_date_bounds(order_rows)
    presets = build_date_presets(data_max, data_min, data_max)

    start = parse_date(request.GET.get("start", "")) or data_min
    end = parse_date(request.GET.get("end", "")) or data_max
    metric = request.GET.get("metric", "order_lines")
    if metric not in ("order_lines", "units"):
        metric = "order_lines"

    error = chart_html = None
    if start > end:
        error = "Start date must be on or before the end date."
    else:
        counts = build_activity_tree(order_rows, start, end)
        if not counts:
            error = "No picking activity recorded in this date range."
        else:
            fig = build_warehouse_map_figure(counts, master_rows, metric)
            if fig:
                chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn",
                                         config={"displayModeBar": False, "responsive": True})

    return render(request, "slotting/warehouse_map.html", {
        "cfg": cfg, "presets": presets, "data_min": data_min, "data_max": data_max,
        "start": start, "end": end, "metric": metric, "chart_html": chart_html, "error": error,
    })


def warehouse_map_export(request):
    orders_dm = DataManager(ORDERS_CONFIG)
    orders_dm.load()
    order_rows = orders_dm.all_rows()
    data_min, data_max = _data_date_bounds(order_rows)

    start = parse_date(request.GET.get("start", "")) or data_min
    end = parse_date(request.GET.get("end", "")) or data_max
    counts = build_activity_tree(order_rows, start, end)
    rows = warehouse_map_rows_for_export(counts)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="warehouse_map_{start}_{end}.csv"'
    writer = csv.writer(response)
    writer.writerow(["location_path", "code", "order_lines", "units"])
    for row in rows:
        writer.writerow([row["location_path"], row["code"], row["order_lines"], row["units"]])
    return response
