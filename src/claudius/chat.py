# ABOUTME: Chat client for sending messages to Claude API via Claudius proxy
# ABOUTME: Handles streaming responses, conversation history, and cost tracking

"""
Claudius Chat Client.

Sends messages to Claude API via the Claudius proxy server and streams
responses back with real-time display.
"""

import json
from dataclasses import dataclass

import httpx
from rich.console import Console

from claudius.pricing import calculate_cost


class ChatError(Exception):
    """Error during chat communication with Claude API."""

    pass


@dataclass
class ChatResponse:
    """Result of a chat request."""

    model: str  # Which model responded ("haiku", "sonnet", "opus")
    text: str  # Full response text
    input_tokens: int
    output_tokens: int
    cost: float  # Cost in configured currency (EUR)


class ChatClient:
    """Sends messages to Claude API via Claudius proxy."""

    def __init__(
        self,
        proxy_url: str = "http://localhost:4000",
        api_key: str | None = None,
    ):
        self.proxy_url = proxy_url
        self.api_key = api_key
        self.conversation: list[dict[str, str]] = []

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation = []

    async def send_message(
        self,
        message: str,
        model_override: str | None = None,
        console: Console | None = None,
    ) -> ChatResponse:
        """
        Send message and stream response.

        Args:
            message: User's message
            model_override: Force specific model ("opus", "sonnet", "haiku") or None for auto
            console: Rich console for streaming output (optional)

        Returns:
            ChatResponse with full response and token counts
        """
        # Build request payload (use copy of existing conversation + new message)
        messages_for_request = list(self.conversation)
        messages_for_request.append({"role": "user", "content": message})

        payload = {
            "model": "claude-sonnet-4-20250514",  # Default, proxy may route differently
            "max_tokens": 4096,
            "messages": messages_for_request,
            "stream": True,
        }

        # Build headers
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        # Add model override header if specified
        if model_override:
            headers["x-model-override"] = model_override

        # Make streaming request
        accumulated_text = ""
        input_tokens = 0
        output_tokens = 0
        model_used = "sonnet"
        # Buffer to accumulate incomplete SSE data across chunks
        sse_buffer = ""

        client = httpx.AsyncClient()
        try:
            try:
                async with client.stream(
                    "POST",
                    f"{self.proxy_url}/v1/messages",
                    json=payload,
                    headers=headers,
                    timeout=300.0,
                ) as response:
                    # Check for HTTP errors
                    if response.status_code >= 400:
                        raise ChatError(
                            f"API error: HTTP {response.status_code}"
                        )

                    async for chunk in response.aiter_bytes():
                        # Add chunk to buffer and process complete SSE events
                        sse_buffer += chunk.decode("utf-8", errors="replace")

                        # Process complete events (delimited by double newline)
                        while "\n\n" in sse_buffer:
                            event_end = sse_buffer.index("\n\n")
                            event_data = sse_buffer[:event_end]
                            sse_buffer = sse_buffer[event_end + 2:]

                            # Extract the data line from the event
                            data_line = None
                            for line in event_data.split("\n"):
                                if line.startswith("data: "):
                                    data_line = line[6:]
                                    break

                            if not data_line:
                                continue

                            try:
                                data = json.loads(data_line)
                                event_type = data.get("type", "")

                                if event_type == "message_start":
                                    msg = data.get("message", {})
                                    usage = msg.get("usage", {})
                                    input_tokens = usage.get("input_tokens", 0)
                                    model_full = msg.get("model", "")
                                    # Extract model name (haiku, sonnet, opus)
                                    if "haiku" in model_full:
                                        model_used = "haiku"
                                    elif "opus" in model_full:
                                        model_used = "opus"
                                    else:
                                        model_used = "sonnet"

                                elif event_type == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        text = delta.get("text", "")
                                        accumulated_text += text

                                elif event_type == "message_delta":
                                    usage = data.get("usage", {})
                                    output_tokens = usage.get("output_tokens", 0)

                            except json.JSONDecodeError:
                                pass

            except httpx.ConnectError as e:
                raise ChatError(f"Connection error: {e}") from e
            except httpx.TimeoutException as e:
                raise ChatError(f"Request timed out: {e}") from e

        finally:
            await client.aclose()

        # Only add to conversation history if successful
        self.conversation.append({"role": "user", "content": message})
        self.conversation.append({"role": "assistant", "content": accumulated_text})

        # Calculate cost
        model_for_pricing = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
        }.get(model_used, "claude-sonnet-4-20250514")
        cost = calculate_cost(model_for_pricing, input_tokens, output_tokens)

        return ChatResponse(
            model=model_used,
            text=accumulated_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
