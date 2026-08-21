import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunRealtimeReportRequest,
    RunReportRequest,
)
from google.api_core.exceptions import GoogleAPIError
from google.oauth2 import service_account
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.analytics import get_order_analytics_totals
from app.schemas.analytics import (
    AnalyticsEcommerceFunnelResponse,
    AnalyticsPeriodResponse,
    AnalyticsRealtimeResponse,
    AnalyticsTopActivePageResponse,
    AnalyticsTopPageResponse,
    AnalyticsTrafficResponse,
    AnalyticsTrafficSeriesPointResponse,
    AnalyticsTrafficSourceResponse,
    AnalyticsTrafficSummaryResponse,
)
from app.services.analytics.dashboard_service import calculate_change_percent
from app.services.analytics.period import (
    AnalyticsPeriod,
    build_analytics_period,
    get_business_zone,
    iter_local_dates,
)

settings = get_settings()

GA_SCOPES = ("https://www.googleapis.com/auth/analytics.readonly",)
GA_PROPERTY_PREFIX = "properties/"


class GoogleAnalyticsUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrafficTotals:
    users: int
    sessions: int
    page_views: int
    engagement_rate: Decimal
    bounce_rate: Decimal


def parse_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def parse_rate(value: str | None) -> Decimal:
    try:
        rate = Decimal(str(value or "0")) * Decimal("100")
    except Exception:
        rate = Decimal("0")
    return rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_percent(part: int, total: int) -> Decimal:
    if total <= 0:
        return Decimal("0.00")
    return (Decimal(part) / Decimal(total) * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def calculate_conversion_rate(orders: int, visitors: int) -> Decimal | None:
    if visitors <= 0:
        return None
    return (Decimal(orders) / Decimal(visitors) * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def ensure_google_analytics_configured() -> None:
    if not settings.ga_property_id or not settings.google_service_account_json:
        raise GoogleAnalyticsUnavailableError("Google Analytics is not configured.")


def get_ga_property_name() -> str:
    property_id = settings.ga_property_id.strip()
    if property_id.startswith(GA_PROPERTY_PREFIX):
        return property_id
    return f"{GA_PROPERTY_PREFIX}{property_id}"


def create_google_analytics_client() -> BetaAnalyticsDataClient:
    ensure_google_analytics_configured()
    try:
        service_account_info = json.loads(settings.google_service_account_json)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=GA_SCOPES,
        )
    except Exception as exc:
        raise GoogleAnalyticsUnavailableError(
            "Google Analytics credentials are invalid."
        ) from exc

    return BetaAnalyticsDataClient(credentials=credentials)


def get_metric(row: Any, index: int) -> str:
    values = getattr(row, "metric_values", []) or []
    if index >= len(values):
        return "0"
    return str(getattr(values[index], "value", "0"))


def get_dimension(row: Any, index: int) -> str:
    values = getattr(row, "dimension_values", []) or []
    if index >= len(values):
        return ""
    return str(getattr(values[index], "value", ""))


def normalize_ga_date(value: str) -> str:
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value


def get_ga_date_range(period: AnalyticsPeriod, *, previous: bool = False) -> tuple[str, str]:
    zone = get_business_zone()
    if previous:
        start_local = period.previous_from.astimezone(zone).date()
        end_local = period.previous_to.astimezone(zone).date()
    else:
        start_local = period.current_from.astimezone(zone).date()
        end_local = period.current_to.astimezone(zone).date()

    return start_local.isoformat(), (end_local).isoformat()


def run_report(
    client: BetaAnalyticsDataClient,
    *,
    period: AnalyticsPeriod,
    dimensions: list[str],
    metrics: list[str],
    start_at_previous_period: bool = False,
    limit: int | None = None,
    order_bys: list[OrderBy] | None = None,
) -> Any:
    start_date, exclusive_end_date = get_ga_date_range(
        period,
        previous=start_at_previous_period,
    )
    end_date = (date.fromisoformat(exclusive_end_date) - timedelta(days=1)).isoformat()

    request = RunReportRequest(
        property=get_ga_property_name(),
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[Dimension(name=name) for name in dimensions],
        metrics=[Metric(name=name) for name in metrics],
        limit=limit or 10000,
        order_bys=order_bys or [],
    )
    return client.run_report(request)


def get_traffic_totals(
    client: BetaAnalyticsDataClient,
    *,
    period: AnalyticsPeriod,
    previous: bool = False,
) -> TrafficTotals:
    response = run_report(
        client,
        period=period,
        dimensions=[],
        metrics=[
            "totalUsers",
            "sessions",
            "screenPageViews",
            "engagementRate",
            "bounceRate",
        ],
        start_at_previous_period=previous,
        limit=1,
    )
    rows = list(getattr(response, "rows", []) or [])
    if not rows:
        return TrafficTotals(0, 0, 0, Decimal("0.00"), Decimal("0.00"))

    row = rows[0]
    return TrafficTotals(
        users=parse_int(get_metric(row, 0)),
        sessions=parse_int(get_metric(row, 1)),
        page_views=parse_int(get_metric(row, 2)),
        engagement_rate=parse_rate(get_metric(row, 3)),
        bounce_rate=parse_rate(get_metric(row, 4)),
    )


def get_traffic_series(
    client: BetaAnalyticsDataClient,
    *,
    period: AnalyticsPeriod,
) -> list[AnalyticsTrafficSeriesPointResponse]:
    response = run_report(
        client,
        period=period,
        dimensions=["date"],
        metrics=["totalUsers", "sessions", "screenPageViews"],
        order_bys=[
            OrderBy(
                dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
            )
        ],
    )
    by_date = {
        date: {"users": 0, "sessions": 0, "page_views": 0}
        for date in iter_local_dates(period.current_from, period.current_to)
    }

    for row in getattr(response, "rows", []) or []:
        date = normalize_ga_date(get_dimension(row, 0))
        if date not in by_date:
            continue
        by_date[date] = {
            "users": parse_int(get_metric(row, 0)),
            "sessions": parse_int(get_metric(row, 1)),
            "page_views": parse_int(get_metric(row, 2)),
        }

    return [
        AnalyticsTrafficSeriesPointResponse(
            date=date,
            users=values["users"],
            sessions=values["sessions"],
            page_views=values["page_views"],
        )
        for date, values in by_date.items()
    ]


def get_traffic_sources(
    client: BetaAnalyticsDataClient,
    *,
    period: AnalyticsPeriod,
    total_users: int,
    limit: int = 6,
) -> list[AnalyticsTrafficSourceResponse]:
    response = run_report(
        client,
        period=period,
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["totalUsers", "sessions"],
        limit=limit,
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="totalUsers"),
                desc=True,
            )
        ],
    )

    return [
        AnalyticsTrafficSourceResponse(
            channel=get_dimension(row, 0) or "Unassigned",
            users=parse_int(get_metric(row, 0)),
            sessions=parse_int(get_metric(row, 1)),
            percent=calculate_percent(parse_int(get_metric(row, 0)), total_users),
        )
        for row in getattr(response, "rows", []) or []
    ]


def get_top_pages(
    client: BetaAnalyticsDataClient,
    *,
    period: AnalyticsPeriod,
    limit: int = 6,
) -> list[AnalyticsTopPageResponse]:
    response = run_report(
        client,
        period=period,
        dimensions=["unifiedPagePathScreen"],
        metrics=["screenPageViews", "totalUsers"],
        limit=limit,
        order_bys=[
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                desc=True,
            )
        ],
    )

    return [
        AnalyticsTopPageResponse(
            path=get_dimension(row, 0) or "/",
            views=parse_int(get_metric(row, 0)),
            users=parse_int(get_metric(row, 1)),
        )
        for row in getattr(response, "rows", []) or []
    ]


def get_realtime_analytics(
    *,
    client: BetaAnalyticsDataClient | None = None,
) -> AnalyticsRealtimeResponse:
    ensure_google_analytics_configured()
    ga_client = client or create_google_analytics_client()

    try:
        active_response = ga_client.run_realtime_report(
            RunRealtimeReportRequest(
                property=get_ga_property_name(),
                metrics=[Metric(name="activeUsers")],
            )
        )
        top_pages_response = ga_client.run_realtime_report(
            RunRealtimeReportRequest(
                property=get_ga_property_name(),
                dimensions=[Dimension(name="unifiedPagePathScreen")],
                metrics=[Metric(name="activeUsers")],
                limit=10,
                order_bys=[
                    OrderBy(
                        metric=OrderBy.MetricOrderBy(metric_name="activeUsers"),
                        desc=True,
                    )
                ],
            )
        )
    except GoogleAPIError as exc:
        raise GoogleAnalyticsUnavailableError(str(exc)) from exc

    active_rows = list(getattr(active_response, "rows", []) or [])
    active_users = parse_int(get_metric(active_rows[0], 0)) if active_rows else 0

    return AnalyticsRealtimeResponse(
        active_users=active_users,
        top_active_pages=[
            AnalyticsTopActivePageResponse(
                path=get_dimension(row, 0) or "/",
                active_users=parse_int(get_metric(row, 0)),
            )
            for row in getattr(top_pages_response, "rows", []) or []
        ],
    )


async def get_traffic_analytics(
    db: AsyncSession,
    *,
    period_key: str | None = None,
    client: BetaAnalyticsDataClient | None = None,
) -> AnalyticsTrafficResponse:
    ensure_google_analytics_configured()
    period = build_analytics_period(period_key)
    ga_client = client or create_google_analytics_client()
    currency = settings.order_currency.upper()

    try:
        current = get_traffic_totals(ga_client, period=period)
        previous = get_traffic_totals(ga_client, period=period, previous=True)
        series = get_traffic_series(ga_client, period=period)
        sources = get_traffic_sources(
            ga_client,
            period=period,
            total_users=current.users,
        )
        top_pages = get_top_pages(ga_client, period=period)
    except GoogleAPIError as exc:
        raise GoogleAnalyticsUnavailableError(str(exc)) from exc

    current_orders = await get_order_analytics_totals(
        db,
        start_at=period.current_from,
        end_at=period.current_to,
        currency=currency,
    )

    return AnalyticsTrafficResponse(
        period=AnalyticsPeriodResponse(
            key=period.key,
            from_=period.current_from,
            to=period.current_to,
            timezone=period.timezone,
        ),
        summary=AnalyticsTrafficSummaryResponse(
            users=current.users,
            users_change_percent=calculate_change_percent(
                Decimal(current.users),
                Decimal(previous.users),
            ),
            sessions=current.sessions,
            sessions_change_percent=calculate_change_percent(
                Decimal(current.sessions),
                Decimal(previous.sessions),
            ),
            page_views=current.page_views,
            page_views_change_percent=calculate_change_percent(
                Decimal(current.page_views),
                Decimal(previous.page_views),
            ),
            engagement_rate=current.engagement_rate,
            engagement_rate_change_percent=calculate_change_percent(
                current.engagement_rate,
                previous.engagement_rate,
            ),
            bounce_rate=current.bounce_rate,
        ),
        series=series,
        sources=sources,
        top_pages=top_pages,
        ecommerce_funnel=AnalyticsEcommerceFunnelResponse(
            visitors=current.users,
            completed_orders=current_orders.count,
            conversion_rate=calculate_conversion_rate(
                current_orders.count,
                current.users,
            ),
        ),
    )
