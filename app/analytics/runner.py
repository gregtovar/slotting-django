"""
runner.py
----------
Tiny dispatch layer: maps an AnalysisConfig.key to the compute function
that produces its results. Keeps app_window.py from needing to know
about individual analytics modules.

Every run function returns a 3-tuple: (results, summary, chart_spec).
chart_spec may be None if a chart doesn't make sense for that module.
"""

from app.analytics import (
    velocity, abc_ranking, cube_movement, pick_frequency, order_affinity,
    optimal_location, bin_assignment, orders_reports,
)

RUNNERS = {
    "velocity": velocity.run,
    "abc_ranking": abc_ranking.run,
    "cube_movement": cube_movement.run,
    "pick_frequency": pick_frequency.run,
    "order_affinity": order_affinity.run,
    "optimal_location": optimal_location.run,
    "bin_assignment": bin_assignment.run,
    "orders_by_status": orders_reports.orders_by_status,
    "orders_trend_by_day": orders_reports.orders_trend_by_day,
    "orders_by_customer_top10": orders_reports.orders_by_customer_top10,
    "picks_per_hour": orders_reports.picks_per_hour,
    "orders_by_zone": orders_reports.orders_by_zone,
}


def run_analysis(key, order_rows, master_rows, start, end, options=None):
    fn = RUNNERS.get(key)
    if fn is None:
        raise ValueError(f"Unknown analysis key: {key}")
    return fn(order_rows, master_rows, start, end, options or {})
