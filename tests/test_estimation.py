# ABOUTME: Tests for pre-flight cost estimation module
# ABOUTME: Covers token counting, output estimation heuristics, and cost calculation

"""Tests for Claudius estimation module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claudius.estimation import (
    MODEL_OUTPUT_MULTIPLIERS,
    EstimationResult,
    count_input_tokens,
    estimate_cost,
    estimate_output_tokens,
)


class TestEstimationResult:
    """Tests for EstimationResult dataclass."""

    def test_estimation_result_creation(self) -> None:
        """Test that EstimationResult can be created with all fields."""
        result = EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.001,
            cost_max=0.005,
            model="claude-3-5-haiku-20241022",
        )
        assert result.input_tokens == 100
        assert result.output_tokens_min == 50
        assert result.output_tokens_max == 200
        assert result.cost_min == 0.001
        assert result.cost_max == 0.005
        assert result.model == "claude-3-5-haiku-20241022"

    def test_estimation_result_to_dict(self) -> None:
        """Test that EstimationResult can be converted to dict for JSON response."""
        result = EstimationResult(
            input_tokens=100,
            output_tokens_min=50,
            output_tokens_max=200,
            cost_min=0.001,
            cost_max=0.005,
            model="claude-3-5-haiku-20241022",
        )
        result_dict = result.to_dict()
        assert result_dict["input_tokens"] == 100
        assert result_dict["output_tokens_min"] == 50
        assert result_dict["output_tokens_max"] == 200
        assert result_dict["cost_min"] == 0.001
        assert result_dict["cost_max"] == 0.005
        assert result_dict["model"] == "claude-3-5-haiku-20241022"


class TestCountInputTokens:
    """Tests for input token counting function."""

    @pytest.mark.asyncio
    async def test_count_input_tokens_calls_anthropic_api(self) -> None:
        """Test that count_input_tokens uses the Anthropic API."""
        messages = [{"role": "user", "content": "Hello, Claude"}]
        model = "claude-3-5-haiku-20241022"

        with patch("claudius.estimation.anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.input_tokens = 42
            mock_client.messages.count_tokens = AsyncMock(return_value=mock_response)

            result = await count_input_tokens(
                messages=messages,
                model=model,
                api_key="test-api-key",
            )

            assert result == 42
            mock_client.messages.count_tokens.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_input_tokens_with_system_prompt(self) -> None:
        """Test that count_input_tokens includes system prompt."""
        messages = [{"role": "user", "content": "Hello"}]
        system = "You are a helpful assistant"
        model = "claude-3-5-haiku-20241022"

        with patch("claudius.estimation.anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.input_tokens = 100
            mock_client.messages.count_tokens = AsyncMock(return_value=mock_response)

            result = await count_input_tokens(
                messages=messages,
                model=model,
                api_key="test-api-key",
                system=system,
            )

            assert result == 100
            call_kwargs = mock_client.messages.count_tokens.call_args[1]
            assert call_kwargs["system"] == system

    @pytest.mark.asyncio
    async def test_count_input_tokens_with_tools(self) -> None:
        """Test that count_input_tokens includes tools in count."""
        messages = [{"role": "user", "content": "What's the weather?"}]
        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "input_schema": {"type": "object", "properties": {}},
            }
        ]
        model = "claude-3-5-haiku-20241022"

        with patch("claudius.estimation.anthropic.AsyncAnthropic") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_response = MagicMock()
            mock_response.input_tokens = 150
            mock_client.messages.count_tokens = AsyncMock(return_value=mock_response)

            result = await count_input_tokens(
                messages=messages,
                model=model,
                api_key="test-api-key",
                tools=tools,
            )

            assert result == 150
            call_kwargs = mock_client.messages.count_tokens.call_args[1]
            assert call_kwargs["tools"] == tools


class TestEstimateOutputTokens:
    """Tests for output token estimation heuristics."""

    def test_short_query_low_estimate(self) -> None:
        """Test that short queries (<50 input tokens) get low output estimates."""
        min_tokens, max_tokens = estimate_output_tokens(
            input_tokens=30,
            model="claude-3-5-haiku-20241022",
        )
        # Short queries: 50-200 base range
        assert min_tokens >= 40  # Allow for model multiplier
        assert max_tokens <= 250  # Allow for model multiplier
        assert min_tokens < max_tokens

    def test_medium_query_medium_estimate(self) -> None:
        """Test that medium queries (50-200 input tokens) get medium output estimates."""
        min_tokens, max_tokens = estimate_output_tokens(
            input_tokens=100,
            model="claude-3-5-haiku-20241022",
        )
        # Medium queries: 100-500 base range
        assert min_tokens >= 80
        assert max_tokens <= 600
        assert min_tokens < max_tokens

    def test_long_query_high_estimate(self) -> None:
        """Test that long queries (>200 input tokens) get higher output estimates."""
        min_tokens, max_tokens = estimate_output_tokens(
            input_tokens=500,
            model="claude-3-5-haiku-20241022",
        )
        # Long queries: 200-1000 base range
        assert min_tokens >= 150
        assert max_tokens <= 1200
        assert min_tokens < max_tokens

    def test_haiku_tends_shorter(self) -> None:
        """Test that Haiku model tends to produce shorter outputs."""
        haiku_min, haiku_max = estimate_output_tokens(
            input_tokens=100,
            model="claude-3-5-haiku-20241022",
        )
        sonnet_min, sonnet_max = estimate_output_tokens(
            input_tokens=100,
            model="claude-sonnet-4-20250514",
        )
        # Haiku should have lower estimates than Sonnet
        assert haiku_max <= sonnet_max

    def test_opus_tends_longer(self) -> None:
        """Test that Opus model tends to produce longer outputs."""
        haiku_min, haiku_max = estimate_output_tokens(
            input_tokens=100,
            model="claude-3-5-haiku-20241022",
        )
        opus_min, opus_max = estimate_output_tokens(
            input_tokens=100,
            model="claude-opus-4-20250514",
        )
        # Opus should have higher estimates than Haiku
        assert opus_max >= haiku_max

    def test_unknown_model_uses_default_multiplier(self) -> None:
        """Test that unknown models use default multiplier of 1.0."""
        min_tokens, max_tokens = estimate_output_tokens(
            input_tokens=100,
            model="unknown-model-123",
        )
        # Should still return reasonable estimates with default multiplier
        assert min_tokens > 0
        assert max_tokens > min_tokens

    def test_boundary_at_50_input_tokens(self) -> None:
        """Test boundary behavior at input_tokens=50 (short->medium transition)."""
        # 49 tokens should be "short" category
        short_min, short_max = estimate_output_tokens(
            input_tokens=49,
            model="claude-3-5-haiku-20241022",
        )

        # 50 tokens should be "medium" category
        medium_min, medium_max = estimate_output_tokens(
            input_tokens=50,
            model="claude-3-5-haiku-20241022",
        )

        # Medium category should have higher base estimates than short
        # Short: (50, 200) * 0.8 = (40, 160)
        # Medium: (100, 500) * 0.8 = (80, 400)
        assert medium_min > short_min
        assert medium_max > short_max

    def test_boundary_at_200_input_tokens(self) -> None:
        """Test boundary behavior at input_tokens=200 (medium->long transition)."""
        # 200 tokens should be "medium" category (inclusive)
        medium_min, medium_max = estimate_output_tokens(
            input_tokens=200,
            model="claude-3-5-haiku-20241022",
        )

        # 201 tokens should be "long" category
        long_min, long_max = estimate_output_tokens(
            input_tokens=201,
            model="claude-3-5-haiku-20241022",
        )

        # Long category should have higher base estimates than medium
        # Medium: (100, 500) * 0.8 = (80, 400)
        # Long: (200, 1000) * 0.8 = (160, 800)
        assert long_min > medium_min
        assert long_max > medium_max


class TestEstimateCost:
    """Tests for the main estimate_cost function."""

    @pytest.mark.asyncio
    async def test_estimate_cost_returns_estimation_result(self) -> None:
        """Test that estimate_cost returns an EstimationResult."""
        messages = [{"role": "user", "content": "Hello"}]
        model = "claude-3-5-haiku-20241022"

        with patch("claudius.estimation.count_input_tokens") as mock_count:
            mock_count.return_value = 10

            result = await estimate_cost(
                messages=messages,
                model=model,
                api_key="test-api-key",
            )

            assert isinstance(result, EstimationResult)
            assert result.model == model
            assert result.input_tokens == 10

    @pytest.mark.asyncio
    async def test_estimate_cost_calculates_cost_range(self) -> None:
        """Test that estimate_cost calculates min and max costs correctly."""
        messages = [{"role": "user", "content": "Hello"}]
        model = "claude-3-5-haiku-20241022"

        with patch("claudius.estimation.count_input_tokens") as mock_count:
            mock_count.return_value = 100

            result = await estimate_cost(
                messages=messages,
                model=model,
                api_key="test-api-key",
            )

            # Cost should be calculated using pricing.calculate_cost
            assert result.cost_min > 0
            assert result.cost_max > result.cost_min
            # Cost min uses output_tokens_min, cost max uses output_tokens_max
            assert result.cost_min < result.cost_max

    @pytest.mark.asyncio
    async def test_estimate_cost_unknown_model_returns_zero_cost(self) -> None:
        """Test that unknown models return zero cost (since pricing is unknown)."""
        messages = [{"role": "user", "content": "Hello"}]
        model = "unknown-model"

        with patch("claudius.estimation.count_input_tokens") as mock_count:
            mock_count.return_value = 100

            result = await estimate_cost(
                messages=messages,
                model=model,
                api_key="test-api-key",
            )

            assert result.cost_min == 0.0
            assert result.cost_max == 0.0

    @pytest.mark.asyncio
    async def test_estimate_cost_passes_system_and_tools(self) -> None:
        """Test that estimate_cost passes system prompt and tools to count_input_tokens."""
        messages = [{"role": "user", "content": "Hello"}]
        model = "claude-3-5-haiku-20241022"
        system = "You are helpful"
        tools = [{"name": "test", "input_schema": {"type": "object"}}]

        with patch("claudius.estimation.count_input_tokens") as mock_count:
            mock_count.return_value = 100

            await estimate_cost(
                messages=messages,
                model=model,
                api_key="test-api-key",
                system=system,
                tools=tools,
            )

            mock_count.assert_called_once_with(
                messages=messages,
                model=model,
                api_key="test-api-key",
                system=system,
                tools=tools,
            )


class TestModelOutputMultipliers:
    """Tests for model output multiplier configuration."""

    def test_haiku_multiplier_is_low(self) -> None:
        """Test that Haiku has a low output multiplier."""
        assert MODEL_OUTPUT_MULTIPLIERS.get("claude-3-5-haiku-20241022", 1.0) <= 1.0

    def test_opus_multiplier_is_high(self) -> None:
        """Test that Opus has a high output multiplier."""
        assert MODEL_OUTPUT_MULTIPLIERS.get("claude-opus-4-20250514", 1.0) >= 1.0

    def test_sonnet_multiplier_is_medium(self) -> None:
        """Test that Sonnet has a medium output multiplier."""
        sonnet_mult = MODEL_OUTPUT_MULTIPLIERS.get("claude-sonnet-4-20250514", 1.0)
        haiku_mult = MODEL_OUTPUT_MULTIPLIERS.get("claude-3-5-haiku-20241022", 1.0)
        opus_mult = MODEL_OUTPUT_MULTIPLIERS.get("claude-opus-4-20250514", 1.0)
        assert haiku_mult <= sonnet_mult <= opus_mult


class TestModelConsistency:
    """Tests for model configuration consistency between modules."""

    def test_model_output_multipliers_match_pricing(self) -> None:
        """Test that MODEL_OUTPUT_MULTIPLIERS keys match MODEL_PRICING keys."""
        from claudius.pricing import MODEL_PRICING

        multiplier_models = set(MODEL_OUTPUT_MULTIPLIERS.keys())
        pricing_models = set(MODEL_PRICING.keys())

        # All models in multipliers should have pricing
        missing_from_pricing = multiplier_models - pricing_models
        assert not missing_from_pricing, (
            f"Models in MODEL_OUTPUT_MULTIPLIERS but not in MODEL_PRICING: {missing_from_pricing}"
        )

        # All models in pricing should have multipliers
        missing_from_multipliers = pricing_models - multiplier_models
        assert not missing_from_multipliers, (
            f"Models in MODEL_PRICING but not in MODEL_OUTPUT_MULTIPLIERS: {missing_from_multipliers}"
        )
