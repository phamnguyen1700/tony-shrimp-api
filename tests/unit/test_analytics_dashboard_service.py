from decimal import Decimal

from app.services.analytics.dashboard_service import calculate_change_percent


def test_calculate_change_percent_handles_increase_and_decrease() -> None:
    assert calculate_change_percent(Decimal("125"), Decimal("100")) == Decimal("25.00")
    assert calculate_change_percent(Decimal("75"), Decimal("100")) == Decimal("-25.00")


def test_calculate_change_percent_handles_zero_previous_period() -> None:
    assert calculate_change_percent(Decimal("0"), Decimal("0")) == Decimal("0.00")
    assert calculate_change_percent(Decimal("50"), Decimal("0")) is None

