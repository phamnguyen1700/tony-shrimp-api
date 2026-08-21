from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.core.config import get_settings

SUPPORTED_ANALYTICS_PERIODS = {"7d": 7, "30d": 30}
DEFAULT_ANALYTICS_PERIOD = "30d"


@dataclass(frozen=True)
class AnalyticsPeriod:
    key: str
    current_from: datetime
    current_to: datetime
    previous_from: datetime
    previous_to: datetime
    timezone: str

    @property
    def stripe_current_from(self) -> int:
        return int(self.current_from.timestamp())

    @property
    def stripe_current_to(self) -> int:
        return int(self.current_to.timestamp())

    @property
    def stripe_previous_from(self) -> int:
        return int(self.previous_from.timestamp())

    @property
    def stripe_previous_to(self) -> int:
        return int(self.previous_to.timestamp())


def get_business_zone() -> ZoneInfo:
    timezone = get_settings().business_timezone
    try:
        return ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(f"Invalid business timezone: {timezone}") from exc


def build_analytics_period(
    period_key: str | None = None,
    *,
    now: datetime | None = None,
) -> AnalyticsPeriod:
    key = period_key or DEFAULT_ANALYTICS_PERIOD
    if key not in SUPPORTED_ANALYTICS_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported analytics period.",
        )

    zone = get_business_zone()
    days = SUPPORTED_ANALYTICS_PERIODS[key]
    local_now = (now or datetime.now(UTC)).astimezone(zone)
    current_to_local = datetime.combine(
        local_now.date() + timedelta(days=1),
        time.min,
        tzinfo=zone,
    )
    current_from_local = current_to_local - timedelta(days=days)
    previous_to_local = current_from_local
    previous_from_local = previous_to_local - timedelta(days=days)

    return AnalyticsPeriod(
        key=key,
        current_from=current_from_local.astimezone(UTC),
        current_to=current_to_local.astimezone(UTC),
        previous_from=previous_from_local.astimezone(UTC),
        previous_to=previous_to_local.astimezone(UTC),
        timezone=str(zone),
    )


def iter_local_dates(start_utc: datetime, end_utc: datetime) -> list[str]:
    zone = get_business_zone()
    start_date = start_utc.astimezone(zone).date()
    end_date = (end_utc - timedelta(microseconds=1)).astimezone(zone).date()

    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates

