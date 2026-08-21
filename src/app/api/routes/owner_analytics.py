from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, require_roles
from app.models.auth import User
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsPayoutListResponse
from app.services.analytics import (
    get_owner_analytics_dashboard,
    get_owner_analytics_payouts,
)

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

