"""
date_range_dialog.py
----------------------
The "Run" dialog shown before every analysis module: pick a date range
(via presets or custom YYYY-MM-DD entries) plus any extra options the
module defines (e.g. ABC Ranking's metric choice).

Presets are anchored to the most recent order_date actually present in
the data (not the system clock) - this dataset is sample/synthetic data
that spans both past and future dates relative to "today," so anchoring
to real wall-clock time would make "Last 30 Days" mean something
different on every machine. Anchoring to the latest date on file keeps
presets meaningful and reproducible.
"""

from datetime import date, timedelta

import tkinter as tk
from tkinter import ttk, messagebox

from app.theme import Palette, Fonts
from app.analytics.common import parse_date, build_date_presets as build_presets


class DateRangeDialog(tk.Toplevel):
    """
    analysis_config: AnalysisConfig (label, description, options)
    order_rows: list[dict] - used only to compute the data's actual min/max date
    on_run: callback(start_date, end_date, options_dict)
    """

    def __init__(self, parent, analysis_config, order_rows, on_run, date_field="order_date"):
        super().__init__(parent)
        self.analysis_config = analysis_config
        self.on_run = on_run
        self.option_vars = {}

        dates = [parse_date(r.get(date_field, "")) for r in order_rows]
        dates = [d for d in dates if d is not None]
        self.data_min = min(dates) if dates else date.today() - timedelta(days=365)
        self.data_max = max(dates) if dates else date.today()
        self.presets = build_presets(self.data_max, self.data_min, self.data_max)

        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.preset_var = tk.StringVar(value="All Time")

        self.title(f"Run: {analysis_config.label}")
        self.configure(bg=Palette.PANEL)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build()
        self._apply_preset("All Time")
        self._center_on_parent(parent)
        self.bind("<Escape>", lambda e: self.destroy())

    def _center_on_parent(self, parent):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        except tk.TclError:
            x, y = 240, 120
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    # ------------------------------------------------------------------
    def _build(self):
        header = ttk.Frame(self, style="Navy.TFrame", padding=(24, 16))
        header.pack(fill="x")
        ttk.Label(header, text=f"{self.analysis_config.icon}  {self.analysis_config.label}",
                  style="Title.TLabel", font=Fonts.H1, background=Palette.NAVY,
                  foreground="#FFFFFF").pack(anchor="w")
        ttk.Label(header, text=self.analysis_config.description, style="Subtitle.TLabel",
                  background=Palette.NAVY, wraplength=440, justify="left").pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, style="Panel.TFrame", padding=(24, 18))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Date Range  (based on Order Date)", style="H2.TLabel").pack(anchor="w")
        ttk.Label(body, text=f"Data on file spans {self.data_min.isoformat()} to {self.data_max.isoformat()}",
                  style="MutedPanel.TLabel").pack(anchor="w", pady=(0, 10))

        preset_frame = ttk.Frame(body, style="Panel.TFrame")
        preset_frame.pack(fill="x", pady=(0, 12))
        cols = 4
        for i, (label, _, _) in enumerate(self.presets):
            btn = ttk.Radiobutton(preset_frame, text=label, value=label, variable=self.preset_var,
                                  command=lambda l=label: self._apply_preset(l))
            btn.grid(row=i // cols, column=i % cols, sticky="w", padx=(0, 14), pady=3)

        custom_frame = ttk.Frame(body, style="Panel.TFrame")
        custom_frame.pack(fill="x", pady=(6, 16))
        ttk.Label(custom_frame, text="Start:", style="FieldLabel.TLabel").grid(row=0, column=0, padx=(0, 6))
        start_entry = ttk.Entry(custom_frame, textvariable=self.start_var, width=14)
        start_entry.grid(row=0, column=1, padx=(0, 18))
        ttk.Label(custom_frame, text="End:", style="FieldLabel.TLabel").grid(row=0, column=2, padx=(0, 6))
        end_entry = ttk.Entry(custom_frame, textvariable=self.end_var, width=14)
        end_entry.grid(row=0, column=3)
        ttk.Label(custom_frame, text="(YYYY-MM-DD - edit directly for a custom range)",
                  style="MutedPanel.TLabel").grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))

        for var in (self.start_var, self.end_var):
            var.trace_add("write", lambda *a: self.preset_var.set(""))

        if self.analysis_config.options:
            ttk.Separator(body, orient="horizontal").pack(fill="x", pady=(4, 14))
            ttk.Label(body, text="Options", style="H2.TLabel").pack(anchor="w", pady=(0, 8))
            for opt in self.analysis_config.options:
                row = ttk.Frame(body, style="Panel.TFrame")
                row.pack(fill="x", pady=4)
                ttk.Label(row, text=opt.label, style="FieldLabel.TLabel", width=28).pack(side="left")
                var = tk.StringVar(value=opt.default)
                self.option_vars[opt.name] = var
                if opt.type == "choice" and opt.choices:
                    ttk.Combobox(row, textvariable=var, values=opt.choices, state="readonly",
                                width=30).pack(side="left")
                else:
                    ttk.Entry(row, textvariable=var, width=14).pack(side="left")
                if opt.help:
                    ttk.Label(row, text=opt.help, style="MutedPanel.TLabel").pack(side="left", padx=(10, 0))

        self.error_label = ttk.Label(body, text="", style="Error.TLabel")
        self.error_label.pack(anchor="w", pady=(8, 0))

        footer = ttk.Frame(self, style="Panel.TFrame", padding=(20, 14))
        footer.pack(fill="x")
        ttk.Button(footer, text="Cancel", style="Ghost.TButton", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Run Analysis \u2192", style="Accent.TButton", command=self._on_run).pack(side="right")

    def _apply_preset(self, label):
        for name, start, end in self.presets:
            if name == label:
                self.start_var.set(start.isoformat())
                self.end_var.set(end.isoformat())
                self.preset_var.set(label)
                return

    def _on_run(self):
        start = parse_date(self.start_var.get())
        end = parse_date(self.end_var.get())
        if start is None or end is None:
            self.error_label.configure(text="Please enter valid dates in YYYY-MM-DD format.")
            return
        if start > end:
            self.error_label.configure(text="Start date must be on or before the end date.")
            return

        options = {}
        for opt in self.analysis_config.options:
            val = self.option_vars[opt.name].get()
            if opt.type in ("int", "float") and val:
                try:
                    float(val)
                except ValueError:
                    self.error_label.configure(text=f"'{opt.label}' must be a number.")
                    return
            options[opt.name] = val

        self.destroy()
        self.on_run(start, end, options)
