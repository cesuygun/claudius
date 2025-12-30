# ABOUTME: Tests for the main CLI entry point that starts REPL and proxy
# ABOUTME: Covers API key resolution, proxy startup, and error handling

"""Tests for Claudius main CLI entry point."""

import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claudius.config import Config


class TestRunProxyServer:
    """Tests for the run_proxy_server function."""

    def test_run_proxy_server_calls_uvicorn(self) -> None:
        """Test that run_proxy_server calls uvicorn with correct args."""
        from claudius.cli import run_proxy_server

        with patch("claudius.cli.uvicorn") as mock_uvicorn:
            # Run in thread and stop it immediately
            thread = threading.Thread(
                target=run_proxy_server,
                args=("127.0.0.1", 4000),
                daemon=True,
            )
            thread.start()
            # Give it a moment to call uvicorn
            time.sleep(0.1)

            mock_uvicorn.run.assert_called_once()
            call_kwargs = mock_uvicorn.run.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"
            assert call_kwargs["port"] == 4000
            assert call_kwargs["log_level"] == "error"


class TestCheckPortAvailable:
    """Tests for port availability checking."""

    def test_check_port_available_returns_true_for_free_port(self) -> None:
        """Test that available port returns True."""
        from claudius.cli import check_port_available

        # Use a random high port that's unlikely to be in use
        result = check_port_available("127.0.0.1", 59999)
        assert result is True

    def test_check_port_available_returns_false_for_used_port(self) -> None:
        """Test that port in use returns False."""
        from claudius.cli import check_port_available

        # Bind to a port to make it unavailable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 59998))
        sock.listen(1)

        try:
            result = check_port_available("127.0.0.1", 59998)
            assert result is False
        finally:
            sock.close()


class TestResolveApiKey:
    """Tests for API key resolution."""

    def test_resolve_api_key_from_config(self) -> None:
        """Test that API key is resolved from config."""
        from claudius.cli import resolve_api_key

        config = Config()
        config.api.key = "sk-config-key"

        with patch.dict("os.environ", {}, clear=True):
            result = resolve_api_key(config)

        assert result == "sk-config-key"

    def test_resolve_api_key_from_env_var(self) -> None:
        """Test that API key is resolved from environment."""
        from claudius.cli import resolve_api_key

        config = Config()
        config.api.key = ""

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env-key"}):
            result = resolve_api_key(config)

        assert result == "sk-env-key"

    def test_resolve_api_key_config_takes_precedence(self) -> None:
        """Test that config API key takes precedence over env var."""
        from claudius.cli import resolve_api_key

        config = Config()
        config.api.key = "sk-config-key"

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env-key"}):
            result = resolve_api_key(config)

        assert result == "sk-config-key"

    def test_resolve_api_key_returns_none_when_not_found(self) -> None:
        """Test that None is returned when no API key found."""
        from claudius.cli import resolve_api_key

        config = Config()
        config.api.key = ""

        with patch.dict("os.environ", {}, clear=True):
            # Clear any existing ANTHROPIC_API_KEY
            import os
            env_copy = dict(os.environ)
            env_copy.pop("ANTHROPIC_API_KEY", None)
            with patch.dict("os.environ", env_copy, clear=True):
                result = resolve_api_key(config)

        assert result is None


class TestMainCommand:
    """Tests for the main CLI command."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return Path(f.name)

    def test_main_shows_error_when_no_api_key(self) -> None:
        """Test that main shows error when no API key is found."""
        from claudius.cli import main

        with patch("claudius.cli.Config") as mock_config_class, \
             patch("claudius.cli.console") as mock_console, \
             patch.dict("os.environ", {}, clear=True):

            mock_config = mock_config_class.load.return_value
            mock_config.api.key = ""

            # Clear any existing ANTHROPIC_API_KEY
            import os
            env_copy = dict(os.environ)
            env_copy.pop("ANTHROPIC_API_KEY", None)
            with patch.dict("os.environ", env_copy, clear=True):
                main([])

            # Should print error message about API key
            mock_console.print.assert_called()
            call_args = str(mock_console.print.call_args_list)
            assert "API key" in call_args or "ANTHROPIC_API_KEY" in call_args

    def test_main_shows_error_when_port_in_use(self) -> None:
        """Test that main shows error when port is already in use."""
        from claudius.cli import main

        # Bind to the port to make it unavailable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 4000))
        sock.listen(1)

        try:
            with patch("claudius.cli.Config") as mock_config_class, \
                 patch("claudius.cli.console") as mock_console:

                mock_config = mock_config_class.load.return_value
                mock_config.api.key = "sk-test-key"
                mock_config.proxy.host = "127.0.0.1"
                mock_config.proxy.port = 4000

                main([])

                # Should print error message about port
                mock_console.print.assert_called()
                call_args = str(mock_console.print.call_args_list)
                assert "4000" in call_args or "port" in call_args.lower()
        finally:
            sock.close()

    def test_main_starts_proxy_and_repl(self, temp_db: Path) -> None:
        """Test that main starts proxy server and REPL."""
        from claudius.cli import main
        from claudius.config import RateLimitConfig

        with patch("claudius.cli.Config") as mock_config_class, \
             patch("claudius.cli.BudgetTracker") as mock_tracker_class, \
             patch("claudius.cli.ClaudiusREPL") as mock_repl_class, \
             patch("claudius.cli.run_proxy_server"), \
             patch("claudius.cli.check_port_available", return_value=True), \
             patch("claudius.cli.set_rate_limit_config"), \
             patch("claudius.cli.set_api_config"), \
             patch("claudius.cli.set_budget_tracker"), \
             patch("claudius.cli.threading") as mock_threading, \
             patch("claudius.cli.asyncio") as mock_asyncio, \
             patch("claudius.cli.time"):

            mock_config = mock_config_class.load.return_value
            mock_config.api.key = "sk-test-key"
            mock_config.proxy.host = "127.0.0.1"
            mock_config.proxy.port = 4000
            mock_config.rate_limit = RateLimitConfig()

            mock_tracker = mock_tracker_class.return_value

            # Configure threading mock
            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            main([])

            # Verify proxy thread was started
            mock_threading.Thread.assert_called_once()
            thread_kwargs = mock_threading.Thread.call_args[1]
            assert thread_kwargs["daemon"] is True
            mock_thread.start.assert_called_once()

            # Verify REPL was created and run
            mock_repl_class.assert_called_once_with(
                mock_tracker,
                mock_config,
                "sk-test-key",
            )
            mock_asyncio.run.assert_called_once()

    def test_main_configures_proxy_with_rate_limit_and_api_config(self) -> None:
        """Test that main configures proxy with rate limit and API config."""
        from claudius.cli import main
        from claudius.config import ApiConfig, RateLimitConfig

        rate_limit_config = RateLimitConfig()
        api_config = ApiConfig(key="sk-test-key")

        with patch("claudius.cli.Config") as mock_config_class, \
             patch("claudius.cli.BudgetTracker"), \
             patch("claudius.cli.ClaudiusREPL"), \
             patch("claudius.cli.set_rate_limit_config") as mock_set_rate_limit, \
             patch("claudius.cli.set_api_config") as mock_set_api_config, \
             patch("claudius.cli.set_budget_tracker") as mock_set_budget_tracker, \
             patch("claudius.cli.check_port_available", return_value=True), \
             patch("claudius.cli.threading") as mock_threading, \
             patch("claudius.cli.asyncio"), \
             patch("claudius.cli.time"):

            mock_config = mock_config_class.load.return_value
            mock_config.api = api_config
            mock_config.proxy.host = "127.0.0.1"
            mock_config.proxy.port = 4000
            mock_config.rate_limit = rate_limit_config

            mock_thread = MagicMock()
            mock_threading.Thread.return_value = mock_thread

            main([])

            # Verify proxy was configured
            mock_set_rate_limit.assert_called_once_with(rate_limit_config)
            mock_set_api_config.assert_called_once_with(api_config)
            mock_set_budget_tracker.assert_called_once()


class TestStatusLineCommand:
    """Tests for the status-line subcommand integration."""

    def test_status_line_still_works(self) -> None:
        """Test that status-line subcommand still works."""
        from claudius.cli import main

        with patch("claudius.cli.status_line_command") as mock_status_line:
            main(["status-line"])

            mock_status_line.assert_called_once()

    def test_main_dispatches_to_status_line(self) -> None:
        """Test that main dispatches to status_line_command."""
        from claudius.cli import main

        with patch("claudius.cli.status_line_command") as mock_status_line:
            main(["status-line"])

            mock_status_line.assert_called_once()


class TestMainHelp:
    """Tests for main command help."""

    def test_main_with_help_flag(self) -> None:
        """Test that main handles --help flag."""
        from claudius.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])

        # argparse exits with 0 for --help
        assert exc_info.value.code == 0
