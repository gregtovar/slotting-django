# Slotting Optimizer
### Warehouse Optimization Suite

A desktop application (Python + Tkinter, no external dependencies) for
managing warehouse reference data and running slotting analyses to
recommend where each SKU should be stored, based on order history and
item attributes.

**Phase 1 — Data Management:** full CRUD (review / add / edit / delete)
on the three reference CSVs.

**Phase 2 — Slotting Analysis & Optimization:** seven analysis modules,
each launched from the main menu, each starting with a date-range (+
options) picker before it runs. Every result screen with a relevant
chart shows it above the grid (toggle on/off with "Show Chart"):

| Module | What it tells you | Chart |
|---|---|---|
| **SKU Velocity** | Units shipped per day, per SKU - identifies fast vs. slow movers | Top 15 bar |
| **ABC Ranking** | Classic 80/15/5 Pareto classification by Revenue, Quantity, or Pick Frequency | Pareto (bars + cumulative %) |
| **Cube Movement** | Total storage volume & weight physically moved per SKU | Top 15 bar |
| **Pick Frequency** | How often a SKU is *touched* (order lines), independent of quantity | Top 15 bar |
| **Order Affinity** | SKU pairs frequently ordered together (candidates to slot near each other) | Top 15 pairs bar |
| **Optimal Warehouse Location** | Combines movement + size into a recommended storage zone, flagged against current placement | Relocation counts bar |
| **Bin-Level Assignment (Capacity-Aware)** | Estimates required storage cube per SKU and assigns real bin codes from your slot inventory | Outcomes bar |

**Reports & Dashboards:** six operational, order-level views (also
date-range driven):

| Report | Chart |
|---|---|
| Orders by Status | Bar |
| Orders Trend by Day (auto-buckets to day/week/month) | Line |
| Orders by Customer \u2013 Top 10 | Bar |
| Picks per Hour (PPH) | Bar |
| Orders by Warehouse Zone | Bar |
| **Warehouse Map** \u2013 drill-down Zone \u2192 Aisle \u2192 Rack \u2192 Shelf \u2192 Bin, heat-colored by picking activity | Interactive heat grid |

| Table     | File               | Key field(s)                     |
|-----------|--------------------|-----------------------------------|
| Customers | `data/customers.csv` | `customer_id`                    |
| Master    | `data/master.csv`    | `sku`                             |
| Orders    | `data/orders.csv`    | `order_number` + `order_line_number` |

All charts are drawn with plain Tkinter Canvas - no matplotlib or other
third-party charting library, keeping the "zero external dependencies"
promise from Phase 1 (and one less thing to break across Python/Tk
installs).

---

## Requirements

- Python 3.8+
- Tkinter (ships with most Python installs; on some Linux distros install
  it separately, e.g. `sudo apt install python3-tk`)
- No third-party packages required — pure standard library.

### macOS note: blank window / Tk deprecation warning

If you see `DEPRECATION WARNING: The system version of Tk is deprecated…`
and the window opens but appears empty, you're running on Apple's
bundled Tcl/Tk 8.5, which has a known bug where windows render blank
until resized. The app already works around this automatically (it
nudges the window size on launch), and the warning itself is silenced.

If the window is still blank for you, the permanent fix is to use a
Python build linked against Tk 8.6 instead of the macOS system one:

```bash
brew install python-tk@3.12      # match this to your python3 -V
# or simply install Python from https://www.python.org/downloads/
# (the official installer bundles Tk 8.6)
```

You can check what your current Python is using with:

```bash
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

`8.6` or higher is good; `8.5` is the old system one.

## Running it

```bash
cd slotting_optimizer
python main.py
```

A 1280×800 window opens with the main menu. Click any card (Customers,
Master, Orders) to open that table's data screen.

## Web version (Streamlit)

Everything above also exists as a browser-based app, built on the exact
same data layer and analytics engine - no business logic was rewritten,
only the UI. Useful if you want to run this on a server and have people
open it in a browser instead of installing Python/Tk locally (this is a
much simpler path to that than the Docker+VNC approach in `deploy/` -
Streamlit *is* a web server natively, so no virtual display or VNC
bridging is needed at all).

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open the URL it prints (typically `http://localhost:8501`). Every table
and analysis module is a separate page in the sidebar.

A few differences from the desktop version, worth knowing:

- **Editing data**: each table page shows a full editable grid
  (`st.data_editor`) - add rows with the **+** row at the bottom, delete
  via the row checkbox + trash icon, edit any cell directly, then click
  **Save Changes**. Nothing writes to disk until you do; the same
  validation and automatic backups as the desktop version apply.
- **Warehouse Map**: instead of the desktop version's click-to-drill
  grid, the web version renders the *entire* Zone → Aisle → Rack → Shelf
  → Bin hierarchy at once as an interactive icicle chart - click any
  segment to zoom in, click the center label to zoom back out. This is
  native Plotly behavior, not custom code, and arguably nicer to use.
- **Multiple users**: Streamlit gives every browser session its own
  independent state automatically - run a single `streamlit run`
  process and any number of people can use it concurrently without
  stepping on each other's UI state. They still share the same
  `data/*.csv` files underneath, so the same note about concurrent saves
  applies (see "Known limitation: concurrent saves" in `deploy/DEPLOYMENT.md`
  if you deploy this on a server).
- **Charts**: rendered with Plotly instead of the desktop version's
  hand-rolled Tkinter Canvas charts (same chart data, nicer interactivity
  - zoom, hover tooltips, etc.) since the "zero dependencies" constraint
  was specific to the Tkinter app, not a general project rule.

## Web version (Django)

A third front end, built the same way as the Streamlit one: zero
business-logic changes, only a new UI layer (`slotting/` + `slotting_django/`)
on top of the exact same `app/config.py` / `app/data_manager.py` /
`app/analytics/` that the desktop and Streamlit versions use. Pick whichever
UI fits your situation - they all read and write the same `data/*.csv` files.

```bash
pip install -r requirements-django.txt
python manage.py migrate    # one-time: creates the (otherwise-unused)
                             # sqlite file Django's session framework needs
python manage.py runserver
```

Open `http://localhost:8000`. Run the test suite any time with `python manage.py test`.

How it differs from the other two UIs:

- **Classic multi-page web app**: real URLs per screen (`/table/orders/`,
  `/run/abc_ranking/`, `/warehouse-map/`, etc.) rather than a single-script
  re-run model - bookmark or share a link straight to a specific analysis
  with its date range baked into the URL.
- **Editing data** uses plain add/edit/delete forms (one record at a time)
  rather than a spreadsheet-style grid - more old-school CRUD, but every
  field's validation still comes from the same `DataManager` the other two
  UIs use, so the rules are identical everywhere.
- **Run forms** use native HTML5 date pickers plus the same date-range
  presets (as quick links) as the other UIs, anchored the same way to the
  latest date in your data.
- **Large result sets** are capped at 500 displayed rows on screen (Export
  to CSV always gives you the full set) - this keeps page rendering fast
  without needing JavaScript-based pagination.
- **Warehouse Map** uses the exact same Plotly icicle chart as the
  Streamlit version (the figure-building code is shared, in `app/charting.py`)
  - click any segment to zoom in, click the center label to zoom back out.
- This UI is a real Django project (`manage.py`, `slotting_django/` settings),
  so anything you already know about deploying Django (gunicorn/uwsgi behind
  nginx, a platform like Railway/Render/Fly, etc.) applies directly. It does
  **not** use Django's ORM/database for the actual warehouse data - that
  stays in `data/*.csv` via the same `DataManager` as the other UIs; the
  database that `migrate` sets up is only there because Django's session
  and messages frameworks expect one to exist.

## Features

**Main menu**
- Live record counts per table, pulled straight from each CSV
- One click into any table's management screen

**Each table screen**
- Sortable, paginated grid (click any column header to sort; choose
  rows-per-page from the toolbar)
- Live search box that filters across the most relevant columns for
  that table (e.g. for Orders: order #, customer, SKU, product name,
  tracking number)
- **Add Record** — opens a form generated from the table's schema, with
  dropdowns for categorical fields (status, type, carrier, etc.), a
  "Today" shortcut for date fields, and an "Suggest" button that proposes
  the next sequential ID (e.g. `CUST-001234`)
- **Edit Selected** — double-click a row, or select it and click Edit
- **Delete Selected** — supports multi-row selection (Ctrl/Shift-click),
  asks for confirmation before deleting
- Validation: required fields, correct number/date formats, and
  duplicate-key prevention before anything is written to disk

**Data safety**
- Every save first writes a timestamped backup of the previous CSV into
  `data/backups/` (the last 8 backups per table are kept, older ones are
  pruned automatically)
- Saves are atomic (written to a temp file, then renamed) so a crash
  mid-write can't corrupt your CSV

## Analysis & Optimization modules

Every module on the main menu's second section opens a **Run dialog**
first: pick a date range (quick presets, or type exact `YYYY-MM-DD`
dates), plus any module-specific options, then click **Run Analysis**.
Results open in a sortable, searchable, paginated grid with an
**Export to CSV** button and a **Change Date Range / Re-run** button.

Date-range presets (Last 7/30/90 Days, This Month, Last Month, Year to
Date, Last 12 Months) are anchored to the **most recent `order_date`
actually present in your data**, not your computer's clock. The bundled
sample data spans 2025-01-01 through 2026-12-31 (including dates in the
future relative to "today"), so anchoring to wall-clock time would make
"Last 30 Days" mean something different - and often empty - depending
on when you happen to run the app. "All Time" always covers the full
range found in the file.

### Methodology / assumptions (adjust anytime - just ask)

- **Velocity / Pick Frequency tiers** (Fast-Medium-Slow, Hot-Warm-Cold)
  are percentile-based: top 20% of *active* SKUs = fast tier, next 30% =
  medium, bottom 50% = slow. A SKU with literally zero activity in the
  selected range is always forced into the slowest tier, even if rank
  position alone would have put it elsewhere.
- **ABC Ranking** defaults to Revenue with 80% / 95% cumulative cutoffs
  for A / B, but you can switch the metric (Quantity, Pick Frequency) and
  the cutoffs right in the run dialog.
- **Cube Movement** = unit volume (from Master) × quantity ordered,
  summed per SKU, converted to cubic feet.
- **Order Affinity** counts how often two SKUs appear on the *same
  order number* within the date range. The sample `orders.csv` was
  regenerated to include realistic multi-line orders (~40% single-line,
  30% two-line, 20% three-line, 10% four-to-five-line) specifically so
  this module has real co-occurrence to find - your original single-line
  file was backed up to `data/backups/` before the rewrite.
- **Optimal Warehouse Location** blends the percentile rank of
  units/day and picks/day into one "movement" score, and unit volume
  into a Small/Medium/Large size tier, then looks up a recommended zone
  class + storage type from a fixed matrix (Golden Zone for fast movers,
  Bulk/Overflow for slow + large, etc.). It flags a SKU for "Review /
  Relocate" when its current `storage_type` doesn't match what's
  recommended. This is a *zone-class* recommendation, not an exact bin
  assignment - see Bin-Level Assignment for that.
- **Bin-Level Assignment** estimates each SKU's required on-hand cube as
  `days_of_supply x units/day x unit volume` (default 14 days - there's
  no real on-hand inventory data in this dataset, so this is a
  velocity-based proxy, adjustable in the run dialog) and divides by an
  assumed per-storage-type slot capacity (also adjustable; defaults are
  rough cu-ft guesses, not measured bin dimensions). It then greedily
  assigns SKUs to real `warehouse_location_code` values pulled from
  Master, prioritizing the biggest movement/placement mismatches first.
  SKUs that can't get enough slots of their recommended type are flagged
  "Insufficient Capacity" - a sign your storage-type mix doesn't match
  your movement profile, worth a look either way.
- **Picks per Hour** uses each order line's `created_timestamp` as a
  proxy for when it was picked (there's no dedicated pick-event or
  labor-hours data in this dataset), bucketed by hour-of-day and
  averaged across the days in range. This is a throughput-by-time-of-day
  view, not a true labor-productivity PPH (picks per labor-hour worked).
- **Warehouse Map** colors each Zone/Aisle/Rack/Shelf/Bin cell by actual
  picking activity recorded directly on the order lines (not Master's
  static "home" location), since that reflects where picks really
  happened. Drill in by clicking a cell; click a breadcrumb to jump back
  up.
- All active-SKU analyses (Velocity, ABC, Cube, Pick Frequency, Optimal
  Location, Bin Assignment) include every `Active`-status SKU in
  Master, even ones with zero activity in the chosen date range - that's
  deliberate, since "never moves" is itself an important slotting
  signal.

## Project structure

```
slotting_optimizer/
├── main.py                  # Tkinter desktop entry point
├── streamlit_app.py         # Streamlit web entry point (home page)
├── pages/                   # Streamlit auto-discovers these as sidebar pages
│   ├── 10_Customers.py / 11_Master_Data.py / 12_Orders.py       (Data Management)
│   ├── 20-26_*.py                                                (Slotting Analysis - 7 modules)
│   ├── 30-34_*.py, 35_Warehouse_Map.py                           (Reports & Dashboards)
├── manage.py                # Django entry point
├── slotting_django/         # Django project package (settings/urls/wsgi/asgi)
├── slotting/                 # Django app
│   ├── views.py / urls.py / forms.py / tests.py
│   ├── context_processors.py # injects nav data into every template
│   ├── templates/slotting/   # base.html, home.html, table_*.html, analysis_run.html, warehouse_map.html
│   └── static/slotting/      # style.css
├── requirements.txt          # streamlit + plotly (Streamlit UI only)
├── requirements-django.txt   # django + plotly (Django UI only)
├── app/                       # shared by ALL THREE front ends - no UI code at all in here
│   ├── config.py              # schema for tables, analyses, AND reports (columns, options, result grids)
│   ├── data_manager.py        # generic CSV CRUD engine (load/save/validate/search/sort/replace_all)
│   ├── colors.py               # plain hex constants - deliberately tkinter-free (see note below)
│   ├── charting.py             # chart_spec -> Plotly figure; also builds the Warehouse Map icicle chart
│   ├── theme.py                # Tkinter-only styling (ttk widgets, fonts) - desktop app exclusively
│   ├── app_window.py           # Tkinter top-level window controller
│   ├── analytics/              # all the actual business logic
│   │   ├── common.py          # per-SKU metrics builder + shared date-range presets
│   │   ├── velocity.py / abc_ranking.py / cube_movement.py / pick_frequency.py
│   │   ├── order_affinity.py / optimal_location.py / bin_assignment.py
│   │   ├── orders_reports.py  # Status / Trend / Top Customers / PPH / Zone
│   │   ├── warehouse_map.py   # hierarchical activity tree for the Warehouse Map
│   │   └── runner.py          # dispatch: analysis/report key -> compute function
│   ├── ui/                     # Tkinter desktop UI (imports app/theme.py - tkinter is fine here)
│   │   ├── main_menu.py / table_view.py / record_dialog.py / date_range_dialog.py
│   │   ├── results_view.py / charts.py / warehouse_map_view.py
│   └── web/                    # Streamlit UI (imports app/colors.py + app/charting.py - NOT app/theme.py)
│       ├── tables.py / analysis.py / warehouse_map.py
└── data/
    ├── customers.csv
    ├── master.csv
    ├── orders.csv
    └── backups/                # auto-created timestamped backups
```

**Why `app/colors.py` and `app/charting.py` are separate from `app/theme.py`:**
`app/theme.py` does `import tkinter as tk` for the desktop app's ttk styling.
That's harmless on a normal desktop OS, but minimal server environments
(notably Streamlit Community Cloud) don't have the underlying Tcl/Tk system
library installed at all - importing tkinter there crashes with
`ImportError: libtk8.6.so: cannot open shared object file`, even though no
window is ever created. Both web UIs (Streamlit and Django) need to be
completely tkinter-free, so the plain color constants and the Plotly
chart-building code live in their own modules that never import `app.theme`.

## Extending it

Adding a 4th table later is mostly declarative:

1. Add a `TableConfig` in `app/config.py` describing its columns,
   key field(s), dropdown choices, and which columns show in the grid.
2. Add it to `ALL_TABLES`.

The menu card, CRUD screen, search, sort, pagination, and add/edit form
all come for free from the generic `TableView` / `RecordDialog` classes.

## Known scale notes

- Orders currently has ~6,000 rows; Master ~1,000; Customers ~1,200. All
  load instantly into memory as plain Python dicts — no database needed
  at this scale. If this grows into the hundreds of thousands of rows,
  the next step would be to move `data_manager.py` onto SQLite while
  keeping the same CRUD interface, with no changes needed to the UI layer.
