# ABOUTME: Tests for budget tracking functionality
# ABOUTME: Covers usage recording, spending calculations, and status reporting

"""Tests for Claudius budget tracker."""

import tempfile
from pathlib import Path

import pytest

from claudius.budget import BudgetStatus, BudgetTracker


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
