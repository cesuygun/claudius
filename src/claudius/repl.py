# ABOUTME: Interactive REPL for Claudius that ties together all components
# ABOUTME: Handles UI, slash commands, and chat interface with Claude API

"""
Claudius Interactive REPL.

Main entry point for interactive chat with Claude API, featuring:
- ASCII banner on startup
- Budget progress bars
- Slash command handling
- Streaming chat responses
- History support
- Interactive confirmation before sending
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import button_dialog, radiolist_dialog
from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.chat import ChatClient, ChatError
from claudius.commands import CommandHandler
from claudius.config import Config
from claudius.estimation import EstimationResult, estimate_cost
from claudius.ui import (
    get_currency_symbol,
    render_banner,
    render_budget_alert,
    render_budget_bars,
    render_cost_estimate,
    render_cost_line,
    render_response,
)


@dataclass
class ConfirmationResult:
    """Result of the send confirmation dialog."""

    action: Literal["send", "change", "cancel"]
    model: str | None = None  # New model if action is "change"


class ClaudiusREPL:
    """Interactive REPL for Claudius."""

    def __init__(self, tracker: BudgetTracker, config: Config, api_key: str):
        """Initialize the REPL with required dependencies.

        Args:
            tracker: Budget tracker for recording usage
            config: Configuration settings
            api_key: Anthropic API key
        """
        self.tracker = tracker
        self.config = config
        self.api_key = api_key
        self.console = Console()

        # Build proxy URL from config
        proxy_url = f"http://{config.proxy.host}:{config.proxy.port}"
        self.chat_client = ChatClient(proxy_url=proxy_url, api_key=api_key)

        self.command_handler = CommandHandler(tracker, config, self.console)

        # Set up history file
        history_path = Path.home() / ".claudius" / "history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.session: PromptSession[str] = PromptSession(
            history=FileHistory(str(history_path))
        )

        # Flag to control whether to show confirmation dialog
        self.skip_confirmation = False

    async def _show_confirmation_dialog(
        self,
        estimation: EstimationResult,
        model: str,
        currency: str,
    ) -> ConfirmationResult:
        """Show interactive confirmation dialog before sending message.

        Args:
            estimation: Cost estimation result
            model: Currently selected model
            currency: Currency code for display

        Returns:
            ConfirmationResult with action and optional new model
        """
        symbol = get_currency_symbol(currency)
        total_min = estimation.input_cost + estimation.output_cost_min
        total_max = estimation.input_cost + estimation.output_cost_max

        # Format the cost estimate text for the dialog
        cost_text = (
            f"Estimated cost: {symbol}{total_min:.4f} - {symbol}{total_max:.4f}\n"
            f"Input: {symbol}{estimation.input_cost:.4f} (exact) | "
            f"Output: {symbol}{estimation.output_cost_min:.4f}-{symbol}{estimation.output_cost_max:.4f} (est)\n"
            f"Model: {model.title()}"
        )

        # Show the confirmation dialog using async version
        result = await button_dialog(
            title="Confirm Send",
            text=cost_text,
            buttons=[
                ("Send", "send"),
                ("Change Model", "change"),
                ("Cancel", "cancel"),
            ],
        ).run_async()

        if result == "change":
            # Show model selection dialog using async version
            new_model = await radiolist_dialog(
                title="Select Model",
                text="Choose a model for this message:",
                values=[
                    ("haiku", "Haiku (cheapest)"),
                    ("sonnet", "Sonnet (balanced)"),
                    ("opus", "Opus (most capable)"),
                ],
                default=model,
            ).run_async()

            if new_model is None:
                # User cancelled model selection, treat as cancel
                return ConfirmationResult(action="cancel")

            return ConfirmationResult(action="change", model=new_model)

        # Validate result and return appropriate action
        if result == "send":
            return ConfirmationResult(action="send")
        return ConfirmationResult(action="cancel")

    async def run(self) -> None:
        """Run the REPL loop."""
        # Show banner on startup
        self.console.print(render_banner())

        # Show budget status
        self.console.print(render_budget_bars(self.tracker, self.config))

        # Main loop
        while True:
            try:
                user_input = await self.session.prompt_async("You: ")

                # Skip empty or whitespace-only input
                if not user_input or not user_input.strip():
                    continue

                # Check if it's a command
                result = self.command_handler.handle(user_input)
                if result is not None:
                    if result.should_exit:
                        break
                    if result.output:
                        self.console.print(result.output)
                    continue

                # It's a chat message - send to Claude
                try:
                    # Check daily hard limit before sending
                    hard_limit_exceeded = self.tracker.is_daily_hard_limit_exceeded(
                        self.config.budget.daily_hard
                    )

                    # Get routing decision to determine model
                    if self.command_handler.current_model_override:
                        target_model = self.command_handler.current_model_override
                        # Warn user if overriding despite hard limit
                        if hard_limit_exceeded and target_model != "haiku":
                            self.console.print(
                                f"[yellow]Daily hard limit exceeded but using {target_model} as requested[/yellow]"
                            )
                    elif hard_limit_exceeded:
                        # Force haiku when hard limit exceeded and no override
                        target_model = "haiku"
                        self.console.print(
                            "[yellow]Daily hard limit reached - using Haiku only[/yellow]"
                        )
                        # Set override to enforce haiku
                        self.command_handler.current_model_override = "haiku"
                    else:
                        decision = self.chat_client.router.classify(user_input)
                        target_model = decision.model

                    # Map short model name to full model ID
                    model_id = self.chat_client.MODEL_IDS.get(
                        target_model, self.chat_client.MODEL_IDS["sonnet"]
                    )

                    # Build messages for estimation (include conversation history)
                    messages_for_estimation = list(self.chat_client.conversation)
                    messages_for_estimation.append(
                        {"role": "user", "content": user_input}
                    )

                    # Confirmation loop - allows model change and re-estimation
                    should_send = False
                    while not should_send:
                        # Estimate cost for current model
                        estimation = await estimate_cost(
                            messages=messages_for_estimation,
                            model=model_id,
                            api_key=self.api_key,
                        )

                        # Show cost estimate before sending
                        self.console.print(
                            render_cost_estimate(
                                input_cost=estimation.input_cost,
                                output_cost_min=estimation.output_cost_min,
                                output_cost_max=estimation.output_cost_max,
                                model=target_model,
                                currency=self.config.budget.currency,
                            )
                        )

                        # Show confirmation dialog unless skipped
                        if self.skip_confirmation:
                            should_send = True
                        else:
                            confirmation = await self._show_confirmation_dialog(
                                estimation=estimation,
                                model=target_model,
                                currency=self.config.budget.currency,
                            )

                            if confirmation.action == "send":
                                should_send = True
                            elif confirmation.action == "cancel":
                                # Break out and continue to next input
                                break
                            elif confirmation.action == "change" and confirmation.model:
                                # Update model and re-estimate
                                target_model = confirmation.model
                                model_id = self.chat_client.MODEL_IDS.get(
                                    target_model, self.chat_client.MODEL_IDS["sonnet"]
                                )
                                # Update the override to use the new model
                                self.command_handler.current_model_override = target_model
                                # Loop back to re-estimate with new model

                    # Skip sending if user cancelled
                    if not should_send:
                        # Clear model override on cancel
                        self.command_handler.current_model_override = None
                        continue

                    response = await self.chat_client.send_message(
                        user_input,
                        model_override=self.command_handler.current_model_override,
                        console=self.console,
                    )

                    # Display response
                    self.console.print(render_response(response.model, response.text))

                    # Show routing info (helps understand model selection)
                    if response.routed_by and response.routed_by != "default":
                        self.console.print(
                            f"[dim]Routed via {response.routed_by}[/dim]"
                        )

                    # Record usage in tracker
                    self.tracker.record_usage(
                        model=response.model,
                        input_tokens=response.input_tokens,
                        output_tokens=response.output_tokens,
                        cost=response.cost,
                        routed_by="repl",
                        query_preview=user_input[:100] if user_input else None,
                    )

                    # Update cost display
                    self.console.print(render_cost_line(self.tracker, self.config))

                    # Check for budget alerts (80% threshold)
                    status = self.tracker.get_status(
                        self.config.budget.monthly,
                        self.config.budget.daily_soft,
                    )

                    if status.daily_percent >= 80:
                        self.console.print(
                            render_budget_alert(
                                "daily",
                                status.daily_percent,
                                status.daily_spent,
                                status.daily_budget,
                                self.config.budget.currency,
                            )
                        )

                    if status.monthly_percent >= 80:
                        self.console.print(
                            render_budget_alert(
                                "monthly",
                                status.monthly_percent,
                                status.monthly_spent,
                                status.monthly_budget,
                                self.config.budget.currency,
                            )
                        )

                except ChatError as e:
                    self.console.print(f"[red]Error: {e}[/red]")

                # Clear model override after use
                self.command_handler.current_model_override = None

            except KeyboardInterrupt:
                break  # Ctrl+C exits
            except EOFError:
                break  # Ctrl+D exits
