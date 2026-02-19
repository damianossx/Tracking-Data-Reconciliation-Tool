# tests/test_core_reconciliation.py

import pandas as pd

from ups_rma_reconciliation.core_reconciliation import build_new_norm


def test_build_new_norm_extracts_rma_and_tracking_number():
    # Arrange: simplified UPS CSV excerpt
    data = [
        {
            "Manifest Date": "2024-01-10",
            "RMA Number": "RMA 67024814",
            "Tracking Number": "1Z1234567890123456",
            "Status": "In Transit",
            "Shipper Name": "Rockwell Automation",
            "Ship To": "Customer XYZ",
            "Scheduled Delivery": "2024-01-15",
            "Date Delivered": "",
            "Exception Description": "",
            "Exception Resolution": "",
            "Ship To Location": "PL",
            "Weight": "1.5",
            "Package Reference No. 2": "",
        }
    ]
    ups_df = pd.DataFrame(data)

    # Act
    new_norm = build_new_norm(ups_df)

    # Assert
    assert len(new_norm) == 1
    row = new_norm.iloc[0]
    # 8-digit RMA extracted
    assert row["RMA Number"] == "67024814"
    # TN normalized to upper case
    assert row["Tracking Number"] == "1Z1234567890123456"