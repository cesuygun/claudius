<p align="center">
  <h1 align="center">⚔️ Claudius 🛡️</h1>
  <p align="center"><strong>Your AI Budget Guardian</strong></p>
  <p align="center">Smart Claude API cost management with auto-routing</p>
</p>

<p align="center">
  <a href="https://github.com/cesuygun/claudius/stargazers"><img src="https://img.shields.io/github/stars/cesuygun/claudius?style=social" alt="Stars"></a>
  <a href="https://github.com/cesuygun/claudius/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://pypi.org/project/claudius/"><img src="https://img.shields.io/pypi/v/claudius.svg" alt="PyPI"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
</p>

---

## The Problem

| Option | Issue |
|--------|-------|
| **Claude Max ($100/month)** | Pay even when you don't use it |
| **API pay-as-you-go** | No budget controls, easy to overspend |
| **LiteLLM** | Overkill - enterprise tool for 100+ providers |

**Claudius fills the gap**: Claude-focused, simple, smart budget management.

## Features

- 🧠 **Smart Routing** - Haiku handles simple queries, escalates to Sonnet/Opus when needed
- 💰 **Budget Limits** - Daily and monthly caps with warnings
- 🔄 **Rollover** - Unused budget carries to next month
- 📊 **Live Tracking** - See your spend in real-time
- 🔌 **Claude Code Compatible** - Works as a proxy for full integration

## Quick Start

```bash
# Install
pipx install claudius

# Set your API key
export ANTHROPIC_API_KEY=sk-...

# Run
claudius
```

## What It Looks Like

```
 ⚔️ ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗ 🛡️
     ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
     ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

  Your AI Budget Guardian • v1.0.0

  ─────────────────────────────────────────────

  💰 Monthly  [████████████████░░░░]  €73.20/€90 (81%)
  📅 Today    [█████████░░░░░░░░░░░]  €2.30/€5  (46%)
  🔄 Rollover: €12.00  |  ⏰ Resets: 14 days

  ─────────────────────────────────────────────

  You: What's the best way to handle auth?

  🤖 [Haiku]: For authentication, I recommend...

  💰 €72.90/€90 [████████████████░░░░] 81%

  You:
```

## Smart Routing

Claudius uses Haiku as a gatekeeper. Simple queries stay with Haiku (€0.001), complex ones escalate:

```
Your Query
    │
    ▼
┌────────┐
│ Haiku  │──── "Can I handle this?"
└────────┘
    │
    ├── YES → Haiku answers (€0.001)
    │
    └── NO → "How complex?"
            │
            ├── Medium → Sonnet (€0.03)
            └── Hard → Opus (€0.30)
```

## Claude Code Integration

Use Claudius as a proxy for Claude Code - get budget tracking with all your skills:

```bash
# Terminal 1: Start Claudius
claudius

# Terminal 2: Point Claude Code to Claudius
export ANTHROPIC_BASE_URL=http://localhost:4000
claude
```

## Commands

| Command | Description |
|---------|-------------|
| `/status` | Show budget status |
| `/logs` | View usage history |
| `/opus` | Force Opus for next query |
| `/sonnet` | Force Sonnet for next query |
| `/haiku` | Force Haiku for next query |
| `/auto` | Return to auto routing |
| `/config` | Open configuration |
| `/help` | Show all commands |

## Configuration

Config file: `~/.claudius/config.toml`

```toml
[budget]
monthly = 90
daily_soft = 5
daily_hard = 10
rollover = true
currency = "EUR"

[routing]
default = "haiku"
auto_classify = true

[proxy]
port = 4000
```

## Support Claudius

If Claudius saves you money, consider supporting development:

- ☕ [Buy me a coffee on Ko-fi](https://ko-fi.com/cesuygun)

## Star History

If you find Claudius useful, please ⭐ star this repo - it helps others discover it!

## License

MIT - see [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/cesuygun">@cesuygun</a> · A project by <strong>IdeaVista</strong></sub>
</p>
