<p align="center">
  <h1 align="center">⚔️ Claudius 🛡️</h1>
  <p align="center"><strong>Your AI Budget Guardian</strong></p>
  <p align="center">Budget tracking & smart routing for Claude Code</p>
</p>

<p align="center">
  <a href="https://github.com/cesuygun/claudius/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
</p>

---

## What is Claudius?

Claudius is a **budget guardian** for Claude Code. It sits between you and the Anthropic API, tracking your spending and automatically routing queries to the cheapest model that can handle them.

**Without Claudius:** Claude Code uses expensive models for everything → surprise bills

**With Claudius:** Smart routing saves money, budget limits prevent overspending

## Quick Start (3 steps)

```bash
# 1. Install
pip install claudius

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# 3. Enable Claudius for Claude Code
claudius enable
```

That's it! Now use Claude Code normally - Claudius handles the rest.

## Usage

### For Claude Code (recommended)

```bash
# One-time setup
claudius enable    # Configure Claude Code to use Claudius

# Every time you code
claudius proxy     # Start this first, keep it running
claude             # Use Claude Code normally in another terminal
```

### Standalone Chat

```bash
claudius           # Interactive chat with budget tracking
```

### Switching Modes

```bash
claudius enable    # Use Claudius (budget tracking ON)
claudius disable   # Bypass Claudius (direct to Anthropic)
```

## Commands

| Command | What it does |
|---------|--------------|
| `claudius` | Start chat mode with budget display |
| `claudius proxy` | Run proxy only (for Claude Code) |
| `claudius enable` | Configure Claude Code to use Claudius |
| `claudius disable` | Configure Claude Code to bypass Claudius |

### Chat Commands

When in chat mode, use these slash commands:

| Command | Description |
|---------|-------------|
| `/status` | Show budget status |
| `/models` | Show available models and pricing |
| `/opus` | Force Opus for next query |
| `/sonnet` | Force Sonnet for next query |
| `/haiku` | Force Haiku for next query |
| `/help` | Show all commands |

## Smart Routing

Claudius automatically picks the cheapest model that can handle your query:

| Query Type | Model | Cost |
|------------|-------|------|
| Simple questions | Haiku | ~€0.001 |
| Code review, medium tasks | Sonnet | ~€0.03 |
| Architecture, complex analysis | Opus | ~€0.30 |

## Configuration

Config file: `~/.claudius/config.toml`

```toml
[api]
key = ""  # Or use ANTHROPIC_API_KEY env var

[budget]
monthly = 90        # Monthly limit in EUR
daily_soft = 5      # Warning threshold
daily_hard = 10     # Force Haiku above this

[proxy]
host = "127.0.0.1"
port = 4000
```

## How It Works

```
┌─────────────┐     ┌──────────┐     ┌───────────┐
│ Claude Code │────▶│ Claudius │────▶│ Anthropic │
└─────────────┘     └──────────┘     └───────────┘
                         │
                    ┌────┴────┐
                    │ Budget  │
                    │Tracking │
                    │ + Smart │
                    │ Routing │
                    └─────────┘
```

## License

MIT - see [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ by the Claudius Contributors</sub>
</p>
