"""
config.py
---------
Declarative schema for each CSV-backed table. The generic table view /
record dialog read these configs to know:
  - which columns exist and in what order
  - which column(s) form the unique key
  - which columns show up in the main grid (vs. only in the edit form)
  - what "type" each field is (text / int / float / date / datetime / choice)
  - what dropdown choices to offer for categorical fields
  - which fields are required

Adding a 4th CSV later is just a matter of adding another TableConfig.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class FieldSpec:
    name: str
    label: str
    type: str = "text"          # text | int | float | date | datetime | choice | email | phone
    choices: list = field(default_factory=list)
    required: bool = False
    width: int = 120            # default column width in the grid (px)
    editable: bool = True       # if False, shown read-only in the form (e.g. derived fields)
    help: str = ""              # short hint shown under the field in the form


@dataclass
class TableConfig:
    key: str                          # internal id, e.g. "customers"
    label: str                        # display name, e.g. "Customers"
    icon: str                         # emoji / unicode icon for the menu card
    csv_path: Path
    fields: list                      # list[FieldSpec] - full schema, order = CSV column order
    key_fields: list                  # list[str] - column(s) that make a row unique
    grid_fields: list                 # list[str] - subset/order shown in the main grid
    search_fields: list               # list[str] - default columns searched by the search box
    description: str = ""
    id_prefix: str = ""               # used for auto-suggesting new IDs, e.g. "CUST-"
    id_field: Optional[str] = None    # which field the auto id applies to

    def field_map(self):
        return {f.name: f for f in self.fields}

    def column_names(self):
        return [f.name for f in self.fields]


# ---------------------------------------------------------------------------
# CUSTOMERS
# ---------------------------------------------------------------------------
CUSTOMERS_CONFIG = TableConfig(
    key="customers",
    label="Customers",
    icon="\U0001F465",  # busts in silhouette
    csv_path=DATA_DIR / "customers.csv",
    description="Customer master data: contacts, addresses, terms & status.",
    id_prefix="CUST-",
    id_field="customer_id",
    key_fields=["customer_id"],
    search_fields=["customer_id", "customer_name", "email", "phone", "billing_city"],
    grid_fields=[
        "customer_id", "customer_name", "customer_type", "customer_segment",
        "customer_status", "email", "phone", "billing_city", "billing_state",
        "payment_terms", "credit_limit",
    ],
    fields=[
        FieldSpec("customer_id", "Customer ID", "text", required=True, width=110,
                  help="Unique ID, e.g. CUST-000123"),
        FieldSpec("customer_name", "Customer Name", "text", required=True, width=160),
        FieldSpec("customer_type", "Customer Type", "choice",
                  choices=["Corporate", "Distributor", "Education", "Government", "Retail", "Wholesale"],
                  required=True, width=110),
        FieldSpec("customer_segment", "Segment", "choice",
                  choices=["Gold", "Platinum", "Silver", "Standard", "Strategic"], width=100),
        FieldSpec("customer_status", "Status", "choice", choices=["Active", "Inactive"],
                  required=True, width=90),
        FieldSpec("email", "Email", "email", width=190),
        FieldSpec("phone", "Phone", "phone", width=130),
        FieldSpec("billing_address1", "Billing Address 1", "text", width=160),
        FieldSpec("billing_address2", "Billing Address 2", "text", width=120),
        FieldSpec("billing_city", "Billing City", "text", width=110),
        FieldSpec("billing_state", "Billing State", "text", width=70),
        FieldSpec("billing_postal_code", "Billing ZIP", "text", width=80),
        FieldSpec("billing_country", "Billing Country", "text", width=90),
        FieldSpec("shipping_address1", "Shipping Address 1", "text", width=160),
        FieldSpec("shipping_address2", "Shipping Address 2", "text", width=120),
        FieldSpec("shipping_city", "Shipping City", "text", width=110),
        FieldSpec("shipping_state", "Shipping State", "text", width=70),
        FieldSpec("shipping_postal_code", "Shipping ZIP", "text", width=80),
        FieldSpec("shipping_country", "Shipping Country", "text", width=90),
        FieldSpec("payment_terms", "Payment Terms", "choice",
                  choices=["ACH Prepaid", "COD", "Credit Card", "Net 15", "Net 30", "Net 45"], width=110),
        FieldSpec("credit_limit", "Credit Limit", "float", width=100),
        FieldSpec("tax_exempt_flag", "Tax Exempt", "choice", choices=["Y", "N"], width=80),
        FieldSpec("preferred_carrier", "Preferred Carrier", "choice",
                  choices=["DHL", "FedEx", "Old Dominion", "UPS", "USPS", "XPO"], width=110),
        FieldSpec("created_date", "Created Date", "date", width=100),
        FieldSpec("last_modified_date", "Last Modified", "date", width=100),
        FieldSpec("source_system", "Source System", "text", width=100),
    ],
)

# ---------------------------------------------------------------------------
# MASTER (SKU master)
# ---------------------------------------------------------------------------
MASTER_CONFIG = TableConfig(
    key="master",
    label="Master (SKU)",
    icon="\U0001F4E6",  # package
    csv_path=DATA_DIR / "master.csv",
    description="Item master: dimensions, costs, vendor & current warehouse slot.",
    id_prefix="ITM-",
    id_field="item_number",
    key_fields=["sku"],
    search_fields=["sku", "item_number", "product_name", "brand", "product_category"],
    grid_fields=[
        "sku", "item_number", "product_name", "product_category", "brand",
        "product_status", "stocking_indicator", "cycle_count_class",
        "warehouse_location_code", "storage_type", "selling_price",
    ],
    fields=[
        FieldSpec("sku", "SKU", "text", required=True, width=160,
                  help="Unique SKU code, e.g. CAB-APE-R333-WH-0002"),
        FieldSpec("item_number", "Item Number", "text", required=True, width=100),
        FieldSpec("upc_ean_gtin", "UPC/EAN/GTIN", "text", width=120),
        FieldSpec("manufacturer_part_number", "Mfr Part #", "text", width=130),
        FieldSpec("product_name", "Product Name", "text", required=True, width=200),
        FieldSpec("short_description", "Short Description", "text", width=160),
        FieldSpec("long_description", "Long Description", "text", width=220),
        FieldSpec("product_category", "Category", "text", width=110),
        FieldSpec("subcategory", "Subcategory", "text", width=110),
        FieldSpec("brand", "Brand", "text", width=110),
        FieldSpec("model", "Model", "text", width=100),
        FieldSpec("product_status", "Product Status", "choice",
                  choices=["Active", "Discontinued", "Inactive", "Pending Launch"], required=True, width=110),
        FieldSpec("unit_of_measure", "UOM", "choice", choices=["EA", "BOX", "CASE", "PALLET"], width=70),
        FieldSpec("inventory_type", "Inventory Type", "choice",
                  choices=["Accessory", "Component", "Finished Good"], width=110),
        FieldSpec("stocking_indicator", "Stocking", "choice",
                  choices=["Stocked", "Non-stocked"], width=90),
        FieldSpec("reorder_point", "Reorder Point", "int", width=90),
        FieldSpec("safety_stock", "Safety Stock", "int", width=90),
        FieldSpec("lead_time_days", "Lead Time (days)", "int", width=90),
        FieldSpec("min_order_qty", "Min Order Qty", "int", width=90),
        FieldSpec("max_order_qty", "Max Order Qty", "int", width=90),
        FieldSpec("cycle_count_class", "Cycle Count Class", "choice", choices=["A", "B", "C"], width=80),
        FieldSpec("lot_controlled", "Lot Controlled", "choice", choices=["Y", "N"], width=80),
        FieldSpec("serial_controlled", "Serial Controlled", "choice", choices=["Y", "N"], width=90),
        FieldSpec("standard_cost", "Standard Cost", "float", width=90),
        FieldSpec("average_cost", "Average Cost", "float", width=90),
        FieldSpec("last_cost", "Last Cost", "float", width=90),
        FieldSpec("list_price", "List Price", "float", width=90),
        FieldSpec("selling_price", "Selling Price", "float", width=90),
        FieldSpec("currency", "Currency", "text", width=70),
        FieldSpec("price_effective_date", "Price Effective Date", "date", width=110),
        FieldSpec("primary_vendor_id", "Primary Vendor ID", "text", width=100),
        FieldSpec("primary_vendor_name", "Primary Vendor Name", "text", width=160),
        FieldSpec("vendor_sku", "Vendor SKU", "text", width=120),
        FieldSpec("vendor_lead_time_days", "Vendor Lead Time", "int", width=100),
        FieldSpec("country_of_origin", "Country of Origin", "text", width=110),
        FieldSpec("weight_lbs", "Weight (lbs)", "float", width=90),
        FieldSpec("length_in", "Length (in)", "float", width=80),
        FieldSpec("width_in", "Width (in)", "float", width=80),
        FieldSpec("height_in", "Height (in)", "float", width=80),
        FieldSpec("volume_cubic_in", "Volume (cu in)", "float", width=100),
        FieldSpec("color", "Color", "text", width=90),
        FieldSpec("material", "Material", "text", width=100),
        FieldSpec("hazardous_material_flag", "Hazmat", "choice", choices=["Y", "N"], width=80),
        FieldSpec("warehouse_id", "Warehouse ID", "text", width=100),
        FieldSpec("zone", "Zone", "text", width=70, help="Current slotting location"),
        FieldSpec("aisle", "Aisle", "text", width=70),
        FieldSpec("rack", "Rack", "text", width=70),
        FieldSpec("shelf", "Shelf", "text", width=70),
        FieldSpec("bin", "Bin", "text", width=70),
        FieldSpec("warehouse_location_code", "Location Code", "text", width=140),
        FieldSpec("storage_type", "Storage Type", "choice",
                  choices=["Bulk", "Cage", "Pallet", "Rack", "Shelf"], width=90),
        FieldSpec("seo_title", "SEO Title", "text", width=160),
        FieldSpec("product_image_url", "Image URL", "text", width=160),
        FieldSpec("product_page_url", "Product Page URL", "text", width=160),
        FieldSpec("marketing_description", "Marketing Description", "text", width=200),
        FieldSpec("keywords", "Keywords", "text", width=160),
        FieldSpec("web_enabled", "Web Enabled", "choice", choices=["Y", "N"], width=90),
        FieldSpec("channel", "Channel", "choice",
                  choices=["B2B", "E-commerce", "Marketplace", "Retail", "Wholesale"], width=100),
        FieldSpec("created_date", "Created Date", "date", width=100),
        FieldSpec("created_by", "Created By", "text", width=90),
        FieldSpec("last_modified_date", "Last Modified", "date", width=100),
        FieldSpec("last_modified_by", "Modified By", "text", width=100),
        FieldSpec("version_number", "Version #", "int", width=80),
    ],
)

# ---------------------------------------------------------------------------
# ORDERS
# ---------------------------------------------------------------------------
ORDERS_CONFIG = TableConfig(
    key="orders",
    label="Orders",
    icon="\U0001F4CB",  # clipboard
    csv_path=DATA_DIR / "orders.csv",
    description="Order lines: what was ordered, by whom, and from which slot.",
    id_prefix="SO-",
    id_field="order_number",
    key_fields=["order_number", "order_line_number"],
    search_fields=["order_number", "customer_id", "customer_name", "sku", "product_name", "tracking_number"],
    grid_fields=[
        "order_number", "order_line_number", "order_date", "order_status",
        "customer_name", "sku", "product_name", "quantity_ordered",
        "warehouse_location_code", "carrier", "order_total",
    ],
    fields=[
        FieldSpec("order_number", "Order Number", "text", required=True, width=120),
        FieldSpec("order_line_number", "Line #", "int", required=True, width=60),
        FieldSpec("external_order_id", "External Order ID", "text", width=130),
        FieldSpec("order_date", "Order Date", "date", required=True, width=100),
        FieldSpec("order_type", "Order Type", "choice",
                  choices=["Replacement", "Return Exchange", "Sales Order"], width=120),
        FieldSpec("order_status", "Order Status", "choice",
                  choices=["Allocated", "Backordered", "Cancelled", "Delivered", "New",
                           "Packed", "Picked", "Processing", "Shipped"], required=True, width=100),
        FieldSpec("channel", "Channel", "choice",
                  choices=["B2B", "E-commerce", "Marketplace", "Retail Store", "Wholesale"], width=110),
        FieldSpec("source_system", "Source System", "choice",
                  choices=["Amazon", "EDI", "ERP", "Manual Entry", "Shopify"], width=100),
        FieldSpec("customer_id", "Customer ID", "text", required=True, width=100),
        FieldSpec("customer_name", "Customer Name", "text", width=150),
        FieldSpec("customer_po_number", "Customer PO #", "text", width=110),
        FieldSpec("customer_email", "Customer Email", "email", width=180),
        FieldSpec("customer_phone", "Customer Phone", "phone", width=120),
        FieldSpec("sku", "SKU", "text", required=True, width=160),
        FieldSpec("item_number", "Item Number", "text", width=100),
        FieldSpec("product_name", "Product Name", "text", width=180),
        FieldSpec("product_category", "Category", "text", width=100),
        FieldSpec("subcategory", "Subcategory", "text", width=110),
        FieldSpec("brand", "Brand", "text", width=100),
        FieldSpec("unit_of_measure", "UOM", "text", width=60),
        FieldSpec("quantity_ordered", "Qty Ordered", "int", required=True, width=80),
        FieldSpec("quantity_allocated", "Qty Allocated", "int", width=80),
        FieldSpec("quantity_shipped", "Qty Shipped", "int", width=80),
        FieldSpec("quantity_backordered", "Qty Backordered", "int", width=90),
        FieldSpec("unit_price", "Unit Price", "float", width=90),
        FieldSpec("extended_price", "Extended Price", "float", width=100),
        FieldSpec("discount_percent", "Discount %", "float", width=80),
        FieldSpec("discount_amount", "Discount Amt", "float", width=90),
        FieldSpec("tax_rate", "Tax Rate %", "float", width=80),
        FieldSpec("tax_amount", "Tax Amount", "float", width=90),
        FieldSpec("freight_amount", "Freight Amount", "float", width=90),
        FieldSpec("order_total", "Order Total", "float", width=100),
        FieldSpec("currency", "Currency", "text", width=70),
        FieldSpec("payment_terms", "Payment Terms", "text", width=100),
        FieldSpec("payment_method", "Payment Method", "text", width=110),
        FieldSpec("payment_status", "Payment Status", "choice",
                  choices=["Authorized", "Invoiced", "Paid", "Pending", "Refunded", "Voided"], width=100),
        FieldSpec("invoice_number", "Invoice Number", "text", width=110),
        FieldSpec("invoice_date", "Invoice Date", "date", width=100),
        FieldSpec("warehouse_id", "Warehouse ID", "text", width=100),
        FieldSpec("warehouse_location_code", "Location Code", "text", width=140),
        FieldSpec("zone", "Zone", "text", width=60),
        FieldSpec("aisle", "Aisle", "text", width=60),
        FieldSpec("rack", "Rack", "text", width=60),
        FieldSpec("shelf", "Shelf", "text", width=60),
        FieldSpec("bin", "Bin", "text", width=60),
        FieldSpec("ship_to_name", "Ship To Name", "text", width=140),
        FieldSpec("ship_to_address1", "Ship To Address 1", "text", width=160),
        FieldSpec("ship_to_address2", "Ship To Address 2", "text", width=120),
        FieldSpec("ship_to_city", "Ship To City", "text", width=110),
        FieldSpec("ship_to_state", "Ship To State", "text", width=70),
        FieldSpec("ship_to_postal_code", "Ship To ZIP", "text", width=80),
        FieldSpec("ship_to_country", "Ship To Country", "text", width=90),
        FieldSpec("carrier", "Carrier", "choice",
                  choices=["DHL", "FedEx", "Old Dominion", "UPS", "USPS", "XPO"], width=90),
        FieldSpec("service_level", "Service Level", "choice",
                  choices=["2-Day", "Economy", "Ground", "Overnight", "Priority", "Standard Freight"], width=110),
        FieldSpec("tracking_number", "Tracking Number", "text", width=130),
        FieldSpec("requested_ship_date", "Requested Ship Date", "date", width=110),
        FieldSpec("actual_ship_date", "Actual Ship Date", "date", width=100),
        FieldSpec("created_by", "Created By", "text", width=90),
        FieldSpec("created_timestamp", "Created Timestamp", "datetime", width=140),
        FieldSpec("last_modified_timestamp", "Last Modified Timestamp", "datetime", width=140),
    ],
)

ALL_TABLES = [CUSTOMERS_CONFIG, MASTER_CONFIG, ORDERS_CONFIG]
TABLES_BY_KEY = {t.key: t for t in ALL_TABLES}

APP_NAME = "Slotting Optimizer"
APP_SUBTITLE = "Warehouse Optimization Suite"
MAX_BACKUPS_PER_TABLE = 8


# ---------------------------------------------------------------------------
# ANALYSIS / OPTIMIZATION MODULES
# ---------------------------------------------------------------------------
@dataclass
class ResultColumn:
    name: str
    label: str
    width: int = 110
    type: str = "text"   # text | int | float


@dataclass
class AnalysisOption:
    """An extra parameter (besides the date range) shown in the run dialog."""
    name: str
    label: str
    type: str = "choice"     # choice | int | float
    choices: list = field(default_factory=list)
    default: str = ""
    help: str = ""


@dataclass
class AnalysisConfig:
    key: str
    label: str
    icon: str
    description: str
    module: str                 # dotted path under app.analytics, e.g. "velocity"
    result_columns: list        # list[ResultColumn]
    default_sort: Optional[str] = None
    options: list = field(default_factory=list)   # list[AnalysisOption]


SKU_VELOCITY = AnalysisConfig(
    key="velocity",
    label="SKU Velocity",
    icon="\U0001F680",
    description="How fast each SKU moves (units/day) over a date range.",
    module="velocity",
    default_sort="units_per_day",
    result_columns=[
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 200),
        ResultColumn("product_category", "Category", 110),
        ResultColumn("brand", "Brand", 100),
        ResultColumn("qty_ordered", "Qty Ordered", 90, "int"),
        ResultColumn("order_lines", "Order Lines", 90, "int"),
        ResultColumn("distinct_orders", "Distinct Orders", 100, "int"),
        ResultColumn("units_per_day", "Units / Day", 90, "float"),
        ResultColumn("velocity_tier", "Velocity Tier", 100),
        ResultColumn("current_location", "Current Location", 130),
        ResultColumn("storage_type", "Storage Type", 100),
    ],
)

ABC_RANKING = AnalysisConfig(
    key="abc_ranking",
    label="ABC Ranking",
    icon="\U0001F3C6",
    description="Classic Pareto classification (A/B/C) by Revenue, Quantity, or Picks.",
    module="abc_ranking",
    default_sort="rank",
    options=[
        AnalysisOption("metric", "Classify By", "choice",
                       choices=["Revenue", "Quantity", "Pick Frequency (Order Lines)"],
                       default="Revenue"),
        AnalysisOption("a_threshold", "Class A cumulative % cutoff", "float", default="80"),
        AnalysisOption("b_threshold", "Class B cumulative % cutoff", "float", default="95"),
    ],
    result_columns=[
        ResultColumn("rank", "Rank", 60, "int"),
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 200),
        ResultColumn("product_category", "Category", 110),
        ResultColumn("metric_value", "Metric Value", 110, "float"),
        ResultColumn("pct_of_total", "% of Total", 90, "float"),
        ResultColumn("cumulative_pct", "Cumulative %", 100, "float"),
        ResultColumn("abc_class", "ABC Class", 80),
        ResultColumn("current_location", "Current Location", 130),
    ],
)

CUBE_MOVEMENT = AnalysisConfig(
    key="cube_movement",
    label="Cube Movement",
    icon="\U0001F4D0",
    description="Total storage volume & weight physically moved per SKU.",
    module="cube_movement",
    default_sort="total_cube_cu_ft",
    result_columns=[
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 200),
        ResultColumn("product_category", "Category", 110),
        ResultColumn("unit_volume_cu_in", "Unit Volume (cu in)", 110, "float"),
        ResultColumn("qty_ordered", "Qty Ordered", 90, "int"),
        ResultColumn("total_cube_cu_ft", "Total Cube (cu ft)", 110, "float"),
        ResultColumn("unit_weight_lbs", "Unit Weight (lbs)", 100, "float"),
        ResultColumn("total_weight_lbs", "Total Weight (lbs)", 110, "float"),
        ResultColumn("storage_type", "Storage Type", 100),
        ResultColumn("current_location", "Current Location", 130),
    ],
)

PICK_FREQUENCY = AnalysisConfig(
    key="pick_frequency",
    label="Pick Frequency",
    icon="\U0001F58F",
    description="How often each SKU is touched, independent of quantity.",
    module="pick_frequency",
    default_sort="picks_per_day",
    result_columns=[
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 200),
        ResultColumn("product_category", "Category", 110),
        ResultColumn("order_lines", "Order Lines (Picks)", 110, "int"),
        ResultColumn("distinct_orders", "Distinct Orders", 100, "int"),
        ResultColumn("avg_qty_per_pick", "Avg Qty / Pick", 100, "float"),
        ResultColumn("picks_per_day", "Picks / Day", 90, "float"),
        ResultColumn("frequency_tier", "Frequency Tier", 100),
        ResultColumn("current_location", "Current Location", 130),
        ResultColumn("storage_type", "Storage Type", 100),
    ],
)

ORDER_AFFINITY = AnalysisConfig(
    key="order_affinity",
    label="Order Affinity",
    icon="\U0001F517",
    description="SKU pairs frequently ordered together (slot them near each other).",
    module="order_affinity",
    default_sort="times_together",
    options=[
        AnalysisOption("min_cooccurrence", "Minimum times ordered together", "int", default="2"),
        AnalysisOption("max_pairs", "Max pairs to show", "int", default="300"),
    ],
    result_columns=[
        ResultColumn("sku_a", "SKU A", 150),
        ResultColumn("product_a", "Product A", 180),
        ResultColumn("sku_b", "SKU B", 150),
        ResultColumn("product_b", "Product B", 180),
        ResultColumn("times_together", "Times Together", 110, "int"),
        ResultColumn("pct_of_a_orders", "% of A's Orders", 110, "float"),
        ResultColumn("pct_of_b_orders", "% of B's Orders", 110, "float"),
    ],
)

OPTIMAL_LOCATION = AnalysisConfig(
    key="optimal_location",
    label="Optimal Warehouse Location",
    icon="\U0001F3AF",
    description="Recommended storage zone per SKU, combining movement + size.",
    module="optimal_location",
    default_sort="action",
    result_columns=[
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 190),
        ResultColumn("product_category", "Category", 100),
        ResultColumn("movement_tier", "Movement Tier", 100),
        ResultColumn("size_tier", "Size Tier", 90),
        ResultColumn("units_per_day", "Units / Day", 90, "float"),
        ResultColumn("picks_per_day", "Picks / Day", 90, "float"),
        ResultColumn("recommended_zone", "Recommended Zone", 220),
        ResultColumn("recommended_storage_type", "Recommended Storage", 130),
        ResultColumn("current_storage_type", "Current Storage", 110),
        ResultColumn("current_location", "Current Location", 130),
        ResultColumn("action", "Action", 130),
    ],
)

BIN_ASSIGNMENT = AnalysisConfig(
    key="bin_assignment",
    label="Bin-Level Assignment (Capacity-Aware)",
    icon="\U0001F4E6",
    description="Estimates required storage cube per SKU and assigns real bin codes from your slot inventory.",
    module="bin_assignment",
    default_sort="assignment_status",
    options=[
        AnalysisOption("days_of_supply", "Days of supply to plan for", "float", default="14"),
        AnalysisOption("capacity_shelf", "Shelf slot capacity (cu ft)", "float", default="2"),
        AnalysisOption("capacity_rack", "Rack slot capacity (cu ft)", "float", default="8"),
        AnalysisOption("capacity_pallet", "Pallet slot capacity (cu ft)", "float", default="60"),
        AnalysisOption("capacity_bulk", "Bulk slot capacity (cu ft)", "float", default="150"),
        AnalysisOption("capacity_cage", "Cage slot capacity (cu ft)", "float", default="10"),
    ],
    result_columns=[
        ResultColumn("sku", "SKU", 150),
        ResultColumn("product_name", "Product Name", 190),
        ResultColumn("movement_tier", "Movement Tier", 100),
        ResultColumn("size_tier", "Size Tier", 90),
        ResultColumn("recommended_storage_type", "Recommended Type", 130),
        ResultColumn("estimated_onhand_cu_ft", "Est. On-Hand (cu ft)", 130, "float"),
        ResultColumn("bins_needed", "Bins Needed", 90, "int"),
        ResultColumn("current_location", "Current Location", 130),
        ResultColumn("assigned_bins", "Assigned Bin(s)", 220),
        ResultColumn("assignment_status", "Status", 220),
    ],
)

ALL_ANALYSES = [SKU_VELOCITY, ABC_RANKING, CUBE_MOVEMENT, PICK_FREQUENCY, ORDER_AFFINITY,
                OPTIMAL_LOCATION, BIN_ASSIGNMENT]
ANALYSES_BY_KEY = {a.key: a for a in ALL_ANALYSES}


# ---------------------------------------------------------------------------
# REPORTS & DASHBOARDS (order-level, operational - not SKU slotting decisions)
# ---------------------------------------------------------------------------
ORDERS_BY_STATUS = AnalysisConfig(
    key="orders_by_status",
    label="Orders by Status",
    icon="\U0001F4CB",
    description="Order line volume broken down by current order status.",
    module="orders_reports",
    default_sort="order_lines",
    result_columns=[
        ResultColumn("status", "Status", 130),
        ResultColumn("order_lines", "Order Lines", 100, "int"),
        ResultColumn("distinct_orders", "Distinct Orders", 110, "int"),
        ResultColumn("revenue", "Revenue", 130, "float"),
        ResultColumn("pct_of_lines", "% of Lines", 90, "float"),
    ],
)

ORDERS_TREND_BY_DAY = AnalysisConfig(
    key="orders_trend_by_day",
    label="Orders Trend by Day",
    icon="\U0001F4C8",
    description="Order volume over time (auto-buckets to day, week, or month based on range length).",
    module="orders_reports",
    default_sort="period",
    options=[
        AnalysisOption("granularity", "Bucket by", "choice",
                       choices=["auto", "day", "week", "month"], default="auto"),
    ],
    result_columns=[
        ResultColumn("period", "Period", 120),
        ResultColumn("order_count", "Orders", 90, "int"),
        ResultColumn("units", "Units", 90, "int"),
        ResultColumn("revenue", "Revenue", 130, "float"),
    ],
)

ORDERS_BY_CUSTOMER_TOP10 = AnalysisConfig(
    key="orders_by_customer_top10",
    label="Orders by Customer \u2013 Top 10",
    icon="\U0001F465",
    description="Your busiest customers in the date range, by order count or revenue.",
    module="orders_reports",
    default_sort="distinct_orders",
    options=[
        AnalysisOption("rank_by", "Rank by", "choice", choices=["Order Count", "Revenue"], default="Order Count"),
        AnalysisOption("top_n", "How many to show", "int", default="10"),
    ],
    result_columns=[
        ResultColumn("customer_name", "Customer", 180),
        ResultColumn("customer_id", "Customer ID", 110),
        ResultColumn("distinct_orders", "Orders", 80, "int"),
        ResultColumn("order_lines", "Order Lines", 90, "int"),
        ResultColumn("units", "Units", 80, "int"),
        ResultColumn("revenue", "Revenue", 120, "float"),
    ],
)

PICKS_PER_HOUR = AnalysisConfig(
    key="picks_per_hour",
    label="Picks per Hour (PPH)",
    icon="\u23F1\uFE0F",
    description="Average picking activity by hour of day (based on order timestamps).",
    module="orders_reports",
    default_sort="hour",
    result_columns=[
        ResultColumn("hour", "Hour", 80),
        ResultColumn("total_picks", "Total Picks", 100, "int"),
        ResultColumn("avg_picks_per_hour", "Avg Picks / Hour", 130, "float"),
        ResultColumn("avg_units_per_hour", "Avg Units / Hour", 130, "float"),
    ],
)

ORDERS_BY_ZONE = AnalysisConfig(
    key="orders_by_zone",
    label="Orders by Warehouse Zone",
    icon="\U0001F5FA\uFE0F",
    description="Order line volume by the warehouse zone each pick came from.",
    module="orders_reports",
    default_sort="zone",
    result_columns=[
        ResultColumn("zone", "Zone", 80),
        ResultColumn("order_lines", "Order Lines", 100, "int"),
        ResultColumn("distinct_orders", "Distinct Orders", 110, "int"),
        ResultColumn("units", "Units", 90, "int"),
        ResultColumn("pct_of_lines", "% of Lines", 90, "float"),
    ],
)

WAREHOUSE_MAP = AnalysisConfig(
    key="warehouse_map",
    label="Warehouse Map \u2013 Picking Heat Map",
    icon="\U0001F525",
    description="Drill down Zone \u2192 Aisle \u2192 Rack \u2192 Shelf \u2192 Bin, color-coded by picking activity.",
    module="warehouse_map",
    result_columns=[],
)

ALL_REPORTS = [ORDERS_BY_STATUS, ORDERS_TREND_BY_DAY, ORDERS_BY_CUSTOMER_TOP10,
              PICKS_PER_HOUR, ORDERS_BY_ZONE, WAREHOUSE_MAP]
REPORTS_BY_KEY = {r.key: r for r in ALL_REPORTS}
