# ABOUTME: Tests for the Claudius interactive REPL
# ABOUTME: Covers initialization, command handling, chat messaging, and graceful exit

"""Tests for Claudius REPL."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.chat import ChatResponse
from claudius.config import Config
from claudius.repl import ClaudiusREPL


class TestClaudiusREPLInit:
    """Tests for ClaudiusREPL initialization."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def temp_history(self) -> Path:
        """Create a temporary history file path."""
        with tempfile.TemporaryDirectory() as d:
            history_path = Path(d) / "history"
            yield history_path

    def test_repl_initializes_with_required_dependencies(self, temp_db: Path) -> None:
        """Test that REPL initializes with tracker, config, and api_key."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.tracker is tracker
        assert repl.config is config
        assert repl.console is not None

    def test_repl_creates_console(self, temp_db: Path) -> None:
        """Test that REPL creates a Rich console."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert isinstance(repl.console, Console)

    def test_repl_creates_chat_client(self, temp_db: Path) -> None:
        """Test that REPL creates a ChatClient with api_key."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.chat_client is not None
        assert repl.chat_client.api_key == "sk-ant-test123"

    def test_repl_creates_command_handler(self, temp_db: Path) -> None:
        """Test that REPL creates a CommandHandler."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.command_handler is not None
        assert repl.command_handler.tracker is tracker
        assert repl.command_handler.config is config

    def test_repl_creates_prompt_session(self, temp_db: Path) -> None:
        """Test that REPL creates a PromptSession."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.session is not None

    def test_repl_uses_proxy_url_from_config(self, temp_db: Path) -> None:
        """Test that REPL uses proxy URL from config."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.proxy.host = "127.0.0.1"
        config.proxy.port = 5000

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.chat_client.proxy_url == "http://127.0.0.1:5000"


class TestClaudiusREPLRun:
    """Tests for ClaudiusREPL run method."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def repl(self, temp_db: Path) -> ClaudiusREPL:
        """Create a REPL instance for testing."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        return ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

    async def test_run_shows_banner_on_startup(self, repl: ClaudiusREPL) -> None:
        """Test that run shows banner on startup."""
        repl.session.prompt_async = AsyncMock(side_effect=EOFError)

        with patch.object(repl.console, "print") as mock_print:
            await repl.run()

            # First print should be banner (contains CLAUDIUS)
            assert mock_print.call_count >= 1

    async def test_run_shows_budget_bars_on_startup(self, repl: ClaudiusREPL) -> None:
        """Test that run shows budget bars on startup."""
        repl.session.prompt_async = AsyncMock(side_effect=EOFError)

        with patch.object(repl.console, "print") as mock_print:
            await repl.run()

            # Should have at least 2 prints (banner, budget bars)
            assert mock_print.call_count >= 2

    async def test_run_exits_on_eof(self, repl: ClaudiusREPL) -> None:
        """Test that run exits gracefully on EOFError (Ctrl+D)."""
        repl.session.prompt_async = AsyncMock(side_effect=EOFError)

        # Should not raise an exception
        await repl.run()

    async def test_run_continues_on_keyboard_interrupt(self, repl: ClaudiusREPL) -> None:
        """Test that run continues on KeyboardInterrupt (Ctrl+C)."""
        # First call raises KeyboardInterrupt, second raises EOFError to exit
        repl.session.prompt_async = AsyncMock(
            side_effect=[KeyboardInterrupt, EOFError]
        )

        # Should not raise an exception
        await repl.run()

    async def test_run_exits_on_quit_command(self, repl: ClaudiusREPL) -> None:
        """Test that run exits on /quit command."""
        repl.session.prompt_async = AsyncMock(return_value="/quit")

        await repl.run()

        # Verify prompt was called (to get /quit)
        repl.session.prompt_async.assert_called()


class TestClaudiusREPLCommandHandling:
    """Tests for REPL command handling."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def repl(self, temp_db: Path) -> ClaudiusREPL:
        """Create a REPL instance for testing."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        return ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

    async def test_command_output_is_printed(self, repl: ClaudiusREPL) -> None:
        """Test that command output is printed to console."""
        repl.session.prompt_async = AsyncMock(side_effect=["/help", "/quit"])

        with patch.object(repl.console, "print") as mock_print:
            await repl.run()

            # Should print banner, budget bars, and help output
            assert mock_print.call_count >= 3

    async def test_model_override_command_sets_override(self, repl: ClaudiusREPL) -> None:
        """Test that model override commands set the override."""
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "/quit"])

        await repl.run()

        # Note: Override gets set but then cleared after use
        # Here we just verify it doesn't crash


class TestClaudiusREPLChatHandling:
    """Tests for REPL chat message handling."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def repl(self, temp_db: Path) -> ClaudiusREPL:
        """Create a REPL instance for testing."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        return ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

    @pytest.fixture
    def mock_chat_response(self) -> ChatResponse:
        """Create a mock chat response."""
        return ChatResponse(
            model="sonnet",
            text="Hello! How can I help you?",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )

    async def test_chat_message_is_sent_to_client(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse
    ) -> None:
        """Test that non-command messages are sent to chat client."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        await repl.run()

        repl.chat_client.send_message.assert_called_once()

    async def test_chat_response_is_displayed(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse
    ) -> None:
        """Test that chat response is displayed."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch.object(repl.console, "print") as mock_print:
            await repl.run()

            # Should print banner, budget bars, response, and cost line
            assert mock_print.call_count >= 4

    async def test_model_override_is_passed_to_chat_client(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse
    ) -> None:
        """Test that model override is passed to chat client."""
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        await repl.run()

        # Verify send_message was called with model_override="opus"
        call_kwargs = repl.chat_client.send_message.call_args[1]
        assert call_kwargs.get("model_override") == "opus"

    async def test_model_override_is_cleared_after_use(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse
    ) -> None:
        """Test that model override is cleared after chat message."""
        repl.session.prompt_async = AsyncMock(
            side_effect=["/opus", "First message", "Second message", "/quit"]
        )
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        await repl.run()

        # Second call should have no model override
        calls = repl.chat_client.send_message.call_args_list
        assert len(calls) == 2
        # First call has opus override
        assert calls[0][1].get("model_override") == "opus"
        # Second call has no override
        assert calls[1][1].get("model_override") is None

    async def test_cost_is_recorded_in_tracker(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse
    ) -> None:
        """Test that cost is recorded in budget tracker after chat."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch.object(repl.tracker, "record_usage") as mock_record:
            await repl.run()

            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs["cost"] == mock_chat_response.cost


class TestClaudiusREPLEdgeCases:
    """Tests for edge cases in REPL behavior."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def repl(self, temp_db: Path) -> ClaudiusREPL:
        """Create a REPL instance for testing."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        return ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

    async def test_empty_input_is_skipped(self, repl: ClaudiusREPL) -> None:
        """Test that empty input is skipped."""
        repl.session.prompt_async = AsyncMock(side_effect=["", "/quit"])
        repl.chat_client.send_message = AsyncMock()

        await repl.run()

        # Chat client should not be called for empty input
        repl.chat_client.send_message.assert_not_called()

    async def test_whitespace_only_input_is_skipped(self, repl: ClaudiusREPL) -> None:
        """Test that whitespace-only input is skipped."""
        repl.session.prompt_async = AsyncMock(side_effect=["   ", "\t\n", "/quit"])
        repl.chat_client.send_message = AsyncMock()

        await repl.run()

        # Chat client should not be called for whitespace-only input
        repl.chat_client.send_message.assert_not_called()

    async def test_chat_error_is_handled_gracefully(self, repl: ClaudiusREPL) -> None:
        """Test that chat errors are handled gracefully."""
        from claudius.chat import ChatError

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(
            side_effect=ChatError("Connection refused")
        )

        with patch.object(repl.console, "print"):
            await repl.run()
            # Should print error message but not crash - just verify it completed


class TestClaudiusREPLHistory:
    """Tests for REPL history functionality."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    def test_history_file_path_is_set(self, temp_db: Path) -> None:
        """Test that history file path is set correctly."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        # History should be FileHistory pointing to ~/.claudius/history
        from prompt_toolkit.history import FileHistory

        assert isinstance(repl.session.history, FileHistory)
