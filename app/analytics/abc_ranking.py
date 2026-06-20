"""
abc_ranking.py
---------------
Classic ABC (Pareto) classification: ranks SKUs by a chosen metric,
then classifies them as A (top ~80% of cumulative value), B (next ~15%),
or C (remaining ~5%) - the thresholds are adjustable via options.
"""

from app.analytics.common import build_sku_metrics, current_location_str

METRIC_CHOICES = {
    "Revenue": "revenue",
    "Quantity": "qty_ordered",
    "Pick Frequency (Order Lines)": "order_lines",
}


def run(order_rows, master_rows, start, end, options=None):
    options = options or {}
    metric_label = options.get("metric", "Revenue")
    metric_field = METRIC_CHOICES.get(metric_label, "revenue")
    a_threshold = float(options.get("a_threshold", 80))
    b_threshold = float(options.get("b_threshold", 95))

    metrics = build_sku_metrics(order_rows, master_rows, start, end)
    metrics.sort(key=lambda m: m[metric_field], reverse=True)

    total = sum(m[metric_field] for m in metrics) or 1.0
    running = 0.0
    results = []
    for i, m in enumerate(metrics, start=1):
        value = m[metric_field]
        running += value
        pct_of_total = (value / total) * 100
        cumulative_pct = (running / total) * 100
        if cumulative_pct <= a_threshold:
            klass = "A"
        elif cumulative_pct <= b_threshold:
            klass = "B"
        else:
            klass = "C"
        results.append({
            "rank": i,
            "sku": m["sku"],
            "product_name": m["product_name"],
            "product_category": m["product_category"],
            "metric_value": round(value, 2),
            "pct_of_total": round(pct_of_total, 2),
            "cumulative_pct": round(cumulative_pct, 2),
            "abc_class": klass,
            "current_location": current_location_str(m),
        })

    a_count = sum(1 for r in results if r["abc_class"] == "A")
    b_count = sum(1 for r in results if r["abc_class"] == "B")
    c_count = sum(1 for r in results if r["abc_class"] == "C")
    summary = (
        f"Classified by {metric_label}  |  {len(results)} SKUs  |  "
        f"A: {a_count}   B: {b_count}   C: {c_count}"
    )
    chart_spec = {
        "type": "pareto",
        "title": f"Pareto \u2013 Top 30 SKUs by {metric_label}",
        "items": [(r["sku"], r["metric_value"], r["cumulative_pct"]) for r in results[:30]],
    }
    return results, summary, chart_spec
