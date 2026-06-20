"""
bin_assignment.py
-------------------
Bin-Level Assignment (Capacity-Aware): goes one step further than
Optimal Location by estimating how much physical storage cube each SKU
actually needs, and assigning it real slot codes drawn from the
warehouse's existing location inventory (every distinct
warehouse_location_code currently on file in Master).

Important assumption: this dataset has no real on-hand inventory or
per-slot capacity data, so two things are estimated:
  1. Required on-hand cube per SKU = a "days of supply" assumption
     (default 14 days) x daily velocity x unit volume. This is a
     reasonable proxy (classic inventory-planning approximation), not
     a measured on-hand quantity.
  2. Each physical slot's capacity is assumed to depend only on its
     storage_type (Shelf/Rack/Pallet/Bulk/Cage), using configurable
     cu-ft defaults - real slots of the same type do vary in size, so
     treat this as planning-level guidance, not a guarantee a specific
     SKU will physically fit a specific bin.

The assignment itself is a simple greedy pass: SKUs are processed in
the same priority order as Optimal Location (mismatches on the fastest
movers first), and each claims slots from the pool matching its
recommended storage_type, with the pool sorted by zone ascending - low
zone numbers are assumed to be closer to shipping. This does NOT try
to minimize physical moves from current locations; it's a from-scratch
ideal assignment to use as a re-slotting target.
"""

import math
from collections import defaultdict

from app.analytics.common import build_sku_metrics, current_location_str
from app.analytics.optimal_location import compute_zone_recommendations

CU_IN_PER_CU_FT = 1728.0

DEFAULT_CAPACITY_CU_FT = {
    "Shelf": 2.0,
    "Rack": 8.0,
    "Pallet": 60.0,
    "Bulk": 150.0,
    "Cage": 10.0,
}


def _build_slot_pool(master_rows):
    """One slot per distinct location code currently on file, grouped by storage_type."""
    pool = defaultdict(list)
    seen_codes = set()
    for m in master_rows:
        code = m.get("warehouse_location_code", "")
        storage_type = (m.get("storage_type") or "").strip()
        if not code or not storage_type or code in seen_codes:
            continue
        seen_codes.add(code)
        pool[storage_type].append({"code": code, "zone": m.get("zone", "")})
    for storage_type in pool:
        pool[storage_type].sort(key=lambda s: s["zone"])
    return pool


def run(order_rows, master_rows, start, end, options=None):
    options = options or {}
    days_of_supply = max(0.0, float(options.get("days_of_supply", 14)))
    capacity = dict(DEFAULT_CAPACITY_CU_FT)
    for storage_type in capacity:
        opt_key = f"capacity_{storage_type.lower()}"
        if opt_key in options and str(options[opt_key]).strip():
            try:
                capacity[storage_type] = max(0.01, float(options[opt_key]))
            except ValueError:
                pass

    metrics = build_sku_metrics(order_rows, master_rows, start, end)
    if not metrics:
        return [], "No active SKUs found in Master.", None

    compute_zone_recommendations(metrics)

    for m in metrics:
        onhand_cu_in = days_of_supply * m["units_per_day"] * m["unit_volume_cu_in"]
        m["estimated_onhand_cu_ft"] = onhand_cu_in / CU_IN_PER_CU_FT
        cap = capacity.get(m["recommended_storage_type"], 2.0)
        m["bins_needed"] = max(1, math.ceil(m["estimated_onhand_cu_ft"] / cap)) if cap > 0 else 1

    movement_sort_order = {"Fast": 0, "Medium": 1, "Slow": 2}
    priority_order = sorted(
        metrics,
        key=lambda m: (
            0 if m["action"] != "OK" else 1,
            movement_sort_order.get(m["movement_tier"], 3),
            -m["units_per_day"],
        ),
    )

    pool = _build_slot_pool(master_rows)

    results = []
    for m in priority_order:
        storage_type = m["recommended_storage_type"]
        needed = m["bins_needed"]
        available = pool.get(storage_type, [])
        assigned = available[:needed]
        del available[:needed]

        if len(assigned) >= needed:
            status = "OK"
        elif len(assigned) > 0:
            status = f"Insufficient Capacity (got {len(assigned)} of {needed})"
        else:
            status = "Insufficient Capacity (none available)"

        assigned_codes = [a["code"] for a in assigned]
        codes_display = ", ".join(assigned_codes[:4])
        if len(assigned_codes) > 4:
            codes_display += f", +{len(assigned_codes) - 4} more"

        results.append({
            "sku": m["sku"],
            "product_name": m["product_name"],
            "movement_tier": m["movement_tier"],
            "size_tier": m["size_tier"],
            "recommended_storage_type": storage_type,
            "estimated_onhand_cu_ft": round(m["estimated_onhand_cu_ft"], 2),
            "bins_needed": needed,
            "current_location": current_location_str(m),
            "assigned_bins": codes_display or "(none)",
            "assignment_status": status,
        })

    # keep results readable: same priority order used for the greedy pass
    insufficient = sum(1 for r in results if r["assignment_status"] != "OK")
    total_bins_needed = sum(r["bins_needed"] for r in results)
    summary = (
        f"{len(results)} active SKUs  |  {total_bins_needed:,} bins needed in total "
        f"(at {days_of_supply:.0f} days of supply)  |  {insufficient} SKUs flagged with insufficient capacity"
    )

    status_counts = defaultdict(int)
    for r in results:
        label = "OK" if r["assignment_status"] == "OK" else "Insufficient Capacity"
        status_counts[label] += 1
    chart_spec = {
        "type": "vbar",
        "title": "Bin Assignment Outcomes",
        "value_fmt": "{:,.0f}",
        "items": [("Fully Assigned", status_counts.get("OK", 0)),
                 ("Insufficient Capacity", status_counts.get("Insufficient Capacity", 0))],
    }
    return results, summary, chart_spec
