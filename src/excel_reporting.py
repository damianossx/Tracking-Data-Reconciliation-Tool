# src/ups_rma_reconciliation/excel_reporting.py

"""
Excel reporting layer.

This module is responsible for:
- taking the reconciled DataFrames:
    - RMA Analysis
    - Non-Standard RMAs
- writing them into an Excel workbook,
- applying:
    - column widths,
    - text wrapping,
    - header/body alignment.

Rich-text alerts and per-line highlight can be added on top using
openpyxl's rich text API (see your original implementation).
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, date as _date

import pandas as pd
import openpyxl
from openpyxl.styles import Alignment

from .config import DEST_SHEET_FINAL, SHEET_NAME_NON_STANDARD, FINAL_COLS
from .core_reconciliation import build_final_output_df  # if you want to reuse


def apply_final_column_layout(ws) -> None:
    """
    Apply column widths for the main RMA Analysis / Non-Standard RMAs sheets.
    """
    ws.column_dimensions["A"].width = 15   # Manifest Date
    ws.column_dimensions["B"].width = 15   # RMA Number
    ws.column_dimensions["C"].width = 170  # Tracking Number - Details
    ws.column_dimensions["D"].width = 20   # Status
    ws.column_dimensions["E"].width = 55   # Shipper Name
    ws.column_dimensions["F"].width = 65   # Ship To
    ws.column_dimensions["G"].width = 18   # Scheduled Delivery
    ws.column_dimensions["H"].width = 18   # Date Delivered
    ws.column_dimensions["I"].width = 125  # Exception Description
    ws.column_dimensions["J"].width = 75   # Exception Resolution
    ws.column_dimensions["K"].width = 15   # Weight


def apply_wrap_and_freeze(ws, freeze_cell: str = "A2") -> None:
    """
    Enable word-wrap and freeze the header row for a given worksheet.
    """
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = freeze_cell


def save_reconciliation_to_excel(
    reconciled_df: pd.DataFrame,
    non_standard_df: pd.DataFrame,
    output_path: Path,
    analysis_date: _date | None = None,
) -> None:
    """
    Persist the analysis to an Excel workbook with two tabs:

    1) "RMA Analysis"
    2) "Non-Standard RMAs"

    Notes
    -----
    - This function overwrites the file if it already exists.
      The caller is responsible for archiving or versioning.
    - Rich-text alerts (orange/red) can be added by extending this function
      using openpyxl's `CellRichText` API as in your original script.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_dt = analysis_date or datetime.now().date()

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        reconciled_df.to_excel(writer, sheet_name=DEST_SHEET_FINAL, index=False)
        non_standard_df.to_excel(writer, sheet_name=SHEET_NAME_NON_STANDARD, index=False)

        # Post-processing with openpyxl
        book = writer.book

        for sheet_name in (DEST_SHEET_FINAL, SHEET_NAME_NON_STANDARD):
            if sheet_name not in book.sheetnames:
                continue
            ws = book[sheet_name]
            apply_final_column_layout(ws)
            apply_wrap_and_freeze(ws, freeze_cell="A2")

    # At this point the Excel file is fully written and formatted.