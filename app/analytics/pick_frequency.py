"""
pick_frequency.py
-------------------
Pick Frequency: how often a SKU is *touched* - i.e. the number of order
lines (picks) and distinct orders it appears on - regardless of the
quantity per pick. This is deliberately separate from Velocity: picking
1 unit 20 times costs far more travel time than picking 20 units once,
even though both have the same total quantity. Pick frequency is usually
the stronger driver of "closeness to the pick face" in a slotting plan.
"""

from app.analytics.common import build_sku_metrics, percentile_rank_tiers, current_location_str


def run(order_rows, master_rows, start, end, options=None):
    metrics = build_sku_metrics(order_rows, master_rows, start, end)
    percentile_rank_tiers(metrics, "picks_per_day", "frequency_tier",
                          fast_label="Hot", medium_label="Warm", slow_label="Cold")

    results = []
    for m in metrics:
        results.append({
            "sku": m["sku"],
            "product_name": m["product_name"],
            "product_category": m["product_category"],
            "order_lines": m["order_lines"],
            "distinct_orders": m["distinct_orders"],
            "avg_qty_per_pick": round(m["avg_qty_per_pick"], 2),
            "picks_per_day": round(m["picks_per_day"], 3),
            "frequency_tier": m["frequency_tier"],
            "current_location": current_location_str(m),
            "storage_type": m["storage_type"],
        })

    results.sort(key=lambda r: r["picks_per_day"], reverse=True)

    total_picks = sum(r["order_lines"] for r in results)
    hot_count = sum(1 for r in results if r["frequency_tier"] == "Hot")
    summary = (
        f"{len(results)} active SKUs analyzed  |  {total_picks:,} total picks (order lines)  |  "
        f"{hot_count} classified Hot"
    )
    chart_spec = {
        "type": "hbar",
        "title": "Top 15 SKUs by Pick Frequency",
        "value_fmt": "{:.3f}/day",
        "items": [(r["sku"], r["picks_per_day"]) for r in results[:15]],
    }
    return results, summary, chart_spec
