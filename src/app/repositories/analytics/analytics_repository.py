from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, PaymentStatus


VALID_ANALYTICS_PAYMENT_STATUSES = (
    PaymentStatus.PAID.value,
    PaymentStatus.REFUNDED.value,
)


@dataclass(frozen=True)
class OrderAnalyticsTotals:
    count: int
    revenue: Decimal


@dataclass(frozen=True)
class TopProductAnalytics:
    name: str
    quantity: int
    revenue: Decimal


def valid_order_filters(
    *,
    start_at: datetime,
    end_at: datetime,
    currency: str,
) -> list[object]:
    return [
        Order.payment_status.in_(VALID_ANALYTICS_PAYMENT_STATUSES),
        Order.paid_at.is_not(None),
        Order.paid_at >= start_at,
        Order.paid_at < end_at,
        func.upper(Order.currency) == currency.upper(),
    ]


async def get_order_analytics_totals(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    currency: str,
) -> OrderAnalyticsTotals:
    result = await db.execute(
        select(
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount), Decimal("0.00")),
        ).where(
            *valid_order_filters(
                start_at=start_at,
                end_at=end_at,
                currency=currency,
            )
        )
    )
    count, revenue = result.one()
    return OrderAnalyticsTotals(
        count=int(count or 0),
        revenue=Decimal(revenue or "0.00"),
    )


async def get_top_product_analytics(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    currency: str,
    limit: int = 5,
) -> list[TopProductAnalytics]:
    revenue_expression = func.sum(OrderItem.quantity * OrderItem.unit_price)
    quantity_expression = func.sum(OrderItem.quantity)
    name_expression = func.concat(
        OrderItem.shrimp_name_snapshot,
        " - ",
        OrderItem.variant_name_snapshot,
    )

    result = await db.execute(
        select(
            name_expression.label("name"),
            quantity_expression.label("quantity"),
            revenue_expression.label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            *valid_order_filters(
                start_at=start_at,
                end_at=end_at,
                currency=currency,
            )
        )
        .group_by(name_expression)
        .order_by(revenue_expression.desc())
        .limit(limit)
    )

    return [
        TopProductAnalytics(
            name=str(row.name),
            quantity=int(row.quantity or 0),
            revenue=Decimal(row.revenue or "0.00"),
        )
        for row in result.all()
    ]

