# ABOUTME: Budget tracking and management for Claudius
# ABOUTME: Handles SQLite storage, rollover logic, and spending limits

"""
Claudius Budget Tracker.

Manages budget tracking with:
- SQLite storage for usage history
- Daily and monthly limits
- Rollover calculations
- Progress bar data
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path.home() / ".claudius" / "claudius.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost REAL NOT NULL,
    routed_by TEXT,
    query_preview TEXT
);

CREATE TABLE IF NOT EXISTS budget_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_type TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    budget REAL NOT NULL,
    spent REAL DEFAULT 0,
    rollover_from REAL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_budget_periods_type ON budget_periods(period_type, period_start);
"""


@dataclass
class BudgetStatus:
    """Current budget status snapshot."""

    monthly_budget: float
    monthly_spent: float
    monthly_remaining: float
    monthly_percent: float

    daily_budget: float
    daily_spent: float
    daily_remaining: float
    daily_percent: float

    rollover: float
    days_until_reset: int

    @property
    def monthly_bar(self) -> str:
        """Generate progress bar for monthly budget."""
        return self._make_bar(self.monthly_percent)

    @property
    def daily_bar(self) -> str:
        """Generate progress bar for daily budget."""
        return self._make_bar(self.daily_percent)

    @staticmethod
    def _make_bar(percent: float, width: int = 20) -> str:
        """Generate a progress bar string."""
        filled = int(width * min(percent, 100) / 100)
        empty = width - filled
        return "█" * filled + "░" * empty


class BudgetTracker:
    """Tracks and manages Claude API budget."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Ensure database exists with schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        routed_by: str | None = None,
        query_preview: str | None = None,
    ) -> None:
        """Record an API call."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO usage (model, input_tokens, output_tokens, cost, routed_by, query_preview)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    model,
                    input_tokens,
                    output_tokens,
                    cost,
                    routed_by,
                    query_preview[:100] if query_preview else None,
                ),
            )

    def get_daily_spent(self, day: date | None = None) -> float:
        """Get total spent for a day."""
        day = day or date.today()
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT COALESCE(SUM(cost), 0) FROM usage WHERE DATE(timestamp) = ?",
                (day.isoformat(),),
            ).fetchone()
            return result[0] if result else 0.0

    def get_monthly_spent(self, year: int | None = None, month: int | None = None) -> float:
        """Get total spent for a month."""
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT COALESCE(SUM(cost), 0) FROM usage
                WHERE strftime('%Y', timestamp) = ? AND strftime('%m', timestamp) = ?
                """,
                (str(year), f"{month:02d}"),
            ).fetchone()
            return result[0] if result else 0.0

    def _calculate_rollover(self, monthly_budget: float, max_rollover_percent: float = 0.5) -> float:
        """Calculate rollover from previous month.

        Args:
            monthly_budget: The monthly budget amount
            max_rollover_percent: Max rollover as fraction of monthly (default 50%)

        Returns:
            Rollover amount (0 if previous month overspent)
        """
        now = datetime.now()

        # Get previous month
        if now.month == 1:
            prev_year, prev_month = now.year - 1, 12
        else:
            prev_year, prev_month = now.year, now.month - 1

        prev_spent = self.get_monthly_spent(prev_year, prev_month)
        unused = monthly_budget - prev_spent

        # No rollover if overspent
        if unused <= 0:
            return 0.0

        # Cap at max rollover
        max_rollover = monthly_budget * max_rollover_percent
        return min(unused, max_rollover)

    def is_daily_hard_limit_exceeded(self, daily_hard: float) -> bool:
        """Check if daily hard limit has been exceeded.

        Args:
            daily_hard: The daily hard limit amount

        Returns:
            True if daily spending is at or above the hard limit
        """
        today_spent = self.get_daily_spent()
        return today_spent >= daily_hard

    def get_status(self, monthly_budget: float, daily_budget: float) -> BudgetStatus:
        """Get current budget status."""
        now = datetime.now()
        monthly_spent = self.get_monthly_spent()
        daily_spent = self.get_daily_spent()

        # Calculate days until reset (end of month)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        days_until_reset = (next_month - now).days

        rollover = self._calculate_rollover(monthly_budget)

        return BudgetStatus(
            monthly_budget=monthly_budget,
            monthly_spent=monthly_spent,
            monthly_remaining=monthly_budget - monthly_spent,
            monthly_percent=(monthly_spent / monthly_budget * 100) if monthly_budget > 0 else 0,
            daily_budget=daily_budget,
            daily_spent=daily_spent,
            daily_remaining=daily_budget - daily_spent,
            daily_percent=(daily_spent / daily_budget * 100) if daily_budget > 0 else 0,
            rollover=rollover,
            days_until_reset=days_until_reset,
        )
