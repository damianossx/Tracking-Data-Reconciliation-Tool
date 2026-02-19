# Architecture Overview

## 1. High-level components

- **GUI (Tkinter + ttkbootstrap)** – `app.py`, `ui_viewer.py`, `ui_theme.py`, `ui_dialogs.py`
- **Core engine** – `core_reconciliation.py`, `excel_reporting.py`, `data_ingestion.py`
- **Integrations**:
  - UPS Quantum View Manage – `qvm_downloader.py` (Selenium)
  - Microsoft Graph API – `graph_client.py` (skeleton)
- **Logging & audit** – `logging_audit.py` (audit logger + SessionLogger)

## 2. Data flow

1. User selects:
   - UPS CSV (source of truth)
   - Baseline Excel (optional historical reference)
2. `data_ingestion.py` loads both into pandas DataFrames.
3. `core_reconciliation.build_new_norm`:
   - harmonizes columns,
   - extracts RMA / Tracking Number,
   - builds normalized view.
4. `core_reconciliation.build_final_output_df`:
   - applies RMA/PR2 logic,
   - prepares final "RMA Analysis" DataFrame.
5. `excel_reporting.save_reconciliation_to_excel`:
   - writes results to Excel (RMA Analysis + Non-Standard RMAs).
6. GUI displays the final DataFrame in `CanvasTable`.

## 3. Error handling & logging

- All high-level actions (file selection, analysis, save) are logged via `logging_audit`.
- Session-level structured logs are written in NDJSON format.