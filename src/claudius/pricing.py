# ABOUTME: Model pricing data and cost calculation for Claude API
# ABOUTME: Stores prices in EUR and calculates costs from token usage

"""
Claudius Pricing Module.

Contains pricing data for Claude models and cost calculation functions.
Prices are stored in EUR (converted from USD at 0.92 rate).
"""

from typing import TypedDict

# USD to EUR conversion rate
USD_TO_EUR = 0.92


class ModelPricing(TypedDict):
    """Pricing data for a model."""

    input_per_million: float  # EUR per million input tokens
    output_per_million: float  # EUR per million output tokens


# Model pricing in EUR (converted from USD)
# Prices per million tokens
MODEL_PRICING: dict[str, ModelPricing] = {
    # Claude 3.5 Haiku: $1 input, $5 output
    "claude-3-5-haiku-20241022": {
        "input_per_million": 1.0 * USD_TO_EUR,
        "output_per_million": 5.0 * USD_TO_EUR,
    },
    # Claude 3.5 Sonnet: $3 input, $15 output
    "claude-3-5-sonnet-20241022": {
        "input_per_million": 3.0 * USD_TO_EUR,
        "output_per_million": 15.0 * USD_TO_EUR,
    },
    # Claude Sonnet 4: $3 input, $15 output
    "claude-sonnet-4-20250514": {
        "input_per_million": 3.0 * USD_TO_EUR,
        "output_per_million": 15.0 * USD_TO_EUR,
    },
    # Claude Opus 4: $15 input, $75 output
    "claude-opus-4-20250514": {
        "input_per_million": 15.0 * USD_TO_EUR,
        "output_per_million": 75.0 * USD_TO_EUR,
    },
}


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing for a model.

    Args:
        model: The model name (e.g., "claude-3-5-haiku-20241022")

    Returns:
        ModelPricing dict with input_per_million and output_per_million in EUR,
        or None if model is not found.
    """
    return MODEL_PRICING.get(model)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate the cost of an API call in EUR.

    Args:
        model: The model name used for the call
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in EUR, or 0.0 if model pricing is not found.
    """
    pricing = get_model_pricing(model)
    if pricing is None:
        return 0.0

    input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]

    return input_cost + output_cost
