# ABOUTME: Tests for cost tracking integration in the proxy
# ABOUTME: Covers non-streaming and streaming response cost recording

"""Tests for cost tracking integration in Claudius proxy."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from claudius.budget import BudgetTracker
from claudius.pricing import calculate_cost
from claudius.proxy import create_app, get_budget_tracker, set_budget_tracker


class TestBudgetTrackerIntegration:
    """Tests for BudgetTracker integration in proxy."""

    def test_set_budget_tracker(self) -> None:
        """Test that budget tracker can be set."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tracker = BudgetTracker(db_path=Path(f.name))
            set_budget_tracker(tracker)
            assert get_budget_tracker() is tracker

    def test_get_budget_tracker_returns_none_by_default(self) -> None:
        """Test that budget tracker is None when not set."""
        set_budget_tracker(None)
        assert get_budget_tracker() is None


class TestNonStreamingCostTracking:
    """Tests for cost tracking in non-streaming responses."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    def test_records_usage_for_successful_response(self, tracker: BudgetTracker) -> None:
        """Test that usage is recorded for successful non-streaming responses."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        response_data = {
            "id": "msg_123",
            "type": "message",
            "model": "claude-3-5-haiku-20241022",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
            "content": [{"type": "text", "text": "Hello!"}],
        }

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = json.dumps(response_data).encode()
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

        # Verify usage was recorded
        daily_spent = tracker.get_daily_spent()
        expected_cost = calculate_cost("claude-3-5-haiku-20241022", 100, 50)
        assert daily_spent == pytest.approx(expected_cost, rel=1e-6)

    def test_does_not_record_usage_for_error_response(self, tracker: BudgetTracker) -> None:
        """Test that usage is NOT recorded for error responses."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = b'{"error": {"type": "invalid_request"}}'
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

        # Verify no usage was recorded
        daily_spent = tracker.get_daily_spent()
        assert daily_spent == 0.0

    def test_records_correct_model_from_response(self, tracker: BudgetTracker) -> None:
        """Test that the model from response is used (not request)."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        # Request asks for one model, response might be different
        response_data = {
            "id": "msg_123",
            "type": "message",
            "model": "claude-sonnet-4-20250514",  # Different from request
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
            },
            "content": [{"type": "text", "text": "Hello!"}],
        }

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = json.dumps(response_data).encode()
            mock_client.post.return_value = mock_response

            client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

        # Verify cost is calculated using response model (sonnet), not request model (haiku)
        daily_spent = tracker.get_daily_spent()
        expected_cost = calculate_cost("claude-sonnet-4-20250514", 100, 50)
        assert daily_spent == pytest.approx(expected_cost, rel=1e-6)

    def test_works_without_budget_tracker_configured(self) -> None:
        """Test that proxy works fine when no budget tracker is configured."""
        set_budget_tracker(None)
        app = create_app()
        client = TestClient(app)

        response_data = {
            "id": "msg_123",
            "type": "message",
            "model": "claude-3-5-haiku-20241022",
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "content": [{"type": "text", "text": "Hello!"}],
        }

        with patch("claudius.proxy.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.content = json.dumps(response_data).encode()
            mock_client.post.return_value = mock_response

            response = client.post(
                "/v1/messages",
                json={"model": "claude-3-5-haiku-20241022", "messages": []},
                headers={"Authorization": "Bearer sk-ant-test123"},
            )

            # Should succeed without errors
            assert response.status_code == 200


class TestStreamingCostTracking:
    """Tests for cost tracking in streaming responses."""

    @pytest.fixture
    def tracker(self) -> BudgetTracker:
        """Create a budget tracker with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            return BudgetTracker(db_path=Path(f.name))

    def test_records_usage_for_streaming_response(self, tracker: BudgetTracker) -> None:
        """Test that usage is recorded for streaming responses."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        # Streaming SSE chunks
        chunks = [
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123", "model": "claude-3-5-haiku-20241022", "usage": {"input_tokens": 100}}}\n\n',
            b'event: content_block_delta\ndata: {"type": "content_block_delta", "delta": {"text": "Hello"}}\n\n',
            b'event: message_delta\ndata: {"type": "message_delta", "usage": {"output_tokens": 50}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]

        async def mock_aiter_bytes():
            for chunk in chunks:
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

            # Consume the response to trigger stream processing
            response = client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [],
                    "stream": True,
                },
                headers={"Authorization": "Bearer sk-ant-test123"},
            )
            # Read all content to ensure stream is fully consumed
            _ = response.content

        # Verify usage was recorded
        daily_spent = tracker.get_daily_spent()
        expected_cost = calculate_cost("claude-3-5-haiku-20241022", 100, 50)
        assert daily_spent == pytest.approx(expected_cost, rel=1e-6)

    def test_streaming_extracts_model_from_message_start(self, tracker: BudgetTracker) -> None:
        """Test that model is extracted from message_start event."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        chunks = [
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123", "model": "claude-sonnet-4-20250514", "usage": {"input_tokens": 200}}}\n\n',
            b'event: message_delta\ndata: {"type": "message_delta", "usage": {"output_tokens": 100}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]

        async def mock_aiter_bytes():
            for chunk in chunks:
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
            _ = response.content

        # Verify cost is for sonnet (from response), not haiku (from request)
        daily_spent = tracker.get_daily_spent()
        expected_cost = calculate_cost("claude-sonnet-4-20250514", 200, 100)
        assert daily_spent == pytest.approx(expected_cost, rel=1e-6)

    def test_streaming_handles_partial_chunks(self, tracker: BudgetTracker) -> None:
        """Test that streaming handles SSE data split across chunks."""
        set_budget_tracker(tracker)
        app = create_app()
        client = TestClient(app)

        # Data split across multiple chunks
        chunks = [
            b"event: message_start\n",
            b'data: {"type": "message_start", "message": {"id": "msg_123", ',
            b'"model": "claude-3-5-haiku-20241022", "usage": {"input_tokens": 150}}}\n\n',
            b'event: message_delta\ndata: {"type": "message_delta", "usage": {"output_tokens": 75}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]

        async def mock_aiter_bytes():
            for chunk in chunks:
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
            _ = response.content

        daily_spent = tracker.get_daily_spent()
        expected_cost = calculate_cost("claude-3-5-haiku-20241022", 150, 75)
        assert daily_spent == pytest.approx(expected_cost, rel=1e-6)

    def test_streaming_works_without_budget_tracker(self) -> None:
        """Test that streaming works when no budget tracker is configured."""
        set_budget_tracker(None)
        app = create_app()
        client = TestClient(app)

        chunks = [
            b'event: message_start\ndata: {"type": "message_start", "message": {"id": "msg_123", "model": "claude-3-5-haiku-20241022", "usage": {"input_tokens": 100}}}\n\n',
            b'event: message_stop\ndata: {"type": "message_stop"}\n\n',
        ]

        async def mock_aiter_bytes():
            for chunk in chunks:
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
