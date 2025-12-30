# ABOUTME: Pre-flight cost estimation for Claude API requests
# ABOUTME: Counts input tokens exactly and estimates output tokens by heuristics

"""
Claudius Estimation Module.

Provides pre-flight cost estimation by:
- Counting input tokens exactly using Anthropic's token counting API
- Estimating output tokens based on query size and model tendencies
- Calculating cost ranges in EUR
"""

from dataclasses import dataclass
from typing import Any

import anthropic

from claudius.pricing import calculate_cost

# Model output multipliers - how verbose each model tends to be
# Haiku is concise, Opus is verbose, Sonnet is in between
MODEL_OUTPUT_MULTIPLIERS: dict[str, float] = {
    "claude-3-5-haiku-20241022": 0.8,
    "claude-3-5-sonnet-20241022": 1.0,
    "claude-sonnet-4-20250514": 1.0,
    "claude-opus-4-20250514": 1.3,
}

# Base output token ranges by input size
# Format: (min_tokens, max_tokens) for each input size category
OUTPUT_RANGES = {
    "short": (50, 200),    # Input < 50 tokens
    "medium": (100, 500),  # Input 50-200 tokens
    "long": (200, 1000),   # Input > 200 tokens
}


@dataclass
class EstimationResult:
    """Result of a pre-flight cost estimation."""

    input_tokens: int  # Exact count from API
    output_tokens_min: int  # Estimated range minimum
    output_tokens_max: int  # Estimated range maximum
    cost_min: float  # EUR - cost with minimum output
    cost_max: float  # EUR - cost with maximum output
    model: str  # Model name used for estimation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens_min": self.output_tokens_min,
            "output_tokens_max": self.output_tokens_max,
            "cost_min": self.cost_min,
            "cost_max": self.cost_max,
            "model": self.model,
        }


async def count_input_tokens(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """Count input tokens exactly using Anthropic's token counting API.

    Args:
        messages: List of message dicts with role and content
        model: Model name (e.g., "claude-3-5-haiku-20241022")
        api_key: Anthropic API key
        system: Optional system prompt
        tools: Optional list of tool definitions

    Returns:
        Exact count of input tokens
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    kwargs: dict[str, Any] = {
        "messages": messages,
        "model": model,
    }

    if system is not None:
        kwargs["system"] = system

    if tools is not None:
        kwargs["tools"] = tools

    response = await client.messages.count_tokens(**kwargs)
    return response.input_tokens


def estimate_output_tokens(
    input_tokens: int,
    model: str,
) -> tuple[int, int]:
    """Estimate output token range based on input size and model.

    Args:
        input_tokens: Number of input tokens
        model: Model name for adjusting estimate

    Returns:
        Tuple of (min_tokens, max_tokens) estimated output range
    """
    # Determine input size category
    if input_tokens < 50:
        base_min, base_max = OUTPUT_RANGES["short"]
    elif input_tokens <= 200:
        base_min, base_max = OUTPUT_RANGES["medium"]
    else:
        base_min, base_max = OUTPUT_RANGES["long"]

    # Apply model multiplier (default 1.0 for unknown models)
    multiplier = MODEL_OUTPUT_MULTIPLIERS.get(model, 1.0)

    # Calculate adjusted range
    min_tokens = int(base_min * multiplier)
    max_tokens = int(base_max * multiplier)

    return min_tokens, max_tokens


async def estimate_cost(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    system: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> EstimationResult:
    """Estimate the cost of an API request before sending.

    Args:
        messages: List of message dicts with role and content
        model: Model name (e.g., "claude-3-5-haiku-20241022")
        api_key: Anthropic API key
        system: Optional system prompt
        tools: Optional list of tool definitions

    Returns:
        EstimationResult with exact input tokens, estimated output range, and cost range
    """
    # Count input tokens exactly
    input_tokens = await count_input_tokens(
        messages=messages,
        model=model,
        api_key=api_key,
        system=system,
        tools=tools,
    )

    # Estimate output token range
    output_min, output_max = estimate_output_tokens(input_tokens, model)

    # Calculate cost range
    cost_min = calculate_cost(model, input_tokens, output_min)
    cost_max = calculate_cost(model, input_tokens, output_max)

    return EstimationResult(
        input_tokens=input_tokens,
        output_tokens_min=output_min,
        output_tokens_max=output_max,
        cost_min=cost_min,
        cost_max=cost_max,
        model=model,
    )
