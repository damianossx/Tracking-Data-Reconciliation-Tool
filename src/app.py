# src/ups_rma_reconciliation/app.py

"""
Main GUI application for the UPS RMA Reconciliation tool.

This module wires together:
- data ingestion,
- reconciliation engine,
- Excel reporting,
- theme controller,
- canvas table viewer,
- audit & session logging.

The GUI is intentionally streamlined to keep the code readable
and portfolio-friendly while still reflecting a realistic workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import ttkbootstrap as tb  # type: ignore
except ImportError:
    tb = None

from .data_ingestion import load_inputs
from .core_reconciliation import build_new_norm, build_final_output_df
from .excel_reporting import save_reconciliation_to_excel
from .ui_theme import ThemeController
from .ui_viewer import CanvasTable
from .ui_dialogs import HelpDialog, KPIInfoDialog
from .logging_audit import setup_audit_logger, SessionLogger


HELP_TEXT = """
UPS RMA Tracking Data Reconciliation Tool

1. Select UPS CSV report:
   - File > Select UPS CSV...
   - The CSV file is exported from UPS Quantum View Manage.

2. Select baseline Excel report:
   - File > Select Baseline Excel...
   - The baseline is your historical RMA analysis report.

3. Run analysis:
   - Click 'Run Analysis'.
   - The tool will:
       - build a normalized view of the UPS CSV (per TN, per RMA),
       - construct a final 'RMA Analysis' view.

4. Review results:
   - The main viewer shows the 'RMA Analysis' table.
   - Click a row to expand/collapse long text in the details column.
   - Use the search box to highlight matching text.

5. Save to Excel:
   - Click 'Save to Excel' to export:
       - RMA Analysis
       - Non-Standard RMAs (if implemented in your core_reconciliation).
"""

KPI_TEXT = """
KPI Definitions (example):

1) Reconciliation Cycle Time
   - Time from 'Run Analysis' click until completion.
   - Unit: seconds.

2) Process Efficiency Gain (PEG)
   - Estimate of manual effort saved vs. manual reconciliation.
   - Inputs:
       - B_manual_min : baseline minutes per RMA (default: 8 min)
       - Weekly overhead: additional minutes per weekly run (default: 2 min)
   - Example formula:
       PEG = (B_manual_min * impacted_RMAs + overhead) - runtime_minutes

3) Impact Penetration Rate
   - impacted_RMAs / total_RMAs

These KPIs are illustrative for portfolio purposes.
In a production environment you would align them with
your organization's process metrics and SLA targets.
"""


class App:
    """
    High-level GUI application.

    Responsibilities:
    - Build the Tkinter/ttkbootstrap window and layout.
    - Handle user actions (file selection, analysis, save).
    - Delegate data processing to the core engine.
    - Display results in the CanvasTable viewer.
    - Use audit and session logging for traceability.
    """

    def __init__(self, theme: str = "dark") -> None:
        if tb is None:
            raise ImportError("ttkbootstrap is required for the GUI (pip install ttkbootstrap).")

        self.theme_ctrl = ThemeController(theme="dark" if theme == "dark" else "light")
        self.window = tb.Window(
            title="UPS RMA Tracking Data Reconciliation",
            themename=self.theme_ctrl.tk_theme,
            resizable=(True, True),
        )
        self.theme_ctrl.apply_to_window(self.window)

        # Logging
        log_dir = Path.cwd() / "logs"
        self.audit_logger = setup_audit_logger(log_dir=log_dir)
        self.session_logger = SessionLogger.create(base_dir=log_dir)

        # State
        self.ups_csv_path: Optional[Path] = None
        self.baseline_path: Optional[Path] = None
        self.rma_analysis_df = None
        self.non_standard_df = None

        # Build UI
        self._build_menu()
        self._build_body()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.window)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(label="Select UPS CSV...", command=self.on_select_ups_csv)
        file_menu.add_command(
            label="Select Baseline Excel...", command=self.on_select_baseline_excel
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="Help", command=self.on_show_help)
        help_menu.add_command(label="KPI Info", command=self.on_show_kpi_info)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.window.config(menu=menu_bar)

    def _build_body(self) -> None:
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Left side: controls
        left = ttk.Frame(main_frame)
        left.pack(side="left", fill="y", padx=(0, 8))

        self.btn_select_ups = ttk.Button(
            left,
            text="Select UPS CSV",
            style="Primary.TButton",
            command=self.on_select_ups_csv,
        )
        self.btn_select_ups.pack(fill="x", pady=4)

        self.btn_select_baseline = ttk.Button(
            left,
            text="Select Baseline Excel",
            command=self.on_select_baseline_excel,
        )
        self.btn_select_baseline.pack(fill="x", pady=4)

        self.btn_run = ttk.Button(
            left,
            text="Run Analysis",
            command=self.on_run_analysis,
        )
        self.btn_run.pack(fill="x", pady=(12, 4))

        self.btn_save = ttk.Button(
            left,
            text="Save to Excel",
            command=self.on_save_to_excel,
            state="disabled",
        )
        self.btn_save.pack(fill="x", pady=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        tk.Label(left, text="Search in results:").pack(anchor="w")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(left, textvariable=self.search_var, style="Search.TEntry")
        search_entry.pack(fill="x", pady=(2, 6))
        search_entry.bind("<KeyRelease>", self._on_search_change)

        # Right side: viewer
        right = ttk.Frame(main_frame)
        right.pack(side="right", fill="both", expand=True)

        self.viewer = CanvasTable(right)
        self.viewer.pack(fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status = ttk.Label(self.window, textvariable=self.status_var, anchor="w")
        status.pack(side="bottom", fill="x")

        self.window.geometry("1100x600")

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def on_select_ups_csv(self) -> None:
        """
        Ask the user to select the UPS CSV report file.
        """
        path_str = filedialog.askopenfilename(
            title="Select UPS CSV report",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path_str:
            return

        path = Path(path_str)
        self.ups_csv_path = path
        self._set_status(f"UPS CSV selected: {path.name}")
        self.audit_logger.info("UPS CSV selected", extra={"file": str(path)})
        self.session_logger.log("INFO", "UPS CSV selected", {"file": str(path)})

    def on_select_baseline_excel(self) -> None:
        """
        Ask the user to select the baseline Excel file.
        """
        path_str = filedialog.askopenfilename(
            title="Select baseline Excel report",
            filetypes=[("Excel files", "*.xlsx;*.xlsm"), ("All files", "*.*")],
        )
        if not path_str:
            return

        path = Path(path_str)
        self.baseline_path = path
        self._set_status(f"Baseline Excel selected: {path.name}")
        self.audit_logger.info("Baseline Excel selected", extra={"file": str(path)})
        self.session_logger.log("INFO", "Baseline Excel selected", {"file": str(path)})

    def on_run_analysis(self) -> None:
        """
        Run the reconciliation analysis.
        """
        if self.ups_csv_path is None or self.baseline_path is None:
            messagebox.showwarning(
                "Missing files",
                "Please select both UPS CSV and baseline Excel before running analysis.",
            )
            return

        try:
            self._set_status("Loading input files...")
            ups_df, baseline_df = load_inputs(
                ups_csv_path=self.ups_csv_path,
                baseline_excel_path=self.baseline_path,
            )

            self._set_status("Building normalized UPS view...")
            new_norm_df = build_new_norm(ups_df)

            # In this portfolio version, we focus on UPS as source of truth
            # and produce a 'current view' from the UPS data alone.
            # The baseline_df is loaded to show architecture extensibility,
            # but not used heavily here.
            self._set_status("Building final RMA Analysis view...")
            rma_analysis_df = build_final_output_df(new_norm_df, new_norm_df)

            # Non-standard sheet is not fully implemented in this simplified version.
            self.rma_analysis_df = rma_analysis_df
            self.non_standard_df = None

            # Push to viewer
            self.viewer.set_data(
                columns=list(rma_analysis_df.columns),
                rows=rma_analysis_df.itertuples(index=False, name=None),
            )

            self._set_status("Analysis completed.")
            self.btn_save.configure(state="normal")

            self.audit_logger.info(
                "Analysis completed",
                extra={
                    "ups_csv": str(self.ups_csv_path),
                    "baseline": str(self.baseline_path),
                    "rows": len(rma_analysis_df),
                },
            )
            self.session_logger.log(
                "INFO",
                "Analysis completed",
                {
                    "rows": len(rma_analysis_df),
                    "ups_csv": str(self.ups_csv_path),
                    "baseline": str(self.baseline_path),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.audit_logger.exception("Analysis failed")
            self.session_logger.log("ERROR", "Analysis failed", {"error": str(exc)})
            messagebox.showerror("Error", f"Analysis failed:\n\n{exc}")
            self._set_status("Analysis failed.")

    def on_save_to_excel(self) -> None:
        """
        Export the current analysis to an Excel workbook.
        """
        if self.rma_analysis_df is None:
            messagebox.showwarning("Nothing to save", "Run analysis before saving.")
            return

        path_str = filedialog.asksaveasfilename(
            title="Save reconciled report",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
        )
        if not path_str:
            return

        output_path = Path(path_str)

        try:
            self._set_status(f"Saving to Excel: {output_path.name}")
            non_standard_df = self.non_standard_df

            # If we don't have a Non-Standard sheet yet, create an empty one.
            if non_standard_df is None:
                import pandas as pd

                non_standard_df = pd.DataFrame(columns=self.rma_analysis_df.columns)

            save_reconciliation_to_excel(
                reconciled_df=self.rma_analysis_df,
                non_standard_df=non_standard_df,
                output_path=output_path,
            )

            self._set_status("Excel file saved.")
            self.audit_logger.info("Excel file saved", extra={"file": str(output_path)})
            self.session_logger.log(
                "INFO", "Excel file saved", {"file": str(output_path)}
            )
        except Exception as exc:  # noqa: BLE001
            self.audit_logger.exception("Failed to save Excel file")
            self.session_logger.log("ERROR", "Failed to save Excel file", {"error": str(exc)})
            messagebox.showerror("Error", f"Failed to save Excel file:\n\n{exc}")
            self._set_status("Save failed.")

    def _on_search_change(self, event) -> None:
        term = self.search_var.get()
        self.viewer.search(term)

    def on_show_help(self) -> None:
        HelpDialog(self.window, help_text=HELP_TEXT)

    def on_show_kpi_info(self) -> None:
        KPIInfoDialog(self.window, kpi_text=KPI_TEXT)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def run(self) -> None:
        """
        Start the Tkinter mainloop.
        """
        try:
            self.window.mainloop()
        finally:
            # Ensure session log is closed when the app exits.
            self.session_logger.close()


def main() -> None:
    """
    CLI entry point to start the GUI application.
    """
    app = App(theme="dark")
    app.run()


if __name__ == "__main__":
    main()