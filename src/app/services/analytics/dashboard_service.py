from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.analytics import (
    get_order_analytics_totals,
    get_top_product_analytics,
)
from app.schemas.analytics import (
    AnalyticsAverageOrderValueResponse,
    AnalyticsBalanceResponse,
    AnalyticsDashboardResponse,
    AnalyticsDisputesResponse,
    AnalyticsPayoutListResponse,
    AnalyticsPayoutResponse,
    AnalyticsPaymentsResponse,
    AnalyticsPeriodResponse,
    AnalyticsRevenuePointResponse,
    AnalyticsSummaryResponse,
    AnalyticsTopProductResponse,
)
from app.services.analytics.period import build_analytics_period
from app.services.analytics.stripe_analytics_service import (
    StripeAnalyticsUnavailableError,
    get_payouts,
    get_stripe_dashboard_analytics,
)

settings = get_settings()


def quantize_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_change_percent(current: Decimal, previous: Decimal) -> Decimal | None:
    current_value = Decimal(current)
    previous_value = Decimal(previous)
    if previous_value == 0:
        return None if current_value != 0 else Decimal("0.00")

    return ((current_value - previous_value) / previous_value * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


async def get_owner_analytics_dashboard(
    db: AsyncSession,
    *,
    period_key: str | None = None,
) -> AnalyticsDashboardResponse:
    period = build_analytics_period(period_key)
    currency = settings.order_currency.upper()

    current_orders = await get_order_analytics_totals(
        db,
        start_at=period.current_from,
        end_at=period.current_to,
        currency=currency,
    )
    previous_orders = await get_order_analytics_totals(
        db,
        start_at=period.previous_from,
        end_at=period.previous_to,
        currency=currency,
    )
    top_products = await get_top_product_analytics(
        db,
        start_at=period.current_from,
        end_at=period.current_to,
        currency=currency,
        limit=5,
    )

    try:
        stripe_analytics = get_stripe_dashboard_analytics(period, currency=currency)
    except StripeAnalyticsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe analytics is unavailable.",
        ) from exc

    average_order_value = (
        current_orders.revenue / Decimal(current_orders.count)
        if current_orders.count
        else Decimal("0.00")
    )

    return AnalyticsDashboardResponse(
        period=AnalyticsPeriodResponse(
            key=period.key,
            from_=period.current_from,
            to=period.current_to,
            timezone=period.timezone,
        ),
        summary=AnalyticsSummaryResponse(
            gross_revenue=quantize_money(stripe_analytics.current_revenue.gross),
            gross_revenue_change_percent=calculate_change_percent(
                stripe_analytics.current_revenue.gross,
                stripe_analytics.previous_revenue.gross,
            ),
            orders=current_orders.count,
            orders_change_percent=calculate_change_percent(
                Decimal(current_orders.count),
                Decimal(previous_orders.count),
            ),
            currency=currency,
        ),
        payments=AnalyticsPaymentsResponse(
            successful_count=stripe_analytics.payments.successful,
            failed_count=stripe_analytics.payments.failed,
            attempts=stripe_analytics.payments.attempts,
            success_rate=stripe_analytics.payments.success_rate,
            refund_amount=quantize_money(stripe_analytics.refunds.amount),
            refund_count=stripe_analytics.refunds.count,
            stripe_fees=quantize_money(stripe_analytics.current_revenue.fees),
            net_revenue=quantize_money(stripe_analytics.current_revenue.net),
            currency=currency,
        ),
        balance=AnalyticsBalanceResponse(
            available=quantize_money(stripe_analytics.balance.available),
            pending=quantize_money(stripe_analytics.balance.pending),
            currency=currency,
        ),
        average_order_value=AnalyticsAverageOrderValueResponse(
            amount=quantize_money(average_order_value),
            currency=currency,
        ),
        revenue_series=[
            AnalyticsRevenuePointResponse(
                date=point.date,
                gross=quantize_money(point.gross),
                fees=quantize_money(point.fees),
                net=quantize_money(point.net),
            )
            for point in stripe_analytics.revenue_series
        ],
        top_products=[
            AnalyticsTopProductResponse(
                name=product.name,
                quantity=product.quantity,
                revenue=quantize_money(product.revenue),
            )
            for product in top_products
        ],
        disputes=AnalyticsDisputesResponse(
            open_count=stripe_analytics.disputes.open_count,
            amount_at_risk=quantize_money(stripe_analytics.disputes.amount_at_risk),
            currency=currency,
        ),
    )


async def get_owner_analytics_payouts(
    *,
    limit: int = 10,
) -> AnalyticsPayoutListResponse:
    currency = settings.order_currency.upper()
    try:
        payouts = get_payouts(currency=currency, limit=limit)
    except StripeAnalyticsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe payouts are unavailable.",
        ) from exc

    return AnalyticsPayoutListResponse(
        payouts=[
            AnalyticsPayoutResponse(
                amount=quantize_money(payout.amount),
                currency=payout.currency,
                status=payout.status,
                created=payout.created,
                arrival_date=payout.arrival_date,
            )
            for payout in payouts
        ]
    )

