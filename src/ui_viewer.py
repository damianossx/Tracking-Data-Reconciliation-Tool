# src/ups_rma_reconciliation/ui_viewer.py

"""
Canvas-based table viewer for large text datasets.

Key behaviours (simplified version of your original CanvasTable):
- Render a header row and body rows on a Tkinter Canvas.
- Support vertical and horizontal scrolling.
- Allow on-demand wrapping: clicking a row toggles full multi-line text vs truncated.
- Provide a simple search API to highlight matching text in visible cells.

Design notes:
- This is a simplified, portfolio-friendly implementation.
- It focuses on readability and core behaviours rather than micro-optimizations.
"""

from __future__ import annotations

from typing import List, Sequence

import tkinter as tk
from tkinter import ttk


class CanvasTable(ttk.Frame):
    """
    Simple canvas-based table widget.

    Public API:
        set_data(columns, rows)
        clear()
        search(text)
    """

    def __init__(
        self,
        master: tk.Widget,
        row_height: int = 22,
        header_height: int = 24,
        wrap_col_index: int = 2,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        master:
            Parent Tkinter widget.
        row_height:
            Default height for rows (in pixels).
        header_height:
            Header row height (in pixels).
        wrap_col_index:
            Index of the column that contains long text (e.g. TN Details).
        """
        super().__init__(master, **kwargs)
        self.row_height = row_height
        self.header_height = header_height
        self.wrap_col_index = wrap_col_index

        # Data
        self.columns: List[str] = []
        self.rows: List[Sequence[str]] = []

        # Internal state
        self._row_wrap_state: List[bool] = []  # True if row is expanded (wrapped)
        self._search_term: str = ""
        self._header_items: List[int] = []
        self._row_items: List[List[int]] = []  # canvas item ids per row
        self._row_y_positions: List[int] = []

        # Build widgets
        self._build_widgets()

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_widgets(self) -> None:
        # Canvas for header + body
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Bind resizing and scrolling
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Row click for wrapping
        self.canvas.bind("<Button-1>", self._on_click)

    # ------------------------------------------------------------------
    # Data API
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """
        Remove all data and visuals from the table.
        """
        self.columns = []
        self.rows = []
        self._row_wrap_state = []
        self._search_term = ""
        self._header_items.clear()
        self._row_items.clear()
        self._row_y_positions.clear()
        self.canvas.delete("all")

    def set_data(
        self,
        columns: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> None:
        """
        Load new data into the table and redraw.

        Parameters
        ----------
        columns:
            Sequence of column headers.
        rows:
            Sequence of row values (each row must have the same length as `columns`).
        """
        self.clear()
        self.columns = list(columns)
        self.rows = [list(r) for r in rows]
        self._row_wrap_state = [False for _ in self.rows]
        self._draw()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        self.canvas.delete("all")
        self._header_items.clear()
        self._row_items.clear()
        self._row_y_positions.clear()

        width = self.canvas.winfo_width()
        if width <= 0:
            width = 800  # fallback

        # Simple column width distribution: equal-width columns
        col_count = max(1, len(self.columns))
        col_width = width // col_count

        # Draw header
        y = 0
        for col_idx, col_name in enumerate(self.columns):
            x = col_idx * col_width
            item = self.canvas.create_rectangle(
                x,
                y,
                x + col_width,
                y + self.header_height,
                fill="#3f3f46",
                outline="#1f2933",
            )
            text_item = self.canvas.create_text(
                x + 4,
                y + self.header_height / 2,
                text=str(col_name),
                anchor="w",
                fill="white",
                font=("Segoe UI Semibold", 9),
            )
            self._header_items.extend([item, text_item])

        y += self.header_height

        # Draw rows
        for row_idx, row in enumerate(self.rows):
            self._row_y_positions.append(y)
            row_items: List[int] = []

            is_wrapped = self._row_wrap_state[row_idx]
            # If wrapped, allow a larger height multiplier
            row_height = self.row_height * (3 if is_wrapped else 1)

            for col_idx, value in enumerate(row):
                x = col_idx * col_width
                bg = "#111827" if row_idx % 2 == 0 else "#020617"

                rect_id = self.canvas.create_rectangle(
                    x,
                    y,
                    x + col_width,
                    y + row_height,
                    fill=bg,
                    outline="#1f2933",
                )

                display_text = self._get_display_text(
                    value,
                    col_width=col_width,
                    wrapped=is_wrapped and col_idx == self.wrap_col_index,
                )

                text_color = "#e5e7eb"

                text_id = self.canvas.create_text(
                    x + 4,
                    y + 4,
                    text=display_text,
                    anchor="nw",
                    fill=text_color,
                    font=("Segoe UI", 9),
                    width=(col_width - 8) if is_wrapped and col_idx == self.wrap_col_index else 0,
                )

                # FIX: correct brackets/parentheses here
                row_items.extend([rect_id, text_id])

            self._row_items.append(row_items)
            y += row_height

        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # After redraw, re-apply search highlight (if any)
        if self._search_term:
            self._apply_search_highlight()

    def _get_display_text(
        self,
        value: str,
        col_width: int,
        wrapped: bool,
        max_chars_per_line: int = 80,
    ) -> str:
        """
        Decide how to render cell text based on:
        - whether wrapping is enabled,
        - approximate number of characters per line.

        If not wrapped:
            - show a single-line preview with '…' suffix if truncated.
        If wrapped:
            - show the full text; the canvas text item will wrap automatically.
        """
        text = str(value or "")

        if wrapped:
            return text

        # Approximate truncation: not perfect but good enough for preview
        max_chars = max(10, col_width // 7)  # 7 px per char heuristic
        if len(text) > max_chars:
            return text[: max_chars - 1] + "…"
        return text

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_canvas_configure(self, event) -> None:
        """
        Redraw content when the canvas size changes.
        """
        self._draw()

    def _on_mousewheel(self, event) -> None:
        """
        Mouse wheel vertical scrolling handler.
        """
        # Windows / macOS have different sign conventions; normalize
        delta = -1 * int(event.delta / 120)
        self.canvas.yview_scroll(delta, "units")

    def _on_click(self, event) -> None:
        """
        Toggle wrap state on row click.

        - Identify clicked row by y-coordinate.
        - Flip wrap state.
        - Redraw table.
        """
        y = self.canvas.canvasy(event.y)
        # skip header row
        if y < self.header_height:
            return

        # Find row index based on stored y-positions
        for idx, row_y in enumerate(self._row_y_positions):
            next_y = row_y + self.row_height * (3 if self._row_wrap_state[idx] else 1)
            if row_y <= y < next_y:
                self._row_wrap_state[idx] = not self._row_wrap_state[idx]
                self._draw()
                break

    # ------------------------------------------------------------------
    # Search API
    # ------------------------------------------------------------------

    def search(self, text: str) -> None:
        """
        Search for text across all visible cells.

        Behaviour:
        - store search term,
        - highlight cells containing the term by changing text color.

        This is intentionally minimal; the App can call `.search()`
        whenever the search entry changes.
        """
        self._search_term = text.strip().lower()
        self._apply_search_highlight()

    def _apply_search_highlight(self) -> None:
        """
        Re-apply search highlights to all rows.
        """
        if not self._row_items:
            return

        term = self._search_term
        for row_idx, row in enumerate(self.rows):
            items = self._row_items[row_idx]
            # items are stored as [rect, text, rect, text, ...]
            for col_idx, value in enumerate(row):
                text_item_id = items[col_idx * 2 + 1]  # text item
                value_str = str(value or "")
                if term and term in value_str.lower():
                    self.canvas.itemconfig(text_item_id, fill="#facc15")  # amber
                else:
                    self.canvas.itemconfig(text_item_id, fill="#e5e7eb")