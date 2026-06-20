"""
orders_reports.py
-------------------
Operational order-level dashboard reports (as opposed to the SKU-level
slotting analyses in velocity.py / abc_ranking.py / etc.). Each function
returns (results, summary, chart_spec) - chart_spec is a ready-to-render
dict consumed by app/ui/charts.py via ResultsView.
"""

from collections import defaultdict
from datetime import date, timedelta

from app.analytics.common import filter_orders_by_date, safe_float, safe_int


# ---------------------------------------------------------------------------
def orders_by_status(order_rows, master_rows, start, end, options=None):
    filtered = filter_orders_by_date(order_rows, start, end)
    by_status = defaultdict(lambda: {"order_lines": 0, "orders": set(), "revenue": 0.0})

    for row in filtered:
        status = row.get("order_status", "(unknown)") or "(unknown)"
        bucket = by_status[status]
        bucket["order_lines"] += 1
        bucket["orders"].add(row.get("order_number", ""))
        bucket["revenue"] += safe_float(row.get("extended_price"))

    total_lines = sum(b["order_lines"] for b in by_status.values()) or 1

    results = []
    for status, b in by_status.items():
        results.append({
            "status": status,
            "order_lines": b["order_lines"],
            "distinct_orders": len(b["orders"]),
            "revenue": round(b["revenue"], 2),
            "pct_of_lines": round(b["order_lines"] / total_lines * 100, 1),
        })
    results.sort(key=lambda r: r["order_lines"], reverse=True)

    chart_spec = {
        "type": "vbar",
        "title": "Order Lines by Status",
        "value_fmt": "{:,.0f}",
        "items": [(r["status"], r["order_lines"]) for r in results],
    }
    summary = f"{len(filtered):,} order lines across {len(results)} statuses in range"
    return results, summary, chart_spec


# ---------------------------------------------------------------------------
def _bucket_label_and_key(d: date, granularity: str):
    if granularity == "day":
        return d.isoformat(), d.isoformat()
    if granularity == "week":
        # ISO week start (Monday)
        week_start = d - timedelta(days=d.weekday())
        return f"Wk of {week_start.isoformat()}", week_start.isoformat()
    # month
    return d.strftime("%Y-%m"), d.strftime("%Y-%m")


def orders_trend_by_day(order_rows, master_rows, start, end, options=None):
    options = options or {}
    days = (end - start).days + 1
    granularity = options.get("granularity", "auto")
    if granularity == "auto" or not granularity:
        if days <= 90:
            granularity = "day"
        elif days <= 540:
            granularity = "week"
        else:
            granularity = "month"

    filtered = filter_orders_by_date(order_rows, start, end)
    buckets = defaultdict(lambda: {"label": "", "orders": set(), "units": 0, "revenue": 0.0})

    from app.analytics.common import parse_date
    for row in filtered:
        d = parse_date(row.get("order_date", ""))
        if d is None:
            continue
        label, key = _bucket_label_and_key(d, granularity)
        b = buckets[key]
        b["label"] = label
        b["orders"].add(row.get("order_number", ""))
        b["units"] += safe_int(row.get("quantity_ordered"))
        b["revenue"] += safe_float(row.get("extended_price"))

    results = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        results.append({
            "period": b["label"],
            "order_count": len(b["orders"]),
            "units": b["units"],
            "revenue": round(b["revenue"], 2),
        })

    chart_spec = {
        "type": "line",
        "title": f"Order Volume Trend (by {granularity})",
        "value_fmt": "{:,.0f}",
        "items": [(r["period"], r["order_count"]) for r in results],
    }
    summary = f"{len(results)} {granularity} buckets  |  {sum(r['order_count'] for r in results):,} total orders"
    return results, summary, chart_spec


# ---------------------------------------------------------------------------
def orders_by_customer_top10(order_rows, master_rows, start, end, options=None):
    options = options or {}
    rank_by = options.get("rank_by", "Order Count")
    top_n = int(options.get("top_n", 10))

    filtered = filter_orders_by_date(order_rows, start, end)
    by_customer = defaultdict(lambda: {"name": "", "orders": set(), "order_lines": 0,
                                        "units": 0, "revenue": 0.0})

    for row in filtered:
        cust_id = row.get("customer_id", "")
        b = by_customer[cust_id]
        b["name"] = row.get("customer_name", cust_id)
        b["orders"].add(row.get("order_number", ""))
        b["order_lines"] += 1
        b["units"] += safe_int(row.get("quantity_ordered"))
        b["revenue"] += safe_float(row.get("extended_price"))

    rows = []
    for cust_id, b in by_customer.items():
        rows.append({
            "customer_id": cust_id,
            "customer_name": b["name"],
            "distinct_orders": len(b["orders"]),
            "order_lines": b["order_lines"],
            "units": b["units"],
            "revenue": round(b["revenue"], 2),
        })

    sort_field = "revenue" if rank_by == "Revenue" else "distinct_orders"
    rows.sort(key=lambda r: r[sort_field], reverse=True)
    results = rows[:top_n]

    value_fmt = "${:,.0f}" if rank_by == "Revenue" else "{:,.0f}"
    chart_spec = {
        "type": "hbar",
        "title": f"Top {top_n} Customers by {rank_by}",
        "value_fmt": value_fmt,
        "items": [(r["customer_name"], r[sort_field]) for r in results],
    }
    summary = f"{len(by_customer):,} distinct customers in range  |  ranked by {rank_by}"
    return results, summary, chart_spec


# ---------------------------------------------------------------------------
def picks_per_hour(order_rows, master_rows, start, end, options=None):
    """
    Approximates Picks per Hour using each order line's created_timestamp
    as a proxy for when it was picked/processed (no dedicated pick-event
    or labor-hours data exists in this dataset). Buckets all picks by
    hour-of-day (00-23) across the whole date range, then divides by the
    number of days in range to get an average picks/hour rate - this is
    a throughput-by-time-of-day view, not a true labor-productivity PPH
    (units picked per labor-hour worked), since no labor hours are
    tracked here.
    """
    from app.analytics.common import parse_date

    filtered = filter_orders_by_date(order_rows, start, end)
    days_in_range = max(1, (end - start).days + 1)

    hour_counts = {h: 0 for h in range(24)}
    hour_units = {h: 0 for h in range(24)}
    for row in filtered:
        ts = row.get("created_timestamp", "")
        if not ts or len(ts) < 13:
            continue
        try:
            hour = int(ts[11:13])
        except ValueError:
            continue
        if 0 <= hour <= 23:
            hour_counts[hour] += 1
            hour_units[hour] += safe_int(row.get("quantity_ordered"))

    results = []
    for h in range(24):
        results.append({
            "hour": f"{h:02d}:00",
            "total_picks": hour_counts[h],
            "avg_picks_per_hour": round(hour_counts[h] / days_in_range, 2),
            "avg_units_per_hour": round(hour_units[h] / days_in_range, 2),
        })

    chart_spec = {
        "type": "vbar",
        "title": "Average Picks per Hour of Day",
        "value_fmt": "{:.1f}",
        "items": [(r["hour"], r["avg_picks_per_hour"]) for r in results],
    }
    peak_hour = max(results, key=lambda r: r["avg_picks_per_hour"])
    summary = (
        f"{sum(hour_counts.values()):,} total picks over {days_in_range} days  |  "
        f"busiest hour: {peak_hour['hour']} ({peak_hour['avg_picks_per_hour']:.1f} picks/hr avg)"
    )
    return results, summary, chart_spec


# ---------------------------------------------------------------------------
def orders_by_zone(order_rows, master_rows, start, end, options=None):
    filtered = filter_orders_by_date(order_rows, start, end)
    by_zone = defaultdict(lambda: {"order_lines": 0, "orders": set(), "units": 0})

    for row in filtered:
        zone = row.get("zone", "") or "(unassigned)"
        b = by_zone[zone]
        b["order_lines"] += 1
        b["orders"].add(row.get("order_number", ""))
        b["units"] += safe_int(row.get("quantity_ordered"))

    total_lines = sum(b["order_lines"] for b in by_zone.values()) or 1

    results = []
    for zone, b in by_zone.items():
        results.append({
            "zone": zone,
            "order_lines": b["order_lines"],
            "distinct_orders": len(b["orders"]),
            "units": b["units"],
            "pct_of_lines": round(b["order_lines"] / total_lines * 100, 1),
        })
    results.sort(key=lambda r: r["zone"])

    chart_spec = {
        "type": "vbar",
        "title": "Order Lines by Warehouse Zone",
        "value_fmt": "{:,.0f}",
        "items": [(r["zone"], r["order_lines"]) for r in results],
    }
    summary = f"{total_lines:,} order lines across {len(results)} zones in range"
    return results, summary, chart_spec
