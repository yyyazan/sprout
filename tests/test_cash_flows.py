"""The dashboard's cash_flows feed the Value chart's deposit/withdrawal bars."""
from __future__ import annotations

import pandas as pd

from portfolio.pipeline import _cash_flows


def frame(rows):
    return pd.DataFrame({
        "Date": pd.to_datetime([d for d, _ in rows]),
        "Amount (USD)": [a for _, a in rows],
    })


def test_sorted_signed_and_zero_rows_dropped():
    txn = frame([("2025-03-03", 534.4), ("2024-08-17", 1000.0), ("2025-03-03", -266.678), ("2025-01-01", 0.0)])
    assert _cash_flows(txn) == [
        {"date": "2024-08-17", "amount": 1000.0},
        {"date": "2025-03-03", "amount": 534.4},     # same day keeps entry order
        {"date": "2025-03-03", "amount": -266.68},
    ]


def test_no_transactions_is_an_empty_list():
    assert _cash_flows(frame([])) == []
