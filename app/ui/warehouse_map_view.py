"""
warehouse_map_view.py
-----------------------
The Warehouse Map / Heat Map of Picking Activity screen. Lets you drill
down Zone -> Aisle -> Rack -> Shelf -> Bin, with each level rendered as
a heat-colored grid (HeatGrid) - darker/hotter cells had more picking
activity in the selected date range. Clicking a cell drills into it;
clicking a breadcrumb segment jumps back up.

This is deliberately visual-first rather than a sortable grid like the
other analyses - but it still offers CSV export of the current level
and a way to change the date range.
"""

import csv
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app.theme import Palette, Fonts
from app.ui.charts import HeatGrid
from app.analytics.warehouse_map import build_activity_tree, get_children, skus_at_location, LEVEL_TITLES, LEVELS


class WarehouseMapView(ttk.Frame):
    def __init__(self, parent, analysis_config, order_rows, master_rows, start, end, on_back, on_rerun):
        super().__init__(parent, style="App.TFrame")
        self.config = analysis_config
        self.master_rows = master_rows
        self.start, self.end = start, end
        self.on_back = on_back
        self.on_rerun = on_rerun

        self.tree_counts = build_activity_tree(order_rows, start, end)
        self.metric_var = tk.StringVar(value="order_lines")
        self.path = ()  # current drill path, e.g. () -> ("Z01",) -> ("Z01","A02") -> ...

        self._build()
        self._render_level()

    # ------------------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        header = ttk.Frame(self, style="Navy.TFrame", padding=(24, 16))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Button(header, text="\u2190 Main Menu", style="Secondary.TButton",
                  command=self.on_back).grid(row=0, column=0, sticky="w")

        title_frame = ttk.Frame(header, style="Navy.TFrame")
        title_frame.grid(row=0, column=1, sticky="w", padx=(20, 0))
        ttk.Label(title_frame, text=f"{self.config.icon}  {self.config.label}",
                  style="Title.TLabel", font=Fonts.H1, background=Palette.NAVY,
                  foreground="#FFFFFF").pack(anchor="w")
        ttk.Label(title_frame, text=f"Date range: {self.start.isoformat()} to {self.end.isoformat()}",
                  style="Subtitle.TLabel", background=Palette.NAVY).pack(anchor="w")

        ttk.Button(header, text="\u21bb Change Date Range", style="Secondary.TButton",
                  command=self.on_rerun).grid(row=0, column=2, sticky="e")

        # ---- Breadcrumb / toolbar ----
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)

        self.breadcrumb_frame = ttk.Frame(toolbar, style="Panel.TFrame")
        self.breadcrumb_frame.grid(row=0, column=0, sticky="w")

        ttk.Label(toolbar, text="Color by:", style="MutedPanel.TLabel").grid(row=0, column=2, padx=(20, 6))
        metric_combo = ttk.Combobox(toolbar, textvariable=self.metric_var, state="readonly",
                                    values=["order_lines", "units"], width=12)
        metric_combo.grid(row=0, column=3)
        metric_combo.bind("<<ComboboxSelected>>", lambda e: self._render_level())

        ttk.Button(toolbar, text="\U0001F4BE Export Level to CSV", style="Accent.TButton",
                  command=self._export_csv).grid(row=0, column=4, padx=(20, 0))

        # ---- Level label / back-up button ----
        level_bar = ttk.Frame(self, style="App.TFrame", padding=(20, 4))
        level_bar.grid(row=2, column=0, sticky="ew")
        self.level_label = ttk.Label(level_bar, text="", style="H1.TLabel")
        self.level_label.pack(side="left")
        self.back_btn = ttk.Button(level_bar, text="\u2191 Back Up", style="Ghost.TButton", command=self._go_up)
        self.back_btn.pack(side="right")

        # ---- Info strip (leaf-level SKU lookup) ----
        self.info_label = ttk.Label(self, text="", style="Muted.TLabel", padding=(20, 0))
        self.info_label.grid(row=3, column=0, sticky="ew")

        # ---- Heat grid ----
        grid_holder = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        grid_holder.grid(row=4, column=0, sticky="nsew")
        grid_holder.rowconfigure(0, weight=1)
        grid_holder.columnconfigure(0, weight=1)
        self.heat_grid = HeatGrid(grid_holder, on_cell_click=self._on_cell_click)
        self.heat_grid.grid(row=0, column=0, sticky="nsew")

        legend = ttk.Frame(self, style="App.TFrame", padding=(20, 8))
        legend.grid(row=5, column=0, sticky="ew")
        ttk.Label(legend, text="Cooler = less picking activity        Hotter (red) = more picking activity",
                  style="Muted.TLabel").pack(side="left")

    # ------------------------------------------------------------------
    def _current_children(self):
        return get_children(self.tree_counts, self.path)

    def _render_level(self):
        children = self._current_children()
        metric = self.metric_var.get()
        cells = [{"code": c["code"], "label": c["code"], "value": c[metric]} for c in children]
        self.heat_grid.set_cells(cells)

        depth = len(self.path)
        level_name = LEVEL_TITLES[LEVELS[depth]] if depth < len(LEVELS) else "Bin"
        self.level_label.configure(text=f"{level_name} level  ({len(children)} shown)")
        self.back_btn.configure(state="normal" if self.path else "disabled")
        self._render_breadcrumb()
        self._render_info()

    def _render_breadcrumb(self):
        for w in self.breadcrumb_frame.winfo_children():
            w.destroy()

        def make_link(text, path):
            lbl = tk.Label(self.breadcrumb_frame, text=text, fg=Palette.TEAL_DARK, bg=Palette.PANEL,
                          font=Fonts.BODY_BOLD, cursor="hand2")
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, p=path: self._jump_to(p))

        make_link("Warehouse", ())
        for i in range(len(self.path)):
            tk.Label(self.breadcrumb_frame, text="  \u203a  ", fg=Palette.TEXT_MUTED,
                    bg=Palette.PANEL, font=Fonts.BODY).pack(side="left")
            make_link(self.path[i], self.path[: i + 1])

    def _render_info(self):
        if len(self.path) == len(LEVELS):
            skus = skus_at_location(self.master_rows, self.path)
            if skus:
                names = ", ".join(f"{s['sku']} ({s['product_name']})" for s in skus[:3])
                self.info_label.configure(text=f"SKU(s) homed here: {names}")
            else:
                self.info_label.configure(text="No SKU is currently homed at this exact bin in Master.")
        else:
            self.info_label.configure(text="Click a cell to drill in. Leaf-level bins show which SKU lives there.")

    # ------------------------------------------------------------------
    def _on_cell_click(self, code):
        if len(self.path) >= len(LEVELS):
            return
        self.path = self.path + (code,)
        self._render_level()

    def _jump_to(self, path):
        self.path = path
        self._render_level()

    def _go_up(self):
        if self.path:
            self.path = self.path[:-1]
            self._render_level()

    # ------------------------------------------------------------------
    def _export_csv(self):
        children = self._current_children()
        if not children:
            messagebox.showinfo("Nothing to export", "There are no rows at this level to export.", parent=self)
            return
        default_name = f"warehouse_map_{'_'.join(self.path) or 'top'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            parent=self, title="Export current level to CSV", defaultextension=".csv",
            initialfile=default_name, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["code", "order_lines", "units"])
                for c in children:
                    writer.writerow([c["code"], c["order_lines"], c["units"]])
        except OSError as e:
            messagebox.showerror("Export failed", f"Could not write file:\n{e}", parent=self)
            return
        messagebox.showinfo("Exported", f"{len(children)} rows exported to:\n{path}", parent=self)
