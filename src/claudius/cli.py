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
import json
import sys
from typing import IO, Any

from rich.console import Console
from rich.panel import Panel

from claudius.budget import BudgetTracker
from claudius.config import Config

console = Console()

# Default USD to EUR conversion rate
DEFAULT_USD_TO_EUR = 0.92

LOGO = r"""
   ⚔️  ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗  🛡️
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

   Your AI Budget Guardian • v0.1.0
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
    parts = []

    # Session cost (if available, converted from USD to local currency)
    if session_data and "cost" in session_data:
        cost_data = session_data.get("cost", {})
        session_cost_usd = cost_data.get("total_cost_usd", 0.0)
        if session_cost_usd > 0:
            session_cost_local = session_cost_usd * usd_to_eur_rate
            parts.append(f"{session_cost_local:.2f} session")

    # Daily budget status
    parts.append(f"{daily_spent:.2f}/{daily_budget:.0f} today")

    # Monthly budget status
    parts.append(f"{monthly_spent:.0f}/{monthly_budget:.0f} month")

    return " | ".join(parts)


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


def main() -> None:
    """Main entry point for Claudius CLI."""
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

    args = parser.parse_args()

    if args.command == "status-line":
        status_line_command()
    else:
        # Default: show banner
        print_banner()
        console.print("\n[yellow]Claudius is under construction![/yellow]")
        console.print("[dim]Coming soon: budget tracking, smart routing, and more.[/dim]\n")


if __name__ == "__main__":
    main()
