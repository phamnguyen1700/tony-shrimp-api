from datetime import UTC, datetime
from decimal import Decimal

from app.services.analytics.period import build_analytics_period
from app.services.analytics.stripe_analytics_service import (
    aggregate_revenue_from_balance_transactions,
    aggregate_revenue_series,
    paginate_stripe_list,
)


def test_aggregate_revenue_uses_balance_transaction_amount_fee_and_net() -> None:
    transactions = [
        {
            "id": "txn_charge",
            "type": "charge",
            "reporting_category": "charge",
            "amount": 10000,
            "fee": 320,
            "net": 9680,
            "currency": "aud",
        },
        {
            "id": "txn_refund",
            "type": "refund",
            "reporting_category": "refund",
            "amount": -2500,
            "fee": 0,
            "net": -2500,
            "currency": "aud",
        },
        {
            "id": "txn_usd",
            "type": "charge",
            "reporting_category": "charge",
            "amount": 5000,
            "fee": 200,
            "net": 4800,
            "currency": "usd",
        },
    ]

    result = aggregate_revenue_from_balance_transactions(transactions, currency="AUD")

    assert result.gross == Decimal("100.00")
    assert result.fees == Decimal("3.20")
    assert result.net == Decimal("71.80")
    assert result.currency == "AUD"


def test_aggregate_revenue_series_groups_by_business_local_date() -> None:
    period = build_analytics_period(
        "7d",
        now=datetime(2026, 8, 21, 4, 30, tzinfo=UTC),
    )
    transactions = [
        {
            "id": "txn_late_utc",
            "type": "charge",
            "reporting_category": "charge",
            "amount": 10000,
            "fee": 300,
            "net": 9700,
            "currency": "aud",
            "created": int(datetime(2026, 8, 20, 16, 0, tzinfo=UTC).timestamp()),
        }
    ]

    result = aggregate_revenue_series(transactions, period=period, currency="AUD")

    assert len(result) == 7
    assert result[-1].date == "2026-08-21"
    assert result[-1].gross == Decimal("100.00")
    assert result[-1].fees == Decimal("3.00")
    assert result[-1].net == Decimal("97.00")


def test_paginate_stripe_list_uses_starting_after() -> None:
    calls = []

    def fake_list(**params):
        calls.append(params)
        if len(calls) == 1:
            return {
                "data": [{"id": "txn_1"}, {"id": "txn_2"}],
                "has_more": True,
            }
        return {
            "data": [{"id": "txn_3"}],
            "has_more": False,
        }

    assert list(paginate_stripe_list(fake_list, limit=100)) == [
        {"id": "txn_1"},
        {"id": "txn_2"},
        {"id": "txn_3"},
    ]
    assert calls[1]["starting_after"] == "txn_2"

