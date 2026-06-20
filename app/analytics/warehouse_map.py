"""
warehouse_map.py
------------------
Builds the data behind the Warehouse Map / Heat Map of Picking Activity:
a hierarchical aggregation of order-line activity by the physical
location hierarchy Zone -> Aisle -> Rack -> Shelf -> Bin.

Note: this uses the location fields recorded directly on each ORDER
LINE (where the pick actually happened), not Master's static "home"
location for the SKU - that's the correct source for an activity heat
map. Master is only used afterward to show which SKU(s) are nominally
homed at a bin you've drilled into, for context.
"""

from collections import defaultdict

from app.analytics.common import filter_orders_by_date, safe_int

LEVELS = ["zone", "aisle", "rack", "shelf", "bin"]
LEVEL_TITLES = {
    "zone": "Zone",
    "aisle": "Aisle",
    "rack": "Rack",
    "shelf": "Shelf",
    "bin": "Bin",
}


def build_activity_tree(order_rows, start, end, date_field="order_date"):
    """
    Returns dict: path_tuple -> {"order_lines": int, "units": int}
    for every prefix length 1..5 of (zone, aisle, rack, shelf, bin)
    found in the filtered order lines.
    """
    filtered = filter_orders_by_date(order_rows, start, end, date_field)
    counts = defaultdict(lambda: {"order_lines": 0, "units": 0})

    for row in filtered:
        parts = [row.get(level, "") for level in LEVELS]
        if not parts[0]:
            continue
        qty = safe_int(row.get("quantity_ordered"))
        path = []
        for part in parts:
            if not part:
                break
            path.append(part)
            key = tuple(path)
            counts[key]["order_lines"] += 1
            counts[key]["units"] += qty

    return counts


def get_children(counts, parent_path):
    """
    parent_path: tuple, e.g. () for top-level zones, ("Z01",) for aisles
    within Z01, etc. Returns a list of dicts sorted by code:
    [{"code", "path", "order_lines", "units"}, ...]
    """
    target_len = len(parent_path) + 1
    children = {}
    for path, vals in counts.items():
        if len(path) == target_len and path[:len(parent_path)] == parent_path:
            code = path[-1]
            children[code] = {
                "code": code,
                "path": path,
                "order_lines": vals["order_lines"],
                "units": vals["units"],
            }
    return [children[k] for k in sorted(children.keys())]


def skus_at_location(master_rows, path):
    """Given a full or partial location path tuple, return matching Master rows
    (e.g. all SKUs homed in a given bin, shelf, rack, aisle, or zone)."""
    n = len(path)
    matches = []
    for m in master_rows:
        m_path = tuple(m.get(level, "") for level in LEVELS[:n])
        if m_path == path:
            matches.append(m)
    return matches
