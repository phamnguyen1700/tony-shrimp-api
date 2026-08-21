from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.models.auth import User
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    AnalyticsPayoutListResponse,
    AnalyticsRealtimeResponse,
    AnalyticsTrafficResponse,
)
from app.services.analytics import (
    get_owner_analytics_dashboard,
    get_owner_analytics_payouts,
    get_realtime_analytics,
    get_traffic_analytics,
)
from app.services.analytics.google_analytics_service import GoogleAnalyticsUnavailableError

router = APIRouter(prefix="/owner/analytics", tags=["analytics - owner"])


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_owner_dashboard_analytics(
    period: str = Query(default="30d"),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles("owner", "admin")),
) -> AnalyticsDashboardResponse:
    return await get_owner_analytics_dashboard(db, period_key=period)


@router.get("/payouts", response_model=AnalyticsPayoutListResponse)
async def list_owner_analytics_payouts(
    limit: int = Query(default=10, ge=1, le=100),
    _: User = Depends(require_roles("owner", "admin")),
) -> AnalyticsPayoutListResponse:
    return await get_owner_analytics_payouts(limit=limit)


@router.get("/realtime", response_model=AnalyticsRealtimeResponse)
async def get_owner_realtime_analytics(
    _: User = Depends(require_roles("owner", "admin")),
) -> AnalyticsRealtimeResponse:
    try:
        return get_realtime_analytics()
    except GoogleAnalyticsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Analytics realtime data is unavailable.",
        ) from exc


@router.get("/traffic", response_model=AnalyticsTrafficResponse)
async def get_owner_traffic_analytics(
    period: str = Query(default="30d"),
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles("owner", "admin")),
) -> AnalyticsTrafficResponse:
    try:
        return await get_traffic_analytics(db, period_key=period)
    except GoogleAnalyticsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Analytics traffic data is unavailable.",
        ) from exc
