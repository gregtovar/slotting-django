"""
results_view.py
-----------------
Generic, read-only "results" screen for any analysis module's output.
Mirrors the look of TableView (search / sort / paginate) but has no
add/edit/delete - instead it offers Export to CSV and Re-run (change
parameters) actions.
"""

import csv
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app.theme import Palette, Fonts
from app.ui.charts import HBarChart, VBarChart, LineChart, ParetoChart

PAGE_SIZES = [25, 50, 100, 250, 500]


class ResultsView(ttk.Frame):
    def __init__(self, parent, analysis_config, rows, summary_text, date_range_text,
                on_back, on_rerun, chart_spec=None):
        super().__init__(parent, style="App.TFrame")
        self.config = analysis_config
        self.all_rows = rows
        self.current_rows = list(rows)
        self.summary_text = summary_text
        self.date_range_text = date_range_text
        self.on_back = on_back
        self.on_rerun = on_rerun
        self.chart_spec = chart_spec
        self.chart_visible = tk.BooleanVar(value=chart_spec is not None)

        self.page = 0
        self.page_size = tk.IntVar(value=100)
        self.sort_column = tk.StringVar(value=analysis_config.default_sort or "")
        self.sort_reverse = True if analysis_config.default_sort else False
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_changed())

        self._build()
        self._apply_search_and_sort()

    # ------------------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        # ---- Header ----
        header = ttk.Frame(self, style="Navy.TFrame", padding=(24, 16))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ttk.Button(header, text="\u2190 Main Menu", style="Secondary.TButton",
                  command=self.on_back).grid(row=0, column=0, sticky="w")

        title_frame = ttk.Frame(header, style="Navy.TFrame")
        title_frame.grid(row=0, column=1, sticky="w", padx=(20, 0))
        ttk.Label(title_frame, text=f"{self.config.icon}  {self.config.label} \u2014 Results",
                  style="Title.TLabel", font=Fonts.H1, background=Palette.NAVY,
                  foreground="#FFFFFF").pack(anchor="w")
        ttk.Label(title_frame, text=f"Date range: {self.date_range_text}", style="Subtitle.TLabel",
                  background=Palette.NAVY).pack(anchor="w")

        ttk.Button(header, text="\u21bb Change Date Range / Re-run", style="Secondary.TButton",
                  command=self.on_rerun).grid(row=0, column=2, sticky="e")

        # ---- Summary strip ----
        summary_bar = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        summary_bar.grid(row=1, column=0, sticky="ew")
        ttk.Label(summary_bar, text=self.summary_text, style="CardBody.TLabel",
                 font=Fonts.BODY_BOLD, background=Palette.PANEL, foreground=Palette.NAVY).pack(anchor="w")

        # ---- Chart panel (optional) ----
        self.chart_frame = ttk.Frame(self, style="Panel.TFrame", padding=(20, 12))
        self.chart_widget = None
        if self.chart_spec is not None:
            self.chart_widget = self._make_chart_widget(self.chart_frame, self.chart_spec)
            if self.chart_widget is not None:
                self.chart_widget.pack(fill="both", expand=True)
                self.chart_widget.configure(height=260)
        self.chart_frame.grid(row=2, column=0, sticky="ew")
        if not self.chart_visible.get() or self.chart_widget is None:
            self.chart_frame.grid_remove()

        # ---- Toolbar ----
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        toolbar.grid(row=3, column=0, sticky="ew")
        toolbar.columnconfigure(5, weight=1)

        ttk.Button(toolbar, text="\U0001F4BE Export to CSV", style="Accent.TButton",
                  command=self._export_csv).grid(row=0, column=0, padx=(0, 16))

        if self.chart_widget is not None:
            ttk.Checkbutton(toolbar, text="Show Chart", variable=self.chart_visible,
                            command=self._toggle_chart, style="TCheckbutton").grid(row=0, column=1, padx=(0, 20))

        ttk.Label(toolbar, text="Search:", style="MutedPanel.TLabel").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(toolbar, textvariable=self.search_var, width=32, style="Search.TEntry").grid(
            row=0, column=3, sticky="w")

        ttk.Label(toolbar, text="Rows/page:", style="MutedPanel.TLabel").grid(row=0, column=4, padx=(20, 6))
        page_combo = ttk.Combobox(toolbar, textvariable=self.page_size, values=PAGE_SIZES,
                                  width=5, state="readonly")
        page_combo.grid(row=0, column=5, sticky="w")
        page_combo.bind("<<ComboboxSelected>>", lambda e: self._render_page())

        self.count_label = ttk.Label(toolbar, text="", style="MutedPanel.TLabel")
        self.count_label.grid(row=0, column=6, sticky="e")

        # ---- Grid ----
        grid_frame = ttk.Frame(self, style="App.TFrame", padding=(20, 10))
        grid_frame.grid(row=4, column=0, sticky="nsew")
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.columnconfigure(0, weight=1)

        col_names = [c.name for c in self.config.result_columns]
        self.tree = ttk.Treeview(grid_frame, columns=col_names, show="headings")
        for col in self.config.result_columns:
            self.tree.heading(col.name, text=col.label, command=lambda c=col.name: self._sort_by(c))
            anchor = "e" if col.type in ("int", "float") else "w"
            self.tree.column(col.name, width=col.width, anchor=anchor, stretch=False)

        vscroll = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        hscroll = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("odd", background=Palette.ROW_ODD)
        self.tree.tag_configure("even", background=Palette.ROW_EVEN)
        self.tree.tag_configure("flag", foreground=Palette.RED)

        # ---- Pagination bar ----
        pager = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        pager.grid(row=5, column=0, sticky="ew")
        pager.columnconfigure(2, weight=1)

        ttk.Button(pager, text="\u2039 Prev", style="Ghost.TButton", command=self._prev_page).grid(row=0, column=0)
        self.page_label = ttk.Label(pager, text="", style="Muted.TLabel")
        self.page_label.grid(row=0, column=1, padx=12)
        ttk.Button(pager, text="Next \u203a", style="Ghost.TButton", command=self._next_page).grid(
            row=0, column=2, sticky="w")
        self.status_label = ttk.Label(pager, text="", style="Muted.TLabel")
        self.status_label.grid(row=0, column=3, sticky="e")

    # ------------------------------------------------------------------
    def _make_chart_widget(self, parent, spec):
        chart_type = spec.get("type")
        items = spec.get("items") or []
        title = spec.get("title", "")
        value_fmt = spec.get("value_fmt", "{:,.0f}")

        if chart_type == "hbar":
            widget = HBarChart(parent, title=title, value_fmt=value_fmt)
            widget.set_data(items)
        elif chart_type == "vbar":
            widget = VBarChart(parent, title=title, value_fmt=value_fmt)
            widget.set_data(items)
        elif chart_type == "line":
            widget = LineChart(parent, title=title, value_fmt=value_fmt)
            widget.set_data(items)
        elif chart_type == "pareto":
            widget = ParetoChart(parent, title=title)
            widget.set_data(items)
        else:
            return None
        return widget

    def _toggle_chart(self):
        if self.chart_visible.get():
            self.chart_frame.grid()
        else:
            self.chart_frame.grid_remove()

    # ------------------------------------------------------------------
    def _on_search_changed(self):
        self.page = 0
        self._apply_search_and_sort()

    def _apply_search_and_sort(self):
        text = self.search_var.get().strip().lower()
        if text:
            rows = [r for r in self.all_rows if any(text in str(v).lower() for v in r.values())]
        else:
            rows = list(self.all_rows)

        col = self.sort_column.get()
        if col:
            col_spec = next((c for c in self.config.result_columns if c.name == col), None)
            is_numeric = col_spec is not None and col_spec.type in ("int", "float")

            def sort_key(row):
                val = row.get(col, "")
                if is_numeric:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return float("-inf")
                return str(val).lower()

            rows = sorted(rows, key=sort_key, reverse=self.sort_reverse)

        self.current_rows = rows
        self._render_page()

    def _sort_by(self, col):
        if self.sort_column.get() == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column.set(col)
            self.sort_reverse = False
        self._apply_search_and_sort()

    def _render_page(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        page_size = self.page_size.get()
        total = len(self.current_rows)
        max_page = max(0, (total - 1) // page_size) if total else 0
        self.page = min(self.page, max_page)
        start = self.page * page_size
        end = start + page_size
        page_rows = self.current_rows[start:end]

        col_names = [c.name for c in self.config.result_columns]
        for i, row in enumerate(page_rows):
            values = [row.get(c, "") for c in col_names]
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(start + i), values=values, tags=(tag,))

        total_all = len(self.all_rows)
        if self.search_var.get().strip():
            self.count_label.configure(text=f"{total} of {total_all} rows match search")
        else:
            self.count_label.configure(text=f"{total_all} total rows")

        showing_from = start + 1 if total else 0
        showing_to = min(end, total)
        self.status_label.configure(text=f"Showing {showing_from}-{showing_to} of {total}")
        self.page_label.configure(text=f"Page {self.page + 1} of {max_page + 1}")

    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._render_page()

    def _next_page(self):
        page_size = self.page_size.get()
        max_page = max(0, (len(self.current_rows) - 1) // page_size)
        if self.page < max_page:
            self.page += 1
            self._render_page()

    # ------------------------------------------------------------------
    def _export_csv(self):
        if not self.current_rows:
            messagebox.showinfo("Nothing to export", "There are no rows to export.", parent=self)
            return
        default_name = f"{self.config.key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export results to CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        col_names = [c.name for c in self.config.result_columns]
        headers = [c.label for c in self.config.result_columns]
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in self.current_rows:
                    writer.writerow([row.get(c, "") for c in col_names])
        except OSError as e:
            messagebox.showerror("Export failed", f"Could not write file:\n{e}", parent=self)
            return
        messagebox.showinfo("Exported", f"{len(self.current_rows)} rows exported to:\n{path}", parent=self)
