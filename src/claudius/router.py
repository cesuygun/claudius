# ABOUTME: Smart model routing with heuristics and Haiku gatekeeper
# ABOUTME: Routes queries to cheapest capable model to save costs

"""
Claudius Smart Router.

Implements intelligent model routing:
1. Free heuristics layer (word count, code blocks, keywords)
2. Haiku classification for ambiguous cases
3. Model selection based on complexity
"""

from dataclasses import dataclass

import httpx


@dataclass
class RouteDecision:
    """Result of routing decision."""

    model: str  # "haiku", "sonnet", "opus"
    reason: str  # "heuristic:short_message", "haiku:self_handle", etc.
    needs_classification: bool = False  # True if Haiku should classify


class SmartRouter:
    """Smart model router with heuristics and Haiku gatekeeper."""

    OPUS_KEYWORDS = [
        "architect",
        "design",
        "complex",
        "plan",
        "analyze",
        "comprehensive",
        "strategy",
        "review thoroughly",
    ]
    SHORT_MESSAGE_WORDS = 20

    def __init__(self) -> None:
        pass

    def classify(self, message: str) -> RouteDecision:
        """Classify message using FREE heuristics only.

        Returns:
            RouteDecision with model recommendation or needs_classification=True
        """
        words = message.split()
        word_count = len(words)
        message_lower = message.lower()

        # Rule 1: Code blocks need at least Sonnet (check first for precedence)
        if "```" in message:
            return RouteDecision(model="sonnet", reason="heuristic:code_block")

        # Rule 2: Short messages go to Haiku
        if word_count < self.SHORT_MESSAGE_WORDS:
            return RouteDecision(model="haiku", reason="heuristic:short_message")

        # Rule 3: Opus keywords
        for keyword in self.OPUS_KEYWORDS:
            if keyword in message_lower:
                return RouteDecision(
                    model="opus", reason=f"heuristic:opus_keyword:{keyword}"
                )

        # Rule 4: Ambiguous - needs Haiku to classify
        return RouteDecision(
            model="haiku", reason="needs_classification", needs_classification=True
        )

    async def classify_with_haiku(
        self, message: str, api_key: str
    ) -> RouteDecision:
        """Ask Haiku if it can handle this query.

        Makes a small API call to Haiku (~10 tokens output) to classify complexity.

        Returns:
            RouteDecision with Haiku's recommendation
        """
        classification_prompt = f"""Classify this query's complexity. Reply with ONE word only:
- HAIKU: Simple questions, basic info, short tasks
- SONNET: Code review, medium complexity, detailed explanations
- OPUS: Architecture, complex analysis, deep reasoning, planning

Query: {message[:500]}

Answer (one word):"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 10,
                        "messages": [
                            {"role": "user", "content": classification_prompt}
                        ],
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data["content"][0]["text"].strip().upper()

                    if "OPUS" in answer:
                        return RouteDecision(
                            model="opus", reason="haiku:classified_opus"
                        )
                    elif "SONNET" in answer:
                        return RouteDecision(
                            model="sonnet", reason="haiku:classified_sonnet"
                        )
                    else:
                        return RouteDecision(
                            model="haiku", reason="haiku:self_handle"
                        )

        except Exception:
            pass  # Fall through to default

        # Fallback to Sonnet on any error
        return RouteDecision(model="sonnet", reason="haiku:classification_error")
