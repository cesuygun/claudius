# ABOUTME: Tests for slash command handler in the Claudius REPL
# ABOUTME: Covers all slash commands including /status, /config, /logs, /models, model overrides, /help, and /quit

"""Tests for Claudius command handler."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.commands import CommandHandler, CommandResult
from claudius.config import Config


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_default_values(self) -> None:
        """Test CommandResult has correct default values."""
        result = CommandResult()
        assert result.output is None
        assert result.should_exit is False
        assert result.model_override is None

    def test_custom_values(self) -> None:
        """Test CommandResult accepts custom values."""
        result = CommandResult(
            output="Test output",
            should_exit=True,
            model_override="opus",
        )
        assert result.output == "Test output"
        assert result.should_exit is True
        assert result.model_override == "opus"


class TestCommandHandlerBasics:
    """Tests for basic CommandHandler functionality."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def config(self) -> Config:
        """Create a default config."""
        return Config()

    @pytest.fixture
    def console(self) -> Console:
        """Create a Rich console."""
        return Console(force_terminal=True, width=100)

    @pytest.fixture
    def handler(
        self, tracker: BudgetTracker, config: Config, console: Console
    ) -> CommandHandler:
        """Create a CommandHandler instance."""
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_non_command_returns_none(self, handler: CommandHandler) -> None:
        """Test that non-command input returns None."""
        result = handler.handle("hello world")
        assert result is None

    def test_empty_input_returns_none(self, handler: CommandHandler) -> None:
        """Test that empty input returns None."""
        result = handler.handle("")
        assert result is None

    def test_slash_without_command_returns_unknown(self, handler: CommandHandler) -> None:
        """Test that just '/' returns unknown command result."""
        result = handler.handle("/")
        assert result is not None
        assert "Unknown command" in (result.output or "")

    def test_unknown_command_returns_error(self, handler: CommandHandler) -> None:
        """Test that unknown command returns error message."""
        result = handler.handle("/foobar")
        assert result is not None
        assert "Unknown command" in (result.output or "")
        assert "/foobar" in (result.output or "")
        assert "/help" in (result.output or "")

    def test_commands_are_case_insensitive(self, handler: CommandHandler) -> None:
        """Test that commands are case insensitive."""
        result_lower = handler.handle("/quit")
        result_upper = handler.handle("/QUIT")
        result_mixed = handler.handle("/QuIt")

        assert result_lower is not None
        assert result_upper is not None
        assert result_mixed is not None
        assert result_lower.should_exit is True
        assert result_upper.should_exit is True
        assert result_mixed.should_exit is True


class TestQuitCommand:
    """Tests for /quit command."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_quit_sets_should_exit(self, handler: CommandHandler) -> None:
        """Test /quit returns result with should_exit=True."""
        result = handler.handle("/quit")
        assert result is not None
        assert result.should_exit is True


class TestStatusCommand:
    """Tests for /status command."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def handler(self, tracker: BudgetTracker) -> CommandHandler:
        """Create a CommandHandler instance."""
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_status_returns_budget_info(self, handler: CommandHandler) -> None:
        """Test /status returns budget status information."""
        result = handler.handle("/status")
        assert result is not None
        assert result.output is not None
        # Should contain budget status tree (from render_status)
        assert "Budget Status" in result.output

    def test_status_shows_monthly_info(self, handler: CommandHandler) -> None:
        """Test /status shows monthly budget information."""
        result = handler.handle("/status")
        assert result is not None
        assert result.output is not None
        assert "Monthly" in result.output

    def test_status_shows_daily_info(self, handler: CommandHandler) -> None:
        """Test /status shows daily budget information."""
        result = handler.handle("/status")
        assert result is not None
        assert result.output is not None
        assert "Today" in result.output


class TestConfigCommand:
    """Tests for /config command."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    @patch("subprocess.run")
    def test_config_opens_editor(
        self, mock_run: MagicMock, handler: CommandHandler
    ) -> None:
        """Test /config opens config file in editor."""
        result = handler.handle("/config")
        assert result is not None
        # Should have called subprocess.run with editor
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        # First arg should be editor, second should be config path
        assert len(call_args) == 2
        assert "config.toml" in str(call_args[1])

    @patch("subprocess.run")
    @patch.dict("os.environ", {"EDITOR": "vim"})
    def test_config_uses_editor_env(
        self, mock_run: MagicMock, handler: CommandHandler
    ) -> None:
        """Test /config uses EDITOR environment variable."""
        handler.handle("/config")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "vim"

    @patch("subprocess.run")
    @patch.dict("os.environ", {}, clear=True)
    def test_config_defaults_to_nano(
        self, mock_run: MagicMock, handler: CommandHandler
    ) -> None:
        """Test /config defaults to nano when EDITOR not set."""
        # Ensure EDITOR is not in environment
        import os
        os.environ.pop("EDITOR", None)
        handler.handle("/config")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "nano"


class TestLogsCommand:
    """Tests for /logs command."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    @pytest.fixture
    def handler(self, tracker: BudgetTracker) -> CommandHandler:
        """Create a CommandHandler instance."""
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_logs_returns_output(self, handler: CommandHandler) -> None:
        """Test /logs returns some output."""
        result = handler.handle("/logs")
        assert result is not None
        assert result.output is not None

    def test_logs_shows_no_usage_when_empty(self, handler: CommandHandler) -> None:
        """Test /logs shows appropriate message when no usage."""
        result = handler.handle("/logs")
        assert result is not None
        assert result.output is not None
        # Should indicate no usage or empty history
        assert "No" in result.output or "empty" in result.output.lower() or "usage" in result.output.lower()

    def test_logs_shows_recent_usage(self, tracker: BudgetTracker) -> None:
        """Test /logs shows recent usage history."""
        # Record some usage
        tracker.record_usage(
            model="claude-3-5-haiku-20241022",
            input_tokens=100,
            output_tokens=200,
            cost=0.001,
            routed_by="heuristic",
            query_preview="Test query",
        )

        config = Config()
        console = Console(force_terminal=True, width=100)
        handler = CommandHandler(tracker=tracker, config=config, console=console)

        result = handler.handle("/logs")
        assert result is not None
        assert result.output is not None
        # Should contain model name or cost info
        assert "haiku" in result.output.lower() or "0.001" in result.output


class TestModelsCommand:
    """Tests for /models command."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_models_command_returns_result(self, handler: CommandHandler) -> None:
        """Test /models returns a CommandResult with output."""
        result = handler.handle("/models")
        assert result is not None
        assert result.output is not None

    def test_models_command_shows_all_models(self, handler: CommandHandler) -> None:
        """Test /models shows all available models."""
        result = handler.handle("/models")
        assert result is not None
        assert result.output is not None
        assert "haiku" in result.output.lower()
        assert "sonnet" in result.output.lower()
        assert "opus" in result.output.lower()

    def test_models_command_shows_pricing(self, handler: CommandHandler) -> None:
        """Test /models shows pricing information."""
        result = handler.handle("/models")
        assert result is not None
        assert result.output is not None
        assert "€" in result.output
        assert "per 1M" in result.output

    def test_models_command_shows_table_format(self, handler: CommandHandler) -> None:
        """Test /models shows output in table format."""
        result = handler.handle("/models")
        assert result is not None
        assert result.output is not None
        # Should have table separators
        assert "|" in result.output
        assert "Input" in result.output
        assert "Output" in result.output

    def test_models_command_shows_usage_hint(self, handler: CommandHandler) -> None:
        """Test /models shows hint about how to force models."""
        result = handler.handle("/models")
        assert result is not None
        assert result.output is not None
        assert "/haiku" in result.output
        assert "/sonnet" in result.output
        assert "/opus" in result.output


class TestModelOverrideCommands:
    """Tests for /opus, /sonnet, /haiku, and /auto commands."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_opus_sets_model_override(self, handler: CommandHandler) -> None:
        """Test /opus sets model_override to 'opus'."""
        result = handler.handle("/opus")
        assert result is not None
        assert result.model_override == "opus"
        assert handler.current_model_override == "opus"

    def test_opus_returns_confirmation(self, handler: CommandHandler) -> None:
        """Test /opus returns confirmation message."""
        result = handler.handle("/opus")
        assert result is not None
        assert result.output is not None
        assert "Opus" in result.output or "opus" in result.output.lower()
        assert "Forcing" in result.output or "forcing" in result.output.lower()

    def test_sonnet_sets_model_override(self, handler: CommandHandler) -> None:
        """Test /sonnet sets model_override to 'sonnet'."""
        result = handler.handle("/sonnet")
        assert result is not None
        assert result.model_override == "sonnet"
        assert handler.current_model_override == "sonnet"

    def test_sonnet_returns_confirmation(self, handler: CommandHandler) -> None:
        """Test /sonnet returns confirmation message."""
        result = handler.handle("/sonnet")
        assert result is not None
        assert result.output is not None
        assert "Sonnet" in result.output or "sonnet" in result.output.lower()

    def test_haiku_sets_model_override(self, handler: CommandHandler) -> None:
        """Test /haiku sets model_override to 'haiku'."""
        result = handler.handle("/haiku")
        assert result is not None
        assert result.model_override == "haiku"
        assert handler.current_model_override == "haiku"

    def test_haiku_returns_confirmation(self, handler: CommandHandler) -> None:
        """Test /haiku returns confirmation message."""
        result = handler.handle("/haiku")
        assert result is not None
        assert result.output is not None
        assert "Haiku" in result.output or "haiku" in result.output.lower()

    def test_auto_clears_model_override(self, handler: CommandHandler) -> None:
        """Test /auto clears model_override."""
        # First set an override
        handler.handle("/opus")
        assert handler.current_model_override == "opus"

        # Then clear it
        result = handler.handle("/auto")
        assert result is not None
        assert result.model_override is None
        assert handler.current_model_override is None

    def test_auto_returns_confirmation(self, handler: CommandHandler) -> None:
        """Test /auto returns confirmation message."""
        result = handler.handle("/auto")
        assert result is not None
        assert result.output is not None
        assert "auto" in result.output.lower() or "automatic" in result.output.lower()


class TestHelpCommand:
    """Tests for /help command."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_help_returns_output(self, handler: CommandHandler) -> None:
        """Test /help returns output."""
        result = handler.handle("/help")
        assert result is not None
        assert result.output is not None

    def test_help_lists_all_commands(self, handler: CommandHandler) -> None:
        """Test /help lists all available commands."""
        result = handler.handle("/help")
        assert result is not None
        assert result.output is not None

        # Should list all commands
        commands = ["/status", "/config", "/logs", "/models", "/opus", "/sonnet", "/haiku", "/auto", "/help", "/quit"]
        for cmd in commands:
            assert cmd in result.output, f"Expected {cmd} in help output"

    def test_help_shows_descriptions(self, handler: CommandHandler) -> None:
        """Test /help shows command descriptions."""
        result = handler.handle("/help")
        assert result is not None
        assert result.output is not None

        # Should have descriptive text
        assert "budget" in result.output.lower() or "status" in result.output.lower()
        assert "exit" in result.output.lower() or "quit" in result.output.lower()


class TestCommandHandlerModelOverrideState:
    """Tests for CommandHandler model override state management."""

    @pytest.fixture
    def handler(self) -> CommandHandler:
        """Create a CommandHandler instance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
        config = Config()
        console = Console(force_terminal=True, width=100)
        return CommandHandler(tracker=tracker, config=config, console=console)

    def test_initial_model_override_is_none(self, handler: CommandHandler) -> None:
        """Test initial model override is None."""
        assert handler.current_model_override is None

    def test_model_override_persists(self, handler: CommandHandler) -> None:
        """Test model override persists after being set."""
        handler.handle("/opus")
        assert handler.current_model_override == "opus"

        # Process a non-command (simulating chat)
        result = handler.handle("hello")
        assert result is None
        # Override should still be set
        assert handler.current_model_override == "opus"

    def test_model_override_can_be_changed(self, handler: CommandHandler) -> None:
        """Test model override can be changed from one model to another."""
        handler.handle("/opus")
        assert handler.current_model_override == "opus"

        handler.handle("/sonnet")
        assert handler.current_model_override == "sonnet"

        handler.handle("/haiku")
        assert handler.current_model_override == "haiku"

    def test_auto_clears_any_override(self, handler: CommandHandler) -> None:
        """Test /auto clears any model override."""
        for model_cmd in ["/opus", "/sonnet", "/haiku"]:
            handler.handle(model_cmd)
            assert handler.current_model_override is not None

            handler.handle("/auto")
            assert handler.current_model_override is None
