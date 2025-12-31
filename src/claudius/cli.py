# ABOUTME: Interactive CLI for Claudius
# ABOUTME: Provides REPL interface with slash commands and budget display

"""
Claudius CLI - Interactive mode with slash commands.

Features:
- Interactive REPL with prompt_toolkit
- Budget status bar with progress indicators
- Slash commands (/status, /opus, /sonnet, etc.)
- Rich terminal UI with colors and formatting
- Status line integration for Claude Code
"""

import argparse
import asyncio
import json
import os
import socket
import sys
import threading
import time
from typing import IO, Any

import uvicorn
from rich.console import Console
from rich.panel import Panel

from claudius.budget import BudgetTracker
from claudius.config import Config
from claudius.proxy import create_app, set_api_config, set_budget_tracker, set_rate_limit_config
from claudius.repl import ClaudiusREPL

console = Console()

# Default USD to EUR conversion rate
DEFAULT_USD_TO_EUR = 0.92

LOGO = r"""
    ⚔️                      🛡️
      ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

   Your AI Budget Guardian • v1.0.0
"""


def print_banner() -> None:
    """Print the Claudius startup banner."""
    console.print(Panel(LOGO, border_style="blue"))


def parse_stdin_json(stdin: IO[str]) -> dict[str, Any] | None:
    """
    Parse JSON input from stdin.

    Claude Code sends session data as JSON to stdin. This function attempts
    to parse it and returns None on empty input or parse errors.

    Args:
        stdin: Input stream to read JSON from.

    Returns:
        Parsed JSON as dict, or None if empty or invalid.
    """
    try:
        content = stdin.read()
        if not content or not content.strip():
            return None
        result: dict[str, Any] = json.loads(content)
        return result
    except (json.JSONDecodeError, OSError):
        return None


def format_status_line(
    session_data: dict[str, Any] | None,
    daily_spent: float,
    daily_budget: float,
    monthly_spent: float,
    monthly_budget: float,
    currency: str = "EUR",
    usd_to_eur_rate: float = DEFAULT_USD_TO_EUR,
) -> str:
    """
    Format the status line for Claude Code display.

    Generates a single-line string showing budget status suitable
    for display in Claude Code's status bar.

    Args:
        session_data: Optional JSON data from Claude Code containing session cost.
        daily_spent: Amount spent today in local currency.
        daily_budget: Daily budget limit in local currency.
        monthly_spent: Amount spent this month in local currency.
        monthly_budget: Monthly budget limit in local currency.
        currency: Currency code (default EUR).
        usd_to_eur_rate: Conversion rate from USD to EUR.

    Returns:
        Formatted status line string.
    """
    # Determine currency symbol
    currency_symbol = "€" if currency == "EUR" else "$"

    parts = []

    # Session cost (if available, converted from USD to local currency)
    if session_data and "cost" in session_data:
        cost_data = session_data.get("cost", {})
        session_cost_usd = cost_data.get("total_cost_usd", 0.0)
        if session_cost_usd > 0:
            session_cost_local = session_cost_usd * usd_to_eur_rate
            parts.append(f"{currency_symbol}{session_cost_local:.2f} session")

    # Daily budget status
    parts.append(f"{currency_symbol}{daily_spent:.2f}/{currency_symbol}{daily_budget:.0f} today")

    # Monthly budget status
    parts.append(f"{currency_symbol}{monthly_spent:.0f}/{currency_symbol}{monthly_budget:.0f} month")

    # Add money bag emoji prefix as per DESIGN.md specification
    return "💰 " + " | ".join(parts)


def status_line_command(
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
) -> None:
    """
    Execute the status-line subcommand.

    Reads JSON from stdin, fetches budget data from BudgetTracker,
    and outputs a formatted status line to stdout.

    Args:
        stdin: Input stream (defaults to sys.stdin).
        stdout: Output stream (defaults to sys.stdout).
    """
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    # Parse session data from stdin
    session_data = parse_stdin_json(stdin)

    # Try to load config and budget tracker
    try:
        config = Config.load()
        monthly_budget = config.budget.monthly
        daily_budget = config.budget.daily_soft
        currency = config.budget.currency
    except Exception:
        # Fallback to defaults if config fails
        monthly_budget = 90.0
        daily_budget = 5.0
        currency = "EUR"

    try:
        tracker = BudgetTracker()
        daily_spent = tracker.get_daily_spent()
        monthly_spent = tracker.get_monthly_spent()
    except Exception:
        # Fallback if tracker fails
        daily_spent = 0.0
        monthly_spent = 0.0

    # Format and output the status line
    status = format_status_line(
        session_data=session_data,
        daily_spent=daily_spent,
        daily_budget=daily_budget,
        monthly_spent=monthly_spent,
        monthly_budget=monthly_budget,
        currency=currency,
    )

    stdout.write(status + "\n")


def check_port_available(host: str, port: int) -> bool:
    """Check if a port is available for binding.

    Args:
        host: Host address to check.
        port: Port number to check.

    Returns:
        True if the port is available, False otherwise.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def resolve_api_key(config: Config) -> str | None:
    """Resolve API key from config or environment.

    Order of precedence:
    1. Config file (config.api.key)
    2. Environment variable (ANTHROPIC_API_KEY)

    Args:
        config: Configuration object.

    Returns:
        API key string or None if not found.
    """
    if config.api.key:
        return config.api.key
    return os.environ.get("ANTHROPIC_API_KEY")


def run_proxy_server(host: str, port: int) -> None:
    """Run the proxy server in a background thread.

    Args:
        host: Host address to bind to.
        port: Port number to bind to.
    """
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="error")


def _start_interactive_mode() -> None:
    """Start Claudius in interactive mode with REPL and proxy server."""
    # Load config
    config = Config.load()

    # Get API key (from config or env)
    api_key = resolve_api_key(config)
    if not api_key:
        console.print(
            "[red]Error: No API key found.[/red]\n"
            "Set ANTHROPIC_API_KEY environment variable or add to ~/.claudius/config.toml"
        )
        return

    # Check if port is available
    if not check_port_available(config.proxy.host, config.proxy.port):
        console.print(
            f"[red]Error: Port {config.proxy.port} is already in use.[/red]\n"
            "Another Claudius instance may be running, or try a different port in "
            "~/.claudius/config.toml"
        )
        return

    # Initialize budget tracker
    tracker = BudgetTracker()

    # Configure proxy with rate limit, API config, and budget tracker
    set_rate_limit_config(config.rate_limit)
    set_api_config(config.api)
    set_budget_tracker(tracker)

    # Start proxy server in background thread
    proxy_thread = threading.Thread(
        target=run_proxy_server,
        args=(config.proxy.host, config.proxy.port),
        daemon=True,
    )
    proxy_thread.start()

    # Give proxy time to start
    time.sleep(0.5)

    # Run REPL
    repl = ClaudiusREPL(tracker, config, api_key)
    asyncio.run(repl.run())


def _run_proxy_only() -> None:
    """Run only the proxy server without REPL (for Claude Code integration)."""
    config = Config.load()
    api_key = resolve_api_key(config)

    if not api_key:
        console.print(
            "[red]Error: No API key found.[/red]\n"
            "Set ANTHROPIC_API_KEY environment variable or add to ~/.claudius/config.toml"
        )
        return

    if not check_port_available(config.proxy.host, config.proxy.port):
        console.print(
            f"[red]Error: Port {config.proxy.port} is already in use.[/red]"
        )
        return

    tracker = BudgetTracker()
    set_rate_limit_config(config.rate_limit)
    set_api_config(config.api)
    set_budget_tracker(tracker)

    console.print(f"[green]🛡️ Claudius proxy running on http://{config.proxy.host}:{config.proxy.port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    app = create_app()
    uvicorn.run(app, host=config.proxy.host, port=config.proxy.port, log_level="warning")


def _enable_claude_code() -> None:
    """Configure Claude Code to use Claudius proxy."""
    import subprocess

    config = Config.load()
    proxy_url = f"http://{config.proxy.host}:{config.proxy.port}"

    try:
        subprocess.run(
            ["claude", "config", "set", "--global", "apiBaseUrl", proxy_url],
            check=True,
            capture_output=True,
        )
        console.print("[green]✅ Claude Code now uses Claudius![/green]")
        console.print(f"[dim]Proxy URL: {proxy_url}[/dim]")
        console.print("\n[yellow]Remember to run 'claudius proxy' before using Claude Code![/yellow]")
    except subprocess.CalledProcessError as e:
        console.print("[red]Error: Failed to configure Claude Code[/red]")
        console.print(f"[dim]{e.stderr.decode() if e.stderr else ''}[/dim]")
    except FileNotFoundError:
        console.print("[red]Error: 'claude' command not found. Is Claude Code installed?[/red]")


def _disable_claude_code() -> None:
    """Configure Claude Code to use Anthropic directly (bypass Claudius)."""
    import subprocess

    try:
        subprocess.run(
            ["claude", "config", "set", "--global", "apiBaseUrl", "https://api.anthropic.com"],
            check=True,
            capture_output=True,
        )
        console.print("[green]✅ Claude Code now uses Anthropic directly[/green]")
        console.print("[dim]Claudius budget tracking disabled[/dim]")
    except subprocess.CalledProcessError as e:
        console.print("[red]Error: Failed to configure Claude Code[/red]")
        console.print(f"[dim]{e.stderr.decode() if e.stderr else ''}[/dim]")
    except FileNotFoundError:
        console.print("[red]Error: 'claude' command not found. Is Claude Code installed?[/red]")


def main(argv: list[str] | None = None) -> None:
    """Main entry point for Claudius CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).
    """
    parser = argparse.ArgumentParser(
        prog="claudius",
        description="Your AI Budget Guardian - Smart Claude API cost management",
    )
    subparsers = parser.add_subparsers(dest="command")

    # status-line subcommand
    subparsers.add_parser(
        "status-line",
        help="Output budget status line for Claude Code integration",
    )

    # proxy subcommand
    subparsers.add_parser(
        "proxy",
        help="Run proxy server only (for Claude Code)",
    )

    # enable subcommand
    subparsers.add_parser(
        "enable",
        help="Configure Claude Code to use Claudius",
    )

    # disable subcommand
    subparsers.add_parser(
        "disable",
        help="Configure Claude Code to bypass Claudius",
    )

    args = parser.parse_args(argv)

    if args.command == "status-line":
        status_line_command()
    elif args.command == "proxy":
        _run_proxy_only()
    elif args.command == "enable":
        _enable_claude_code()
    elif args.command == "disable":
        _disable_claude_code()
    else:
        # Default: start REPL + proxy server
        _start_interactive_mode()


if __name__ == "__main__":
    main()
