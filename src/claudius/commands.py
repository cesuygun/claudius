# ABOUTME: Slash command handler for the Claudius REPL
# ABOUTME: Handles commands like /status, /config, /logs, /models, /opus, /sonnet, /haiku, /auto, /help, /quit

"""
Claudius Command Handler.

Processes slash commands in the REPL:
- /status: Show budget status
- /config: Open configuration file in editor
- /logs: View recent usage history
- /models: Show available models and pricing
- /opus, /sonnet, /haiku: Force model for next query
- /auto: Return to automatic routing
- /help: Show all commands
- /quit: Exit REPL
"""

import os
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.config import DEFAULT_CONFIG_PATH, Config
from claudius.ui import render_status


@dataclass
class CommandResult:
    """Result of executing a command."""

    output: str | None = None  # Text to print (if any)
    should_exit: bool = False  # True for /quit
    model_override: str | None = None  # "opus", "sonnet", "haiku", or None for /auto


COMMANDS_HELP = """Available Commands:
  /status  - Show budget status
  /config  - Open configuration file in editor
  /logs    - View recent usage history
  /models  - Show available models and pricing
  /opus    - Force Opus for next query
  /sonnet  - Force Sonnet for next query
  /haiku   - Force Haiku for next query
  /auto    - Return to automatic routing
  /help    - Show this help message
  /quit    - Exit Claudius"""


class CommandHandler:
    """Handles slash commands in the REPL."""

    def __init__(self, tracker: BudgetTracker, config: Config, console: Console):
        self.tracker = tracker
        self.config = config
        self.console = console
        self.current_model_override: str | None = None
        self._config_path: Path = DEFAULT_CONFIG_PATH

    def handle(self, input_text: str) -> CommandResult | None:
        """Handle input. Returns CommandResult if it was a command, None if regular chat."""
        if not input_text.startswith("/"):
            return None

        # Parse command (case-insensitive)
        command = input_text.strip().lower()

        # Route to appropriate handler
        if command == "/quit":
            return self._handle_quit()
        elif command == "/status":
            return self._handle_status()
        elif command == "/config":
            return self._handle_config()
        elif command == "/logs":
            return self._handle_logs()
        elif command == "/opus":
            return self._handle_model_override("opus")
        elif command == "/sonnet":
            return self._handle_model_override("sonnet")
        elif command == "/haiku":
            return self._handle_model_override("haiku")
        elif command == "/auto":
            return self._handle_auto()
        elif command == "/help":
            return self._handle_help()
        elif command == "/models":
            return self._handle_models()
        else:
            return self._handle_unknown(input_text)

    def _handle_quit(self) -> CommandResult:
        """Handle /quit command."""
        return CommandResult(should_exit=True)

    def _handle_status(self) -> CommandResult:
        """Handle /status command."""
        status_renderable = render_status(self.tracker, self.config)
        with self.console.capture() as capture:
            self.console.print(status_renderable)
        output = capture.get()
        return CommandResult(output=output)

    def _handle_config(self) -> CommandResult:
        """Handle /config command."""
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(self._config_path)])
        return CommandResult(output=f"Opened config in {editor}")

    def _handle_logs(self) -> CommandResult:
        """Handle /logs command."""
        usages = self._get_recent_usage(limit=10)
        if not usages:
            return CommandResult(output="No usage history found.")

        lines = ["Recent Usage History:", ""]
        for usage in usages:
            timestamp, model, input_tokens, output_tokens, cost, query_preview = usage
            preview = query_preview[:50] + "..." if query_preview and len(query_preview) > 50 else query_preview or ""
            lines.append(f"  {timestamp} | {model} | ${cost:.4f} | {preview}")

        return CommandResult(output="\n".join(lines))

    def _get_recent_usage(self, limit: int = 10) -> list[tuple[str, str, int, int, float, str | None]]:
        """Get recent usage history from tracker."""
        with sqlite3.connect(self.tracker.db_path) as conn:
            result = conn.execute(
                """
                SELECT timestamp, model, input_tokens, output_tokens, cost, query_preview
                FROM usage
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return result

    def _handle_model_override(self, model: str) -> CommandResult:
        """Handle /opus, /sonnet, /haiku commands."""
        self.current_model_override = model
        model_display = model.capitalize()
        return CommandResult(
            output=f"Forcing {model_display} for next query",
            model_override=model,
        )

    def _handle_auto(self) -> CommandResult:
        """Handle /auto command."""
        self.current_model_override = None
        return CommandResult(
            output="Returning to automatic routing",
            model_override=None,
        )

    def _handle_help(self) -> CommandResult:
        """Handle /help command."""
        return CommandResult(output=COMMANDS_HELP)

    def _handle_models(self) -> CommandResult:
        """Handle /models command - show available models and pricing."""
        from claudius.pricing import MODEL_PRICING

        lines = ["📊 Available Models:\n"]
        lines.append("| Model  | Input (per 1M) | Output (per 1M) |")
        lines.append("|--------|----------------|-----------------|")

        model_order = [
            ("haiku", "claude-3-5-haiku-20241022"),
            ("sonnet", "claude-sonnet-4-20250514"),
            ("opus", "claude-opus-4-20250514"),
        ]

        for short_name, model_id in model_order:
            prices = MODEL_PRICING.get(model_id, {"input_per_million": 0, "output_per_million": 0})
            input_per_m = prices["input_per_million"]
            output_per_m = prices["output_per_million"]
            lines.append(f"| {short_name:6} | €{input_per_m:<13.2f} | €{output_per_m:<15.2f} |")

        lines.append("\nUse /haiku, /sonnet, /opus to force a model.")

        return CommandResult(output="\n".join(lines))

    def _handle_unknown(self, input_text: str) -> CommandResult:
        """Handle unknown commands."""
        return CommandResult(
            output=f"Unknown command: {input_text}. Type /help for available commands."
        )
