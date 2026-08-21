import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import InvalidArgument

from app.repositories.analytics import OrderAnalyticsTotals
from app.services.analytics import google_analytics_service


def metric(value: object) -> SimpleNamespace:
    return SimpleNamespace(value=str(value))


def dimension(value: object) -> SimpleNamespace:
    return SimpleNamespace(value=str(value))


def row(
    dimensions: list[object] | None = None,
    metrics: list[object] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        dimension_values=[dimension(value) for value in dimensions or []],
        metric_values=[metric(value) for value in metrics or []],
    )


def response(rows: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(rows=rows)


def configure_ga(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google_analytics_service.settings, "ga_property_id", "123456789")
    monkeypatch.setattr(
        google_analytics_service.settings,
        "google_service_account_json",
        '{"type":"service_account"}',
    )


class FakeRealtimeClient:
    def __init__(self) -> None:
        self.calls = 0

    def run_realtime_report(self, _request):
        self.calls += 1
        if self.calls == 1:
            return response([row(metrics=[421])])

        return response(
            [
                row(dimensions=["/aquarium-shrimp"], metrics=[184]),
                row(dimensions=["/cart"], metrics=[41]),
            ]
        )


class FakeRealtimeTopPagesErrorClient:
    def __init__(self) -> None:
        self.calls = 0

    def run_realtime_report(self, _request):
        self.calls += 1
        if self.calls == 1:
            return response([row(metrics=[12])])

        raise InvalidArgument("Unsupported realtime dimension.")


class FakeTrafficClient:
    def run_report(self, request):
        dimensions = tuple(dimension.name for dimension in request.dimensions)

        if dimensions == ():
            start_date = request.date_ranges[0].start_date
            if start_date == "2026-08-15":
                return response([row(metrics=[100, 20, 50, "0.75", "0.25"])])
            return response([row(metrics=[50, 10, 25, "0.50", "0.50"])])

        if dimensions == ("date",):
            return response(
                [
                    row(dimensions=["20260815"], metrics=[10, 2, 5]),
                    row(dimensions=["20260816"], metrics=[20, 4, 10]),
                ]
            )

        if dimensions == ("sessionDefaultChannelGroup",):
            return response(
                [
                    row(dimensions=["Direct"], metrics=[60, 12]),
                    row(dimensions=["Organic Search"], metrics=[40, 8]),
                ]
            )

        if dimensions == ("unifiedPagePathScreen",):
            return response(
                [
                    row(dimensions=["/aquarium-shrimp"], metrics=[30, 20]),
                    row(dimensions=["/cart"], metrics=[10, 5]),
                ]
            )

        return response([])


def test_realtime_analytics_returns_active_users_and_top_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_ga(monkeypatch)

    result = google_analytics_service.get_realtime_analytics(
        client=FakeRealtimeClient()
    )

    assert result.active_users == 421
    assert result.top_active_pages[0].path == "/aquarium-shrimp"
    assert result.top_active_pages[0].active_users == 184


def test_realtime_analytics_keeps_active_users_when_top_pages_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_ga(monkeypatch)

    result = google_analytics_service.get_realtime_analytics(
        client=FakeRealtimeTopPagesErrorClient()
    )

    assert result.active_users == 12
    assert result.top_active_pages == []


def test_traffic_analytics_returns_summary_sources_pages_and_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_ga(monkeypatch)

    async def fake_order_totals(*args, **kwargs):
        return OrderAnalyticsTotals(count=5, revenue=Decimal("500.00"))

    monkeypatch.setattr(
        google_analytics_service,
        "get_order_analytics_totals",
        fake_order_totals,
    )

    result = asyncio.run(
        google_analytics_service.get_traffic_analytics(
            SimpleNamespace(),
            period_key="7d",
            client=FakeTrafficClient(),
        )
    )

    assert result.summary.users == 100
    assert result.summary.users_change_percent == Decimal("100.00")
    assert result.summary.engagement_rate == Decimal("75.00")
    assert result.summary.engagement_rate_change_percent == Decimal("50.00")
    assert result.series[0].date == "2026-08-15"
    assert result.sources[0].channel == "Direct"
    assert result.sources[0].percent == Decimal("60.00")
    assert result.top_pages[0].path == "/aquarium-shrimp"
    assert result.ecommerce_funnel.visitors == 100
    assert result.ecommerce_funnel.completed_orders == 5
    assert result.ecommerce_funnel.conversion_rate == Decimal("5.00")


def test_missing_google_analytics_config_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(google_analytics_service.settings, "ga_property_id", "")
    monkeypatch.setattr(
        google_analytics_service.settings,
        "google_service_account_json",
        "",
    )

    with pytest.raises(google_analytics_service.GoogleAnalyticsUnavailableError):
        google_analytics_service.get_realtime_analytics(client=FakeRealtimeClient())
