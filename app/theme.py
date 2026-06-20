"""
theme.py
---------
Centralized visual theme for the Slotting Optimizer application.
Keeping all colors/fonts in one place makes the whole app look
consistent and makes it trivial to re-skin later.
"""

import tkinter as tk
from tkinter import ttk


class Palette:
    """Color palette - a clean, modern 'warehouse / logistics' look."""

    # Core brand colors
    NAVY = "#0F2A43"          # primary dark (headers, sidebar)
    NAVY_LIGHT = "#16374F"
    TEAL = "#1ABC9C"          # primary accent (buttons, highlights)
    TEAL_DARK = "#149174"
    AMBER = "#F5A623"         # secondary accent (warnings / highlights)
    RED = "#E74C3C"           # destructive actions
    RED_DARK = "#C0392B"
    GREEN = "#2ECC71"         # success / positive

    # Neutrals
    BG = "#F4F6F8"            # app background
    PANEL = "#FFFFFF"         # card / panel background
    BORDER = "#E1E5EA"
    TEXT = "#1F2933"
    TEXT_MUTED = "#6B7785"
    TEXT_ON_DARK = "#F4F6F8"

    # Row striping for tables
    ROW_EVEN = "#FFFFFF"
    ROW_ODD = "#F7F9FB"
    ROW_SELECTED = "#D6F2EC"


class Fonts:
    FAMILY = "Segoe UI"        # falls back gracefully on macOS/Linux
    FAMILY_MONO = "Consolas"

    TITLE = (FAMILY, 22, "bold")
    SUBTITLE = (FAMILY, 11)
    H1 = (FAMILY, 16, "bold")
    H2 = (FAMILY, 13, "bold")
    BODY = (FAMILY, 10)
    BODY_BOLD = (FAMILY, 10, "bold")
    SMALL = (FAMILY, 9)
    BUTTON = (FAMILY, 10, "bold")
    CARD_TITLE = (FAMILY, 14, "bold")
    CARD_BODY = (FAMILY, 9)
    MONO = (FAMILY_MONO, 10)


def apply_theme(root: tk.Tk) -> None:
    """Configure ttk styles globally. Call once, right after creating root."""
    root.configure(bg=Palette.BG)

    style = ttk.Style(root)
    # 'clam' is the most "skinnable" built-in theme across platforms.
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # ---- Generic ----
    style.configure(".", font=Fonts.BODY, background=Palette.BG, foreground=Palette.TEXT)

    # ---- Frames ----
    style.configure("App.TFrame", background=Palette.BG)
    style.configure("Panel.TFrame", background=Palette.PANEL)
    style.configure("Navy.TFrame", background=Palette.NAVY)
    style.configure("Card.TFrame", background=Palette.PANEL, relief="flat")

    # ---- Labels ----
    style.configure("TLabel", background=Palette.BG, foreground=Palette.TEXT, font=Fonts.BODY)
    style.configure("Title.TLabel", background=Palette.NAVY, foreground="#FFFFFF", font=Fonts.TITLE)
    style.configure("Subtitle.TLabel", background=Palette.NAVY, foreground=Palette.TEAL, font=Fonts.SUBTITLE)
    style.configure("H1.TLabel", background=Palette.BG, foreground=Palette.NAVY, font=Fonts.H1)
    style.configure("H2.TLabel", background=Palette.PANEL, foreground=Palette.NAVY, font=Fonts.H2)
    style.configure("Muted.TLabel", background=Palette.BG, foreground=Palette.TEXT_MUTED, font=Fonts.SMALL)
    style.configure("MutedPanel.TLabel", background=Palette.PANEL, foreground=Palette.TEXT_MUTED, font=Fonts.SMALL)
    style.configure("CardTitle.TLabel", background=Palette.PANEL, foreground=Palette.NAVY, font=Fonts.CARD_TITLE)
    style.configure("CardBody.TLabel", background=Palette.PANEL, foreground=Palette.TEXT_MUTED, font=Fonts.CARD_BODY)
    style.configure("CardCount.TLabel", background=Palette.PANEL, foreground=Palette.TEAL_DARK, font=Fonts.H1)
    style.configure("StatusBar.TLabel", background=Palette.NAVY, foreground=Palette.TEXT_ON_DARK, font=Fonts.SMALL)
    style.configure("FieldLabel.TLabel", background=Palette.PANEL, foreground=Palette.TEXT, font=Fonts.BODY_BOLD)
    style.configure("Required.TLabel", background=Palette.PANEL, foreground=Palette.RED, font=Fonts.SMALL)
    style.configure("Error.TLabel", background=Palette.PANEL, foreground=Palette.RED, font=Fonts.SMALL)

    # ---- Buttons ----
    style.configure(
        "Accent.TButton",
        font=Fonts.BUTTON,
        background=Palette.TEAL,
        foreground="#FFFFFF",
        borderwidth=0,
        padding=(14, 8),
    )
    style.map(
        "Accent.TButton",
        background=[("active", Palette.TEAL_DARK), ("disabled", "#A9D9CD")],
    )

    style.configure(
        "Danger.TButton",
        font=Fonts.BUTTON,
        background=Palette.RED,
        foreground="#FFFFFF",
        borderwidth=0,
        padding=(14, 8),
    )
    style.map("Danger.TButton", background=[("active", Palette.RED_DARK), ("disabled", "#F0B3AC")])

    style.configure(
        "Secondary.TButton",
        font=Fonts.BUTTON,
        background=Palette.NAVY_LIGHT,
        foreground="#FFFFFF",
        borderwidth=0,
        padding=(14, 8),
    )
    style.map("Secondary.TButton", background=[("active", Palette.NAVY), ("disabled", "#8FA1B0")])

    style.configure(
        "Ghost.TButton",
        font=Fonts.BUTTON,
        background=Palette.BG,
        foreground=Palette.NAVY,
        borderwidth=1,
        padding=(12, 7),
    )
    style.map("Ghost.TButton", background=[("active", Palette.BORDER)])

    style.configure(
        "Card.TButton",
        font=Fonts.BUTTON,
        background=Palette.PANEL,
        foreground=Palette.NAVY,
        borderwidth=0,
        padding=(0, 0),
    )

    # ---- Entries / Combos ----
    style.configure(
        "TEntry",
        fieldbackground="#FFFFFF",
        foreground=Palette.TEXT,
        bordercolor=Palette.BORDER,
        lightcolor=Palette.BORDER,
        darkcolor=Palette.BORDER,
        padding=6,
    )
    style.configure(
        "TCombobox",
        fieldbackground="#FFFFFF",
        foreground=Palette.TEXT,
        padding=6,
    )
    style.configure(
        "Search.TEntry",
        padding=8,
    )

    # ---- Treeview (the data grids) ----
    style.configure(
        "Treeview",
        background="#FFFFFF",
        fieldbackground="#FFFFFF",
        foreground=Palette.TEXT,
        rowheight=28,
        font=Fonts.BODY,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=Palette.NAVY,
        foreground="#FFFFFF",
        font=Fonts.BODY_BOLD,
        relief="flat",
        padding=(8, 8),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", Palette.NAVY_LIGHT)],
    )
    style.map(
        "Treeview",
        background=[("selected", Palette.ROW_SELECTED)],
        foreground=[("selected", Palette.TEXT)],
    )

    # ---- Notebook (tabs, if used) ----
    style.configure("TNotebook", background=Palette.BG, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=Palette.BORDER,
        foreground=Palette.TEXT,
        font=Fonts.BODY_BOLD,
        padding=(16, 8),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", Palette.PANEL)],
        foreground=[("selected", Palette.NAVY)],
    )

    # ---- Radiobutton / Checkbutton ----
    style.configure("TRadiobutton", background=Palette.PANEL, foreground=Palette.TEXT, font=Fonts.BODY)
    style.map("TRadiobutton", background=[("active", Palette.PANEL)])
    style.configure("TCheckbutton", background=Palette.PANEL, foreground=Palette.TEXT, font=Fonts.BODY)
    style.map("TCheckbutton", background=[("active", Palette.PANEL)])

    # ---- Scrollbar ----
    style.configure("Vertical.TScrollbar", background=Palette.BORDER, troughcolor=Palette.BG, arrowsize=14)
    style.configure("Horizontal.TScrollbar", background=Palette.BORDER, troughcolor=Palette.BG, arrowsize=14)
