import datetime as dt
import uuid

import pytest
from sqlalchemy.util.typing import NoneType

import app.analytics as analytics
from app.core.project_types import PeriodPreset

TEST_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def frozen_today(monkeypatch) -> dt.date:
    today = dt.date(2026, 3, 27)

    class FrozenDate(dt.date):
        @classmethod
        def today(cls) -> dt.date:
            return today

    monkeypatch.setattr(analytics.dt, "date", FrozenDate)
    return today


class TestBuildStatsQuery:
    def test_all_time_ignores_previous_and_resets_dates(self):
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            date_from=dt.date(2026, 1, 1),
            date_to=dt.date(2026, 1, 31),
            selected_period=PeriodPreset.ALL_TIME,
            previous_requested=True,
        )

        assert query.user_id == TEST_USER_ID
        assert query.date_from is None
        assert query.date_to is None
        assert query.include_previous is False

    @pytest.mark.parametrize("previous_requested", [True, False])
    def test_custom_passes_through_dates_and_previous_flag(self, previous_requested):
        date_from = dt.date(2026, 2, 10)
        date_to = dt.date(2026, 2, 20)

        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            date_from=date_from,
            date_to=date_to,
            selected_period=PeriodPreset.CUSTOM,
            previous_requested=previous_requested,
        )

        assert query.user_id == TEST_USER_ID
        assert query.date_from == date_from
        assert query.date_to == date_to
        assert query.include_previous is previous_requested

    def test_custom_preserves_original_date_from(self):
        date_to = dt.date(2026, 2, 1)
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            date_from=None,
            date_to=date_to,
            selected_period=PeriodPreset.CUSTOM,
            previous_requested=False,
        )

        assert query.date_from is None
        assert query.date_to == date_to
        assert query.include_previous is False

    def test_custom_empty_date_to_resolves_today(self, frozen_today):
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            date_from=None,
            date_to=None,
            selected_period=PeriodPreset.CUSTOM,
            previous_requested=False,
        )

        assert query.date_from is None
        assert query.date_to == frozen_today
        assert query.include_previous is False

    @pytest.mark.parametrize("previous_requested", [True, False])
    def test_last_30_resolves_rolling_dates(self, frozen_today, previous_requested):
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            selected_period=PeriodPreset.LAST_30,
            previous_requested=previous_requested,
        )

        assert query.date_from == frozen_today - dt.timedelta(days=29)
        assert query.date_to == frozen_today
        assert query.include_previous is previous_requested

    @pytest.mark.parametrize("previous_requested", [True, False])
    def test_month_to_date_resolves_from_month_start(
        self, frozen_today, previous_requested
    ):
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            selected_period=PeriodPreset.MONTH_TO_DATE,
            previous_requested=previous_requested,
        )

        assert query.date_from == dt.date(
            year=frozen_today.year, month=frozen_today.month, day=1
        )
        assert query.date_to == frozen_today
        assert query.include_previous is previous_requested

    @pytest.mark.parametrize("previous_requested", [True, False])
    def test_year_to_date_resolves_from_year_start(
        self, frozen_today, previous_requested
    ):
        query = analytics.build_stats_query(
            user_id=TEST_USER_ID,
            selected_period=PeriodPreset.YEAR_TO_DATE,
            previous_requested=previous_requested,
        )

        assert query.date_from == dt.date(year=frozen_today.year, month=1, day=1)
        assert query.date_to == frozen_today
        assert query.include_previous is previous_requested
