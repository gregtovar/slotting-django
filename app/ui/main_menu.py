"""
main_menu.py
------------
The application's home screen: a branded header, a "Data Management"
section (one card per CRUD table), and a "Slotting Analysis &
Optimization" section (one card per analysis module). The whole body
scrolls so it always fits regardless of window size.
"""

import tkinter as tk
from tkinter import ttk

from app.config import ALL_TABLES, ALL_ANALYSES, ALL_REPORTS, APP_NAME, APP_SUBTITLE
from app.theme import Palette, Fonts
from app.data_manager import DataManager


class MainMenu(ttk.Frame):
    def __init__(self, parent, on_open_table, on_open_analysis):
        super().__init__(parent, style="App.TFrame")
        self.on_open_table = on_open_table
        self.on_open_analysis = on_open_analysis
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---- Header / banner ----
        header = ttk.Frame(self, style="Navy.TFrame", padding=(40, 32))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text=f"\U0001F4E6  {APP_NAME}", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=APP_SUBTITLE.upper(), style="Subtitle.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            header,
            text="Analyze order history and SKU attributes to recommend optimal\n"
                 "storage locations - reducing travel time and lowering pick costs.",
            background=Palette.NAVY, foreground="#C9D6E3", font=Fonts.BODY, justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        # ---- Scrollable body ----
        body_outer = ttk.Frame(self, style="App.TFrame")
        body_outer.grid(row=1, column=0, sticky="nsew")
        body_outer.rowconfigure(0, weight=1)
        body_outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(body_outer, bg=Palette.BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(body_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")

        body = ttk.Frame(canvas, style="App.TFrame", padding=(40, 30))
        body_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def on_body_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(body_id, width=event.width)

        body.bind("<Configure>", on_body_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # ---- Data Management section ----
        body.columnconfigure((0, 1, 2), weight=1, uniform="cards")

        ttk.Label(body, text="Data Management", style="H1.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(
            body,
            text="Review, add, edit, and delete the records that power the slotting analysis.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 18))

        for i, table_cfg in enumerate(ALL_TABLES):
            card = self._make_table_card(body, table_cfg)
            card.grid(row=2, column=i, sticky="nsew", padx=(0 if i == 0 else 14, 0), pady=(0, 8))

        # ---- Slotting Analysis & Optimization section ----
        ttk.Separator(body, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=(20, 20))

        ttk.Label(body, text="Slotting Analysis & Optimization", style="H1.TLabel").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(
            body,
            text="Every analysis asks you to pick a date range (and any relevant options) before it runs.",
            style="Muted.TLabel",
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 18))

        row_cursor = 6
        for i, analysis_cfg in enumerate(ALL_ANALYSES):
            card = self._make_analysis_card(body, analysis_cfg)
            col = i % 3
            if col == 0 and i > 0:
                row_cursor += 1
            card.grid(row=row_cursor, column=col, sticky="nsew", padx=(0 if col == 0 else 14, 0), pady=(0, 14))
        row_cursor += 1

        # ---- Reports & Dashboards section ----
        ttk.Separator(body, orient="horizontal").grid(row=row_cursor, column=0, columnspan=3, sticky="ew", pady=(6, 20))
        row_cursor += 1

        ttk.Label(body, text="Reports & Dashboards", style="H1.TLabel").grid(
            row=row_cursor, column=0, columnspan=3, sticky="w", pady=(0, 4))
        row_cursor += 1
        ttk.Label(
            body,
            text="Operational, order-level views - also start with a date range.",
            style="Muted.TLabel",
        ).grid(row=row_cursor, column=0, columnspan=3, sticky="w", pady=(0, 18))
        row_cursor += 1

        for i, report_cfg in enumerate(ALL_REPORTS):
            card = self._make_analysis_card(body, report_cfg)
            col = i % 3
            if col == 0 and i > 0:
                row_cursor += 1
            card.grid(row=row_cursor, column=col, sticky="nsew", padx=(0 if col == 0 else 14, 0), pady=(0, 14))

        # ---- Footer ----
        footer = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Label(footer, text="Data files are read from / written to the local data/ folder " \
                                "(a timestamped backup is kept on every save).",
                  style="MutedPanel.TLabel").pack(side="left")
        ttk.Button(footer, text="Exit", style="Ghost.TButton",
                  command=self.winfo_toplevel().destroy).pack(side="right")

    # ------------------------------------------------------------------
    def _make_table_card(self, parent, table_cfg):
        card = tk.Frame(parent, bg=Palette.PANEL, highlightbackground=Palette.BORDER,
                        highlightthickness=1, bd=0)

        inner = tk.Frame(card, bg=Palette.PANEL, padx=22, pady=20)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=table_cfg.icon, font=("Segoe UI Emoji", 30),
                bg=Palette.PANEL, fg=Palette.TEAL_DARK).pack(anchor="w")
        tk.Label(inner, text=table_cfg.label, font=Fonts.CARD_TITLE,
                bg=Palette.PANEL, fg=Palette.NAVY).pack(anchor="w", pady=(10, 2))
        tk.Label(inner, text=table_cfg.description, font=Fonts.CARD_BODY, bg=Palette.PANEL,
                fg=Palette.TEXT_MUTED, wraplength=220, justify="left").pack(anchor="w")

        count_var = tk.StringVar(value="...")
        tk.Label(inner, textvariable=count_var, font=Fonts.H1, bg=Palette.PANEL,
                fg=Palette.TEAL_DARK).pack(anchor="w", pady=(14, 0))
        tk.Label(inner, text="records on file", font=Fonts.SMALL, bg=Palette.PANEL,
                fg=Palette.TEXT_MUTED).pack(anchor="w")

        btn = ttk.Button(inner, text=f"Open {table_cfg.label} \u2192", style="Accent.TButton",
                         command=lambda: self.on_open_table(table_cfg.key))
        btn.pack(anchor="w", pady=(18, 0), fill="x")

        def refresh_count():
            try:
                dm = DataManager(table_cfg)
                dm.load()
                count_var.set(f"{dm.row_count():,}")
            except Exception:
                count_var.set("?")

        self.after(50, refresh_count)
        self._wire_hover(card, inner)
        return card

    def _make_analysis_card(self, parent, analysis_cfg):
        card = tk.Frame(parent, bg=Palette.PANEL, highlightbackground=Palette.BORDER,
                        highlightthickness=1, bd=0)

        inner = tk.Frame(card, bg=Palette.PANEL, padx=20, pady=18)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text=analysis_cfg.icon, font=("Segoe UI Emoji", 24),
                bg=Palette.PANEL, fg=Palette.TEAL_DARK).pack(anchor="w")
        tk.Label(inner, text=analysis_cfg.label, font=Fonts.CARD_TITLE,
                bg=Palette.PANEL, fg=Palette.NAVY, wraplength=240, justify="left").pack(anchor="w", pady=(8, 2))
        tk.Label(inner, text=analysis_cfg.description, font=Fonts.CARD_BODY, bg=Palette.PANEL,
                fg=Palette.TEXT_MUTED, wraplength=240, justify="left").pack(anchor="w")

        btn = ttk.Button(inner, text="Run \u2192", style="Accent.TButton",
                         command=lambda: self.on_open_analysis(analysis_cfg.key))
        btn.pack(anchor="w", pady=(16, 0), fill="x")

        self._wire_hover(card, inner)
        return card

    @staticmethod
    def _wire_hover(card, inner):
        def on_enter(_e):
            card.configure(highlightbackground=Palette.TEAL)

        def on_leave(_e):
            card.configure(highlightbackground=Palette.BORDER)

        for widget in (card, inner):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
