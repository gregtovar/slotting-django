"""
table_view.py
--------------
A generic "review / add / edit / delete" screen for any CSV table driven
by a TableConfig. One class powers the Customers, Master, and Orders
screens (and any future table) - just pass in a different DataManager.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.theme import Palette, Fonts
from app.ui.record_dialog import RecordDialog

PAGE_SIZES = [25, 50, 100, 250, 500]


class TableView(ttk.Frame):
    def __init__(self, parent, data_manager, on_back):
        super().__init__(parent, style="App.TFrame")
        self.data_manager = data_manager
        self.config = data_manager.config
        self.on_back = on_back

        self.current_rows = []          # filtered/sorted full result set
        self.page = 0
        self.page_size = tk.IntVar(value=100)
        self.sort_column = tk.StringVar(value="")
        self.sort_reverse = False
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._on_search_changed())

        self._build()
        self.refresh()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Header ----
        header = ttk.Frame(self, style="Navy.TFrame", padding=(24, 16))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        back_btn = ttk.Button(header, text="\u2190 Main Menu", style="Secondary.TButton",
                              command=self.on_back)
        back_btn.grid(row=0, column=0, sticky="w")

        title_frame = ttk.Frame(header, style="Navy.TFrame")
        title_frame.grid(row=0, column=1, sticky="w", padx=(20, 0))
        ttk.Label(title_frame, text=f"{self.config.icon}  {self.config.label}",
                  style="Title.TLabel", font=Fonts.H1, background=Palette.NAVY,
                  foreground="#FFFFFF").pack(anchor="w")
        ttk.Label(title_frame, text=self.config.description, style="Subtitle.TLabel",
                  background=Palette.NAVY).pack(anchor="w")

        self.count_label = ttk.Label(header, text="", style="Subtitle.TLabel", background=Palette.NAVY)
        self.count_label.grid(row=0, column=2, sticky="e")

        # ---- Toolbar ----
        toolbar = ttk.Frame(self, style="Panel.TFrame", padding=(20, 12))
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(6, weight=1)

        ttk.Button(toolbar, text="+ Add Record", style="Accent.TButton",
                  command=self._add_record).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(toolbar, text="Edit Selected", style="Ghost.TButton",
                  command=self._edit_selected).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(toolbar, text="Delete Selected", style="Danger.TButton",
                  command=self._delete_selected).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(toolbar, text="\u21bb Refresh", style="Ghost.TButton",
                  command=self.refresh).grid(row=0, column=3, padx=(0, 20))

        ttk.Label(toolbar, text="Search:", style="MutedPanel.TLabel").grid(row=0, column=4, padx=(0, 6))
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=32, style="Search.TEntry")
        search_entry.grid(row=0, column=5, sticky="w")
        search_hint = ", ".join(self.config.field_map()[c].label for c in self.config.search_fields)
        ttk.Label(toolbar, text=f"(searches {search_hint})", style="MutedPanel.TLabel").grid(
            row=0, column=6, sticky="w", padx=(8, 0))

        ttk.Label(toolbar, text="Rows/page:", style="MutedPanel.TLabel").grid(row=0, column=7, padx=(8, 6))
        page_combo = ttk.Combobox(toolbar, textvariable=self.page_size, values=PAGE_SIZES,
                                  width=5, state="readonly")
        page_combo.grid(row=0, column=8)
        page_combo.bind("<<ComboboxSelected>>", lambda e: self._render_page())

        # ---- Grid ----
        grid_frame = ttk.Frame(self, style="App.TFrame", padding=(20, 10))
        grid_frame.grid(row=2, column=0, sticky="nsew")
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.columnconfigure(0, weight=1)

        display_cols = self.config.grid_fields
        self.tree = ttk.Treeview(grid_frame, columns=display_cols, show="headings",
                                 selectmode="extended")
        field_map = self.config.field_map()
        for col in display_cols:
            spec = field_map[col]
            self.tree.heading(col, text=spec.label, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=spec.width, anchor="w", stretch=False)

        vscroll = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        hscroll = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("odd", background=Palette.ROW_ODD)
        self.tree.tag_configure("even", background=Palette.ROW_EVEN)

        self.tree.bind("<Double-1>", lambda e: self._edit_selected())

        # ---- Pagination bar ----
        pager = ttk.Frame(self, style="Panel.TFrame", padding=(20, 10))
        pager.grid(row=3, column=0, sticky="ew")
        pager.columnconfigure(2, weight=1)

        ttk.Button(pager, text="\u2039 Prev", style="Ghost.TButton",
                  command=self._prev_page).grid(row=0, column=0)
        self.page_label = ttk.Label(pager, text="", style="Muted.TLabel")
        self.page_label.grid(row=0, column=1, padx=12)
        ttk.Button(pager, text="Next \u203a", style="Ghost.TButton",
                  command=self._next_page).grid(row=0, column=2, sticky="w")

        self.status_label = ttk.Label(pager, text="", style="Muted.TLabel")
        self.status_label.grid(row=0, column=3, sticky="e")

    # ------------------------------------------------------------------
    # Data flow
    # ------------------------------------------------------------------
    def refresh(self):
        self.data_manager.load()
        self._apply_search_and_sort()

    def _on_search_changed(self):
        self.page = 0
        self._apply_search_and_sort()

    def _apply_search_and_sort(self):
        text = self.search_var.get()
        rows = self.data_manager.search(text)
        col = self.sort_column.get()
        if col:
            field_type = self.config.field_map()[col].type
            rows = self.data_manager.sort_rows(rows, col, self.sort_reverse, field_type)
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

        for i, row in enumerate(page_rows):
            values = [row.get(c, "") for c in self.config.grid_fields]
            key = "|".join(row.get(k, "") for k in self.config.key_fields)
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=key, values=values, tags=(tag,))

        total_all = self.data_manager.row_count()
        if text := self.search_var.get():
            self.count_label.configure(text=f"{total} of {total_all} records match \u201c{text}\u201d")
        else:
            self.count_label.configure(text=f"{total_all} total records")

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
    # Selection helpers
    # ------------------------------------------------------------------
    def _selected_keys(self):
        keys = []
        for iid in self.tree.selection():
            keys.append(tuple(iid.split("|")))
        return keys

    def _selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None
        key = tuple(sel[0].split("|"))
        return self.data_manager.get(key)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _add_record(self):
        RecordDialog(self, self.data_manager, mode="add", on_saved=lambda r: self.refresh())

    def _edit_selected(self):
        row = self._selected_row()
        if row is None:
            messagebox.showinfo("No selection", "Please select a record to edit.", parent=self)
            return
        RecordDialog(self, self.data_manager, mode="edit", initial=row,
                    on_saved=lambda r: self.refresh())

    def _delete_selected(self):
        keys = self._selected_keys()
        if not keys:
            messagebox.showinfo("No selection", "Please select one or more records to delete.", parent=self)
            return
        noun = "record" if len(keys) == 1 else f"{len(keys)} records"
        if not messagebox.askyesno(
            "Confirm delete",
            f"Are you sure you want to permanently delete {noun} from "
            f"{self.config.label}?\n\nA backup of the current file will be kept "
            f"in data/backups before the change is saved.",
            parent=self,
        ):
            return
        removed = self.data_manager.delete_rows(keys)
        self.refresh()
        messagebox.showinfo("Deleted", f"{removed} record(s) deleted.", parent=self)
