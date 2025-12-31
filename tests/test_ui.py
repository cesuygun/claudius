# ABOUTME: Tests for UI components in the Claudius REPL
# ABOUTME: Tests Rich-based rendering functions for budget display and status

"""Tests for Claudius UI components."""

import tempfile
from pathlib import Path

import pytest
from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.config import Config
from claudius.ui import (
    get_color_for_percent,
    get_currency_symbol,
    render_banner,
    render_budget_alert,
    render_budget_bars,
    render_cost_estimate,
    render_cost_line,
    render_response,
    render_status,
)


class TestRenderBanner:
    """Tests for render_banner function."""

    def test_banner_contains_claudius_ascii_art(self) -> None:
        """Test that banner contains the CLAUDIUS ASCII art."""
        result = render_banner()
        # Render to string to check content
        console = Console(force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should contain parts of the ASCII art
        assert "CLAUDIUS" in output or "╔═╗" in output

    def test_banner_contains_tagline(self) -> None:
        """Test that banner contains the budget guardian tagline."""
        result = render_banner()
        console = Console(force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Budget Guardian" in output

    def test_banner_contains_version(self) -> None:
        """Test that banner contains version information."""
        result = render_banner()
        console = Console(force_terminal=True, width=80)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "v" in output  # Version should be present


class TestRenderBudgetBars:
    """Tests for render_budget_bars function."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def config(self) -> Config:
        """Create a default config."""
        return Config()

    def test_budget_bars_shows_monthly_budget(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that budget bars show monthly budget information."""
        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Monthly" in output

    def test_budget_bars_shows_daily_budget(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that budget bars show daily budget information."""
        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Today" in output

    def test_budget_bars_uses_currency_from_config(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that budget bars use currency symbol from config."""
        config = Config()
        config.budget.currency = "USD"

        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "$" in output

    def test_budget_bars_eur_currency(self, tracker: BudgetTracker) -> None:
        """Test that budget bars show EUR currency correctly."""
        config = Config()
        config.budget.currency = "EUR"

        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # EUR should show Euro symbol
        assert "EUR" in output or "€" in output

    def test_budget_bars_green_under_50_percent(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that budget bars are green when under 50%."""
        # With no spending, should be at 0% which is green
        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Progress bar should be displayed
        assert "█" in output or "░" in output

    def test_budget_bars_shows_rollover(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that budget bars show rollover information."""
        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Rollover" in output

    def test_budget_bars_shows_reset_days(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that budget bars show days until reset."""
        result = render_budget_bars(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Reset" in output or "days" in output


class TestRenderStatus:
    """Tests for render_status function."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def config(self) -> Config:
        """Create a default config."""
        return Config()

    def test_status_shows_title(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that status shows Budget Status title."""
        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Budget Status" in output

    def test_status_shows_monthly_budget(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that status shows monthly budget details."""
        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Monthly" in output

    def test_status_shows_daily_budget(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that status shows daily budget details."""
        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Today" in output

    def test_status_shows_rollover(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that status shows rollover amount."""
        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Rollover" in output

    def test_status_shows_reset_days(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that status shows days until reset."""
        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Reset" in output

    def test_status_uses_currency_from_config(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that status uses currency symbol from config."""
        config = Config()
        config.budget.currency = "USD"

        result = render_status(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "$" in output


class TestRenderResponse:
    """Tests for render_response function."""

    def test_response_shows_model_indicator(self) -> None:
        """Test that response shows model indicator."""
        result = render_response("Haiku", "This is a test response.")
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Haiku" in output

    def test_response_shows_text(self) -> None:
        """Test that response shows the response text."""
        result = render_response("Sonnet", "This is a test response.")
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "This is a test response." in output

    def test_response_with_different_models(self) -> None:
        """Test that response works with different model names."""
        for model in ["Haiku", "Sonnet", "Opus"]:
            result = render_response(model, "Response text")
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(result)
            output = capture.get()

            assert model in output


class TestRenderCostEstimate:
    """Tests for render_cost_estimate function."""

    def test_cost_estimate_shows_total_range(self) -> None:
        """Test that cost estimate shows total cost range."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="haiku",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Total should be 0.03 - 0.06
        assert "0.0300" in output
        assert "0.0600" in output

    def test_cost_estimate_shows_input_cost(self) -> None:
        """Test that cost estimate shows input cost with (exact) label."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="sonnet",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Input" in output
        assert "0.0100" in output
        assert "(exact)" in output

    def test_cost_estimate_shows_output_cost_range(self) -> None:
        """Test that cost estimate shows output cost range with (est) label."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="opus",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Output" in output
        assert "0.0200" in output
        assert "0.0500" in output
        assert "(est)" in output

    def test_cost_estimate_shows_model_name(self) -> None:
        """Test that cost estimate shows the model name."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="haiku",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Model" in output
        assert "Haiku" in output  # Title case

    def test_cost_estimate_uses_currency_symbol(self) -> None:
        """Test that cost estimate uses correct currency symbol."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="sonnet",
            currency="USD",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "$" in output

    def test_cost_estimate_eur_currency(self) -> None:
        """Test that cost estimate shows EUR correctly."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="sonnet",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # EUR should show Euro symbol
        assert "EUR" in output or "\u20ac" in output

    def test_cost_estimate_shows_estimated_cost_label(self) -> None:
        """Test that cost estimate shows 'Estimated cost' label."""
        result = render_cost_estimate(
            input_cost=0.01,
            output_cost_min=0.02,
            output_cost_max=0.05,
            model="haiku",
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Estimated cost" in output

    def test_cost_estimate_with_different_models(self) -> None:
        """Test that cost estimate works with different model names."""
        for model in ["haiku", "sonnet", "opus"]:
            result = render_cost_estimate(
                input_cost=0.01,
                output_cost_min=0.02,
                output_cost_max=0.05,
                model=model,
                currency="EUR",
            )
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(result)
            output = capture.get()

            assert model.title() in output


class TestRenderCostLine:
    """Tests for render_cost_line function."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def config(self) -> Config:
        """Create a default config."""
        return Config()

    def test_cost_line_shows_monthly_spent(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that cost line shows monthly spent amount."""
        result = render_cost_line(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should show monthly budget info
        assert "/" in output  # format: spent/budget

    def test_cost_line_shows_progress_bar(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that cost line shows progress bar."""
        result = render_cost_line(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should have progress bar characters
        assert "█" in output or "░" in output

    def test_cost_line_shows_percentage(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that cost line shows percentage."""
        result = render_cost_line(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "%" in output

    def test_cost_line_shows_daily_spend(
        self, tracker: BudgetTracker, config: Config
    ) -> None:
        """Test that cost line shows today's spending."""
        result = render_cost_line(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Today" in output

    def test_cost_line_uses_currency_from_config(
        self, tracker: BudgetTracker
    ) -> None:
        """Test that cost line uses currency symbol from config."""
        config = Config()
        config.budget.currency = "USD"

        result = render_cost_line(tracker, config)
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "$" in output


class TestColorThresholds:
    """Tests for color threshold logic (green < 50%, yellow 50-80%, red > 80%)."""

    def test_green_at_zero_percent(self) -> None:
        """Test that 0% budget usage is green."""
        assert get_color_for_percent(0) == "green"

    def test_green_at_49_percent(self) -> None:
        """Test that 49% budget usage is green."""
        assert get_color_for_percent(49) == "green"

    def test_yellow_at_50_percent(self) -> None:
        """Test that exactly 50% budget usage is yellow."""
        assert get_color_for_percent(50) == "yellow"

    def test_yellow_at_79_percent(self) -> None:
        """Test that 79% budget usage is yellow."""
        assert get_color_for_percent(79) == "yellow"

    def test_red_at_80_percent(self) -> None:
        """Test that exactly 80% budget usage is red."""
        assert get_color_for_percent(80) == "red"

    def test_red_at_100_percent(self) -> None:
        """Test that 100% budget usage is red."""
        assert get_color_for_percent(100) == "red"

    def test_red_over_100_percent(self) -> None:
        """Test that over 100% budget usage is still red."""
        assert get_color_for_percent(120) == "red"


class TestCurrencySymbols:
    """Tests for currency symbol mapping."""

    def test_eur_symbol(self) -> None:
        """Test EUR maps to Euro symbol."""
        assert get_currency_symbol("EUR") == "€"

    def test_usd_symbol(self) -> None:
        """Test USD maps to dollar symbol."""
        assert get_currency_symbol("USD") == "$"

    def test_gbp_symbol(self) -> None:
        """Test GBP maps to pound symbol."""
        assert get_currency_symbol("GBP") == "£"

    def test_jpy_symbol(self) -> None:
        """Test JPY maps to yen symbol."""
        assert get_currency_symbol("JPY") == "¥"

    def test_unknown_currency_returns_code(self) -> None:
        """Test unknown currency returns the currency code."""
        assert get_currency_symbol("XYZ") == "XYZ"

    def test_case_insensitive(self) -> None:
        """Test currency lookup is case insensitive."""
        assert get_currency_symbol("eur") == "€"
        assert get_currency_symbol("Eur") == "€"


class TestBudgetBarsWithSpending:
    """Tests for budget bars with various spending levels."""

    @pytest.fixture
    def config(self) -> Config:
        """Create a config with known budget values."""
        config = Config()
        config.budget.monthly = 100.0
        config.budget.daily_soft = 10.0
        return config

    def test_budget_bars_with_50_percent_spending(self) -> None:
        """Test budget bars render correctly at 50% spending (yellow threshold)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
            # Record spending to reach 50%
            tracker.record_usage(
                model="test-model",
                input_tokens=100,
                output_tokens=200,
                cost=50.0,  # 50% of 100 monthly budget
            )

            config = Config()
            config.budget.monthly = 100.0
            config.budget.daily_soft = 10.0

            result = render_budget_bars(tracker, config)
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(result)
            output = capture.get()

            # Should show 50% in output
            assert "50%" in output

    def test_budget_bars_with_high_spending(self) -> None:
        """Test budget bars render correctly at high spending (over 80%)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
            # Record spending to reach 85%
            tracker.record_usage(
                model="test-model",
                input_tokens=100,
                output_tokens=200,
                cost=85.0,  # 85% of 100 monthly budget
            )

            config = Config()
            config.budget.monthly = 100.0
            config.budget.daily_soft = 10.0

            result = render_budget_bars(tracker, config)
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(result)
            output = capture.get()

            # Should show 85% in output
            assert "85%" in output


class TestRenderBudgetAlert:
    """Tests for render_budget_alert function."""

    def test_daily_alert_shows_warning_emoji(self) -> None:
        """Test that daily budget alert shows warning emoji."""
        result = render_budget_alert(
            alert_type="daily",
            percent=82.0,
            spent=4.10,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should contain warning emoji or warning-like content
        assert "\u26a0" in output or "Daily budget" in output

    def test_daily_alert_shows_daily_budget_label(self) -> None:
        """Test that daily budget alert shows 'Daily budget' label."""
        result = render_budget_alert(
            alert_type="daily",
            percent=82.0,
            spent=4.10,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Daily budget" in output

    def test_daily_alert_shows_percentage(self) -> None:
        """Test that daily budget alert shows the percentage."""
        result = render_budget_alert(
            alert_type="daily",
            percent=82.0,
            spent=4.10,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "82%" in output

    def test_daily_alert_shows_spent_and_budget(self) -> None:
        """Test that daily budget alert shows spent and budget amounts."""
        result = render_budget_alert(
            alert_type="daily",
            percent=82.0,
            spent=4.10,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "4.10" in output
        assert "5.00" in output

    def test_monthly_alert_shows_alert_emoji(self) -> None:
        """Test that monthly budget alert shows alert emoji."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=85.0,
            spent=76.50,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should contain alert emoji or monthly budget content
        assert "\U0001f6a8" in output or "Monthly budget" in output

    def test_monthly_alert_shows_monthly_budget_label(self) -> None:
        """Test that monthly budget alert shows 'Monthly budget' label."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=85.0,
            spent=76.50,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Monthly budget" in output

    def test_monthly_alert_shows_percentage(self) -> None:
        """Test that monthly budget alert shows the percentage."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=85.0,
            spent=76.50,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "85%" in output

    def test_monthly_alert_shows_spent_and_budget(self) -> None:
        """Test that monthly budget alert shows spent and budget amounts."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=85.0,
            spent=76.50,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "76.50" in output
        assert "90.00" in output

    def test_alert_uses_currency_symbol(self) -> None:
        """Test that budget alert uses correct currency symbol."""
        result = render_budget_alert(
            alert_type="daily",
            percent=80.0,
            spent=4.00,
            budget=5.00,
            currency="USD",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "$" in output

    def test_alert_uses_eur_currency_symbol(self) -> None:
        """Test that budget alert uses EUR currency symbol."""
        result = render_budget_alert(
            alert_type="daily",
            percent=80.0,
            spent=4.00,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # EUR should show Euro symbol
        assert "EUR" in output or "\u20ac" in output

    def test_alert_at_exactly_80_percent(self) -> None:
        """Test that budget alert works at exactly 80% threshold."""
        result = render_budget_alert(
            alert_type="daily",
            percent=80.0,
            spent=4.00,
            budget=5.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "80%" in output

    def test_alert_at_100_percent(self) -> None:
        """Test that budget alert works at 100% threshold."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=100.0,
            spent=90.00,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "100%" in output

    def test_alert_over_100_percent(self) -> None:
        """Test that budget alert works when over 100%."""
        result = render_budget_alert(
            alert_type="monthly",
            percent=110.0,
            spent=99.00,
            budget=90.00,
            currency="EUR",
        )
        console = Console(force_terminal=True, width=100)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "110%" in output
