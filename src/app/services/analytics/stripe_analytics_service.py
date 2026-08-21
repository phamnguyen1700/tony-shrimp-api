from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

import stripe

from app.core.config import get_settings
from app.services.analytics.period import AnalyticsPeriod, iter_local_dates

settings = get_settings()

SUCCESSFUL_PAYMENT_INTENT_STATUSES = {"succeeded"}
FAILED_PAYMENT_INTENT_STATUSES = {"requires_payment_method", "canceled"}
OPEN_DISPUTE_STATUSES = {
    "warning_needs_response",
    "warning_under_review",
    "needs_response",
    "under_review",
}
CHARGE_BALANCE_TYPES = {"charge", "payment"}
REFUND_BALANCE_TYPES = {"refund", "payment_refund"}
CHARGE_REPORTING_CATEGORIES = {"charge"}
REFUND_REPORTING_CATEGORIES = {"refund"}


class StripeAnalyticsUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RevenueAnalytics:
    gross: Decimal
    fees: Decimal
    net: Decimal
    currency: str


@dataclass(frozen=True)
class RefundAnalytics:
    amount: Decimal
    count: int
    currency: str


@dataclass(frozen=True)
class PaymentIntentAnalytics:
    successful: int
    failed: int
    attempts: int
    success_rate: Decimal


@dataclass(frozen=True)
class BalanceAnalytics:
    available: Decimal
    pending: Decimal
    currency: str


@dataclass(frozen=True)
class RevenueSeriesPoint:
    date: str
    gross: Decimal
    fees: Decimal
    net: Decimal


@dataclass(frozen=True)
class PayoutAnalytics:
    amount: Decimal
    currency: str
    status: str
    created: datetime
    arrival_date: datetime | None


@dataclass(frozen=True)
class DisputeAnalytics:
    open_count: int
    amount_at_risk: Decimal
    currency: str


@dataclass(frozen=True)
class StripeDashboardAnalytics:
    current_revenue: RevenueAnalytics
    previous_revenue: RevenueAnalytics
    refunds: RefundAnalytics
    payments: PaymentIntentAnalytics
    balance: BalanceAnalytics
    revenue_series: list[RevenueSeriesPoint]
    disputes: DisputeAnalytics


def stripe_get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)

    return getattr(value, key, default)


def stripe_minor_to_money(value: int | None) -> Decimal:
    amount = Decimal(value or 0) / Decimal("100")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_currency(value: str | None) -> str:
    return str(value or "").upper()


def datetime_from_stripe_timestamp(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value), tz=UTC)


def ensure_stripe_configured() -> None:
    if not settings.stripe_secret_key:
        raise StripeAnalyticsUnavailableError("Stripe secret key is not configured.")


def paginate_stripe_list(
    list_method: Callable[..., Any],
    **params: Any,
) -> Iterable[Any]:
    starting_after = None
    while True:
        page_params = dict(params)
        page_params["limit"] = min(int(page_params.get("limit", 100)), 100)
        if starting_after:
            page_params["starting_after"] = starting_after

        page = list_method(**page_params)
        data = list(stripe_get(page, "data", []) or [])
        for item in data:
            yield item

        if not stripe_get(page, "has_more", False) or not data:
            break

        starting_after = stripe_get(data[-1], "id")


def is_charge_balance_transaction(transaction: Any) -> bool:
    transaction_type = str(stripe_get(transaction, "type", ""))
    reporting_category = str(stripe_get(transaction, "reporting_category", ""))
    amount = int(stripe_get(transaction, "amount", 0) or 0)
    return (
        transaction_type in CHARGE_BALANCE_TYPES
        or reporting_category in CHARGE_REPORTING_CATEGORIES
    ) and amount > 0


def is_refund_balance_transaction(transaction: Any) -> bool:
    transaction_type = str(stripe_get(transaction, "type", ""))
    reporting_category = str(stripe_get(transaction, "reporting_category", ""))
    amount = int(stripe_get(transaction, "amount", 0) or 0)
    return (
        transaction_type in REFUND_BALANCE_TYPES
        or reporting_category in REFUND_REPORTING_CATEGORIES
    ) and amount < 0


def aggregate_revenue_from_balance_transactions(
    transactions: Iterable[Any],
    *,
    currency: str,
) -> RevenueAnalytics:
    gross = Decimal("0.00")
    fees = Decimal("0.00")
    net = Decimal("0.00")
    expected_currency = currency.upper()

    for transaction in transactions:
        if normalize_currency(stripe_get(transaction, "currency")) != expected_currency:
            continue

        if is_charge_balance_transaction(transaction):
            gross += stripe_minor_to_money(stripe_get(transaction, "amount"))
            fees += stripe_minor_to_money(stripe_get(transaction, "fee"))
            net += stripe_minor_to_money(stripe_get(transaction, "net"))
        elif is_refund_balance_transaction(transaction):
            fees += stripe_minor_to_money(stripe_get(transaction, "fee"))
            net += stripe_minor_to_money(stripe_get(transaction, "net"))

    return RevenueAnalytics(
        gross=gross,
        fees=fees,
        net=net,
        currency=expected_currency,
    )


def aggregate_revenue_series(
    transactions: Iterable[Any],
    *,
    period: AnalyticsPeriod,
    currency: str,
) -> list[RevenueSeriesPoint]:
    zone = ZoneInfo(period.timezone)
    empty_points = {
        date: {"gross": Decimal("0.00"), "fees": Decimal("0.00"), "net": Decimal("0.00")}
        for date in iter_local_dates(period.current_from, period.current_to)
    }
    expected_currency = currency.upper()

    for transaction in transactions:
        if normalize_currency(stripe_get(transaction, "currency")) != expected_currency:
            continue

        created = datetime_from_stripe_timestamp(stripe_get(transaction, "created"))
        date_key = created.astimezone(zone).date().isoformat()
        if date_key not in empty_points:
            continue

        if is_charge_balance_transaction(transaction):
            empty_points[date_key]["gross"] += stripe_minor_to_money(
                stripe_get(transaction, "amount")
            )
            empty_points[date_key]["fees"] += stripe_minor_to_money(
                stripe_get(transaction, "fee")
            )
            empty_points[date_key]["net"] += stripe_minor_to_money(
                stripe_get(transaction, "net")
            )
        elif is_refund_balance_transaction(transaction):
            empty_points[date_key]["fees"] += stripe_minor_to_money(
                stripe_get(transaction, "fee")
            )
            empty_points[date_key]["net"] += stripe_minor_to_money(
                stripe_get(transaction, "net")
            )

    return [
        RevenueSeriesPoint(
            date=date,
            gross=values["gross"],
            fees=values["fees"],
            net=values["net"],
        )
        for date, values in empty_points.items()
    ]


def list_balance_transactions(
    *,
    start_timestamp: int,
    end_timestamp: int,
) -> list[Any]:
    return list(
        paginate_stripe_list(
            stripe.BalanceTransaction.list,
            created={"gte": start_timestamp, "lt": end_timestamp},
        )
    )


def get_refund_analytics(period: AnalyticsPeriod, *, currency: str) -> RefundAnalytics:
    refunds = paginate_stripe_list(
        stripe.Refund.list,
        created={"gte": period.stripe_current_from, "lt": period.stripe_current_to},
    )
    amount = Decimal("0.00")
    count = 0
    expected_currency = currency.upper()

    for refund in refunds:
        if normalize_currency(stripe_get(refund, "currency")) != expected_currency:
            continue
        if str(stripe_get(refund, "status", "")) != "succeeded":
            continue

        amount += stripe_minor_to_money(stripe_get(refund, "amount"))
        count += 1

    return RefundAnalytics(amount=amount, count=count, currency=expected_currency)


def get_payment_intent_analytics(period: AnalyticsPeriod) -> PaymentIntentAnalytics:
    payment_intents = paginate_stripe_list(
        stripe.PaymentIntent.list,
        created={"gte": period.stripe_current_from, "lt": period.stripe_current_to},
    )
    successful = 0
    failed = 0

    for payment_intent in payment_intents:
        status = str(stripe_get(payment_intent, "status", ""))
        if status in SUCCESSFUL_PAYMENT_INTENT_STATUSES:
            successful += 1
        elif status in FAILED_PAYMENT_INTENT_STATUSES:
            failed += 1

    attempts = successful + failed
    success_rate = (
        (Decimal(successful) / Decimal(attempts) * Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        if attempts
        else Decimal("0.00")
    )

    return PaymentIntentAnalytics(
        successful=successful,
        failed=failed,
        attempts=attempts,
        success_rate=success_rate,
    )


def get_balance_analytics(*, currency: str) -> BalanceAnalytics:
    balance = stripe.Balance.retrieve()
    expected_currency = currency.upper()

    def get_total(bucket: str) -> Decimal:
        total = Decimal("0.00")
        for item in stripe_get(balance, bucket, []) or []:
            if normalize_currency(stripe_get(item, "currency")) == expected_currency:
                total += stripe_minor_to_money(stripe_get(item, "amount"))
        return total

    return BalanceAnalytics(
        available=get_total("available"),
        pending=get_total("pending"),
        currency=expected_currency,
    )


def get_dispute_analytics(*, currency: str) -> DisputeAnalytics:
    disputes = paginate_stripe_list(stripe.Dispute.list)
    expected_currency = currency.upper()
    open_count = 0
    amount_at_risk = Decimal("0.00")

    for dispute in disputes:
        if str(stripe_get(dispute, "status", "")) not in OPEN_DISPUTE_STATUSES:
            continue
        if normalize_currency(stripe_get(dispute, "currency")) != expected_currency:
            continue

        open_count += 1
        amount_at_risk += stripe_minor_to_money(stripe_get(dispute, "amount"))

    return DisputeAnalytics(
        open_count=open_count,
        amount_at_risk=amount_at_risk,
        currency=expected_currency,
    )


def get_payouts(*, currency: str, limit: int = 10) -> list[PayoutAnalytics]:
    ensure_stripe_configured()
    payouts = []
    expected_currency = currency.upper()

    try:
        for payout in paginate_stripe_list(stripe.Payout.list, limit=limit):
            if normalize_currency(stripe_get(payout, "currency")) != expected_currency:
                continue

            payouts.append(
                PayoutAnalytics(
                    amount=stripe_minor_to_money(stripe_get(payout, "amount")),
                    currency=expected_currency,
                    status=str(stripe_get(payout, "status", "")),
                    created=datetime_from_stripe_timestamp(stripe_get(payout, "created")),
                    arrival_date=(
                        datetime_from_stripe_timestamp(stripe_get(payout, "arrival_date"))
                        if stripe_get(payout, "arrival_date")
                        else None
                    ),
                )
            )
            if len(payouts) >= limit:
                break
    except stripe.StripeError as exc:
        raise StripeAnalyticsUnavailableError(str(exc)) from exc

    return payouts


def get_stripe_dashboard_analytics(
    period: AnalyticsPeriod,
    *,
    currency: str,
) -> StripeDashboardAnalytics:
    ensure_stripe_configured()

    try:
        current_transactions = list_balance_transactions(
            start_timestamp=period.stripe_current_from,
            end_timestamp=period.stripe_current_to,
        )
        previous_transactions = list_balance_transactions(
            start_timestamp=period.stripe_previous_from,
            end_timestamp=period.stripe_previous_to,
        )

        return StripeDashboardAnalytics(
            current_revenue=aggregate_revenue_from_balance_transactions(
                current_transactions,
                currency=currency,
            ),
            previous_revenue=aggregate_revenue_from_balance_transactions(
                previous_transactions,
                currency=currency,
            ),
            refunds=get_refund_analytics(period, currency=currency),
            payments=get_payment_intent_analytics(period),
            balance=get_balance_analytics(currency=currency),
            revenue_series=aggregate_revenue_series(
                current_transactions,
                period=period,
                currency=currency,
            ),
            disputes=get_dispute_analytics(currency=currency),
        )
    except stripe.StripeError as exc:
        raise StripeAnalyticsUnavailableError(str(exc)) from exc

