from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsPeriodResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    from_: datetime = Field(alias="from")
    to: datetime
    timezone: str


class AnalyticsSummaryResponse(BaseModel):
    gross_revenue: Decimal
    gross_revenue_change_percent: Decimal | None
    orders: int
    orders_change_percent: Decimal | None
    currency: str


class AnalyticsPaymentsResponse(BaseModel):
    successful_count: int
    failed_count: int
    attempts: int
    success_rate: Decimal
    refund_amount: Decimal
    refund_count: int
    stripe_fees: Decimal
    net_revenue: Decimal
    currency: str


class AnalyticsBalanceResponse(BaseModel):
    available: Decimal
    pending: Decimal
    currency: str


class AnalyticsAverageOrderValueResponse(BaseModel):
    amount: Decimal
    currency: str


class AnalyticsRevenuePointResponse(BaseModel):
    date: str
    gross: Decimal
    fees: Decimal
    net: Decimal


class AnalyticsTopProductResponse(BaseModel):
    name: str
    quantity: int
    revenue: Decimal


class AnalyticsDisputesResponse(BaseModel):
    open_count: int
    amount_at_risk: Decimal
    currency: str


class AnalyticsDashboardResponse(BaseModel):
    period: AnalyticsPeriodResponse
    summary: AnalyticsSummaryResponse
    payments: AnalyticsPaymentsResponse
    balance: AnalyticsBalanceResponse
    average_order_value: AnalyticsAverageOrderValueResponse
    revenue_series: list[AnalyticsRevenuePointResponse]
    top_products: list[AnalyticsTopProductResponse]
    disputes: AnalyticsDisputesResponse


class AnalyticsPayoutResponse(BaseModel):
    amount: Decimal
    currency: str
    status: str
    created: datetime
    arrival_date: datetime | None


class AnalyticsPayoutListResponse(BaseModel):
    payouts: list[AnalyticsPayoutResponse]


class AnalyticsTopActivePageResponse(BaseModel):
    path: str
    active_users: int


class AnalyticsRealtimeResponse(BaseModel):
    active_users: int
    top_active_pages: list[AnalyticsTopActivePageResponse]


class AnalyticsTrafficSummaryResponse(BaseModel):
    users: int
    users_change_percent: Decimal | None
    sessions: int
    sessions_change_percent: Decimal | None
    page_views: int
    page_views_change_percent: Decimal | None
    engagement_rate: Decimal
    engagement_rate_change_percent: Decimal | None
    bounce_rate: Decimal


class AnalyticsTrafficSeriesPointResponse(BaseModel):
    date: str
    users: int
    sessions: int
    page_views: int


class AnalyticsTrafficSourceResponse(BaseModel):
    channel: str
    users: int
    sessions: int
    percent: Decimal


class AnalyticsTopPageResponse(BaseModel):
    path: str
    views: int
    users: int


class AnalyticsEcommerceFunnelResponse(BaseModel):
    visitors: int
    completed_orders: int
    conversion_rate: Decimal | None


class AnalyticsTrafficResponse(BaseModel):
    period: AnalyticsPeriodResponse
    summary: AnalyticsTrafficSummaryResponse
    series: list[AnalyticsTrafficSeriesPointResponse]
    sources: list[AnalyticsTrafficSourceResponse]
    top_pages: list[AnalyticsTopPageResponse]
    ecommerce_funnel: AnalyticsEcommerceFunnelResponse
