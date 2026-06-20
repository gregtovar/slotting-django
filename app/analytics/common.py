"""
common.py
----------
Shared building blocks for every analysis module.

The central function here is `build_sku_metrics()`. It:
  1. Filters Orders to the selected date range (on `order_date` by default)
  2. Aggregates quantity, revenue, and pick counts per SKU
  3. Joins that against EVERY active SKU in Master (so SKUs with zero
     activity in the date range still show up with zeroed metrics -
     that matters for slotting, since "never moves" is itself a key
     signal for where something should be stored)

Every other analytics module builds on top of this one shared table so
the numbers are guaranteed to be consistent across Velocity, ABC,
Cube Movement, Pick Frequency, and Optimal Location.
"""

from datetime import datetime, date, timedelta


def parse_date(value):
    """Parse a YYYY-MM-DD (optionally with a time portion) string into a date object.
    Returns None if blank/invalid."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # last-resort: try just the first 10 characters as YYYY-MM-DD
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def filter_orders_by_date(order_rows, start: date, end: date, date_field="order_date"):
    """Return only order lines whose date_field falls within [start, end] inclusive."""
    out = []
    for row in order_rows:
        d = parse_date(row.get(date_field, ""))
        if d is not None and start <= d <= end:
            out.append(row)
    return out


def percentile_rank_tiers(rows, metric_field, tier_field,
                          fast_label="Fast", medium_label="Medium", slow_label="Slow",
                          fast_pct=0.20, medium_pct=0.50, higher_is_better=True):
    """
    Assigns a 3-tier label based on percentile rank of metric_field across
    `rows` (mutates rows in place by adding tier_field). Top fast_pct -> fast,
    next (medium_pct - fast_pct) -> medium, the rest -> slow.

    Rows with a zero (or negative) metric value are always forced to
    slow_label regardless of rank - with no real signal (e.g. a SKU with
    zero activity in the selected date range), rank position is
    arbitrary and shouldn't produce a misleading "Fast" label.
    """
    n = len(rows)
    if n == 0:
        return rows
    ordered = sorted(rows, key=lambda r: r.get(metric_field, 0), reverse=higher_is_better)
    fast_cut = max(1, round(n * fast_pct)) if n > 0 else 0
    medium_cut = max(fast_cut, round(n * medium_pct))
    for i, row in enumerate(ordered):
        value = row.get(metric_field, 0)
        if value <= 0:
            row[tier_field] = slow_label
        elif i < fast_cut:
            row[tier_field] = fast_label
        elif i < medium_cut:
            row[tier_field] = medium_label
        else:
            row[tier_field] = slow_label
    return rows


def tercile_tiers(rows, metric_field, tier_field,
                  small_label="Small", medium_label="Medium", large_label="Large"):
    """Buckets rows into three equal-count groups by ascending metric_field."""
    n = len(rows)
    if n == 0:
        return rows
    ordered = sorted(rows, key=lambda r: r.get(metric_field, 0))
    cut1 = max(1, round(n / 3))
    cut2 = max(cut1, round(2 * n / 3))
    for i, row in enumerate(ordered):
        if i < cut1:
            row[tier_field] = small_label
        elif i < cut2:
            row[tier_field] = medium_label
        else:
            row[tier_field] = large_label
    return rows


MASTER_FIELDS_TO_CARRY = [
    "item_number", "product_name", "product_category", "subcategory", "brand",
    "product_status", "unit_of_measure", "cycle_count_class", "stocking_indicator",
    "standard_cost", "selling_price", "weight_lbs", "volume_cubic_in",
    "warehouse_id", "zone", "aisle", "rack", "shelf", "bin",
    "warehouse_location_code", "storage_type",
]


def build_sku_metrics(order_rows, master_rows, start: date, end: date,
                      date_field="order_date", active_only=True):
    """
    Returns a list of dicts, one per SKU in Master (optionally only
    'Active' product_status), with order activity aggregated from
    order_rows filtered to [start, end].

    Each dict contains:
        sku, item_number, product_name, product_category, subcategory, brand,
        storage_type, warehouse_location_code, zone, aisle, rack, shelf, bin,
        unit_volume_cu_in, unit_weight_lbs, unit_cost, unit_price,
        qty_ordered, qty_shipped, order_lines, distinct_orders, revenue,
        total_volume_cu_in, total_weight_lbs,
        days_in_range, units_per_day, picks_per_day, avg_qty_per_pick
    """
    days_in_range = max(1, (end - start).days + 1)

    # Seed one entry per master SKU
    metrics = {}
    for m in master_rows:
        if active_only and m.get("product_status") and m.get("product_status") != "Active":
            continue
        sku = m.get("sku", "")
        if not sku:
            continue
        unit_volume = safe_float(m.get("volume_cubic_in"))
        unit_weight = safe_float(m.get("weight_lbs"))
        metrics[sku] = {
            "sku": sku,
            "item_number": m.get("item_number", ""),
            "product_name": m.get("product_name", ""),
            "product_category": m.get("product_category", ""),
            "subcategory": m.get("subcategory", ""),
            "brand": m.get("brand", ""),
            "storage_type": m.get("storage_type", ""),
            "warehouse_location_code": m.get("warehouse_location_code", ""),
            "zone": m.get("zone", ""),
            "aisle": m.get("aisle", ""),
            "rack": m.get("rack", ""),
            "shelf": m.get("shelf", ""),
            "bin": m.get("bin", ""),
            "unit_volume_cu_in": unit_volume,
            "unit_weight_lbs": unit_weight,
            "unit_cost": safe_float(m.get("standard_cost")),
            "unit_price": safe_float(m.get("selling_price")),
            "qty_ordered": 0,
            "qty_shipped": 0,
            "order_lines": 0,
            "distinct_orders": 0,
            "revenue": 0.0,
            "days_in_range": days_in_range,
        }

    # Aggregate filtered order lines into the seeded metrics
    filtered = filter_orders_by_date(order_rows, start, end, date_field)
    distinct_order_sets = {sku: set() for sku in metrics}

    for row in filtered:
        sku = row.get("sku", "")
        m = metrics.get(sku)
        if m is None:
            continue  # SKU on the order isn't in (active) master - skip
        qty = safe_int(row.get("quantity_ordered"))
        m["qty_ordered"] += qty
        m["qty_shipped"] += safe_int(row.get("quantity_shipped"))
        m["order_lines"] += 1
        m["revenue"] += safe_float(row.get("extended_price"))
        order_no = row.get("order_number", "")
        if order_no:
            distinct_order_sets[sku].add(order_no)

    results = []
    for sku, m in metrics.items():
        m["distinct_orders"] = len(distinct_order_sets.get(sku, ()))
        m["total_volume_cu_in"] = m["unit_volume_cu_in"] * m["qty_ordered"]
        m["total_weight_lbs"] = m["unit_weight_lbs"] * m["qty_ordered"]
        m["units_per_day"] = m["qty_ordered"] / days_in_range
        m["picks_per_day"] = m["order_lines"] / days_in_range
        m["avg_qty_per_pick"] = (m["qty_ordered"] / m["order_lines"]) if m["order_lines"] else 0.0
        results.append(m)

    return results


def current_location_str(row):
    code = row.get("warehouse_location_code", "")
    if code:
        return code
    parts = [row.get(k, "") for k in ("zone", "aisle", "rack", "shelf", "bin")]
    parts = [p for p in parts if p]
    return "-".join(parts) if parts else "(unassigned)"


# ---------------------------------------------------------------------------
# Date-range presets - shared by every UI's "Run" form (Tkinter, Streamlit,
# Django). Anchored to the latest date actually present in the data, not
# wall-clock "today" - see date_range_dialog.py for why.
# ---------------------------------------------------------------------------
def month_start(d: date) -> date:
    return d.replace(day=1)


def prev_month_range(d: date):
    first_this_month = month_start(d)
    last_day_prev_month = first_this_month - timedelta(days=1)
    return month_start(last_day_prev_month), last_day_prev_month


def build_date_presets(anchor: date, data_min: date, data_max: date):
    """Returns a list of (label, start_date, end_date) tuples."""
    return [
        ("Last 7 Days", anchor - timedelta(days=6), anchor),
        ("Last 30 Days", anchor - timedelta(days=29), anchor),
        ("Last 90 Days", anchor - timedelta(days=89), anchor),
        ("This Month", month_start(anchor), anchor),
        ("Last Month", *prev_month_range(anchor)),
        ("Year to Date", date(anchor.year, 1, 1), anchor),
        ("Last 12 Months", anchor - timedelta(days=364), anchor),
        ("All Time", data_min, data_max),
    ]
