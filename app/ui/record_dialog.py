"""
record_dialog.py
-----------------
A modal Add/Edit form generated dynamically from a TableConfig's field
list. Works for any table - customers, master, orders, or future ones -
without needing a hand-built form per table.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from app.theme import Palette, Fonts
from app.data_manager import ValidationError


class RecordDialog(tk.Toplevel):
    """
    mode: "add" or "edit"
    data_manager: DataManager for the table
    initial: dict of existing values (for edit) or partial prefill (for add)
    on_saved: callback(saved_row_dict) invoked after a successful save
    """

    def __init__(self, parent, data_manager, mode="add", initial=None, on_saved=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.config = data_manager.config
        self.mode = mode
        self.initial = initial or {}
        self.on_saved = on_saved
        self.vars = {}
        self.original_key = tuple(self.initial.get(k, "") for k in self.config.key_fields) if mode == "edit" else None

        self.title(f"{'Add' if mode == 'add' else 'Edit'} {self.config.label[:-1] if self.config.label.endswith('s') else self.config.label} Record")
        self.configure(bg=Palette.PANEL)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build()
        self._center_on_parent(parent)
        self.bind("<Escape>", lambda e: self.destroy())

    def _center_on_parent(self, parent):
        self.update_idletasks()
        w, h = 720, min(720, 90 + 46 * len(self.config.fields) // 2)
        try:
            px, py = parent.winfo_rootx(), parent.winfo_rooty()
            pw, ph = parent.winfo_width(), parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        except tk.TclError:
            x, y = 200, 80
        self.geometry(f"{w}x{h}+{max(x,0)}+{max(y,0)}")
        self.minsize(560, 360)

    # ------------------------------------------------------------------
    def _build(self):
        header = ttk.Frame(self, style="Navy.TFrame", padding=(20, 14))
        header.pack(fill="x")
        action = "New" if self.mode == "add" else "Edit"
        singular = self.config.label[:-1] if self.config.label.endswith("s") else self.config.label
        ttk.Label(header, text=f"{action} {singular}", style="Title.TLabel",
                  font=Fonts.H1, background=Palette.NAVY, foreground="#FFFFFF").pack(anchor="w")
        ttk.Label(header, text=self.config.description, style="Subtitle.TLabel",
                  background=Palette.NAVY).pack(anchor="w")

        body_outer = ttk.Frame(self, style="Panel.TFrame")
        body_outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(body_outer, bg=Palette.PANEL, highlightthickness=0)
        vscroll = ttk.Scrollbar(body_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        form = ttk.Frame(canvas, style="Panel.TFrame", padding=(24, 18))
        form_id = canvas.create_window((0, 0), window=form, anchor="nw")

        def on_form_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(form_id, width=event.width)

        form.bind("<Configure>", on_form_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        form.columnconfigure(0, weight=0)
        form.columnconfigure(1, weight=1)

        self.error_label = ttk.Label(form, text="", style="Error.TLabel", wraplength=600, justify="left")

        row_i = 0
        for spec in self.config.fields:
            label_text = spec.label + (" *" if spec.required else "")
            lbl = ttk.Label(form, text=label_text, style="FieldLabel.TLabel")
            lbl.grid(row=row_i, column=0, sticky="ne", padx=(0, 12), pady=6)

            value = self.initial.get(spec.name, "")
            var = tk.StringVar(value=value)
            self.vars[spec.name] = var

            widget = self._make_widget(form, spec, var)
            widget.grid(row=row_i, column=1, sticky="ew", pady=6)

            if spec.name == self.config.id_field and self.mode == "add":
                btn = ttk.Button(form, text="Suggest", style="Ghost.TButton",
                                  command=lambda v=var: self._suggest_id(v))
                btn.grid(row=row_i, column=2, padx=(8, 0))

            if spec.help:
                row_i += 1
                ttk.Label(form, text=spec.help, style="MutedPanel.TLabel").grid(
                    row=row_i, column=1, sticky="w", pady=(0, 4))
            row_i += 1

        self.error_label.grid(row=row_i, column=0, columnspan=3, sticky="w", pady=(8, 0))

        footer = ttk.Frame(self, style="Panel.TFrame", padding=(20, 12))
        footer.pack(fill="x")
        ttk.Button(footer, text="Cancel", style="Ghost.TButton",
                  command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(footer, text="Save Record", style="Accent.TButton",
                  command=self._on_save).pack(side="right")

    def _make_widget(self, parent, spec, var):
        if spec.type == "choice" and spec.choices:
            cb = ttk.Combobox(parent, textvariable=var, values=spec.choices, state="normal")
            return cb
        if spec.type == "date":
            frame = ttk.Frame(parent, style="Panel.TFrame")
            entry = ttk.Entry(frame, textvariable=var, width=18)
            entry.pack(side="left", fill="x", expand=True)
            ttk.Button(frame, text="Today", style="Ghost.TButton",
                      command=lambda: var.set(date.today().isoformat())).pack(side="left", padx=(6, 0))
            return frame
        entry = ttk.Entry(parent, textvariable=var)
        return entry

    def _suggest_id(self, var):
        if self.config.key == "orders":
            var.set(self.data_manager.suggest_next_order_number())
        else:
            var.set(self.data_manager.suggest_next_id())

    # ------------------------------------------------------------------
    def _collect(self):
        return {name: var.get() for name, var in self.vars.items()}

    def _on_save(self):
        data = self._collect()
        try:
            if self.mode == "add":
                saved = self.data_manager.add_row(data)
            else:
                saved = self.data_manager.update_row(self.original_key, data)
        except ValidationError as e:
            self.error_label.configure(text=str(e))
            return
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Unexpected error", f"Could not save record:\n{e}", parent=self)
            return

        if self.on_saved:
            self.on_saved(saved)
        self.destroy()
