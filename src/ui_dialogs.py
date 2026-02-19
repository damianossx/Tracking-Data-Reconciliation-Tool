# src/ups_rma_reconciliation/ui_dialogs.py

"""
Dialog windows used in the UPS RMA Reconciliation GUI.

Includes:
- SheetCellDialog: select Excel sheet name and top-left cell.
- BaselineModeDialog: choose how to obtain the baseline (local file / SharePoint).
- HelpDialog: static help / instructions.
- KPIInfoDialog: explain how KPIs are calculated.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple


class SheetCellDialog(tk.Toplevel):
    """
    Dialog to select an Excel sheet and starting cell for data paste.

    Returns:
        (sheet_name, start_cell) or (None, None) if cancelled.
    """

    def __init__(
        self,
        master: tk.Widget,
        title: str = "Select Sheet & Cell",
        default_sheet: str = "RMA Analysis",
        default_cell: str = "A1",
    ) -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.sheet: Optional[str] = None
        self.cell: Optional[str] = None

        tk.Label(self, text="Sheet name:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.sheet_var = tk.StringVar(value=default_sheet)
        ttk.Entry(self, textvariable=self.sheet_var, width=30).grid(
            row=0, column=1, sticky="ew", padx=8, pady=(8, 2)
        )

        tk.Label(self, text="Start cell (e.g. A1):").grid(
            row=1, column=0, sticky="w", padx=8, pady=2
        )
        self.cell_var = tk.StringVar(value=default_cell)
        ttk.Entry(self, textvariable=self.cell_var, width=10).grid(
            row=1, column=1, sticky="w", padx=8, pady=2
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).grid(
            row=0, column=1, padx=4
        )

        self.columnconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_ok(self) -> None:
        self.sheet = self.sheet_var.get().strip() or None
        self.cell = self.cell_var.get().strip() or None
        self.destroy()

    def _on_cancel(self) -> None:
        self.sheet = None
        self.cell = None
        self.destroy()

    @classmethod
    def ask(cls, master: tk.Widget, **kwargs) -> Tuple[Optional[str], Optional[str]]:
        dlg = cls(master, **kwargs)
        master.wait_window(dlg)
        return dlg.sheet, dlg.cell


class BaselineModeDialog(tk.Toplevel):
    """
    Dialog to select baseline acquisition mode.

    Modes:
    - 'local'     : user picks a local Excel file.
    - 'sharepoint': baseline will be obtained from SharePoint/OneDrive.
    """

    def __init__(self, master: tk.Widget, title: str = "Baseline Mode") -> None:
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()

        self.mode: Optional[str] = None
        self._mode_var = tk.StringVar(value="local")

        tk.Label(
            self,
            text="How do you want to provide the baseline report?",
            justify="left",
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 6), sticky="w")

        ttk.Radiobutton(
            self,
            text="Local Excel file (manual selection)",
            variable=self._mode_var,
            value="local",
        ).grid(row=1, column=0, columnspan=2, padx=12, sticky="w")

        ttk.Radiobutton(
            self,
            text="SharePoint / OneDrive (via Graph API or sync folder)",
            variable=self._mode_var,
            value="sharepoint",
        ).grid(row=2, column=0, columnspan=2, padx=12, sticky="w")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="OK", command=self._on_ok).grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).grid(
            row=0, column=1, padx=4
        )

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_ok(self) -> None:
        self.mode = self._mode_var.get()
        self.destroy()

    def _on_cancel(self) -> None:
        self.mode = None
        self.destroy()

    @classmethod
    def ask(cls, master: tk.Widget) -> Optional[str]:
        dlg = cls(master)
        master.wait_window(dlg)
        return dlg.mode


class HelpDialog(tk.Toplevel):
    """
    Simple help dialog explaining the tool and its workflow.
    """

    def __init__(self, master: tk.Widget, help_text: str) -> None:
        super().__init__(master)
        self.title("Help")
        self.resizable(True, True)
        self.grab_set()

        text = tk.Text(self, wrap="word")
        text.insert("1.0", help_text)
        text.configure(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(self, orient="vertical", command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Button(self, text="Close", command=self.destroy).grid(
            row=1, column=0, columnspan=2, pady=6
        )


class KPIInfoDialog(tk.Toplevel):
    """
    Dialog that explains key KPI definitions and formulas.
    """

    def __init__(self, master: tk.Widget, kpi_text: str) -> None:
        super().__init__(master)
        self.title("KPI Definitions")
        self.resizable(True, True)
        self.grab_set()

        text = tk.Text(self, wrap="word")
        text.insert("1.0", kpi_text)
        text.configure(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(self, orient="vertical", command=text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scroll.set)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        ttk.Button(self, text="Close", command=self.destroy).grid(
            row=1, column=0, columnspan=2, pady=6
        )