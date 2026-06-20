"""
optimal_location.py
---------------------
Optimal Warehouse Location: combines movement (a blend of pick frequency
and unit velocity) with item size (unit cube) to recommend a storage
*zone class* for each SKU, then flags whether the current storage_type
on file matches that recommendation.

This is intentionally a zone-class recommendation (Golden / Standard /
Bulk, plus a suggested storage_type), not a specific bin assignment.
For an actual bin-level, capacity-aware assignment see bin_assignment.py,
which builds on `compute_zone_recommendations()` below.
"""

from app.analytics.common import build_sku_metrics, tercile_tiers, current_location_str

# Recommended zone class + suggested storage type, keyed by (movement_tier, size_tier)
ZONE_MATRIX = {
    ("Fast", "Small"): ("Golden Zone \u2013 Forward Pick Face", "Shelf"),
    ("Fast", "Medium"): ("Golden Zone \u2013 Forward Pick Face", "Rack"),
    ("Fast", "Large"): ("Golden Zone \u2013 Ground-Level Bulk/Pallet", "Pallet"),
    ("Medium", "Small"): ("Standard Reserve \u2013 Mid-Aisle Shelving", "Shelf"),
    ("Medium", "Medium"): ("Standard Reserve \u2013 Mid-Aisle Racking", "Rack"),
    ("Medium", "Large"): ("Standard Reserve \u2013 Pallet Rack", "Pallet"),
    ("Slow", "Small"): ("Upper Reserve \u2013 Slow-Mover Shelving", "Shelf"),
    ("Slow", "Medium"): ("Upper Reserve \u2013 Slow-Mover Shelving", "Shelf"),
    ("Slow", "Large"): ("Bulk/Overflow Storage \u2013 Far Zone", "Bulk"),
}

# Which current storage_type values are considered an acceptable match
# for a given recommended storage_type
ACCEPTABLE_MATCH = {
    "Shelf": {"Shelf", "Rack"},
    "Rack": {"Rack", "Shelf", "Pallet"},
    "Pallet": {"Pallet", "Rack", "Bulk"},
    "Bulk": {"Bulk", "Cage", "Pallet"},
}


def compute_zone_recommendations(metrics):
    """
    Takes the output of build_sku_metrics() and annotates each row IN
    PLACE with: movement_rank_pct, movement_tier, size_tier,
    recommended_zone, recommended_storage_type, action.
    Returns the same list (now enriched) for convenience.
    """
    n = len(metrics)
    if n == 0:
        return metrics

    by_units = sorted(metrics, key=lambda m: m["units_per_day"], reverse=True)
    by_picks = sorted(metrics, key=lambda m: m["picks_per_day"], reverse=True)
    units_rank = {m["sku"]: i for i, m in enumerate(by_units)}
    picks_rank = {m["sku"]: i for i, m in enumerate(by_picks)}

    for m in metrics:
        avg_rank = (units_rank[m["sku"]] + picks_rank[m["sku"]]) / 2.0
        m["movement_rank_pct"] = avg_rank / max(1, n - 1)  # 0 = most active, 1 = least

    fast_cut = max(1, round(n * 0.20))
    medium_cut = max(fast_cut, round(n * 0.50))
    ordered_by_movement = sorted(metrics, key=lambda m: m["movement_rank_pct"])
    for i, m in enumerate(ordered_by_movement):
        no_activity = m["units_per_day"] <= 0 and m["picks_per_day"] <= 0
        if no_activity:
            m["movement_tier"] = "Slow"
        elif i < fast_cut:
            m["movement_tier"] = "Fast"
        elif i < medium_cut:
            m["movement_tier"] = "Medium"
        else:
            m["movement_tier"] = "Slow"

    tercile_tiers(metrics, "unit_volume_cu_in", "size_tier",
                  small_label="Small", medium_label="Medium", large_label="Large")

    for m in metrics:
        key = (m["movement_tier"], m["size_tier"])
        recommended_zone, recommended_storage_type = ZONE_MATRIX.get(key, ("Standard Reserve", "Rack"))
        current_storage = (m.get("storage_type") or "").strip()
        acceptable = ACCEPTABLE_MATCH.get(recommended_storage_type, {recommended_storage_type})
        is_match = current_storage in acceptable if current_storage else False
        m["recommended_zone"] = recommended_zone
        m["recommended_storage_type"] = recommended_storage_type
        m["action"] = "OK" if is_match else "Review / Relocate"

    return metrics


def run(order_rows, master_rows, start, end, options=None):
    metrics = build_sku_metrics(order_rows, master_rows, start, end)
    if not metrics:
        return [], "No active SKUs found in Master.", None

    compute_zone_recommendations(metrics)

    results = []
    for m in metrics:
        results.append({
            "sku": m["sku"],
            "product_name": m["product_name"],
            "product_category": m["product_category"],
            "movement_tier": m["movement_tier"],
            "size_tier": m["size_tier"],
            "units_per_day": round(m["units_per_day"], 2),
            "picks_per_day": round(m["picks_per_day"], 3),
            "recommended_zone": m["recommended_zone"],
            "recommended_storage_type": m["recommended_storage_type"],
            "current_storage_type": (m.get("storage_type") or "").strip() or "(none)",
            "current_location": current_location_str(m),
            "action": m["action"],
        })

    # Prioritize: biggest opportunities first - mismatches on the fastest movers
    movement_sort_order = {"Fast": 0, "Medium": 1, "Slow": 2}
    results.sort(key=lambda r: (
        0 if r["action"] != "OK" else 1,
        movement_sort_order.get(r["movement_tier"], 3),
        -r["units_per_day"],
    ))

    mismatches = sum(1 for r in results if r["action"] != "OK")
    fast_mismatches = sum(1 for r in results if r["action"] != "OK" and r["movement_tier"] == "Fast")
    summary = (
        f"{len(results)} active SKUs analyzed  |  {mismatches} flagged for review  |  "
        f"{fast_mismatches} are Fast-movers currently mis-slotted (highest priority)"
    )
    tier_order = ["Fast", "Medium", "Slow"]
    flagged_by_tier = {t: 0 for t in tier_order}
    for r in results:
        if r["action"] != "OK":
            flagged_by_tier[r["movement_tier"]] = flagged_by_tier.get(r["movement_tier"], 0) + 1
    chart_spec = {
        "type": "vbar",
        "title": "SKUs Flagged for Relocation, by Movement Tier",
        "value_fmt": "{:,.0f}",
        "items": [(t, flagged_by_tier[t]) for t in tier_order],
    }
    return results, summary, chart_spec
