# src/ups_rma_reconciliation/config.py

"""
Global configuration and business constants for the UPS RMA Reconciliation project.

This module holds:
- sheet names,
- colors for alerts,
- business thresholds (manual baseline, weekly overhead),
- column definitions and regex patterns.

Having these in a dedicated module:
- avoids hardcoding values across the codebase,
- makes business rules explicit,
- simplifies future tuning of thresholds or naming conventions.
"""

from dataclasses import dataclass
import re

# Sheet names in the Excel output
DEST_SHEET_FINAL = "RMA Analysis"
SHEET_NAME_NON_STANDARD = "Non-Standard RMAs"

# Hex colors (ARGB) for Excel rich-text highlights
COLOR_BLACK = "FF000000"
COLOR_RED = "FFB91C1C"    # Exception / N/A
COLOR_ORANGE = "FFD97706"  # In Transit / Manifest aging (>5 days)

# Text suffix appended to alert lines in Tracking Number - Details
ALERT_SUFFIX = " (⚠️action to be taken)"

# Baseline manual effort assumptions (for KPI calculations)
B_MANUAL_MIN_DEFAULT = 8.0   # minutes per RMA in manual reconciliation
WEEKLY_OVERHEAD_MIN = 2.0    # overhead minutes per weekly run

# UPS tracking number: 1Z + 16 alphanumeric chars
UPS_TN_REGEX = re.compile(r"\b1Z[0-9A-Z]{16}\b", re.IGNORECASE)

# RMA rules:
# - valid RMAs are exactly 8 digits
# - prefer those starting with '6'
RMA_STRICT_RX = re.compile(r"^\d{8}$")
RMA_PREF6_RX = re.compile(r"^6\d{7}$")
RMA_ANY8_IN_TEXT_RX = re.compile(r"(?<!\d)\d{8}(?!\d)")

# Unified output columns for the main "RMA Analysis" view
FINAL_COLS = [
    "Manifest Date",
    "RMA Number",
    "Tracking Number - Details",
    "Status",
    "Shipper Name",
    "Ship To",
    "Scheduled Delivery",
    "Date Delivered",
    "Exception Description",
    "Exception Resolution",
    "Weight",
]

# OUT_COLS = core columns used in baseline preservation logic
OUT_COLS = [
    "Manifest Date",
    "RMA Number",
    "Tracking Number - Details",
    "Status",
    "Shipper Name",
    "Ship To",
    "Scheduled Delivery",
    "Date Delivered",
    "Exception Description",
    "Exception Resolution",
    "Ship To Location",
    "Weight",
    "Tracking Number",
]


@dataclass
class AlertThresholds:
    """
    Threshold configuration for alert aging (in days).
    """

    in_transit_days_threshold: int = 5
    manifest_days_threshold: int = 5


ALERT_THRESHOLDS = AlertThresholds()