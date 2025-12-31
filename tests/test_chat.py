# ABOUTME: Tests for the Claudius chat client
# ABOUTME: Covers message sending, streaming responses, and conversation history

"""Tests for Claudius chat client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from claudius.chat import ChatClient, ChatResponse


class TestChatResponse:
    """Tests for the ChatResponse dataclass."""

    def test_chat_response_has_required_fields(self) -> None:
        """Test that ChatResponse has all required fields."""
        response = ChatResponse(
            model="sonnet",
            text="Hello, world!",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )

        assert response.model == "sonnet"
        assert response.text == "Hello, world!"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.cost == 0.005

    def test_chat_response_cost_is_float(self) -> None:
        """Test that cost is stored as a float."""
        response = ChatResponse(
            model="haiku",
            text="Test",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
        )

        assert isinstance(response.cost, float)


class TestChatClientInit:
    """Tests for ChatClient initialization."""

    def test_default_proxy_url(self) -> None:
        """Test that default proxy URL is localhost:4000."""
        client = ChatClient()

        assert client.proxy_url == "http://localhost:4000"

    def test_custom_proxy_url(self) -> None:
        """Test that custom proxy URL can be set."""
        client = ChatClient(proxy_url="http://localhost:5000")

        assert client.proxy_url == "http://localhost:5000"

    def test_api_key_storage(self) -> None:
        """Test that API key is stored."""
        client = ChatClient(api_key="sk-ant-test123")

        assert client.api_key == "sk-ant-test123"

    def test_conversation_starts_empty(self) -> None:
        """Test that conversation history starts empty."""
        client = ChatClient()

        assert client.conversation == []

    def test_clear_history_empties_conversation(self) -> None:
        """Test that clear_history empties the conversation."""
        client = ChatClient()
        client.conversation = [{"role": "user", "content": "Hello"}]

        client.clear_history()

        assert client.conversation == []


class TestSendMessageBasic:
    """Tests for basic send_message functionality."""

    @pytest.fixture
    def mock_streaming_response(self):
        """Create a mock streaming SSE response."""

        async def create_mock_response():
            """Create async iterator for SSE chunks."""
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":", world!"}}\n\n',
                b'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        return create_mock_response

    async def test_send_message_returns_chat_response(
        self, mock_streaming_response
    ) -> None:
        """Test that send_message returns a ChatResponse."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            assert isinstance(response, ChatResponse)
            assert response.text == "Hello, world!"
            assert response.input_tokens == 100
            assert response.output_tokens == 50

    async def test_send_message_posts_to_proxy(self, mock_streaming_response) -> None:
        """Test that send_message posts to the proxy server."""
        client = ChatClient(
            proxy_url="http://localhost:4000", api_key="sk-ant-test123"
        )

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            mock_client.stream.assert_called_once()
            call_args = mock_client.stream.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "http://localhost:4000/v1/messages"

    async def test_send_message_includes_api_key_header(
        self, mock_streaming_response
    ) -> None:
        """Test that send_message includes x-api-key header."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["headers"]["x-api-key"] == "sk-ant-test123"

    async def test_send_message_includes_anthropic_version_header(
        self, mock_streaming_response
    ) -> None:
        """Test that send_message includes anthropic-version header."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["headers"]["anthropic-version"] == "2023-06-01"

    async def test_send_message_sets_stream_true(
        self, mock_streaming_response
    ) -> None:
        """Test that send_message sets stream to true in payload."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["json"]["stream"] is True

    async def test_send_message_includes_message_in_payload(
        self, mock_streaming_response
    ) -> None:
        """Test that send_message includes the message in payload."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            call_kwargs = mock_client.stream.call_args[1]
            messages = call_kwargs["json"]["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Hello"


class TestConversationHistory:
    """Tests for conversation history management."""

    @pytest.fixture
    def mock_streaming_response(self):
        """Create a mock streaming SSE response."""

        async def create_mock_response():
            """Create async iterator for SSE chunks."""
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        return create_mock_response

    async def test_conversation_stores_user_message(
        self, mock_streaming_response
    ) -> None:
        """Test that user message is added to conversation history."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            assert len(client.conversation) >= 1
            assert client.conversation[0]["role"] == "user"
            assert client.conversation[0]["content"] == "Hello"

    async def test_conversation_stores_assistant_response(
        self, mock_streaming_response
    ) -> None:
        """Test that assistant response is added to conversation history."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            assert len(client.conversation) == 2
            assert client.conversation[1]["role"] == "assistant"
            assert client.conversation[1]["content"] == "Response"

    async def test_conversation_maintains_history_across_messages(
        self, mock_streaming_response
    ) -> None:
        """Test that conversation history is maintained across multiple messages."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("First message")

            # Reset mock for second call
            mock_response.aiter_bytes = mock_streaming_response
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Second message")

            # Should have 4 messages: user1, assistant1, user2, assistant2
            assert len(client.conversation) == 4
            assert client.conversation[2]["role"] == "user"
            assert client.conversation[2]["content"] == "Second message"

    async def test_second_message_includes_history_in_payload(
        self, mock_streaming_response
    ) -> None:
        """Test that second message includes conversation history in payload."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("First message")

            # Reset mock for second call
            mock_response.aiter_bytes = mock_streaming_response
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Second message")

            # Check the second call's payload
            call_kwargs = mock_client.stream.call_args[1]
            messages = call_kwargs["json"]["messages"]
            # Should include: user1, assistant1, user2
            assert len(messages) == 3
            assert messages[0]["content"] == "First message"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["content"] == "Second message"

    def test_clear_history_resets_conversation(self) -> None:
        """Test that clear_history resets the conversation."""
        client = ChatClient()
        client.conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        client.clear_history()

        assert client.conversation == []


class TestModelOverride:
    """Tests for model override functionality."""

    @pytest.fixture
    def mock_streaming_response(self):
        """Create a mock streaming SSE response."""

        async def create_mock_response():
            """Create async iterator for SSE chunks."""
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        return create_mock_response

    async def test_model_override_header_sent(self, mock_streaming_response) -> None:
        """Test that model override header is sent when specified."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello", model_override="opus")

            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["headers"]["x-model-override"] == "opus"

    async def test_no_model_override_header_when_not_specified(
        self, mock_streaming_response
    ) -> None:
        """Test that model override header is not sent when not specified."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            await client.send_message("Hello")

            call_kwargs = mock_client.stream.call_args[1]
            assert "x-model-override" not in call_kwargs["headers"]


class TestModelDetection:
    """Tests for model detection from response."""

    async def test_detects_haiku_model(self) -> None:
        """Test that haiku model is correctly detected."""
        client = ChatClient(api_key="sk-ant-test123")

        async def haiku_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-3-5-haiku-20241022","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":10}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = haiku_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            assert response.model == "haiku"

    async def test_detects_opus_model(self) -> None:
        """Test that opus model is correctly detected."""
        client = ChatClient(api_key="sk-ant-test123")

        async def opus_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-opus-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":10}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = opus_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            assert response.model == "opus"

    async def test_detects_sonnet_model(self) -> None:
        """Test that sonnet model is correctly detected."""
        client = ChatClient(api_key="sk-ant-test123")

        async def sonnet_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":10}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = sonnet_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            assert response.model == "sonnet"


class TestCostCalculation:
    """Tests for cost calculation."""

    async def test_cost_is_calculated(self) -> None:
        """Test that cost is calculated from token usage."""
        client = ChatClient(api_key="sk-ant-test123")

        async def response_with_tokens():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":1000}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":500}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = response_with_tokens

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            # Cost should be non-zero for real token usage
            assert response.cost > 0

    async def test_haiku_is_cheaper_than_opus(self) -> None:
        """Test that haiku is cheaper than opus for same token counts."""
        client = ChatClient(api_key="sk-ant-test123")

        async def haiku_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-3-5-haiku-20241022","usage":{"input_tokens":1000}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":500}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        async def opus_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-opus-4-20250514","usage":{"input_tokens":1000}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":500}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            # Test haiku
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = haiku_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            haiku_result = await client.send_message("Hello")

            # Test opus - clear history first
            client.clear_history()
            mock_response.aiter_bytes = opus_response
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)

            opus_result = await client.send_message("Hello")

            assert haiku_result.cost < opus_result.cost


class TestErrorHandling:
    """Tests for error handling."""

    async def test_connection_error_raises_exception(self) -> None:
        """Test that connection refused raises ChatError."""
        from claudius.chat import ChatError

        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            with pytest.raises(ChatError) as exc_info:
                await client.send_message("Hello")

            assert "Connection" in str(exc_info.value) or "connect" in str(
                exc_info.value
            ).lower()

    async def test_timeout_error_raises_exception(self) -> None:
        """Test that timeout raises ChatError."""
        from claudius.chat import ChatError

        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            with pytest.raises(ChatError) as exc_info:
                await client.send_message("Hello")

            assert "timeout" in str(exc_info.value).lower() or "timed" in str(
                exc_info.value
            ).lower()

    async def test_api_error_raises_exception(self) -> None:
        """Test that HTTP error response raises ChatError."""
        from claudius.chat import ChatError

        client = ChatClient(api_key="sk-ant-test123")

        async def error_response():
            yield b'data: {"type":"error","error":{"type":"invalid_request_error","message":"Invalid API key"}}\n\n'

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = error_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            with pytest.raises(ChatError) as exc_info:
                await client.send_message("Hello")

            assert "401" in str(exc_info.value) or "error" in str(exc_info.value).lower()

    async def test_conversation_not_modified_on_error(self) -> None:
        """Test that conversation history is not modified when error occurs."""
        from claudius.chat import ChatError

        client = ChatClient(api_key="sk-ant-test123")
        original_conversation = list(client.conversation)

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            try:
                await client.send_message("Hello")
            except ChatError:
                pass

            # Conversation should remain unchanged after error
            assert client.conversation == original_conversation


class TestSSEChunkBuffering:
    """Tests for SSE chunk buffering to handle split events."""

    async def test_handles_split_message_start_event(self) -> None:
        """Test that message_start event split across chunks is handled correctly."""
        client = ChatClient(api_key="sk-ant-test123")

        async def split_chunks():
            # First chunk contains partial message_start data
            yield b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_'
            # Second chunk continues the data
            yield b'123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":150}}}\n\n'
            # Complete events
            yield b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
            yield b'event: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":75}}\n\n'
            yield b'event: message_stop\ndata: {"type":"message_stop"}\n\n'

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = split_chunks

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            # Input tokens should be correctly extracted even with split chunks
            assert response.input_tokens == 150
            assert response.output_tokens == 75
            assert response.cost > 0

    async def test_handles_split_message_delta_event(self) -> None:
        """Test that message_delta event split across chunks is handled correctly."""
        client = ChatClient(api_key="sk-ant-test123")

        async def split_chunks():
            yield b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n'
            yield b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hi"}}\n\n'
            # Split message_delta across chunks
            yield b'event: message_delta\ndata: {"type":"message_'
            yield b'delta","usage":{"output_tokens":200}}\n\n'
            yield b'event: message_stop\ndata: {"type":"message_stop"}\n\n'

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = split_chunks

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            # Output tokens should be correctly extracted even with split chunks
            assert response.input_tokens == 100
            assert response.output_tokens == 200

    async def test_handles_multiple_events_in_single_chunk(self) -> None:
        """Test that multiple complete events in a single chunk are all processed."""
        client = ChatClient(api_key="sk-ant-test123")

        async def combined_chunks():
            # All events in a single chunk
            yield b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":250}}}\n\nevent: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello, world!"}}\n\nevent: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":300}}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n'

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = combined_chunks

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            assert response.input_tokens == 250
            assert response.output_tokens == 300
            assert response.text == "Hello, world!"

    async def test_handles_byte_by_byte_streaming(self) -> None:
        """Test extreme case where each byte arrives as a separate chunk."""
        client = ChatClient(api_key="sk-ant-test123")

        # Full SSE data
        full_data = b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":42}}}\n\nevent: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"X"}}\n\nevent: message_delta\ndata: {"type":"message_delta","usage":{"output_tokens":24}}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n'

        async def byte_by_byte():
            for byte in full_data:
                yield bytes([byte])

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = byte_by_byte

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            # Should correctly parse even with byte-by-byte streaming
            assert response.input_tokens == 42
            assert response.output_tokens == 24
            assert response.text == "X"


class TestSmartRouting:
    """Tests for smart model routing integration."""

    @pytest.fixture
    def mock_streaming_response(self):
        """Create a mock streaming SSE response."""

        async def create_mock_response():
            """Create async iterator for SSE chunks."""
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-3-5-haiku-20241022","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        return create_mock_response

    async def test_chat_client_has_router(self) -> None:
        """ChatClient should have a SmartRouter instance."""
        from claudius.router import SmartRouter

        client = ChatClient(api_key="sk-ant-test123")
        assert hasattr(client, "router")
        assert isinstance(client.router, SmartRouter)

    async def test_chat_response_has_routed_by_field(self) -> None:
        """ChatResponse should have routed_by field."""
        response = ChatResponse(
            model="sonnet",
            text="Hello",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
        )
        assert hasattr(response, "routed_by")
        assert response.routed_by == "default"

    async def test_chat_response_routed_by_can_be_set(self) -> None:
        """ChatResponse routed_by field can be set."""
        response = ChatResponse(
            model="sonnet",
            text="Hello",
            input_tokens=100,
            output_tokens=50,
            cost=0.005,
            routed_by="heuristic:short_message",
        )
        assert response.routed_by == "heuristic:short_message"

    async def test_short_message_routes_to_haiku(
        self, mock_streaming_response
    ) -> None:
        """Short messages should be routed to Haiku via heuristics."""
        client = ChatClient(api_key="sk-ant-test123")

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = mock_streaming_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            response = await client.send_message("Hello")

            # Verify model in payload is haiku
            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["json"]["model"] == "claude-3-5-haiku-20241022"

            # Verify routed_by reflects heuristic routing
            assert response.routed_by == "heuristic:short_message"

    async def test_model_override_bypasses_routing(
        self, mock_streaming_response
    ) -> None:
        """Model override should bypass smart routing."""
        client = ChatClient(api_key="sk-ant-test123")

        # Create opus response mock
        async def opus_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-opus-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = opus_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            # Short message that would normally route to haiku, but with opus override
            response = await client.send_message("Hello", model_override="opus")

            # Verify model in payload is opus (override worked)
            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["json"]["model"] == "claude-opus-4-20250514"

            # Verify routed_by shows manual override
            assert response.routed_by == "manual:opus"
            assert response.routed_by.startswith("manual:")

    async def test_code_block_routes_to_sonnet(self) -> None:
        """Messages with code blocks should route to Sonnet."""
        client = ChatClient(api_key="sk-ant-test123")

        async def sonnet_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-sonnet-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = sonnet_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            message = """Review this code:
```python
def hello():
    print("hi")
```"""
            response = await client.send_message(message)

            # Verify model in payload is sonnet
            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["json"]["model"] == "claude-sonnet-4-20250514"

            # Verify routed_by reflects code block heuristic
            assert response.routed_by == "heuristic:code_block"

    async def test_opus_keyword_routes_to_opus(self) -> None:
        """Messages with opus keywords should route to Opus."""
        client = ChatClient(api_key="sk-ant-test123")

        async def opus_response():
            chunks = [
                b'event: message_start\ndata: {"type":"message_start","message":{"id":"msg_123","model":"claude-opus-4-20250514","usage":{"input_tokens":100}}}\n\n',
                b'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}\n\n',
                b'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":50}}\n\n',
                b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
            ]
            for chunk in chunks:
                yield chunk

        with patch("claudius.chat.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.aclose = AsyncMock()

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/event-stream"}
            mock_response.aiter_bytes = opus_response

            mock_stream_cm = MagicMock()
            mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
            mock_stream_cm.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream.return_value = mock_stream_cm

            # 21 words - above short message threshold, with opus keyword
            message = "I need you to architect a new system for our application that handles user authentication and payment processing with high availability and scalability requirements."
            response = await client.send_message(message)

            # Verify model in payload is opus
            call_kwargs = mock_client.stream.call_args[1]
            assert call_kwargs["json"]["model"] == "claude-opus-4-20250514"

            # Verify routed_by reflects opus keyword heuristic
            assert "heuristic:opus_keyword" in response.routed_by
            assert "architect" in response.routed_by


class TestChatClientModelIds:
    """Tests for ChatClient.MODEL_IDS constant."""

    def test_model_ids_constant_exists(self) -> None:
        """ChatClient should have MODEL_IDS constant."""
        assert hasattr(ChatClient, "MODEL_IDS")
        assert isinstance(ChatClient.MODEL_IDS, dict)

    def test_model_ids_has_all_models(self) -> None:
        """MODEL_IDS should contain haiku, sonnet, and opus."""
        assert "haiku" in ChatClient.MODEL_IDS
        assert "sonnet" in ChatClient.MODEL_IDS
        assert "opus" in ChatClient.MODEL_IDS

    def test_model_ids_correct_values(self) -> None:
        """MODEL_IDS should map to correct model IDs."""
        assert ChatClient.MODEL_IDS["haiku"] == "claude-3-5-haiku-20241022"
        assert ChatClient.MODEL_IDS["sonnet"] == "claude-sonnet-4-20250514"
        assert ChatClient.MODEL_IDS["opus"] == "claude-opus-4-20250514"
