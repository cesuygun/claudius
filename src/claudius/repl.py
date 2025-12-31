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
"""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from claudius.budget import BudgetTracker
from claudius.chat import ChatClient, ChatError
from claudius.commands import CommandHandler
from claudius.config import Config
from claudius.estimation import estimate_cost
from claudius.ui import (
    render_banner,
    render_budget_alert,
    render_budget_bars,
    render_cost_estimate,
    render_cost_line,
    render_response,
)


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
                    # Get routing decision to determine model
                    if self.command_handler.current_model_override:
                        target_model = self.command_handler.current_model_override
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

                    # Estimate cost and show to user
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
                continue  # Ctrl+C cancels current input
            except EOFError:
                break  # Ctrl+D exits
