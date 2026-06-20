#!/usr/bin/env python3
"""
Slotting Optimizer
===================
Warehouse Optimization Suite - Phase 1 (Data Management)

Run this file to launch the application:

    python main.py

This phase provides full CRUD (review / add / edit / delete) screens for
the three reference CSV files:
    data/customers.csv
    data/master.csv
    data/orders.csv

Later phases will add the actual slotting analysis & optimization engine
that uses these tables together.
"""

import os

# On macOS, Python builds that link against Apple's bundled system Tcl/Tk
# (8.5.x) print a deprecation warning on every launch. Setting this before
# tkinter is imported silences that cosmetic warning. It does NOT change
# which Tk is actually used - see the README for how to install a modern
# Tk 8.6 if you also see a blank window on first launch (a known bug in
# that old system Tk, worked around below).
os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import sys
import tkinter as tk
from tkinter import messagebox

from app.app_window import AppWindow


def _fix_blank_window_on_old_tk(root: tk.Tk) -> None:
    """
    Workaround for a long-standing bug in Apple's bundled Tcl/Tk 8.5:
    the window paints completely blank until it is resized or moved.
    This nudges the window size by 1px and back, twice, shortly after
    launch, which forces Tk to repaint without the user noticing.
    Harmless (and a no-op in practice) on platforms/Tk builds that don't
    have the bug.
    """

    def nudge():
        try:
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            x = root.winfo_x()
            y = root.winfo_y()
            root.geometry(f"{w}x{h + 1}+{x}+{y}")
            root.update_idletasks()
            root.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass

    root.after(60, nudge)
    root.after(250, nudge)


def main():
    root = tk.Tk()
    try:
        app = AppWindow(root)  # noqa: F841  (kept alive via closure/bindings)
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror("Startup error", f"The application failed to start:\n\n{exc}")
        raise
    _fix_blank_window_on_old_tk(root)
    root.mainloop()


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("Slotting Optimizer requires Python 3.8 or newer.")
        sys.exit(1)
    main()

