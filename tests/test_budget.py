# ABOUTME: Tests for budget tracking functionality
# ABOUTME: Covers usage recording, spending calculations, and status reporting

"""Tests for Claudius budget tracker."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from claudius.budget import BudgetStatus, BudgetTracker


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
        # Initialize the tracker to create schema
        BudgetTracker(db_path=db_path)
        return db_path


class TestBudgetTracker:
    """Tests for BudgetTracker class."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    def test_record_usage(self, tracker: BudgetTracker) -> None:
        """Test recording API usage."""
        tracker.record_usage(
            model="claude-3-5-haiku-20241022",
            input_tokens=100,
            output_tokens=200,
            cost=0.001,
            routed_by="heuristic",
            query_preview="Test query",
        )

        daily_spent = tracker.get_daily_spent()
        assert daily_spent == 0.001

    def test_get_daily_spent_empty(self, tracker: BudgetTracker) -> None:
        """Test daily spent with no usage."""
        assert tracker.get_daily_spent() == 0.0

    def test_get_monthly_spent_empty(self, tracker: BudgetTracker) -> None:
        """Test monthly spent with no usage."""
        assert tracker.get_monthly_spent() == 0.0

    def test_get_status(self, tracker: BudgetTracker) -> None:
        """Test getting budget status."""
        status = tracker.get_status(monthly_budget=90.0, daily_budget=5.0)

        assert status.monthly_budget == 90.0
        assert status.daily_budget == 5.0
        assert status.monthly_spent == 0.0
        assert status.daily_spent == 0.0
        assert status.monthly_percent == 0.0
        assert status.daily_percent == 0.0


class TestBudgetStatus:
    """Tests for BudgetStatus dataclass."""

    def test_progress_bar_empty(self) -> None:
        """Test progress bar at 0%."""
        status = BudgetStatus(
            monthly_budget=90,
            monthly_spent=0,
            monthly_remaining=90,
            monthly_percent=0,
            daily_budget=5,
            daily_spent=0,
            daily_remaining=5,
            daily_percent=0,
            rollover=0,
            days_until_reset=15,
        )

        assert status.monthly_bar == "░" * 20
        assert status.daily_bar == "░" * 20

    def test_progress_bar_half(self) -> None:
        """Test progress bar at 50%."""
        status = BudgetStatus(
            monthly_budget=90,
            monthly_spent=45,
            monthly_remaining=45,
            monthly_percent=50,
            daily_budget=5,
            daily_spent=2.5,
            daily_remaining=2.5,
            daily_percent=50,
            rollover=0,
            days_until_reset=15,
        )

        assert status.monthly_bar == "█" * 10 + "░" * 10
        assert status.daily_bar == "█" * 10 + "░" * 10

    def test_progress_bar_full(self) -> None:
        """Test progress bar at 100%."""
        status = BudgetStatus(
            monthly_budget=90,
            monthly_spent=90,
            monthly_remaining=0,
            monthly_percent=100,
            daily_budget=5,
            daily_spent=5,
            daily_remaining=0,
            daily_percent=100,
            rollover=0,
            days_until_reset=15,
        )

        assert status.monthly_bar == "█" * 20
        assert status.daily_bar == "█" * 20


class TestRolloverCalculation:
    """Tests for rollover budget calculation."""

    def test_rollover_from_unused_budget(self, temp_db: Path) -> None:
        """Rollover should equal unused budget from previous month."""
        tracker = BudgetTracker(db_path=temp_db)

        # Insert usage from previous month (spent 70 of 90 budget)
        now = datetime.now()
        if now.month == 1:
            prev_month = datetime(now.year - 1, 12, 15)
        else:
            prev_month = datetime(now.year, now.month - 1, 15)

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "INSERT INTO usage (timestamp, model, input_tokens, output_tokens, cost) VALUES (?, ?, ?, ?, ?)",
                (prev_month.isoformat(), "sonnet", 1000, 500, 70.0),
            )

        status = tracker.get_status(monthly_budget=90.0, daily_budget=5.0)
        assert status.rollover == 20.0  # 90 - 70 = 20

    def test_rollover_capped_at_max(self, temp_db: Path) -> None:
        """Rollover should be capped at 50% of monthly budget."""
        tracker = BudgetTracker(db_path=temp_db)
        # No previous spending = full 90 unused, but cap at 45 (50%)
        status = tracker.get_status(monthly_budget=90.0, daily_budget=5.0)
        assert status.rollover == 45.0  # Capped at 50% of 90

    def test_no_rollover_if_overspent(self, temp_db: Path) -> None:
        """No rollover if previous month was overspent."""
        tracker = BudgetTracker(db_path=temp_db)

        # Insert overspending from previous month
        now = datetime.now()
        if now.month == 1:
            prev_month = datetime(now.year - 1, 12, 15)
        else:
            prev_month = datetime(now.year, now.month - 1, 15)

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "INSERT INTO usage (timestamp, model, input_tokens, output_tokens, cost) VALUES (?, ?, ?, ?, ?)",
                (prev_month.isoformat(), "opus", 5000, 2000, 100.0),  # Overspent!
            )

        status = tracker.get_status(monthly_budget=90.0, daily_budget=5.0)
        assert status.rollover == 0.0


class TestDailyHardLimit:
    """Tests for daily hard limit detection."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    def test_daily_hard_limit_exceeded_returns_true_when_over_limit(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that is_daily_hard_limit_exceeded returns True when spending exceeds limit."""
        # Record enough usage to exceed the daily hard limit of 10.0
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=15.0,
            routed_by="test",
        )
        assert tracker.is_daily_hard_limit_exceeded(daily_hard=10.0) is True

    def test_daily_hard_limit_exceeded_returns_true_when_at_limit(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that is_daily_hard_limit_exceeded returns True when spending equals limit."""
        # Record usage exactly at the limit
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=10.0,
            routed_by="test",
        )
        assert tracker.is_daily_hard_limit_exceeded(daily_hard=10.0) is True

    def test_daily_hard_limit_not_exceeded_returns_false(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that is_daily_hard_limit_exceeded returns False when under limit."""
        # Record usage under the limit
        tracker.record_usage(
            model="haiku",
            input_tokens=100,
            output_tokens=100,
            cost=0.50,
            routed_by="test",
        )
        assert tracker.is_daily_hard_limit_exceeded(daily_hard=10.0) is False

    def test_daily_hard_limit_not_exceeded_with_no_spending(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that is_daily_hard_limit_exceeded returns False with no spending."""
        assert tracker.is_daily_hard_limit_exceeded(daily_hard=10.0) is False
