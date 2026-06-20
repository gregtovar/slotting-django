"""
colors.py (web)
------------------
Plain color constants for the Streamlit UI - intentionally a standalone
module that does NOT import from app.theme.

app/theme.py does `import tkinter as tk` at the top (it's used to style
the desktop app's ttk widgets). That import works fine on a normal
desktop OS, but many minimal server / cloud Python environments
(notably Streamlit Community Cloud) don't have the underlying Tcl/Tk
system library installed at all - importing tkinter there raises
`ImportError: libtk8.6.so: cannot open shared object file`, even though
nothing ever tries to open a window. The web UI must have zero
dependency on tkinter so it can run anywhere Streamlit can.

These values are kept in sync with app/theme.py's Palette by hand - if
you change one, change the other.
"""

NAVY = "#0F2A43"
NAVY_LIGHT = "#16374F"
TEAL = "#1ABC9C"
TEAL_DARK = "#149174"
AMBER = "#F5A623"
RED = "#E74C3C"
RED_DARK = "#C0392B"
GREEN = "#2ECC71"

BG = "#F4F6F8"
PANEL = "#FFFFFF"
BORDER = "#E1E5EA"
TEXT = "#1F2933"
TEXT_MUTED = "#6B7785"
TEXT_ON_DARK = "#F4F6F8"

ROW_EVEN = "#FFFFFF"
ROW_ODD = "#F7F9FB"
ROW_SELECTED = "#D6F2EC"
