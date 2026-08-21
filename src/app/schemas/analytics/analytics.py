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
