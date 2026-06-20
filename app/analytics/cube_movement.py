"""
cube_movement.py
------------------
Cube Movement: total storage volume (and weight) that physically moved
through the warehouse per SKU over the date range - unit cube x quantity
shipped. High-cube movers need space and easy material-handling access
(forklift/pallet zones) regardless of how "fast" they rank by unit count.
"""

from app.analytics.common import build_sku_metrics, current_location_str

CU_IN_PER_CU_FT = 1728.0


def run(order_rows, master_rows, start, end, options=None):
    metrics = build_sku_metrics(order_rows, master_rows, start, end)

    results = []
    for m in metrics:
        total_cu_ft = m["total_volume_cu_in"] / CU_IN_PER_CU_FT
        results.append({
            "sku": m["sku"],
            "product_name": m["product_name"],
            "product_category": m["product_category"],
            "unit_volume_cu_in": round(m["unit_volume_cu_in"], 2),
            "qty_ordered": m["qty_ordered"],
            "total_cube_cu_ft": round(total_cu_ft, 2),
            "unit_weight_lbs": round(m["unit_weight_lbs"], 2),
            "total_weight_lbs": round(m["total_weight_lbs"], 1),
            "storage_type": m["storage_type"],
            "current_location": current_location_str(m),
        })

    results.sort(key=lambda r: r["total_cube_cu_ft"], reverse=True)

    total_cube = sum(r["total_cube_cu_ft"] for r in results)
    total_weight = sum(r["total_weight_lbs"] for r in results)
    summary = (
        f"{len(results)} active SKUs analyzed  |  {total_cube:,.0f} cu ft total cube moved  |  "
        f"{total_weight:,.0f} lbs total weight moved"
    )
    chart_spec = {
        "type": "hbar",
        "title": "Top 15 SKUs by Total Cube Moved",
        "value_fmt": "{:,.0f} cu ft",
        "items": [(r["sku"], r["total_cube_cu_ft"]) for r in results[:15]],
    }
    return results, summary, chart_spec
