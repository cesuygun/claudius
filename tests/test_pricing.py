# ABOUTME: Tests for model pricing and cost calculation
# ABOUTME: Covers pricing lookup, cost calculation, and EUR conversion

"""Tests for Claudius pricing module."""

import pytest

from claudius.pricing import (
    USD_TO_EUR,
    calculate_cost,
    get_model_pricing,
)


class TestModelPricing:
    """Tests for model pricing data."""

    def test_haiku_pricing_exists(self) -> None:
        """Test that claude-3-5-haiku pricing exists."""
        pricing = get_model_pricing("claude-3-5-haiku-20241022")
        assert pricing is not None
        assert "input_per_million" in pricing
        assert "output_per_million" in pricing

    def test_sonnet_pricing_exists(self) -> None:
        """Test that claude-3-5-sonnet pricing exists."""
        pricing = get_model_pricing("claude-3-5-sonnet-20241022")
        assert pricing is not None

    def test_sonnet_4_pricing_exists(self) -> None:
        """Test that claude-sonnet-4 pricing exists."""
        pricing = get_model_pricing("claude-sonnet-4-20250514")
        assert pricing is not None

    def test_opus_4_pricing_exists(self) -> None:
        """Test that claude-opus-4 pricing exists."""
        pricing = get_model_pricing("claude-opus-4-20250514")
        assert pricing is not None

    def test_unknown_model_returns_none(self) -> None:
        """Test that unknown model returns None."""
        pricing = get_model_pricing("unknown-model-123")
        assert pricing is None

    def test_haiku_pricing_values_in_eur(self) -> None:
        """Test haiku pricing is correctly converted to EUR."""
        pricing = get_model_pricing("claude-3-5-haiku-20241022")
        # $1 input, $5 output per million tokens, converted to EUR
        expected_input = 1.0 * USD_TO_EUR
        expected_output = 5.0 * USD_TO_EUR
        assert pricing["input_per_million"] == pytest.approx(expected_input, rel=1e-6)
        assert pricing["output_per_million"] == pytest.approx(expected_output, rel=1e-6)

    def test_sonnet_pricing_values_in_eur(self) -> None:
        """Test sonnet pricing is correctly converted to EUR."""
        pricing = get_model_pricing("claude-3-5-sonnet-20241022")
        # $3 input, $15 output per million tokens, converted to EUR
        expected_input = 3.0 * USD_TO_EUR
        expected_output = 15.0 * USD_TO_EUR
        assert pricing["input_per_million"] == pytest.approx(expected_input, rel=1e-6)
        assert pricing["output_per_million"] == pytest.approx(expected_output, rel=1e-6)

    def test_opus_pricing_values_in_eur(self) -> None:
        """Test opus pricing is correctly converted to EUR."""
        pricing = get_model_pricing("claude-opus-4-20250514")
        # $15 input, $75 output per million tokens, converted to EUR
        expected_input = 15.0 * USD_TO_EUR
        expected_output = 75.0 * USD_TO_EUR
        assert pricing["input_per_million"] == pytest.approx(expected_input, rel=1e-6)
        assert pricing["output_per_million"] == pytest.approx(expected_output, rel=1e-6)


class TestCostCalculation:
    """Tests for cost calculation function."""

    def test_calculate_cost_zero_tokens(self) -> None:
        """Test cost calculation with zero tokens."""
        cost = calculate_cost("claude-3-5-haiku-20241022", 0, 0)
        assert cost == 0.0

    def test_calculate_cost_input_only(self) -> None:
        """Test cost calculation with input tokens only."""
        # 1 million input tokens at $1/million = $1 = €0.92
        cost = calculate_cost("claude-3-5-haiku-20241022", 1_000_000, 0)
        expected = 1.0 * USD_TO_EUR
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_output_only(self) -> None:
        """Test cost calculation with output tokens only."""
        # 1 million output tokens at $5/million = $5 = €4.60
        cost = calculate_cost("claude-3-5-haiku-20241022", 0, 1_000_000)
        expected = 5.0 * USD_TO_EUR
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_calculate_cost_both_tokens(self) -> None:
        """Test cost calculation with both input and output tokens."""
        # 100 input + 50 output tokens with haiku
        # Input: 100/1_000_000 * $1 = $0.0001
        # Output: 50/1_000_000 * $5 = $0.00025
        # Total: $0.00035 = €0.000322
        cost = calculate_cost("claude-3-5-haiku-20241022", 100, 50)
        expected_input = (100 / 1_000_000) * 1.0 * USD_TO_EUR
        expected_output = (50 / 1_000_000) * 5.0 * USD_TO_EUR
        expected_total = expected_input + expected_output
        assert cost == pytest.approx(expected_total, rel=1e-6)

    def test_calculate_cost_opus_expensive(self) -> None:
        """Test that opus is significantly more expensive."""
        haiku_cost = calculate_cost("claude-3-5-haiku-20241022", 1000, 1000)
        opus_cost = calculate_cost("claude-opus-4-20250514", 1000, 1000)
        # Opus should be ~15x more expensive
        assert opus_cost > haiku_cost * 10

    def test_calculate_cost_unknown_model_returns_zero(self) -> None:
        """Test that unknown model returns zero cost."""
        cost = calculate_cost("unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_calculate_cost_realistic_request(self) -> None:
        """Test cost calculation for a realistic API request."""
        # Typical request: 500 input tokens, 200 output tokens with sonnet
        # Input: 500/1_000_000 * $3 = $0.0015
        # Output: 200/1_000_000 * $15 = $0.003
        # Total: $0.0045 = €0.00414
        cost = calculate_cost("claude-sonnet-4-20250514", 500, 200)
        expected_input = (500 / 1_000_000) * 3.0 * USD_TO_EUR
        expected_output = (200 / 1_000_000) * 15.0 * USD_TO_EUR
        expected_total = expected_input + expected_output
        assert cost == pytest.approx(expected_total, rel=1e-6)


class TestModelAliases:
    """Tests for model name aliases and variants."""

    def test_haiku_variant_names(self) -> None:
        """Test that haiku variants are recognized."""
        # The pricing should work for the full model name
        pricing = get_model_pricing("claude-3-5-haiku-20241022")
        assert pricing is not None

    def test_sonnet_variant_names(self) -> None:
        """Test that sonnet variants are recognized."""
        # Both sonnet versions should work
        pricing1 = get_model_pricing("claude-3-5-sonnet-20241022")
        pricing2 = get_model_pricing("claude-sonnet-4-20250514")
        assert pricing1 is not None
        assert pricing2 is not None
