# ABOUTME: Tests for the status-line CLI subcommand
# ABOUTME: Covers stdin parsing, formatting, and graceful error handling

"""Tests for Claudius status-line CLI command."""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from claudius.cli import format_status_line, parse_stdin_json, status_line_command


class TestParseStdinJson:
    """Tests for parsing JSON input from stdin."""

    def test_parse_valid_json(self) -> None:
        """Test parsing valid JSON with cost data."""
        json_data = json.dumps({
            "cost": {"total_cost_usd": 0.05},
            "context_window": {"total_input_tokens": 1000, "total_output_tokens": 500},
        })
        stdin = StringIO(json_data)

        result = parse_stdin_json(stdin)

        assert result is not None
        assert result["cost"]["total_cost_usd"] == 0.05
        assert result["context_window"]["total_input_tokens"] == 1000

    def test_parse_empty_input(self) -> None:
        """Test parsing empty stdin returns None."""
        stdin = StringIO("")

        result = parse_stdin_json(stdin)

        assert result is None

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns None."""
        stdin = StringIO("not valid json {")

        result = parse_stdin_json(stdin)

        assert result is None

    def test_parse_partial_data(self) -> None:
        """Test parsing JSON with only cost data."""
        json_data = json.dumps({"cost": {"total_cost_usd": 0.10}})
        stdin = StringIO(json_data)

        result = parse_stdin_json(stdin)

        assert result is not None
        assert result["cost"]["total_cost_usd"] == 0.10


class TestFormatStatusLine:
    """Tests for formatting the status line output."""

    def test_format_with_session_cost(self) -> None:
        """Test formatting with session cost in output."""
        session_data = {"cost": {"total_cost_usd": 0.05}}

        result = format_status_line(
            session_data=session_data,
            daily_spent=2.30,
            daily_budget=5.0,
            monthly_spent=73.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        assert "session" in result
        assert "today" in result
        assert "month" in result

    def test_format_without_session_data(self) -> None:
        """Test formatting when no session data is provided."""
        result = format_status_line(
            session_data=None,
            daily_spent=2.30,
            daily_budget=5.0,
            monthly_spent=73.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        assert "today" in result
        assert "month" in result
        # Session should not appear without session data
        assert "session" not in result

    def test_format_shows_daily_budget(self) -> None:
        """Test that daily budget info is shown correctly."""
        result = format_status_line(
            session_data=None,
            daily_spent=2.50,
            daily_budget=5.0,
            monthly_spent=50.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        # Should contain daily budget info
        assert "2.50" in result or "2.5" in result
        assert "5" in result

    def test_format_shows_monthly_budget(self) -> None:
        """Test that monthly budget info is shown correctly."""
        result = format_status_line(
            session_data=None,
            daily_spent=2.0,
            daily_budget=5.0,
            monthly_spent=73.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        # Should contain monthly budget info
        assert "73" in result
        assert "90" in result

    def test_format_usd_to_eur_conversion(self) -> None:
        """Test that USD session cost is converted to EUR."""
        session_data = {"cost": {"total_cost_usd": 1.00}}

        result = format_status_line(
            session_data=session_data,
            daily_spent=0.0,
            daily_budget=5.0,
            monthly_spent=0.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        # $1.00 USD * 0.92 = 0.92 EUR
        assert "0.92" in result

    def test_format_uses_currency_symbol(self) -> None:
        """Test that correct currency symbol is used."""
        result = format_status_line(
            session_data=None,
            daily_spent=2.0,
            daily_budget=5.0,
            monthly_spent=50.0,
            monthly_budget=90.0,
            currency="EUR",
            usd_to_eur_rate=0.92,
        )

        # Should not contain $ for EUR currency
        assert "$" not in result


class TestStatusLineCommand:
    """Tests for the status_line_command function."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def mock_config(self) -> dict:
        """Create mock configuration data."""
        return {
            "budget": {
                "monthly": 90.0,
                "daily_soft": 5.0,
                "currency": "EUR",
            }
        }

    def test_status_line_command_with_valid_input(self, temp_db: Path) -> None:
        """Test command with valid stdin JSON."""
        json_data = json.dumps({
            "cost": {"total_cost_usd": 0.05},
            "context_window": {"total_input_tokens": 1000, "total_output_tokens": 500},
        })
        stdin = StringIO(json_data)
        stdout = StringIO()

        with patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.Config") as mock_config_class:

            mock_tracker = mock_tracker_class.return_value
            mock_tracker.get_daily_spent.return_value = 2.30
            mock_tracker.get_monthly_spent.return_value = 73.0

            mock_config = mock_config_class.load.return_value
            mock_config.budget.monthly = 90.0
            mock_config.budget.daily_soft = 5.0
            mock_config.budget.currency = "EUR"

            status_line_command(stdin=stdin, stdout=stdout)

        output = stdout.getvalue()
        assert len(output) > 0
        assert "today" in output or "month" in output

    def test_status_line_command_with_empty_input(self, temp_db: Path) -> None:
        """Test command with empty stdin."""
        stdin = StringIO("")
        stdout = StringIO()

        with patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.Config") as mock_config_class:

            mock_tracker = mock_tracker_class.return_value
            mock_tracker.get_daily_spent.return_value = 1.0
            mock_tracker.get_monthly_spent.return_value = 20.0

            mock_config = mock_config_class.load.return_value
            mock_config.budget.monthly = 90.0
            mock_config.budget.daily_soft = 5.0
            mock_config.budget.currency = "EUR"

            status_line_command(stdin=stdin, stdout=stdout)

        output = stdout.getvalue()
        # Should still output something useful without session data
        assert len(output) > 0

    def test_status_line_command_graceful_on_tracker_error(self) -> None:
        """Test command handles BudgetTracker errors gracefully."""
        stdin = StringIO("")
        stdout = StringIO()

        with patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.Config") as mock_config_class:

            mock_tracker_class.side_effect = Exception("DB error")

            mock_config = mock_config_class.load.return_value
            mock_config.budget.monthly = 90.0
            mock_config.budget.daily_soft = 5.0
            mock_config.budget.currency = "EUR"

            # Should not raise
            status_line_command(stdin=stdin, stdout=stdout)

        output = stdout.getvalue()
        # Should output fallback message
        assert len(output) > 0

    def test_status_line_command_graceful_on_config_error(self) -> None:
        """Test command handles Config load errors gracefully."""
        stdin = StringIO("")
        stdout = StringIO()

        with patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.Config") as mock_config_class:

            mock_tracker = mock_tracker_class.return_value
            mock_tracker.get_daily_spent.return_value = 0.0
            mock_tracker.get_monthly_spent.return_value = 0.0

            mock_config_class.load.side_effect = Exception("Config error")

            # Should not raise
            status_line_command(stdin=stdin, stdout=stdout)

        output = stdout.getvalue()
        # Should output fallback message
        assert len(output) > 0

    def test_status_line_outputs_single_line(self) -> None:
        """Test that output is a single line (no embedded newlines except trailing)."""
        json_data = json.dumps({"cost": {"total_cost_usd": 0.05}})
        stdin = StringIO(json_data)
        stdout = StringIO()

        with patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.Config") as mock_config_class:

            mock_tracker = mock_tracker_class.return_value
            mock_tracker.get_daily_spent.return_value = 2.0
            mock_tracker.get_monthly_spent.return_value = 50.0

            mock_config = mock_config_class.load.return_value
            mock_config.budget.monthly = 90.0
            mock_config.budget.daily_soft = 5.0
            mock_config.budget.currency = "EUR"

            status_line_command(stdin=stdin, stdout=stdout)

        output = stdout.getvalue()
        # Strip trailing newline and check no embedded newlines
        assert "\n" not in output.rstrip("\n")
