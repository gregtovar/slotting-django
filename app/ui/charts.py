"""
charts.py
----------
Small, dependency-free charting widgets built on plain Tkinter Canvas.
No matplotlib or other third-party library is used, consistent with the
rest of this app - this also avoids adding another thing that can go
wrong with a particular Python/Tk install.

Each widget redraws itself on resize, so it can be packed/gridded like
any other widget and will adapt to the window size.
"""

import tkinter as tk
import tkinter.font as tkfont

from app.theme import Palette, Fonts

# A small categorical palette for multi-series charts, built from the
# existing brand colors plus a few complementary tones.
SERIES_COLORS = [Palette.TEAL, Palette.NAVY_LIGHT, Palette.AMBER, Palette.RED, Palette.GREEN, "#8E6CC9", "#3E7CB1"]


def _fit_text(text: str, font_obj: tkfont.Font, max_width: int) -> str:
    """Truncate text with an ellipsis so it renders on a single line within
    max_width pixels, instead of letting Canvas wrap it onto multiple lines
    (which overlaps adjacent rows when row height is small)."""
    if max_width <= 0 or font_obj.measure(text) <= max_width:
        return text
    ellipsis = "\u2026"
    lo, hi = 0, len(text)
    best = ellipsis
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ellipsis
        if font_obj.measure(candidate) <= max_width:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def _heat_color(t: float) -> str:
    """t in [0, 1] -> a color from cool (low activity) to hot (high activity)."""
    t = max(0.0, min(1.0, t))
    # cool grey-blue -> teal -> amber -> red, a 4-stop gradient
    stops = [
        (0.00, (0xE3, 0xE8, 0xED)),   # near-white grey (no/low activity)
        (0.35, (0x6F, 0xC8, 0xB8)),   # teal
        (0.70, (0xF5, 0xA6, 0x23)),   # amber
        (1.00, (0xE7, 0x4C, 0x3C)),   # red (hottest)
    ]
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            frac = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            r = round(c0[0] + (c1[0] - c0[0]) * frac)
            g = round(c0[1] + (c1[1] - c0[1]) * frac)
            b = round(c0[2] + (c1[2] - c0[2]) * frac)
            return f"#{r:02X}{g:02X}{b:02X}"
    return "#E74C3C"


class _BaseChart(tk.Canvas):
    def __init__(self, parent, height=320, bg=None, **kwargs):
        super().__init__(parent, height=height, bg=bg or Palette.PANEL,
                         highlightthickness=0, **kwargs)
        self._redraw_job = None
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        if self._redraw_job is not None:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(40, self.redraw)

    def redraw(self):
        raise NotImplementedError

    def _empty_message(self, text="No data to display for this range."):
        self.delete("all")
        w = self.winfo_width() or 600
        h = self.winfo_height() or 200
        self.create_text(w // 2, h // 2, text=text, fill=Palette.TEXT_MUTED, font=Fonts.BODY)


class HBarChart(_BaseChart):
    """Horizontal bar chart - best for ranked lists with long text labels (e.g. SKU/product names)."""

    def __init__(self, parent, title="", value_fmt="{:,.0f}", bar_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.value_fmt = value_fmt
        self.bar_color = bar_color or Palette.TEAL
        self.items = []  # list of (label, value)

    def set_data(self, items):
        self.items = items
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        if not self.items:
            self._empty_message()
            return

        top_pad = 30 if self.title else 10
        left_pad = 14
        label_w = min(300, int(w * 0.32))
        right_pad = 70
        bar_area_x0 = left_pad + label_w
        bar_area_x1 = w - right_pad
        bottom_pad = 10

        if self.title:
            self.create_text(left_pad, 14, text=self.title, anchor="w",
                             fill=Palette.NAVY, font=Fonts.H2)

        n = len(self.items)
        row_h = (h - top_pad - bottom_pad) / n
        max_val = max((v for _, v in self.items), default=1) or 1
        label_font = tkfont.Font(font=Fonts.SMALL)

        for i, (label, value) in enumerate(self.items):
            y0 = top_pad + i * row_h
            y_mid = y0 + row_h / 2
            bar_h = max(4, row_h * 0.55)

            label_text = _fit_text(str(label), label_font, label_w - 6)
            self.create_text(bar_area_x0 - 8, y_mid, text=label_text, anchor="e",
                             fill=Palette.TEXT, font=Fonts.SMALL)

            frac = (value / max_val) if max_val else 0
            bar_x1 = bar_area_x0 + max(2, frac * (bar_area_x1 - bar_area_x0))
            self.create_rectangle(bar_area_x0, y_mid - bar_h / 2, bar_x1, y_mid + bar_h / 2,
                                  fill=self.bar_color, outline="")

            self.create_text(bar_x1 + 8, y_mid, text=self.value_fmt.format(value), anchor="w",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)

        self.create_line(bar_area_x0, top_pad, bar_area_x0, h - bottom_pad, fill=Palette.BORDER)


class VBarChart(_BaseChart):
    """Vertical bar chart - good for short category labels (status, hour-of-day, day-of-week)."""

    def __init__(self, parent, title="", value_fmt="{:,.0f}", bar_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.value_fmt = value_fmt
        self.bar_color = bar_color or Palette.TEAL
        self.items = []

    def set_data(self, items):
        self.items = items
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        if not self.items:
            self._empty_message()
            return

        top_pad = 36 if self.title else 16
        bottom_pad = 46
        left_pad = 56
        right_pad = 16

        if self.title:
            self.create_text(left_pad, 14, text=self.title, anchor="w",
                             fill=Palette.NAVY, font=Fonts.H2)

        plot_x0, plot_x1 = left_pad, w - right_pad
        plot_y0, plot_y1 = top_pad, h - bottom_pad
        max_val = max((v for _, v in self.items), default=1) or 1

        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            y = plot_y1 - frac * (plot_y1 - plot_y0)
            self.create_line(plot_x0, y, plot_x1, y, fill=Palette.BORDER)
            self.create_text(plot_x0 - 8, y, text=f"{max_val * frac:,.0f}", anchor="e",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)

        n = len(self.items)
        col_w = (plot_x1 - plot_x0) / n
        for i, (label, value) in enumerate(self.items):
            x0 = plot_x0 + i * col_w
            bar_w = max(4, col_w * 0.6)
            x_mid = x0 + col_w / 2
            frac = (value / max_val) if max_val else 0
            bar_y0 = plot_y1 - frac * (plot_y1 - plot_y0)
            self.create_rectangle(x_mid - bar_w / 2, bar_y0, x_mid + bar_w / 2, plot_y1,
                                  fill=self.bar_color, outline="")
            if frac > 0.001:
                self.create_text(x_mid, bar_y0 - 9, text=self.value_fmt.format(value),
                                 fill=Palette.TEXT, font=Fonts.SMALL)
            self.create_text(x_mid, plot_y1 + 10, text=str(label), anchor="n",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL, angle=0, width=max(col_w, 1))

        self.create_line(plot_x0, plot_y0, plot_x0, plot_y1, fill=Palette.BORDER)
        self.create_line(plot_x0, plot_y1, plot_x1, plot_y1, fill=Palette.BORDER)


class LineChart(_BaseChart):
    """Simple line/trend chart - X = ordered category labels (dates), Y = numeric value."""

    def __init__(self, parent, title="", value_fmt="{:,.0f}", line_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.value_fmt = value_fmt
        self.line_color = line_color or Palette.TEAL
        self.items = []  # list of (label, value), already in x-order

    def set_data(self, items):
        self.items = items
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        if not self.items:
            self._empty_message()
            return

        top_pad = 36 if self.title else 16
        bottom_pad = 40
        left_pad = 60
        right_pad = 16

        if self.title:
            self.create_text(left_pad, 14, text=self.title, anchor="w",
                             fill=Palette.NAVY, font=Fonts.H2)

        plot_x0, plot_x1 = left_pad, w - right_pad
        plot_y0, plot_y1 = top_pad, h - bottom_pad
        values = [v for _, v in self.items]
        max_val = max(values, default=1) or 1
        min_val = min(0, min(values, default=0))

        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            y = plot_y1 - frac * (plot_y1 - plot_y0)
            val = min_val + frac * (max_val - min_val)
            self.create_line(plot_x0, y, plot_x1, y, fill=Palette.BORDER)
            self.create_text(plot_x0 - 8, y, text=f"{val:,.0f}", anchor="e",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)

        n = len(self.items)
        span = max(1, n - 1)
        points = []
        for i, (label, value) in enumerate(self.items):
            x = plot_x0 + (i / span) * (plot_x1 - plot_x0) if n > 1 else (plot_x0 + plot_x1) / 2
            frac = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
            y = plot_y1 - frac * (plot_y1 - plot_y0)
            points.append((x, y))

        if len(points) >= 2:
            flat = [c for xy in points for c in xy]
            self.create_line(*flat, fill=self.line_color, width=2, smooth=True)
        for x, y in points:
            self.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=self.line_color, outline="")

        label_every = max(1, n // 10)
        for i, (label, _value) in enumerate(self.items):
            if i % label_every != 0 and i != n - 1:
                continue
            x = points[i][0]
            self.create_text(x, plot_y1 + 8, text=str(label), anchor="n",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)

        self.create_line(plot_x0, plot_y0, plot_x0, plot_y1, fill=Palette.BORDER)
        self.create_line(plot_x0, plot_y1, plot_x1, plot_y1, fill=Palette.BORDER)


class ParetoChart(_BaseChart):
    """Bars (ranked values) + an overlaid cumulative-percent line - the classic ABC visual."""

    def __init__(self, parent, title="", bar_color=None, line_color=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.bar_color = bar_color or Palette.TEAL
        self.line_color = line_color or Palette.AMBER
        self.items = []  # list of (label, value, cumulative_pct)

    def set_data(self, items):
        self.items = items
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        if not self.items:
            self._empty_message()
            return

        top_pad = 36 if self.title else 16
        bottom_pad = 44
        left_pad = 64
        right_pad = 46

        if self.title:
            self.create_text(left_pad, 14, text=self.title, anchor="w",
                             fill=Palette.NAVY, font=Fonts.H2)

        plot_x0, plot_x1 = left_pad, w - right_pad
        plot_y0, plot_y1 = top_pad, h - bottom_pad
        max_val = max((v for _, v, _ in self.items), default=1) or 1

        for frac in (0, 0.25, 0.5, 0.75, 1.0):
            y = plot_y1 - frac * (plot_y1 - plot_y0)
            self.create_line(plot_x0, y, plot_x1, y, fill=Palette.BORDER)
            self.create_text(plot_x0 - 8, y, text=f"{max_val * frac:,.0f}", anchor="e",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)
            self.create_text(plot_x1 + 8, y, text=f"{frac * 100:.0f}%", anchor="w",
                             fill=Palette.TEXT_MUTED, font=Fonts.SMALL)

        n = len(self.items)
        col_w = (plot_x1 - plot_x0) / n
        line_points = []
        for i, (label, value, cum_pct) in enumerate(self.items):
            x0 = plot_x0 + i * col_w
            bar_w = max(2, col_w * 0.7)
            x_mid = x0 + col_w / 2
            frac = (value / max_val) if max_val else 0
            bar_y0 = plot_y1 - frac * (plot_y1 - plot_y0)
            self.create_rectangle(x_mid - bar_w / 2, bar_y0, x_mid + bar_w / 2, plot_y1,
                                  fill=self.bar_color, outline="")
            line_y = plot_y1 - (cum_pct / 100.0) * (plot_y1 - plot_y0)
            line_points.append((x_mid, line_y))

            label_every = max(1, n // 12)
            if i % label_every == 0 or i == n - 1:
                self.create_text(x_mid, plot_y1 + 8, text=str(label), anchor="n",
                                 fill=Palette.TEXT_MUTED, font=Fonts.SMALL, angle=0)

        if len(line_points) >= 2:
            flat = [c for xy in line_points for c in xy]
            self.create_line(*flat, fill=self.line_color, width=2)

        self.create_line(plot_x0, plot_y0, plot_x0, plot_y1, fill=Palette.BORDER)
        self.create_line(plot_x0, plot_y1, plot_x1, plot_y1, fill=Palette.BORDER)


class HeatGrid(_BaseChart):
    """
    A grid of clickable, heat-colored cells - the basis for the Warehouse
    Map drill-down. Each cell: (code, label, value). Color intensity is
    relative to the max value among currently-shown cells.
    """

    def __init__(self, parent, on_cell_click=None, value_fmt="{:,.0f}", **kwargs):
        super().__init__(parent, **kwargs)
        self.on_cell_click = on_cell_click
        self.value_fmt = value_fmt
        self.cells = []  # list of dicts: code, label, value
        self._cell_bounds = []  # (x0, y0, x1, y1, code)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Motion>", self._on_motion)
        self._tooltip_id = None

    def set_cells(self, cells):
        self.cells = cells
        self.redraw()

    def redraw(self):
        self.delete("all")
        self._cell_bounds = []
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return
        if not self.cells:
            self._empty_message("No locations found for this selection.")
            return

        n = len(self.cells)
        cols = max(1, min(n, round((n * w / max(h, 1)) ** 0.5)))
        rows = -(-n // cols)

        pad = 6
        cell_w = (w - pad) / cols - pad
        cell_h = max(46, (h - pad) / rows - pad)

        max_val = max((c["value"] for c in self.cells), default=1) or 1

        for i, cell in enumerate(self.cells):
            r, c = divmod(i, cols)
            x0 = pad + c * (cell_w + pad)
            y0 = pad + r * (cell_h + pad)
            x1 = x0 + cell_w
            y1 = y0 + cell_h
            frac = cell["value"] / max_val if max_val else 0
            color = _heat_color(frac)
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline=Palette.PANEL, width=2)
            text_color = Palette.TEXT if frac < 0.7 else "#FFFFFF"
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2 - 8, text=cell["label"],
                             fill=text_color, font=Fonts.BODY_BOLD)
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2 + 10,
                             text=self.value_fmt.format(cell["value"]),
                             fill=text_color, font=Fonts.SMALL)
            self._cell_bounds.append((x0, y0, x1, y1, cell["code"]))

    def _on_click(self, event):
        if not self.on_cell_click:
            return
        for x0, y0, x1, y1, code in self._cell_bounds:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.on_cell_click(code)
                return

    def _on_motion(self, event):
        self.configure(cursor="hand2" if self._cell_at(event.x, event.y) else "arrow")

    def _cell_at(self, x, y):
        for x0, y0, x1, y1, code in self._cell_bounds:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return code
        return None
