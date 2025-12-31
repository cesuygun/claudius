# ABOUTME: Rich-based UI components for Claudius REPL
# ABOUTME: Provides budget progress bars, status display, and formatted output

"""
Claudius UI Components.

Renders budget information and responses using the Rich library:
- ASCII banner on startup
- Progress bars for monthly/daily budgets
- Detailed status display
- Formatted model responses
- Compact cost update line
"""

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from claudius.budget import BudgetTracker
from claudius.config import Config

VERSION = "1.0.0"

BANNER_ASCII = """
   ⚔️  ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗  🛡️
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝
"""

CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "JPY": "¥",
}


def get_currency_symbol(currency: str) -> str:
    """Get currency symbol from currency code."""
    return CURRENCY_SYMBOLS.get(currency.upper(), currency)


def get_color_for_percent(percent: float) -> str:
    """Get color based on percentage threshold.

    - Green: Under 50%
    - Yellow: 50-80%
    - Red: Over 80%
    """
    if percent >= 80:
        return "red"
    elif percent >= 50:
        return "yellow"
    return "green"


def render_banner() -> RenderableType:
    """Render the ASCII art banner for startup.

    Returns a Rich renderable containing the CLAUDIUS ASCII art
    and tagline with version information. Uses raw Text without
    Panel wrapper for better terminal compatibility.
    """
    banner_text = Text()
    banner_text.append(BANNER_ASCII, style="bold cyan")
    banner_text.append("\n   Your AI Budget Guardian", style="bold white")
    banner_text.append(" • ", style="dim")
    banner_text.append(f"v{VERSION}", style="cyan")
    banner_text.append("\n")

    return banner_text


def render_budget_bars(tracker: BudgetTracker, config: Config) -> RenderableType:
    """Render budget progress bars with color coding.

    Shows monthly and daily budgets with visual progress bars.
    Color coding:
    - Green: Under 50%
    - Yellow: 50-80%
    - Red: Over 80%
    """
    status = tracker.get_status(
        monthly_budget=config.budget.monthly,
        daily_budget=config.budget.daily_soft,
    )

    symbol = get_currency_symbol(config.budget.currency)

    # Create table for budget bars
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("icon", width=2)
    table.add_column("label", width=8)
    table.add_column("bar", width=24)
    table.add_column("values", width=25)

    # Monthly budget row
    monthly_color = get_color_for_percent(status.monthly_percent)
    monthly_bar = Text()
    monthly_bar.append("│ ", style="dim")
    monthly_bar.append(status.monthly_bar, style=monthly_color)
    monthly_bar.append(" │", style="dim")

    monthly_values = Text()
    monthly_values.append(f"{symbol}{status.monthly_spent:.2f}", style=monthly_color)
    monthly_values.append(f"/{symbol}{status.monthly_budget:.0f}", style="dim")
    monthly_values.append(f" ({status.monthly_percent:.0f}%)", style=monthly_color)

    table.add_row("💰", "Monthly", monthly_bar, monthly_values)

    # Daily budget row
    daily_color = get_color_for_percent(status.daily_percent)
    daily_bar = Text()
    daily_bar.append("│ ", style="dim")
    daily_bar.append(status.daily_bar, style=daily_color)
    daily_bar.append(" │", style="dim")

    daily_values = Text()
    daily_values.append(f"{symbol}{status.daily_spent:.2f}", style=daily_color)
    daily_values.append(f"/{symbol}{status.daily_budget:.0f}", style="dim")
    daily_values.append(f" ({status.daily_percent:.0f}%)", style=daily_color)

    table.add_row("📅", "Today", daily_bar, daily_values)

    # Rollover and reset info row - use a separate text block with no_wrap
    rollover_line = Text(no_wrap=True)
    rollover_line.append("🔄 Rollover: ", style="dim")
    rollover_line.append(f"{symbol}{status.rollover:.2f}", style="cyan")
    rollover_line.append(" │ ", style="dim")
    rollover_line.append("⏰ Resets: ", style="dim")
    rollover_line.append(f"{status.days_until_reset} days", style="cyan")

    # Add rollover as a full-width row spanning all columns
    from rich.console import Group

    return Group(table, rollover_line)


def render_status(tracker: BudgetTracker, config: Config) -> RenderableType:
    """Render detailed budget status for /status command.

    Shows a tree view of budget information including:
    - Monthly budget (spent / total with percentage)
    - Daily budget (spent / total with percentage)
    - Rollover amount
    - Days until reset
    """
    status = tracker.get_status(
        monthly_budget=config.budget.monthly,
        daily_budget=config.budget.daily_soft,
    )

    symbol = get_currency_symbol(config.budget.currency)

    tree = Tree("📊 Budget Status", style="bold")

    # Monthly
    monthly_color = get_color_for_percent(status.monthly_percent)
    monthly_text = Text()
    monthly_text.append("Monthly: ", style="bold")
    monthly_text.append(
        f"{symbol}{status.monthly_spent:.2f} / {symbol}{status.monthly_budget:.2f}",
        style=monthly_color,
    )
    monthly_text.append(f" ({status.monthly_percent:.0f}%)", style=monthly_color)
    tree.add(monthly_text)

    # Daily (Today)
    daily_color = get_color_for_percent(status.daily_percent)
    daily_text = Text()
    daily_text.append("Today: ", style="bold")
    daily_text.append(
        f"{symbol}{status.daily_spent:.2f} / {symbol}{status.daily_budget:.2f}",
        style=daily_color,
    )
    daily_text.append(f" ({status.daily_percent:.0f}%)", style=daily_color)
    tree.add(daily_text)

    # Rollover
    rollover_text = Text()
    rollover_text.append("Rollover: ", style="bold")
    rollover_text.append(f"{symbol}{status.rollover:.2f}", style="cyan")
    tree.add(rollover_text)

    # Reset
    reset_text = Text()
    reset_text.append("Resets: ", style="bold")
    reset_text.append(f"{status.days_until_reset} days", style="cyan")
    tree.add(reset_text)

    return tree


def render_response(model: str, text: str) -> RenderableType:
    """Render Claude's response with model indicator.

    Shows the model name in brackets followed by the response text.
    """
    response = Text()
    response.append("🤖 ", style="bold")
    response.append(f"[{model}]", style="bold cyan")
    response.append(": ", style="dim")
    response.append(text)

    return response


def render_cost_estimate(
    input_cost: float,
    output_cost_min: float,
    output_cost_max: float,
    model: str,
    currency: str,
) -> RenderableType:
    """Render pre-flight cost estimation before sending a message.

    Shows the estimated cost range based on exact input tokens and estimated
    output tokens, along with the model that will be used.

    Args:
        input_cost: Exact cost for input tokens
        output_cost_min: Minimum estimated cost for output tokens
        output_cost_max: Maximum estimated cost for output tokens
        model: Model name (short form like "haiku", "sonnet", "opus")
        currency: Currency code for symbol lookup

    Returns:
        Rich Text renderable with formatted cost estimation
    """
    symbol = get_currency_symbol(currency)
    total_min = input_cost + output_cost_min
    total_max = input_cost + output_cost_max

    text = Text()
    text.append("\n")
    text.append("   Estimated cost: ", style="dim")
    text.append(f"{symbol}{total_min:.4f} - {symbol}{total_max:.4f}", style="cyan bold")
    text.append("\n   Input: ", style="dim")
    text.append(f"{symbol}{input_cost:.4f}", style="green")
    text.append(" (exact)", style="dim")
    text.append(" | Output: ", style="dim")
    text.append(f"{symbol}{output_cost_min:.4f}-{symbol}{output_cost_max:.4f}", style="yellow")
    text.append(" (est)", style="dim")
    text.append("\n   Model: ", style="dim")
    text.append(f"{model.title()}", style="cyan")
    text.append("\n")

    return text


def render_budget_alert(
    alert_type: str,
    percent: float,
    spent: float,
    budget: float,
    currency: str,
) -> RenderableType:
    """Render budget warning alert.

    Shows a warning when budget reaches 80% threshold:
    - Daily alerts use yellow warning emoji
    - Monthly alerts use red alert emoji

    Args:
        alert_type: Either "daily" or "monthly"
        percent: Current percentage of budget used
        spent: Amount spent so far
        budget: Total budget amount
        currency: Currency code for symbol lookup

    Returns:
        Rich Text renderable with formatted alert message
    """
    symbol = get_currency_symbol(currency)

    if alert_type == "daily":
        emoji = "\u26a0\ufe0f"  # Warning sign
        label = "Daily budget"
        style = "yellow"
    else:
        emoji = "\U0001f6a8"  # Police car light / alert
        label = "Monthly budget"
        style = "red"

    text = Text()
    text.append(f"{emoji} ", style=f"bold {style}")
    text.append(f"{label} at {percent:.0f}%!", style=f"bold {style}")
    text.append(f" ({symbol}{spent:.2f}/{symbol}{budget:.2f})", style="dim")

    return text


def render_cost_line(tracker: BudgetTracker, config: Config) -> RenderableType:
    """Render compact cost update line after each response.

    Shows monthly spent/budget with progress bar, percentage, and daily spending.
    """
    status = tracker.get_status(
        monthly_budget=config.budget.monthly,
        daily_budget=config.budget.daily_soft,
    )

    symbol = get_currency_symbol(config.budget.currency)
    monthly_color = get_color_for_percent(status.monthly_percent)

    line = Text()
    line.append("💰 ", style="bold")
    line.append(f"{symbol}{status.monthly_spent:.2f}", style=monthly_color)
    line.append(f"/{symbol}{status.monthly_budget:.0f}", style="dim")
    line.append(" ", style="dim")
    line.append(status.monthly_bar, style=monthly_color)
    line.append(" ", style="dim")
    line.append(f"{status.monthly_percent:.0f}%", style=monthly_color)
    line.append(" │ ", style="dim")
    line.append("Today: ", style="dim")

    daily_color = get_color_for_percent(status.daily_percent)
    line.append(f"{symbol}{status.daily_spent:.2f}", style=daily_color)
    line.append(f"/{symbol}{status.daily_budget:.0f}", style="dim")

    return line
