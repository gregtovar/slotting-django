"""
velocity.py
------------
SKU Velocity: how fast each SKU moves out the door, in units per day,
over the selected date range. This is one of the two core inputs (along
with Pick Frequency) into the Optimal Warehouse Location recommendation.
"""

from app.analytics.common import build_sku_metrics, percentile_rank_tiers, current_location_str


def run(order_rows, master_rows, start, end, options=None):
    metrics = build_sku_metrics(order_rows, master_rows, start, end)
    percentile_rank_tiers(metrics, "units_per_day", "velocity_tier",
                          fast_label="Fast", medium_label="Medium", slow_label="Slow")

    results = []
    for m in metrics:
        results.append({
            "sku": m["sku"],
            "product_name": m["product_name"],
            "product_category": m["product_category"],
            "brand": m["brand"],
            "qty_ordered": m["qty_ordered"],
            "order_lines": m["order_lines"],
            "distinct_orders": m["distinct_orders"],
            "units_per_day": round(m["units_per_day"], 2),
            "velocity_tier": m["velocity_tier"],
            "current_location": current_location_str(m),
            "storage_type": m["storage_type"],
        })

    results.sort(key=lambda r: r["units_per_day"], reverse=True)

    total_units = sum(r["qty_ordered"] for r in results)
    fast_count = sum(1 for r in results if r["velocity_tier"] == "Fast")
    summary = (
        f"{len(results)} active SKUs analyzed  |  {total_units:,} total units ordered  |  "
        f"{fast_count} classified Fast"
    )
    chart_spec = {
        "type": "hbar",
        "title": "Top 15 SKUs by Velocity (Units/Day)",
        "value_fmt": "{:.2f}/day",
        "items": [(r["sku"], r["units_per_day"]) for r in results[:15]],
    }
    return results, summary, chart_spec
