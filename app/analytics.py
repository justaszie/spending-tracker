import datetime as dt
import uuid
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel
from sqlalchemy import Engine

from app.core.project_types import (
    CategoryAggregate,
    DeltasGroup,
    DeltaValues,
    MetricsGroup,
    PeriodPreset,
    PeriodStats,
    StatsDeltas,
)
from app.db.transactions import get_spend_data_by_category, get_total_spend_data


class Period(TypedDict):
    date_from: dt.date | None
    date_to: dt.date | None


class TransactionStatsQuery(BaseModel):
    user_id: uuid.UUID
    selected_period: PeriodPreset
    current_date_from: dt.date | None = None
    current_date_to: dt.date | None = None
    include_previous: bool
    previous_date_from: dt.date | None = None
    previous_date_to: dt.date | None = None


class TransactionStatsResults(BaseModel):
    current_period: PeriodStats | None = None
    previous_period: PeriodStats | None = None
    deltas: StatsDeltas | None = None


def _get_query_dates(
    selected_period: PeriodPreset,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Period:
    match selected_period:
        # 30 rolling days, including today
        case PeriodPreset.LAST_30:
            today = dt.date.today()
            start = today - dt.timedelta(days=29)
            return {
                "date_from": start,
                "date_to": today,
            }
        # From beginning of the month until today
        case PeriodPreset.MONTH_TO_DATE:
            today = dt.date.today()
            start = dt.date(year=today.year, month=today.month, day=1)
            return {
                "date_from": start,
                "date_to": today,
            }
        # From beginning of the year until today
        case PeriodPreset.YEAR_TO_DATE:
            today = dt.date.today()
            start = dt.date(year=today.year, month=1, day=1)
            return {
                "date_from": start,
                "date_to": today,
            }
        case PeriodPreset.ALL_TIME:
            return {"date_from": None, "date_to": None}

    # For custom period, date_from can be null (from beginning) but date_to is bounded to today
    return {
        "date_from": date_from,
        "date_to": date_to if date_to else dt.date.today(),
    }


# Conditional logic to resolve the query input based on API input
def build_stats_query(
    *,
    user_id: uuid.UUID,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    selected_period: PeriodPreset = PeriodPreset.ALL_TIME,
    previous_requested: bool = False,
) -> TransactionStatsQuery:
    # Resolve the dates based on period selection and dates input
    current_dates = _get_query_dates(
        selected_period=selected_period,
        date_from=date_from,
        date_to=date_to,
    )

    # If period is ALL_TIME or no beginning date provided, there can be no previous period
    if selected_period == PeriodPreset.ALL_TIME or (
        selected_period == PeriodPreset.CUSTOM and date_from is None
    ):
        include_previous = False
    else:
        include_previous = previous_requested

    # Calculate date filters for previous period
    previous_date_from, previous_date_to = None, None
    current_date_from = current_dates["date_from"]
    current_date_to = current_dates["date_to"]

    if include_previous:
        if selected_period == PeriodPreset.LAST_30:
            if not current_date_from or not current_date_to:
                raise ValueError("One of the dates is not resolved")
            previous_date_to = current_date_from - dt.timedelta(days=1)
            previous_date_from = previous_date_to - dt.timedelta(days=29)
        elif selected_period == PeriodPreset.MONTH_TO_DATE:
            if not current_date_to:
                raise ValueError("Date to must be resolved")
            previous_dates = _calculate_previous_mtd(current_date=current_date_to)
            previous_date_from = previous_dates["date_from"]
            previous_date_to = previous_dates["date_to"]
        elif selected_period == PeriodPreset.YEAR_TO_DATE:
            if not current_date_to:
                raise ValueError("Date to must be resolved")
            prev_year = current_date_to.year - 1
            previous_date_from = dt.date(year=prev_year, month=1, day=1)
            previous_date_to = dt.date(
                year=prev_year,
                month=current_date_to.month,
                day=current_date_to.day,
            )
        elif selected_period == PeriodPreset.CUSTOM:
            # if include_previous is True, both dates must be resolved
            if not current_date_from or not current_date_to:
                raise ValueError("One of the dates is not resolved")

            days_count = (current_date_to - current_date_from).days + 1

            previous_date_to = current_date_from - dt.timedelta(days=1)
            previous_date_from = previous_date_to - dt.timedelta(days=days_count - 1)

    return TransactionStatsQuery(
        user_id=user_id,
        selected_period=selected_period,
        current_date_from=current_date_from,
        current_date_to=current_date_to,
        include_previous=include_previous,
        previous_date_from=previous_date_from,
        previous_date_to=previous_date_to,
    )


def _calculate_previous_mtd(current_date: dt.date) -> Period:
    """Calculates and returns the period covering previous MTD"""
    current_day = current_date.day

    year = current_date.year
    prev_month = current_date.month - 1
    # If previous  period is december last year
    if prev_month == 0:
        prev_month = 12
        year = year - 1

    prev_month_last_day = (current_date - dt.timedelta(days=current_day)).day

    previous_date_from = dt.date(year=year, month=prev_month, day=1)
    previous_month_day = min(current_day, prev_month_last_day)
    previous_date_to = dt.date(year=year, month=prev_month, day=previous_month_day)

    return {
        "date_from": previous_date_from,
        "date_to": previous_date_to,
    }


def generate_transactions_stats(
    query: TransactionStatsQuery, db: Engine
) -> TransactionStatsResults:
    current_period_stats = get_transaction_stats_for_period(
        user_id=query.user_id,
        date_from=query.current_date_from,
        date_to=query.current_date_to,
        db=db,
    )

    previous_period_stats = None
    deltas = None

    if query.include_previous:
        previous_period_stats = get_transaction_stats_for_period(
            user_id=query.user_id,
            date_from=query.previous_date_from,
            date_to=query.previous_date_to,
            db=db,
        )

        spend_deltas = calculate_spend_stats_deltas(
            current_spend=current_period_stats.groups["spend"],
            previous_spend=previous_period_stats.groups["spend"],
            metrics=["total", "avg_daily"],
        )
        deltas = StatsDeltas(groups={"spend": spend_deltas})

    return TransactionStatsResults(
        current_period=current_period_stats,
        previous_period=previous_period_stats,
        deltas=deltas,
    )

    # call analytics helper to calculate deltas for each metric (TBD how to match the metric names)
    # The analytics are key driven (total, avg_spend, etc. so we can match prev with curr and calculate deltas)


def get_transaction_stats_for_period(
    user_id: uuid.UUID,
    date_from: dt.date | None,
    date_to: dt.date | None,
    db: Engine,
) -> PeriodStats:
    if date_from and date_to and date_from > date_to:
        raise ValueError('"date_from" cannot be after "date_to"')
    period_data = get_total_spend_data(
        user_id=user_id, db=db, date_from=date_from, date_to=date_to
    )

    # If the query did not contain filter dates, we use the dates from fetched data to define the period
    final_date_from = date_from or (
        period_data.earliest_txn_datetime.date()
        if period_data.earliest_txn_datetime
        else None
    )
    final_date_to = date_to or (
        period_data.latest_txn_datetime.date()
        if period_data.latest_txn_datetime
        else None
    )

    if final_date_from and final_date_to:
        days_count = (final_date_to - final_date_from).days + 1
        current_avg_net_spend = Decimal(
            period_data.net_total_spend / days_count
        ).quantize(Decimal("1.00"))
    else:
        days_count = 0
        current_avg_net_spend = Decimal("0")

    stats_by_category = get_spend_data_by_category(
        user_id=user_id, db=db, date_from=date_from, date_to=date_to
    )

    spend_group = MetricsGroup(
        total=period_data.net_total_spend,
        avg_daily=current_avg_net_spend,
        by_category=[
            CategoryAggregate(
                category=cat.spending_category,
                total=cat.net_total_spend,
                avg_daily=Decimal(cat.net_total_spend / days_count).quantize(
                    Decimal("1.00")
                ),
            )
            for cat in stats_by_category
        ],
    )

    return PeriodStats(
        date_from=final_date_from,
        date_to=final_date_to,
        days_count=days_count,
        groups={"spend": spend_group},
    )


def calculate_spend_stats_deltas(
    current_spend: MetricsGroup,
    previous_spend: MetricsGroup,
    metrics: list[str],
) -> DeltasGroup:
    deltas = {}
    for metric in metrics:
        current_val = getattr(current_spend, metric)
        previous_val = getattr(previous_spend, metric)
        abs_change = current_val - previous_val
        pct_change = None
        if previous_val > 0:
            pct_change = (Decimal(abs_change / previous_val) * 100).quantize(
                Decimal("1.00")
            )
        deltas[metric] = DeltaValues(abs_change=abs_change, pct_change=pct_change)

    return DeltasGroup.model_validate(deltas)
