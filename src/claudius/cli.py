# ABOUTME: Interactive CLI for Claudius
# ABOUTME: Provides REPL interface with slash commands and budget display

"""
Claudius CLI - Interactive mode with slash commands.

Features:
- Interactive REPL with prompt_toolkit
- Budget status bar with progress indicators
- Slash commands (/status, /opus, /sonnet, etc.)
- Rich terminal UI with colors and formatting
"""

from rich.console import Console
from rich.panel import Panel

console = Console()

LOGO = r"""
   ⚔️  ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗  🛡️
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

   Your AI Budget Guardian • v0.1.0
"""


def print_banner() -> None:
    """Print the Claudius startup banner."""
    console.print(Panel(LOGO, border_style="blue"))


def main() -> None:
    """Main entry point for Claudius CLI."""
    print_banner()
    console.print("\n[yellow]🚧 Claudius is under construction![/yellow]")
    console.print("[dim]Coming soon: budget tracking, smart routing, and more.[/dim]\n")


if __name__ == "__main__":
    main()
