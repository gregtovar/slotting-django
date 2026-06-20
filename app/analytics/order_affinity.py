"""
order_affinity.py
-------------------
Order Affinity: finds pairs of SKUs that frequently appear together on
the same order. Useful for slotting SKUs that are often picked together
near each other, cutting travel distance for combo picks.

Implementation note: this is a simple co-occurrence count (support),
not full market-basket lift/confidence - sufficient for slotting
purposes where the question is "do these two get picked together often
enough that placing them apart costs real travel time?"
"""

from collections import defaultdict
from itertools import combinations

from app.analytics.common import filter_orders_by_date


def run(order_rows, master_rows, start, end, options=None):
    options = options or {}
    min_cooccurrence = int(options.get("min_cooccurrence", 2))
    max_pairs = int(options.get("max_pairs", 300))

    master_lookup = {m.get("sku", ""): m for m in master_rows}

    filtered = filter_orders_by_date(order_rows, start, end)

    # Group SKUs by order_number
    order_skus = defaultdict(set)
    for row in filtered:
        sku = row.get("sku", "")
        order_no = row.get("order_number", "")
        if sku and order_no:
            order_skus[order_no].add(sku)

    pair_counts = defaultdict(int)
    sku_order_counts = defaultdict(int)
    for skus in order_skus.values():
        for sku in skus:
            sku_order_counts[sku] += 1
        if len(skus) < 2:
            continue
        for a, b in combinations(sorted(skus), 2):
            pair_counts[(a, b)] += 1

    results = []
    for (sku_a, sku_b), count in pair_counts.items():
        if count < min_cooccurrence:
            continue
        a_orders = sku_order_counts.get(sku_a, 0) or 1
        b_orders = sku_order_counts.get(sku_b, 0) or 1
        master_a = master_lookup.get(sku_a, {})
        master_b = master_lookup.get(sku_b, {})
        results.append({
            "sku_a": sku_a,
            "product_a": master_a.get("product_name", ""),
            "sku_b": sku_b,
            "product_b": master_b.get("product_name", ""),
            "times_together": count,
            "pct_of_a_orders": round((count / a_orders) * 100, 1),
            "pct_of_b_orders": round((count / b_orders) * 100, 1),
        })

    results.sort(key=lambda r: r["times_together"], reverse=True)
    truncated = len(results) > max_pairs
    results = results[:max_pairs]

    summary = (
        f"{len(order_skus):,} orders analyzed  |  {len(results)} SKU pairs shown "
        f"(min {min_cooccurrence} co-occurrences)"
        + ("  |  list truncated to top results, narrow your filters for the full set" if truncated else "")
    )
    chart_spec = {
        "type": "hbar",
        "title": "Top 15 SKU Pairs by Co-Occurrence",
        "value_fmt": "{:,.0f}",
        "items": [(f"{r['sku_a']} + {r['sku_b']}", r["times_together"]) for r in results[:15]],
    }
    return results, summary, chart_spec
