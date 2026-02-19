# UPS RMA Tracking Data Reconciliation Tool

End-to-end Python application to **automate, reconcile, and analyse UPS shipment data**  
with a focus on **RMA tracking, exception management, and auditable, repeatable reporting**.

---

## 1. Business Problem & Goal

Manual reconciliation of UPS tracking data (CSV exports from **Quantum View Manage**) against
Excel-based RMA reports is:

- time-consuming and error-prone,
- hard to audit and reproduce,
- inconsistent in how it flags delayed shipments and non-standard RMAs.

**Goal of this tool**

> Provide a **repeatable, auditable, GUI-driven reconciliation pipeline** where:
>
> - UPS CSV is the *source of truth*,
> - baselines are preserved and extendable,
> - all lines remain visible (no hidden rows),
> - exception and delay cases are highlighted,
> - output is delivered as a clean Excel report.

---

## 2. Features

### 2.1. UPS data ingestion

- Reads UPS **CSV reports** exported from Quantum View Manage.
- Harmonizes column names across header variations.
- Treats the CSV as the **authoritative source** for tracking data.

### 2.2. RMA normalization & reconciliation (core engine)

- Extracts **8-digit RMA numbers** from multiple columns using regex:
  - prefers numbers starting with `6`, then `7`, then others.
- Builds a normalized view with:
  - one row per **RMA + Tracking Number**,
  - full shipment context (status, dates, shipper, ship-to, exceptions).
- Separates:
  - **Standard RMAs** (valid 8-digit numbers),
  - **Non-Standard RMAs** (no valid 8-digit RMA, extra digits, fallback to PR2, etc.).
- Can be extended to implement full baseline preservation:
  - never overwriting the original file,
  - keeping additive history.

### 2.3. Alerts and “Tracking Number - Details” lines

- Generates human-readable “TN detail lines” in the format:

  ```text
  1ZXXXXXXXXXXXXXXX - In Transit, 2024-01-05 → CUSTOMER (optional exception text)