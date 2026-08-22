from types import SimpleNamespace

import pytest
from google.api_core.exceptions import InvalidArgument

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
