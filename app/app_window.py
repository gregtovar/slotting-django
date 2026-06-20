"""
app_window.py
--------------
Top-level application controller. Owns the root Tk window and swaps
between the Main Menu, each table's CRUD screen, and each analysis /
report's run-dialog -> results (or Warehouse Map) flow, all inside the
same window.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.config import ALL_TABLES, TABLES_BY_KEY, ANALYSES_BY_KEY, REPORTS_BY_KEY, APP_NAME
from app.theme import apply_theme, Palette
from app.data_manager import DataManager
from app.ui.main_menu import MainMenu
from app.ui.table_view import TableView
from app.ui.date_range_dialog import DateRangeDialog
from app.ui.results_view import ResultsView
from app.ui.warehouse_map_view import WarehouseMapView
from app.analytics.runner import run_analysis

# Both Slotting Analyses and Reports & Dashboards share the same
# run-dialog -> results flow, so they're looked up from one merged dict.
CONFIGS_BY_KEY = {**ANALYSES_BY_KEY, **REPORTS_BY_KEY}


class AppWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} \u2014 Warehouse Optimization Suite")
        self.root.geometry("1280x800")
        self.root.minsize(1024, 650)

        apply_theme(self.root)

        self.container = ttk.Frame(self.root, style="App.TFrame")
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.data_managers = {cfg.key: DataManager(cfg) for cfg in ALL_TABLES}
        self.current_view = None

        self.show_main_menu()

    # ------------------------------------------------------------------
    def _clear(self):
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None

    def show_main_menu(self):
        self._clear()
        self.current_view = MainMenu(
            self.container,
            on_open_table=self.show_table,
            on_open_analysis=self.open_analysis_dialog,
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_table(self, table_key):
        self._clear()
        dm = self.data_managers[table_key]
        self.current_view = TableView(self.container, dm, on_back=self.show_main_menu)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # Analysis / Report flow: Main Menu -> DateRangeDialog (modal) -> compute -> ResultsView
    # (Warehouse Map is visual-first, so it opens WarehouseMapView instead of ResultsView.)
    # ------------------------------------------------------------------
    def open_analysis_dialog(self, analysis_key):
        analysis_cfg = CONFIGS_BY_KEY[analysis_key]
        orders_dm = self.data_managers["orders"]
        orders_dm.load()

        DateRangeDialog(
            self.root,
            analysis_cfg,
            orders_dm.all_rows(),
            on_run=lambda start, end, options: self._run_and_show(analysis_key, start, end, options),
        )

    def _run_and_show(self, analysis_key, start, end, options):
        analysis_cfg = CONFIGS_BY_KEY[analysis_key]
        orders_dm = self.data_managers["orders"]
        master_dm = self.data_managers["master"]
        orders_dm.load()
        master_dm.load()

        if analysis_key == "warehouse_map":
            self._clear()
            self.current_view = WarehouseMapView(
                self.container, analysis_cfg, orders_dm.all_rows(), master_dm.all_rows(),
                start, end,
                on_back=self.show_main_menu,
                on_rerun=lambda: self.open_analysis_dialog(analysis_key),
            )
            self.current_view.grid(row=0, column=0, sticky="nsew")
            return

        try:
            results, summary, chart_spec = run_analysis(
                analysis_key, orders_dm.all_rows(), master_dm.all_rows(), start, end, options
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Analysis failed",
                f"Something went wrong while running {analysis_cfg.label}:\n\n{exc}",
                parent=self.root,
            )
            return

        date_range_text = f"{start.isoformat()} to {end.isoformat()}"
        self._clear()
        self.current_view = ResultsView(
            self.container,
            analysis_cfg,
            results,
            summary,
            date_range_text,
            on_back=self.show_main_menu,
            on_rerun=lambda: self.open_analysis_dialog(analysis_key),
            chart_spec=chart_spec,
        )
        self.current_view.grid(row=0, column=0, sticky="nsew")
