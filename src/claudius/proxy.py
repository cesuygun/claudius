# ABOUTME: FastAPI proxy server for Anthropic API requests
# ABOUTME: Intercepts, forwards, and handles streaming responses

"""
Claudius Proxy Server.

A transparent proxy that sits between Claude clients and the Anthropic API.
Handles both regular and streaming (SSE) responses.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

ANTHROPIC_API_URL = "https://api.anthropic.com"

# Headers to filter out when forwarding requests
FILTERED_REQUEST_HEADERS = frozenset({"host", "content-length"})

# Hop-by-hop headers to filter from responses (RFC 2616)
HOP_BY_HOP_HEADERS = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
})

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Claudius Proxy",
        description="Budget guardian proxy for Claude API",
        version="0.1.0",
    )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.post("/v1/messages")
    async def proxy_messages(request: Request) -> Response:
        """Proxy requests to the Anthropic messages API."""
        logger.info("Request received: POST /v1/messages")

        # Check for authentication
        auth_header = request.headers.get("authorization")
        api_key_header = request.headers.get("x-api-key")

        if not auth_header and not api_key_header:
            logger.error("Missing Authorization or x-api-key header")
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization or x-api-key header",
            )

        # Get request body
        body = await request.body()
        body_json = json.loads(body)

        # Filter and forward headers
        forwarded_headers = _filter_request_headers(request.headers)

        # Check if this is a streaming request
        is_streaming = body_json.get("stream", False)

        target_url = f"{ANTHROPIC_API_URL}/v1/messages"
        logger.debug(f"Forwarding request to {target_url}")

        if is_streaming:
            return await _handle_streaming_request(
                target_url, forwarded_headers, body
            )
        else:
            return await _handle_regular_request(
                target_url, forwarded_headers, body
            )

    return app


def _filter_request_headers(headers: Any) -> dict[str, str]:
    """Filter out headers that shouldn't be forwarded."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in FILTERED_REQUEST_HEADERS
    }


def _filter_response_headers(headers: Any) -> dict[str, str]:
    """Filter out hop-by-hop headers from response."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }


async def _handle_regular_request(
    url: str, headers: dict[str, str], body: bytes
) -> Response:
    """Handle a regular (non-streaming) request."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                content=body,
                timeout=300.0,  # 5 minute timeout for long requests
            )

            logger.debug(f"Response received: {response.status_code}")

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=_filter_response_headers(response.headers),
            )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Anthropic API: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to connect to Anthropic API",
        ) from e
    except httpx.TimeoutException as e:
        logger.error(f"Request to Anthropic API timed out: {e}")
        raise HTTPException(
            status_code=502,
            detail="Request to Anthropic API timed out",
        ) from e


async def _handle_streaming_request(
    url: str, headers: dict[str, str], body: bytes
) -> StreamingResponse:
    """Handle a streaming (SSE) request."""
    client = httpx.AsyncClient()

    # Start the stream connection before returning the response
    # This allows connection errors to be caught and returned as proper HTTP errors
    try:
        stream_context = client.stream(
            "POST",
            url,
            headers=headers,
            content=body,
            timeout=300.0,
        )
        response = await stream_context.__aenter__()
    except httpx.ConnectError as e:
        await client.aclose()
        logger.error(f"Failed to connect to Anthropic API: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to connect to Anthropic API",
        ) from e
    except httpx.TimeoutException as e:
        await client.aclose()
        logger.error(f"Request to Anthropic API timed out: {e}")
        raise HTTPException(
            status_code=502,
            detail="Request to Anthropic API timed out",
        ) from e

    async def stream_generator() -> AsyncGenerator[bytes, None]:
        try:
            logger.debug(f"Streaming response started: {response.status_code}")
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await stream_context.__aexit__(None, None, None)
            await client.aclose()

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def run_server(host: str = "127.0.0.1", port: int = 4000) -> None:
    """Run the proxy server."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info(f"Starting Claudius proxy on {host}:{port}")

    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    from claudius.config import Config

    config = Config.load()
    run_server(host=config.proxy.host, port=config.proxy.port)
