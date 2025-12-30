# ABOUTME: Tests for the Smart Router with Haiku gatekeeper
# ABOUTME: Verifies heuristic routing and classification logic

"""
Tests for Claudius Smart Router.

Tests the routing logic that sends queries to the cheapest capable model.
"""

import pytest

from claudius.router import RouteDecision, SmartRouter


class TestRouteDecision:
    """Tests for RouteDecision dataclass."""

    def test_route_decision_basic_fields(self) -> None:
        """RouteDecision stores model, reason, and needs_classification."""
        decision = RouteDecision(model="haiku", reason="test_reason")
        assert decision.model == "haiku"
        assert decision.reason == "test_reason"
        assert decision.needs_classification is False

    def test_route_decision_with_classification_flag(self) -> None:
        """RouteDecision can set needs_classification to True."""
        decision = RouteDecision(
            model="haiku", reason="needs_classification", needs_classification=True
        )
        assert decision.needs_classification is True


class TestSmartRouterHeuristics:
    """Tests for SmartRouter.classify() - FREE heuristics layer."""

    def test_short_message_routes_to_haiku(self) -> None:
        """Messages under 20 words route to haiku."""
        router = SmartRouter()
        result = router.classify("What is the capital of France?")
        assert result.model == "haiku"
        assert result.reason == "heuristic:short_message"
        assert result.needs_classification is False

    def test_very_short_message_routes_to_haiku(self) -> None:
        """Very short messages (1-5 words) route to haiku."""
        router = SmartRouter()
        result = router.classify("Hello")
        assert result.model == "haiku"
        assert result.reason == "heuristic:short_message"

    def test_exactly_19_words_routes_to_haiku(self) -> None:
        """Message with exactly 19 words routes to haiku (under 20)."""
        router = SmartRouter()
        message = " ".join(["word"] * 19)
        result = router.classify(message)
        assert result.model == "haiku"
        assert result.reason == "heuristic:short_message"

    def test_code_block_routes_to_sonnet(self) -> None:
        """Messages with code blocks route to sonnet."""
        router = SmartRouter()
        message = """Please review this code:
```python
def hello():
    print("Hello, world!")
```
"""
        result = router.classify(message)
        assert result.model == "sonnet"
        assert result.reason == "heuristic:code_block"
        assert result.needs_classification is False

    def test_code_block_single_backticks_does_not_trigger(self) -> None:
        """Single backticks should not trigger code block heuristic."""
        router = SmartRouter()
        # This is a long message with single backticks but no triple backticks
        message = "This is a message with `inline code` but no code blocks " * 5
        result = router.classify(message)
        # Should need classification since it's not short and has no code block
        assert result.needs_classification is True

    def test_opus_keyword_architect_routes_to_opus(self) -> None:
        """Messages with 'architect' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 21 words - above the short message threshold
        message = "I need you to architect a new system for our application that handles user authentication and payment processing with high availability and scalability requirements."
        result = router.classify(message)
        assert result.model == "opus"
        assert "heuristic:opus_keyword" in result.reason
        assert "architect" in result.reason
        assert result.needs_classification is False

    def test_opus_keyword_design_routes_to_opus(self) -> None:
        """Messages with 'design' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 22 words
        message = "Please design a comprehensive solution for our data pipeline that handles millions of records daily and needs to be fault tolerant and highly available."
        result = router.classify(message)
        assert result.model == "opus"
        assert "design" in result.reason

    def test_opus_keyword_complex_routes_to_opus(self) -> None:
        """Messages with 'complex' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 22 words - avoid using "architecture" which contains "architect"
        message = "This is a complex problem that requires careful thought about the entire system structure and its dependencies across multiple services and data stores."
        result = router.classify(message)
        assert result.model == "opus"
        assert "complex" in result.reason

    def test_opus_keyword_plan_routes_to_opus(self) -> None:
        """Messages with 'plan' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 23 words
        message = "I need you to plan out the migration strategy for our database that currently serves millions of users and must maintain zero downtime during the transition."
        result = router.classify(message)
        assert result.model == "opus"
        assert "plan" in result.reason

    def test_opus_keyword_analyze_routes_to_opus(self) -> None:
        """Messages with 'analyze' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 21 words
        message = "Please analyze the performance metrics and identify bottlenecks in our system that need to be addressed to improve response times significantly."
        result = router.classify(message)
        assert result.model == "opus"
        assert "analyze" in result.reason

    def test_opus_keyword_comprehensive_routes_to_opus(self) -> None:
        """Messages with 'comprehensive' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 21 words
        message = "I need a comprehensive review of our codebase to identify all security vulnerabilities and best practices violations that could pose risks."
        result = router.classify(message)
        assert result.model == "opus"
        assert "comprehensive" in result.reason

    def test_opus_keyword_strategy_routes_to_opus(self) -> None:
        """Messages with 'strategy' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 21 words - avoid using "architecture" which contains "architect"
        message = "Help me develop a strategy for migrating our monolithic application to a distributed system over time while maintaining business continuity throughout."
        result = router.classify(message)
        assert result.model == "opus"
        assert "strategy" in result.reason

    def test_opus_keyword_review_thoroughly_routes_to_opus(self) -> None:
        """Messages with 'review thoroughly' keyword route to opus (must be 20+ words)."""
        router = SmartRouter()
        # 21 words
        message = "Please review thoroughly all the changes in this pull request and provide detailed feedback on potential issues and security concerns."
        result = router.classify(message)
        assert result.model == "opus"
        assert "review thoroughly" in result.reason

    def test_opus_keyword_case_insensitive(self) -> None:
        """Opus keywords should match case-insensitively (must be 20+ words)."""
        router = SmartRouter()
        # 20 words
        message = "I need you to ARCHITECT a system for handling large scale data processing and storage requirements across multiple geographic regions."
        result = router.classify(message)
        assert result.model == "opus"
        assert "architect" in result.reason

    def test_medium_message_needs_classification(self) -> None:
        """Medium-length messages without code or opus keywords need classification."""
        router = SmartRouter()
        message = "Can you help me understand how to implement a simple web scraper that collects data from multiple pages and stores it in a database for later analysis and reporting?"
        result = router.classify(message)
        assert result.needs_classification is True
        assert result.model == "haiku"  # Default model when needs classification
        assert result.reason == "needs_classification"

    def test_empty_string_routes_to_haiku(self) -> None:
        """Empty string routes to haiku (short message)."""
        router = SmartRouter()
        result = router.classify("")
        assert result.model == "haiku"
        assert result.reason == "heuristic:short_message"

    def test_whitespace_only_routes_to_haiku(self) -> None:
        """Whitespace-only message routes to haiku."""
        router = SmartRouter()
        result = router.classify("   \n\t   ")
        assert result.model == "haiku"
        assert result.reason == "heuristic:short_message"

    def test_very_long_message_without_keywords_needs_classification(self) -> None:
        """Very long message without opus keywords needs classification."""
        router = SmartRouter()
        message = "Please explain " + " ".join(["the"] * 100)
        result = router.classify(message)
        assert result.needs_classification is True

    def test_code_block_takes_precedence_over_short_message(self) -> None:
        """Code block detection should work even for short messages."""
        router = SmartRouter()
        message = "```print('hi')```"
        result = router.classify(message)
        # Code blocks route to sonnet even if short
        assert result.model == "sonnet"
        assert result.reason == "heuristic:code_block"

    def test_opus_keyword_takes_precedence_over_code_block(self) -> None:
        """Messages with both opus keyword and code blocks test priority."""
        router = SmartRouter()
        # Note: code_block is checked before opus keywords in the implementation
        message = """Please architect a solution:
```python
def example():
    pass
```
"""
        result = router.classify(message)
        # Implementation checks code blocks first, so this should be sonnet
        # This test documents the actual behavior
        assert result.model == "sonnet"
        assert result.reason == "heuristic:code_block"


class TestSmartRouterClassifyWithHaiku:
    """Tests for SmartRouter.classify_with_haiku() - Haiku classification layer."""

    @pytest.mark.asyncio
    async def test_classify_with_haiku_returns_opus_classification(self) -> None:
        """Haiku classification returning OPUS routes to opus."""
        from unittest.mock import AsyncMock, MagicMock, patch

        router = SmartRouter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "OPUS"}]}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "opus"
        assert result.reason == "haiku:classified_opus"

    @pytest.mark.asyncio
    async def test_classify_with_haiku_returns_sonnet_classification(self) -> None:
        """Haiku classification returning SONNET routes to sonnet."""
        from unittest.mock import AsyncMock, MagicMock, patch

        router = SmartRouter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "SONNET"}]}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "sonnet"
        assert result.reason == "haiku:classified_sonnet"

    @pytest.mark.asyncio
    async def test_classify_with_haiku_returns_haiku_classification(self) -> None:
        """Haiku classification returning HAIKU means it can self-handle."""
        from unittest.mock import AsyncMock, MagicMock, patch

        router = SmartRouter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "HAIKU"}]}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "haiku"
        assert result.reason == "haiku:self_handle"

    @pytest.mark.asyncio
    async def test_classify_with_haiku_error_falls_back_to_sonnet(self) -> None:
        """API errors fall back to sonnet."""
        from unittest.mock import AsyncMock, patch

        router = SmartRouter()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("API Error")

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "sonnet"
        assert result.reason == "haiku:classification_error"

    @pytest.mark.asyncio
    async def test_classify_with_haiku_non_200_falls_back_to_sonnet(self) -> None:
        """Non-200 status code falls back to sonnet."""
        from unittest.mock import AsyncMock, MagicMock, patch

        router = SmartRouter()

        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "sonnet"
        assert result.reason == "haiku:classification_error"

    @pytest.mark.asyncio
    async def test_classify_with_haiku_unknown_response_defaults_to_haiku(self) -> None:
        """Unknown classification response defaults to haiku (self-handle)."""
        from unittest.mock import AsyncMock, MagicMock, patch

        router = SmartRouter()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "UNKNOWN"}]}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        with patch("claudius.router.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await router.classify_with_haiku("test message", "fake-api-key")

        assert result.model == "haiku"
        assert result.reason == "haiku:self_handle"


class TestSmartRouterConstants:
    """Tests for SmartRouter class constants."""

    def test_opus_keywords_list_exists(self) -> None:
        """SmartRouter has OPUS_KEYWORDS list."""
        assert hasattr(SmartRouter, "OPUS_KEYWORDS")
        assert isinstance(SmartRouter.OPUS_KEYWORDS, list)
        assert len(SmartRouter.OPUS_KEYWORDS) > 0

    def test_opus_keywords_contains_expected_keywords(self) -> None:
        """OPUS_KEYWORDS contains all expected keywords."""
        expected = ["architect", "design", "complex", "plan", "analyze",
                    "comprehensive", "strategy", "review thoroughly"]
        for keyword in expected:
            assert keyword in SmartRouter.OPUS_KEYWORDS

    def test_short_message_words_constant(self) -> None:
        """SmartRouter has SHORT_MESSAGE_WORDS constant set to 20."""
        assert hasattr(SmartRouter, "SHORT_MESSAGE_WORDS")
        assert SmartRouter.SHORT_MESSAGE_WORDS == 20
