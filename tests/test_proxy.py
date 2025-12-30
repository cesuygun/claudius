# ABOUTME: Tests for the Claudius proxy server
# ABOUTME: Covers request forwarding, streaming, headers, and error handling

"""Tests for Claudius proxy server."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from claudius.proxy import ANTHROPIC_API_URL, create_app


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self) -> None:
        """Test that GET /health returns status ok."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMessagesEndpointValidation:
    """Tests for request validation on /v1/messages."""

    def test_missing_authorization_returns_401(self) -> None:
        """Test that missing Authorization header returns 401."""
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/v1/messages",
            json={"model": "claude-3-5-haiku-20241022", "messages": []},
        )

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_missing_x_api_key_also_accepted(self) -> None:
        """Test that x-api-key header is accepted as alternative to Authorization."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123"}'
            mock_client.post.return_value = mock_response

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"x-api-key": "sk-ant-test123"},
            )

            assert response.status_code == 200


class TestMessagesEndpointForwarding:
    """Tests for request forwarding to Anthropic API."""

    def test_forwards_request_to_anthropic(self) -> None:
        """Test that requests are forwarded to Anthropic API."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123", "content": [{"text": "Hello"}]}'
            mock_client.post.return_value = mock_response

            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 100,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 200
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == f"{ANTHROPIC_API_URL}/v1/messages"

    def test_passes_through_authorization_header(self) -> None:
        """Test that Authorization header is forwarded."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123"}'
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            call_args = mock_client.post.call_args
            forwarded_headers = call_args[1]["headers"]
            # Headers may be lowercase, check case-insensitively
            header_keys_lower = {k.lower(): k for k in forwarded_headers.keys()}
            assert "authorization" in header_keys_lower
            actual_key = header_keys_lower["authorization"]
            assert forwarded_headers[actual_key] == "Bearer sk-ant-test123"

    def test_passes_through_anthropic_version_header(self) -> None:
        """Test that anthropic-version header is forwarded."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123"}'
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={
                    "Authorization": "Bearer sk-ant-test123",
                    "anthropic-version": "2023-06-01",
                },
            )

            call_args = mock_client.post.call_args
            assert "anthropic-version" in call_args[1]["headers"]
            assert call_args[1]["headers"]["anthropic-version"] == "2023-06-01"

    def test_filters_out_host_header(self) -> None:
        """Test that Host header is not forwarded."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123"}'
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={
                    "Authorization": "Bearer sk-ant-test123",
                    "Host": "localhost:4000",
                },
            )

            call_args = mock_client.post.call_args
            forwarded_headers = call_args[1]["headers"]
            assert "host" not in {k.lower() for k in forwarded_headers.keys()}

    def test_filters_out_content_length_header(self) -> None:
        """Test that Content-Length header is not forwarded (httpx recalculates)."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123"}'
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={
                    "Authorization": "Bearer sk-ant-test123",
                    "Content-Length": "999",
                },
            )

            call_args = mock_client.post.call_args
            forwarded_headers = call_args[1]["headers"]
            assert "content-length" not in {k.lower() for k in forwarded_headers.keys()}


class TestMessagesEndpointResponses:
    """Tests for response handling from Anthropic API."""

    def test_returns_anthropic_response(self) -> None:
        """Test that Anthropic response is returned to client."""
        app = create_app()
        client = TestClient(app)

        expected_response = {
            "id": "msg_123",
            "type": "message",
            "content": [{"type": "text", "text": "Hello!"}],
        }

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"id": "msg_123", "type": "message", "content": [{"type": "text", "text": "Hello!"}]}'
            mock_client.post.return_value = mock_response

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 200
            assert response.json() == expected_response

    def test_passes_through_anthropic_error_response(self) -> None:
        """Test that Anthropic error responses are passed through."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = (
                b'{"error": {"type": "invalid_request_error", "message": "Invalid model"}}'
            )
            mock_client.post.return_value = mock_response

            response = client.post(
                "/v1/messages",
                json={"model": "invalid-model", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 400
            assert "error" in response.json()


class TestMessagesEndpointErrorHandling:
    """Tests for error handling."""

    def test_anthropic_unreachable_returns_502(self) -> None:
        """Test that unreachable Anthropic API returns 502 Bad Gateway."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 502
            assert "Anthropic API" in response.json()["detail"]

    def test_timeout_returns_502(self) -> None:
        """Test that timeout returns 502 Bad Gateway."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 502
            # The message contains "timed out" which indicates timeout
            assert "timed out" in response.json()["detail"].lower()


class TestStreamingResponses:
    """Tests for SSE streaming response handling."""

    def test_streaming_request_returns_event_stream(self) -> None:
        """Test that streaming requests return event-stream content type."""
        app = create_app()
        client = TestClient(app)

        async def mock_aiter_bytes():
            yield b"event: message_start\n"
            yield b'data: {"type": "message_start"}\n\n'
            yield b"event: message_stop\n"
            yield b'data: {"type": "message_stop"}\n\n'

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_aiter_bytes

            # Setup the stream context manager
            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

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
            assert "text/event-stream" in response.headers.get("content-type", "")

    def test_streaming_request_uses_stream_method(self) -> None:
        """Test that streaming requests use httpx stream method."""
        app = create_app()
        client = TestClient(app)

        async def mock_aiter_bytes():
            yield b"event: message_start\n"
            yield b'data: {"type": "message_start"}\n\n'

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_aiter_bytes

            # Setup the stream context manager
            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [],
                    "stream": True,
                },
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            mock_client.stream.assert_called_once()
            call_args = mock_client.stream.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == f"{ANTHROPIC_API_URL}/v1/messages"

    def test_streaming_response_content(self) -> None:
        """Test that streaming response content is passed through."""
        app = create_app()
        client = TestClient(app)

        expected_chunks = [
            b"event: message_start\n",
            b'data: {"type": "message_start"}\n\n',
        ]

        async def mock_aiter_bytes():
            for chunk in expected_chunks:
                yield chunk

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_aiter_bytes

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

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
            # Check that content contains the streamed data
            assert b"message_start" in response.content


class TestStreamingErrorHandling:
    """Tests for streaming error handling."""

    def test_streaming_connection_error_returns_502(self) -> None:
        """Test that streaming connection error returns 502 Bad Gateway."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            # Setup the stream context manager to raise ConnectError on enter
            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [],
                    "stream": True,
                },
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 502
            assert "Anthropic API" in response.json()["detail"]

    def test_streaming_timeout_returns_502(self) -> None:
        """Test that streaming timeout returns 502 Bad Gateway."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            # Setup the stream context manager to raise TimeoutException on enter
            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [],
                    "stream": True,
                },
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            assert response.status_code == 502
            assert "timed out" in response.json()["detail"].lower()


class TestEstimateEndpoint:
    """Tests for the /v1/estimate cost estimation endpoint."""

    def test_estimate_requires_authorization(self) -> None:
        """Test that POST /v1/estimate requires authentication."""
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/v1/estimate",
            json={
                "model": "claude-3-5-haiku-20241022",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )

        assert response.status_code == 401
        assert "Authorization" in response.json()["detail"]

    def test_estimate_returns_estimation_result(self) -> None:
        """Test that estimate endpoint returns cost estimation."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            from claudius.estimation import EstimationResult

            mock_estimate.return_value = EstimationResult(
                input_tokens=100,
                output_tokens_min=50,
                output_tokens_max=200,
                cost_min=0.001,
                cost_max=0.005,
                model="claude-3-5-haiku-20241022",
            )

            response = client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers={"x-api-key": "sk-ant-test123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["input_tokens"] == 100
            assert data["output_tokens_min"] == 50
            assert data["output_tokens_max"] == 200
            assert data["cost_min"] == 0.001
            assert data["cost_max"] == 0.005
            assert data["model"] == "claude-3-5-haiku-20241022"

    def test_estimate_passes_system_prompt(self) -> None:
        """Test that estimate endpoint passes system prompt to estimation."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            from claudius.estimation import EstimationResult

            mock_estimate.return_value = EstimationResult(
                input_tokens=150,
                output_tokens_min=50,
                output_tokens_max=200,
                cost_min=0.001,
                cost_max=0.005,
                model="claude-3-5-haiku-20241022",
            )

            client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "system": "You are a helpful assistant",
                },
                headers={"x-api-key": "sk-ant-test123"},
            )

            mock_estimate.assert_called_once()
            call_kwargs = mock_estimate.call_args[1]
            assert call_kwargs["system"] == "You are a helpful assistant"

    def test_estimate_passes_tools(self) -> None:
        """Test that estimate endpoint passes tools to estimation."""
        app = create_app()
        client = TestClient(app)

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            from claudius.estimation import EstimationResult

            mock_estimate.return_value = EstimationResult(
                input_tokens=200,
                output_tokens_min=50,
                output_tokens_max=200,
                cost_min=0.001,
                cost_max=0.005,
                model="claude-3-5-haiku-20241022",
            )

            client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "What's the weather?"}],
                    "tools": tools,
                },
                headers={"x-api-key": "sk-ant-test123"},
            )

            mock_estimate.assert_called_once()
            call_kwargs = mock_estimate.call_args[1]
            assert call_kwargs["tools"] == tools

    def test_estimate_extracts_api_key_from_x_api_key_header(self) -> None:
        """Test that API key is extracted from x-api-key header."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            from claudius.estimation import EstimationResult

            mock_estimate.return_value = EstimationResult(
                input_tokens=100,
                output_tokens_min=50,
                output_tokens_max=200,
                cost_min=0.001,
                cost_max=0.005,
                model="claude-3-5-haiku-20241022",
            )

            client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers={"x-api-key": "sk-ant-my-api-key"},
            )

            mock_estimate.assert_called_once()
            call_kwargs = mock_estimate.call_args[1]
            assert call_kwargs["api_key"] == "sk-ant-my-api-key"

    def test_estimate_extracts_api_key_from_authorization_bearer(self) -> None:
        """Test that API key is extracted from Authorization Bearer header."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            from claudius.estimation import EstimationResult

            mock_estimate.return_value = EstimationResult(
                input_tokens=100,
                output_tokens_min=50,
                output_tokens_max=200,
                cost_min=0.001,
                cost_max=0.005,
                model="claude-3-5-haiku-20241022",
            )

            client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers={"Authorization": "Bearer sk-ant-bearer-key"},
            )

            mock_estimate.assert_called_once()
            call_kwargs = mock_estimate.call_args[1]
            assert call_kwargs["api_key"] == "sk-ant-bearer-key"

    def test_estimate_handles_api_error(self) -> None:
        """Test that estimate endpoint handles API errors gracefully."""
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.estimate_cost") as mock_estimate:
            mock_estimate.side_effect = Exception("API error")

            response = client.post(
                "/v1/estimate",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                headers={"x-api-key": "sk-ant-test123"},
            )

            assert response.status_code == 500
            assert "estimation" in response.json()["detail"].lower()
