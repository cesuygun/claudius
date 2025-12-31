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
from claudius.estimation import EstimationResult
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
        """Create a REPL instance for testing with confirmation skipped."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        return repl

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

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

    async def test_chat_message_is_sent_to_client(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that non-command messages are sent to chat client."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        repl.chat_client.send_message.assert_called_once()

    async def test_chat_response_is_displayed(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that chat response is displayed."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print") as mock_print:
                await repl.run()

                # Should print banner, budget bars, cost estimate, response, and cost line
                assert mock_print.call_count >= 5

    async def test_model_override_is_passed_to_chat_client(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that model override is passed to chat client."""
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Verify send_message was called with model_override="opus"
        call_kwargs = repl.chat_client.send_message.call_args[1]
        assert call_kwargs.get("model_override") == "opus"

    async def test_model_override_is_cleared_after_use(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that model override is cleared after chat message."""
        repl.session.prompt_async = AsyncMock(
            side_effect=["/opus", "First message", "Second message", "/quit"]
        )
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Second call should have no model override
        calls = repl.chat_client.send_message.call_args_list
        assert len(calls) == 2
        # First call has opus override
        assert calls[0][1].get("model_override") == "opus"
        # Second call has no override
        assert calls[1][1].get("model_override") is None

    async def test_cost_is_recorded_in_tracker(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost is recorded in budget tracker after chat."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
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
        """Create a REPL instance for testing with confirmation skipped."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        return repl

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

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

    async def test_chat_error_is_handled_gracefully(
        self, repl: ClaudiusREPL, mock_estimation: EstimationResult
    ) -> None:
        """Test that chat errors are handled gracefully."""
        from claudius.chat import ChatError

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(
            side_effect=ChatError("Connection refused")
        )

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
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


class TestClaudiusREPLCostEstimation:
    """Tests for REPL cost estimation display."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def repl(self, temp_db: Path) -> ClaudiusREPL:
        """Create a REPL instance for testing with confirmation skipped."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        return repl

    @pytest.fixture
    def mock_chat_response(self) -> ChatResponse:
        """Create a mock chat response."""
        return ChatResponse(
            model="haiku",
            text="Hello! How can I help you?",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

    async def test_cost_estimation_is_called_before_send(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation is called before sending message."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

            # estimate_cost should be called once for "Hello" message
            mock_estimate.assert_called_once()

    async def test_cost_estimation_shows_output(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation output is printed to console."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation

            with patch.object(repl.console, "print") as mock_print:
                await repl.run()

                # Should print: banner, budget bars, cost estimate, response, cost line
                assert mock_print.call_count >= 5

    async def test_cost_estimation_uses_correct_model(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation uses the routed model."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

            # Check that estimate_cost was called with the correct model
            call_kwargs = mock_estimate.call_args[1]
            # Short message "Hello" routes to haiku
            assert "haiku" in call_kwargs["model"].lower()

    async def test_cost_estimation_with_model_override(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation respects model override."""
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

            # Check that estimate_cost was called with opus model
            call_kwargs = mock_estimate.call_args[1]
            assert "opus" in call_kwargs["model"].lower()

    async def test_cost_estimation_includes_conversation_history(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation includes conversation history."""
        repl.session.prompt_async = AsyncMock(
            side_effect=["First message", "Second message", "/quit"]
        )

        # Create a side effect that updates conversation history like the real implementation
        async def send_with_history(message: str, **kwargs):  # noqa: ANN003, ARG001
            repl.chat_client.conversation.append({"role": "user", "content": message})
            repl.chat_client.conversation.append(
                {"role": "assistant", "content": mock_chat_response.text}
            )
            return mock_chat_response

        repl.chat_client.send_message = AsyncMock(side_effect=send_with_history)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

            # Second call should include first message in history
            calls = mock_estimate.call_args_list
            assert len(calls) == 2

            # Second call messages should be longer (includes history)
            second_call_messages = calls[1][1]["messages"]
            # Should have: user (first), assistant (response), user (second)
            assert len(second_call_messages) == 3

    async def test_cost_estimation_uses_api_key(
        self, repl: ClaudiusREPL, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that cost estimation uses the API key."""
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

            # Check that estimate_cost was called with the API key
            call_kwargs = mock_estimate.call_args[1]
            assert call_kwargs["api_key"] == "sk-ant-test123"

    async def test_repl_stores_api_key(self, temp_db: Path) -> None:
        """Test that REPL stores the API key for estimation."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        assert repl.api_key == "sk-ant-test123"


class TestClaudiusREPLBudgetAlerts:
    """Tests for REPL budget alert display."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

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

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

    async def test_daily_alert_shown_at_80_percent(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that daily budget alert is shown when daily spending reaches 80%."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        # Set daily budget to 10 and pre-spend 7.5 (75%), then chat adds 0.005 to reach ~75%
        config.budget.daily_soft = 10.0
        config.budget.monthly = 1000.0

        # Pre-record enough spending to push us over 80% after the chat
        # We need 8.0+ to be at 80%, so pre-spend 7.996 and chat adds 0.005 = 8.001
        tracker.record_usage(
            model="test-model",
            input_tokens=100,
            output_tokens=100,
            cost=7.996,
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        # Check that daily alert was printed
        all_output = "".join(printed_outputs)
        assert "Daily budget" in all_output

    async def test_monthly_alert_shown_at_80_percent(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that monthly budget alert is shown when monthly spending reaches 80%."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        # Set monthly budget to 100 and pre-spend enough to reach 80%
        config.budget.monthly = 100.0
        config.budget.daily_soft = 1000.0  # High daily to avoid daily alert

        # Pre-record spending to push us over 80%
        tracker.record_usage(
            model="test-model",
            input_tokens=100,
            output_tokens=100,
            cost=79.996,  # 79.996 + 0.005 = 80.001
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        # Check that monthly alert was printed
        all_output = "".join(printed_outputs)
        assert "Monthly budget" in all_output

    async def test_no_alert_under_80_percent(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that no budget alert is shown when spending is under 80%."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        # Set budgets high enough that we stay under 80%
        config.budget.monthly = 1000.0
        config.budget.daily_soft = 100.0

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        # Check that neither budget alert was printed (using keywords from alert rendering)
        all_output = "".join(printed_outputs)
        # The budget bars show "Monthly" and "Today", but alerts use "Daily budget" and "Monthly budget"
        assert "Daily budget at" not in all_output
        assert "Monthly budget at" not in all_output

    async def test_both_alerts_shown_when_both_exceed_threshold(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that both daily and monthly alerts are shown when both exceed 80%."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        # Set both budgets low enough that we exceed 80%
        config.budget.monthly = 100.0
        config.budget.daily_soft = 10.0

        # Pre-record spending to push both over 80%
        tracker.record_usage(
            model="test-model",
            input_tokens=100,
            output_tokens=100,
            cost=79.996,  # 79.996 + 0.005 = 80.001% of monthly
        )
        # Also record more to push daily over
        tracker.record_usage(
            model="test-model",
            input_tokens=100,
            output_tokens=100,
            cost=7.999,  # Additional to push daily: 79.996 + 7.999 + 0.005 = 87.996 daily
        )

        # Now daily spent is 79.996 + 7.999 = 87.995, plus 0.005 = 88.0 (880% of daily)
        # Monthly spent is also 88.0 (88% of monthly)

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        # Check that both alerts were printed
        all_output = "".join(printed_outputs)
        assert "Daily budget" in all_output
        assert "Monthly budget" in all_output


class TestClaudiusREPLDailyHardLimit:
    """Tests for REPL daily hard limit enforcement."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def mock_chat_response(self) -> ChatResponse:
        """Create a mock chat response."""
        return ChatResponse(
            model="haiku",
            text="Hello! How can I help you?",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

    async def test_hard_limit_forces_haiku_model(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that exceeding daily hard limit forces Haiku model."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.budget.daily_hard = 10.0

        # Pre-record spending to exceed hard limit
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=15.0,
            routed_by="test",
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Verify send_message was called with haiku model override
        call_kwargs = repl.chat_client.send_message.call_args[1]
        assert call_kwargs.get("model_override") == "haiku"

    async def test_hard_limit_shows_warning_message(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that exceeding daily hard limit shows a warning message."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.budget.daily_hard = 10.0

        # Pre-record spending to exceed hard limit
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=15.0,
            routed_by="test",
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        all_output = "".join(printed_outputs)
        assert "Daily hard limit reached" in all_output or "hard limit" in all_output.lower()

    async def test_hard_limit_allows_manual_override(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that user can manually override to expensive model despite hard limit."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.budget.daily_hard = 10.0

        # Pre-record spending to exceed hard limit
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=15.0,
            routed_by="test",
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        # User explicitly requests opus with /opus command
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # User override should be respected
        call_kwargs = repl.chat_client.send_message.call_args[1]
        assert call_kwargs.get("model_override") == "opus"

    async def test_hard_limit_override_shows_warning(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that overriding hard limit with expensive model shows warning."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.budget.daily_hard = 10.0

        # Pre-record spending to exceed hard limit
        tracker.record_usage(
            model="sonnet",
            input_tokens=1000,
            output_tokens=1000,
            cost=15.0,
            routed_by="test",
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        # User explicitly requests opus
        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        all_output = "".join(printed_outputs)
        # Should warn that user is overriding despite hard limit
        assert "hard limit" in all_output.lower()
        assert "opus" in all_output.lower()

    async def test_no_hard_limit_enforcement_when_under_limit(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that no hard limit enforcement happens when under the limit."""
        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        config.budget.daily_hard = 10.0

        # Small spending - under the limit
        tracker.record_usage(
            model="haiku",
            input_tokens=100,
            output_tokens=100,
            cost=0.50,
            routed_by="test",
        )

        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True  # Skip confirmation dialog in tests
        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        printed_outputs: list[str] = []

        def capture_print(renderable: object) -> None:
            console = Console(force_terminal=True, width=100)
            with console.capture() as capture:
                console.print(renderable)
            printed_outputs.append(capture.get())

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            with patch.object(repl.console, "print", side_effect=capture_print):
                await repl.run()

        all_output = "".join(printed_outputs)
        # Should not see hard limit warning
        assert "hard limit" not in all_output.lower()


class TestClaudiusREPLConfirmationDialog:
    """Tests for REPL interactive confirmation dialog."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    @pytest.fixture
    def mock_chat_response(self) -> ChatResponse:
        """Create a mock chat response."""
        return ChatResponse(
            model="haiku",
            text="Hello! How can I help you?",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )

    @pytest.fixture
    def mock_estimation(self) -> EstimationResult:
        """Create a mock estimation result."""
        return EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.01,
            cost_max=0.05,
            model="claude-3-5-haiku-20241022",
            input_cost=0.005,
            output_cost_min=0.005,
            output_cost_max=0.045,
        )

    async def test_confirmation_dialog_send_proceeds(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that 'Send' action in confirmation dialog sends the message."""
        from claudius.repl import ConfirmationResult

        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        # Mock the confirmation dialog to return "send"
        mock_confirmation = AsyncMock(
            return_value=ConfirmationResult(action="send")
        )
        repl._show_confirmation_dialog = mock_confirmation

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Message should be sent
        repl.chat_client.send_message.assert_called_once()
        # Confirmation dialog should be called
        mock_confirmation.assert_called_once()

    async def test_confirmation_dialog_cancel_returns_to_prompt(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that 'Cancel' action in confirmation dialog returns to input without sending."""
        from claudius.repl import ConfirmationResult

        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        # Mock the confirmation dialog to return "cancel"
        mock_confirmation = AsyncMock(
            return_value=ConfirmationResult(action="cancel")
        )
        repl._show_confirmation_dialog = mock_confirmation

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Message should NOT be sent when cancelled
        repl.chat_client.send_message.assert_not_called()
        # Confirmation dialog should still be called
        mock_confirmation.assert_called_once()

    async def test_confirmation_dialog_change_model_updates_model(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that 'Change Model' action updates the model and re-estimates."""
        from claudius.repl import ConfirmationResult

        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        # First call returns "change" with opus, second call returns "send"
        mock_confirmation = AsyncMock(
            side_effect=[
                ConfirmationResult(action="change", model="opus"),
                ConfirmationResult(action="send"),
            ]
        )
        repl._show_confirmation_dialog = mock_confirmation

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # estimate_cost should be called twice - once for initial haiku, once for opus
        assert mock_estimate.call_count == 2
        # Second call should use opus model
        second_call_kwargs = mock_estimate.call_args_list[1][1]
        assert "opus" in second_call_kwargs["model"].lower()

        # Message should be sent with opus model override
        repl.chat_client.send_message.assert_called_once()
        call_kwargs = repl.chat_client.send_message.call_args[1]
        assert call_kwargs.get("model_override") == "opus"

    async def test_skip_confirmation_flag_bypasses_dialog(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that skip_confirmation=True bypasses the confirmation dialog."""
        from claudius.repl import ConfirmationResult

        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")
        repl.skip_confirmation = True

        # Set up mock that should NOT be called
        mock_confirmation = AsyncMock(
            return_value=ConfirmationResult(action="send")
        )
        repl._show_confirmation_dialog = mock_confirmation

        repl.session.prompt_async = AsyncMock(side_effect=["Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Message should be sent
        repl.chat_client.send_message.assert_called_once()
        # Confirmation dialog should NOT be called when skip_confirmation=True
        mock_confirmation.assert_not_called()

    async def test_confirmation_result_dataclass(self) -> None:
        """Test ConfirmationResult dataclass creation and fields."""
        from claudius.repl import ConfirmationResult

        # Test send action
        send_result = ConfirmationResult(action="send")
        assert send_result.action == "send"
        assert send_result.model is None

        # Test cancel action
        cancel_result = ConfirmationResult(action="cancel")
        assert cancel_result.action == "cancel"
        assert cancel_result.model is None

        # Test change action with model
        change_result = ConfirmationResult(action="change", model="opus")
        assert change_result.action == "change"
        assert change_result.model == "opus"

    async def test_model_override_cleared_on_cancel(
        self, temp_db: Path, mock_chat_response: ChatResponse, mock_estimation: EstimationResult
    ) -> None:
        """Test that model override is cleared when user cancels."""
        from claudius.repl import ConfirmationResult

        tracker = BudgetTracker(db_path=temp_db)
        config = Config()
        repl = ClaudiusREPL(tracker=tracker, config=config, api_key="sk-ant-test123")

        # Set model override via /opus command, then cancel at confirmation
        mock_confirmation = AsyncMock(
            return_value=ConfirmationResult(action="cancel")
        )
        repl._show_confirmation_dialog = mock_confirmation

        repl.session.prompt_async = AsyncMock(side_effect=["/opus", "Hello", "/quit"])
        repl.chat_client.send_message = AsyncMock(return_value=mock_chat_response)

        with patch("claudius.repl.estimate_cost", new_callable=AsyncMock) as mock_estimate:
            mock_estimate.return_value = mock_estimation
            await repl.run()

        # Model override should be cleared after cancel
        assert repl.command_handler.current_model_override is None
