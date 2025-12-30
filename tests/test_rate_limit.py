# ABOUTME: Tests for rate limit handling in the Claudius proxy
# ABOUTME: Covers exponential backoff retry logic for 429 responses

"""Tests for rate limit handling with exponential backoff."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from claudius.config import RateLimitConfig
from claudius.proxy import (
    create_app,
    get_rate_limit_config,
    set_rate_limit_config,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that RateLimitConfig has correct defaults."""
        config = RateLimitConfig()

        assert config.max_retries == 3
        assert config.initial_delay == 5
        assert config.backoff_multiplier == 3

    def test_custom_values(self) -> None:
        """Test that RateLimitConfig accepts custom values."""
        config = RateLimitConfig(
            max_retries=5,
            initial_delay=10,
            backoff_multiplier=2,
        )

        assert config.max_retries == 5
        assert config.initial_delay == 10
        assert config.backoff_multiplier == 2


class TestRateLimitConfigWiring:
    """Tests for rate limit config wiring from config file to proxy."""

    def test_set_rate_limit_config_updates_global(self) -> None:
        """Test that set_rate_limit_config updates the module-level config."""
        # Save original config for cleanup
        original_config = get_rate_limit_config()

        try:
            custom_config = RateLimitConfig(
                max_retries=7,
                initial_delay=20,
                backoff_multiplier=4,
            )
            set_rate_limit_config(custom_config)

            current_config = get_rate_limit_config()
            assert current_config.max_retries == 7
            assert current_config.initial_delay == 20
            assert current_config.backoff_multiplier == 4
        finally:
            # Restore original config
            set_rate_limit_config(original_config)

    def test_custom_config_used_in_retry_logic(self) -> None:
        """Test that custom config values are actually used in retry logic."""
        # Save original config for cleanup
        original_config = get_rate_limit_config()

        try:
            # Set custom config with 1 retry and 2s initial delay
            custom_config = RateLimitConfig(
                max_retries=1,
                initial_delay=2,
                backoff_multiplier=2,
            )
            set_rate_limit_config(custom_config)

            app = create_app()
            client = TestClient(app)

            with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # Return 429 for all attempts
                mock_response_429 = MagicMock()
                mock_response_429.status_code = 429
                mock_response_429.headers = {"content-type": "application/json"}
                mock_response_429.content = b'{"error": {"type": "rate_limit_error"}}'

                mock_client.post.return_value = mock_response_429

                sleep_calls = []

                async def mock_sleep(delay: float) -> None:
                    sleep_calls.append(delay)

                with patch("claudius.proxy.asyncio.sleep", side_effect=mock_sleep):
                    response = client.post(
                        "/v1/messages",
                        json={"model": "claude-3-5-haiku-20241022", "messages": []},
                        headers={"Authorization": "Bearer sk-ant-test123"},
                    )

                assert response.status_code == 429
                # With max_retries=1: initial attempt + 1 retry = 2 total calls
                assert mock_client.post.call_count == 2
                # With initial_delay=2: should sleep for 2 seconds on retry
                assert sleep_calls == [2]
        finally:
            # Restore original config
            set_rate_limit_config(original_config)


class TestRateLimitRetryNonStreaming:
    """Tests for rate limit retry logic with non-streaming requests."""

    def test_429_triggers_retry(self) -> None:
        """Test that 429 response triggers retry."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # First call returns 429, second returns 200
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"content-type": "application/json"}
            mock_response_429.content = b'{"error": {"type": "rate_limit_error"}}'

            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.headers = {"content-type": "application/json"}
            mock_response_200.content = b'{"id": "msg_123"}'

            mock_client.post.side_effect = [mock_response_429, mock_response_200]

            with patch("claudius.proxy.asyncio.sleep", new_callable=AsyncMock):
                response = client.post(
                    "/v1/messages",
                    json={"model": "claude-3-5-haiku-20241022", "messages": []},
                    headers={"Authorization": "Bearer sk-ant-test123"},
                )

            assert response.status_code == 200
            assert mock_client.post.call_count == 2

    def test_exponential_backoff_delays(self) -> None:
        """Test that retry delays follow exponential backoff."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Return 429 twice, then 200
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"content-type": "application/json"}
            mock_response_429.content = b'{"error": {"type": "rate_limit_error"}}'

            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.headers = {"content-type": "application/json"}
            mock_response_200.content = b'{"id": "msg_123"}'

            mock_client.post.side_effect = [
                mock_response_429,
                mock_response_429,
                mock_response_200,
            ]

            sleep_calls = []

            async def mock_sleep(delay: float) -> None:
                sleep_calls.append(delay)

            with patch("claudius.proxy.asyncio.sleep", side_effect=mock_sleep):
                response = client.post(
                    "/v1/messages",
                    json={"model": "claude-3-5-haiku-20241022", "messages": []},
                    headers={"Authorization": "Bearer sk-ant-test123"},
                )

            assert response.status_code == 200
            assert mock_client.post.call_count == 3
            # Default: 5s, then 15s (5 * 3)
            assert sleep_calls == [5, 15]

    def test_max_retries_exceeded_returns_429(self) -> None:
        """Test that exceeding max retries returns 429 to client."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Return 429 for all attempts
            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"content-type": "application/json"}
            mock_response_429.content = b'{"error": {"type": "rate_limit_error"}}'

            mock_client.post.return_value = mock_response_429

            with patch("claudius.proxy.asyncio.sleep", new_callable=AsyncMock):
                response = client.post(
                    "/v1/messages",
                    json={"model": "claude-3-5-haiku-20241022", "messages": []},
                    headers={"Authorization": "Bearer sk-ant-test123"},
                )

            assert response.status_code == 429
            # Initial + 3 retries = 4 total
            assert mock_client.post.call_count == 4

    def test_non_429_error_not_retried(self) -> None:
        """Test that non-429 errors are not retried."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Return 400 Bad Request
            mock_response_400 = MagicMock()
            mock_response_400.status_code = 400
            mock_response_400.headers = {"content-type": "application/json"}
            mock_response_400.content = b'{"error": {"type": "invalid_request"}}'

            mock_client.post.return_value = mock_response_400

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 400
            assert mock_client.post.call_count == 1

    def test_500_error_not_retried(self) -> None:
        """Test that 500 errors are not retried."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Return 500 Internal Server Error
            mock_response_500 = MagicMock()
            mock_response_500.status_code = 500
            mock_response_500.headers = {"content-type": "application/json"}
            mock_response_500.content = b'{"error": {"type": "internal_error"}}'

            mock_client.post.return_value = mock_response_500

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 500
            assert mock_client.post.call_count == 1


class TestRateLimitRetryStreaming:
    """Tests for rate limit retry logic with streaming requests."""

    def test_streaming_429_triggers_retry(self) -> None:
        """Test that 429 response triggers retry for streaming requests."""
        app = create_app()
        client = TestClient(app)

        call_count = 0

        async def mock_aiter_bytes():
            yield b"event: message_start\n"
            yield b'data: {"type": "message_start"}\n\n'

        async def mock_aread():
            return b'{"error": {"type": "rate_limit_error"}}'

        def create_stream_cm(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_cm = MagicMock()

            if call_count == 1:
                # First call: 429
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.headers = {"content-type": "application/json"}
                mock_response.aread = mock_aread
            else:
                # Second call: 200 with stream
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.headers = {"content-type": "text/event-stream"}
                mock_response.aiter_bytes = mock_aiter_bytes

            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()
            mock_client.stream.side_effect = create_stream_cm

            with patch("claudius.proxy.asyncio.sleep", new_callable=AsyncMock):
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "messages": [],
                        "stream": True,
                    },
                    headers={"Authorization": "Bearer sk-ant-test123"},
                )

            assert response.status_code == 200
            assert call_count == 2

    def test_streaming_max_retries_returns_429(self) -> None:
        """Test that streaming requests return 429 after max retries."""
        app = create_app()
        client = TestClient(app)

        call_count = 0

        async def mock_aread():
            return b'{"error": {"type": "rate_limit_error"}}'

        def create_stream_cm(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_cm = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"content-type": "application/json"}
            mock_response.aread = mock_aread
            mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            return mock_cm

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()
            mock_client.stream.side_effect = create_stream_cm

            with patch("claudius.proxy.asyncio.sleep", new_callable=AsyncMock):
                response = client.post(
                    "/v1/messages",
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "messages": [],
                        "stream": True,
                    },
                    headers={"Authorization": "Bearer sk-ant-test123"},
                )

            assert response.status_code == 429
            # Initial + 3 retries = 4 total
            assert call_count == 4


class TestRateLimitLogging:
    """Tests for rate limit retry logging."""

    def test_retry_logged_at_warning_level(self) -> None:
        """Test that retry attempts are logged at WARNING level."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response_429 = MagicMock()
            mock_response_429.status_code = 429
            mock_response_429.headers = {"content-type": "application/json"}
            mock_response_429.content = b'{"error": {"type": "rate_limit_error"}}'

            mock_response_200 = MagicMock()
            mock_response_200.status_code = 200
            mock_response_200.headers = {"content-type": "application/json"}
            mock_response_200.content = b'{"id": "msg_123"}'

            mock_client.post.side_effect = [mock_response_429, mock_response_200]

            with patch("claudius.proxy.asyncio.sleep", new_callable=AsyncMock):
                with patch("claudius.proxy.logger") as mock_logger:
                    response = client.post(
                        "/v1/messages",
                        json={"model": "claude-3-5-haiku-20241022", "messages": []},
                        headers={"Authorization": "Bearer sk-ant-test123"},
                    )

                    assert response.status_code == 200
                    # Check that warning was logged
                    mock_logger.warning.assert_called()
                    call_args = mock_logger.warning.call_args[0][0]
                    assert "rate limit" in call_args.lower() or "retry" in call_args.lower()
