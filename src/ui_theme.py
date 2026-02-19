# src/ups_rma_reconciliation/ui_theme.py

"""
UI theming utilities based on ttkbootstrap.

This module encapsulates:
- theme selection (dark / light),
- common color palette (success, warning, error),
- application-wide style configuration (buttons, tables, search box).

The goal is to:
- keep UI styling in one place,
- make it easy to switch themes,
- avoid scattered "magic colors" in the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

try:
    import ttkbootstrap as tb  # type: ignore
except ImportError:
    tb = None  # We still want this module to import without failing in non-GUI contexts.


ThemeName = Literal["dark", "light"]


@dataclass
class ThemePalette:
    """
    Palette of commonly used colors for a given theme.
    """

    bg: str
    fg: str
    accent_ok: str
    accent_warn: str
    accent_err: str
    table_header_bg: str
    table_header_fg: str
    table_row_bg: str
    table_row_alt_bg: str
    search_bg: str
    search_fg: str


DARK_PALETTE = ThemePalette(
    bg="#1e1e1e",
    fg="#e5e5e5",
    accent_ok="#4CAF50",
    accent_warn="#FF9800",
    accent_err="#F44336",
    table_header_bg="#2d2d30",
    table_header_fg="#f5f5f5",
    table_row_bg="#252526",
    table_row_alt_bg="#303031",
    search_bg="#333333",
    search_fg="#ffffff",
)

LIGHT_PALETTE = ThemePalette(
    bg="#f5f5f5",
    fg="#202020",
    accent_ok="#2e7d32",
    accent_warn="#ef6c00",
    accent_err="#c62828",
    table_header_bg="#e0e0e0",
    table_header_fg="#202020",
    table_row_bg="#ffffff",
    table_row_alt_bg="#f0f0f0",
    search_bg="#ffffff",
    search_fg="#202020",
)


class ThemeController:
    """
    High-level theme manager for the GUI.

    Responsibilities:
    - Apply base ttkbootstrap theme.
    - Provide a palette object (colors).
    - Configure common widget styles (buttons, labels, entries, Treeviews).

    Example usage:
        theme_ctrl = ThemeController(theme="dark")
        app = tb.Window(themename=theme_ctrl.tk_theme)
        theme_ctrl.configure_styles(app.style)
    """

    def __init__(self, theme: ThemeName = "dark") -> None:
        if theme not in ("dark", "light"):
            raise ValueError(f"Unsupported theme: {theme}")
        self.theme: ThemeName = theme
        self.palette: ThemePalette = DARK_PALETTE if theme == "dark" else LIGHT_PALETTE

        # Map our logical theme to ttkbootstrap's built-in theme names
        self.tk_theme = "darkly" if theme == "dark" else "flatly"

    def configure_styles(self, style: "tb.Style") -> None:  # type: ignore[name-defined]
        """
        Configure ttkbootstrap styles for common widgets.

        Parameters
        ----------
        style:
            ttkbootstrap Style instance from the main Window.
        """
        if tb is None:
            # ttkbootstrap is not installed; nothing to style.
            return

        # Global font & background
        style.configure(
            ".",
            background=self.palette.bg,
            foreground=self.palette.fg,
            font=("Segoe UI", 10),
        )

        # Buttons
        style.configure(
            "Primary.TButton",
            font=("Segoe UI Semibold", 10),
            padding=6,
        )

        # Table header
        style.configure(
            "UpsHeader.TLabel",
            background=self.palette.table_header_bg,
            foreground=self.palette.table_header_fg,
            padding=(4, 2),
        )

        # Search entry style
        style.configure(
            "Search.TEntry",
            fieldbackground=self.palette.search_bg,
            foreground=self.palette.search_fg,
            padding=4,
        )

    def apply_to_window(self, window: "tb.Window") -> None:  # type: ignore[name-defined]
        """
        Apply background color and style configuration to the main window.
        """
        if tb is None:
            return
        window.style.theme_use(self.tk_theme)
        window.configure(bg=self.palette.bg)
        self.configure_styles(window.style)