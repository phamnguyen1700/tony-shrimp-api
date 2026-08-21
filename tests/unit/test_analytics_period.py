from datetime import UTC, datetime

from app.services.analytics.period import build_analytics_period, iter_local_dates


def test_build_analytics_period_uses_business_local_days() -> None:
    period = build_analytics_period(
        "30d",
        now=datetime(2026, 8, 21, 4, 30, tzinfo=UTC),
    )

    assert period.key == "30d"
    assert period.timezone == "Australia/Sydney"
    assert period.current_from.isoformat() == "2026-07-22T14:00:00+00:00"
    assert period.current_to.isoformat() == "2026-08-21T14:00:00+00:00"
    assert period.previous_from.isoformat() == "2026-06-22T14:00:00+00:00"
    assert period.previous_to.isoformat() == "2026-07-22T14:00:00+00:00"


def test_iter_local_dates_returns_continuous_dates() -> None:
    period = build_analytics_period(
        "7d",
        now=datetime(2026, 8, 21, 4, 30, tzinfo=UTC),
    )

    assert iter_local_dates(period.current_from, period.current_to) == [
        "2026-08-15",
        "2026-08-16",
        "2026-08-17",
        "2026-08-18",
        "2026-08-19",
        "2026-08-20",
        "2026-08-21",
    ]

