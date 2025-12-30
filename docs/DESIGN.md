# Claudius - Your AI Budget Guardian

> "LiteLLM is an aircraft carrier. Claudius is a speedboat."

## Overview

Claudius is a smart Claude API budget manager that provides intelligent model routing, budget tracking with rollover, and a beautiful CLI experience. It acts as a proxy between you and the Anthropic API, making pay-as-you-go viable for power users.

## The Problem

- **Max plan ($100/month)**: Flat rate, but you pay even when you don't use it
- **API pay-as-you-go**: Flexible, but no budget controls, easy to overspend
- **LiteLLM**: Powerful but overkill - enterprise tool for 100+ providers

**Claudius fills the gap**: Claude-focused, simple, smart budget management.

## Core Features

### 1. Smart Model Routing (Haiku Gatekeeper)

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
            │
            └── Hard → Opus (€0.30)
```

Haiku acts as gatekeeper AND cheap workhorse. Only escalates what it can't handle.

**Heuristics layer (free, runs first):**
- Very short message (<20 words) → Haiku
- Contains code blocks → Sonnet minimum
- Keywords: "architect", "design", "complex" → Opus

### 2. Budget Management

| Feature | Description |
|---------|-------------|
| Monthly limit | Hard cap (e.g., €90/month) |
| Daily soft limit | Warning threshold (e.g., €5/day) |
| Daily hard limit | Downgrades to cheaper models (e.g., €10/day) |
| Rollover | Unused budget carries to next month |
| Daily → Weekly pool | Unused daily allowance accumulates |

### 3. Interactive CLI with Slash Commands

```bash
$ claudius

   ⚔️  ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗  🛡️
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

   Your AI Budget Guardian • v1.0.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Monthly │ ████████████████░░░░ │ €73.20/€90 (81%)
📅 Today   │ █████████░░░░░░░░░░░ │ €2.30/€5  (46%)
🔄 Rollover: €12.00 │ ⏰ Resets: 14 days

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You: What's the best way to handle auth?

🤖 [Haiku]: For authentication, I recommend...

💰 €72.90/€90 ████████████████░░░░ 81% │ Today: €2.40/€5

You: /status

📊 Budget Status
├─ Monthly: €73.20 / €90.00 (81%)
├─ Today: €2.30 / €5.00 (46%)
├─ Rollover: €12.00
└─ Resets: 14 days

You: /opus
🔒 Forcing Opus for next query

You: /help
Available commands:
  /status     - Show budget status
  /config     - Open configuration
  /logs       - View usage history
  /opus       - Force Opus for next query
  /sonnet     - Force Sonnet for next query
  /haiku      - Force Haiku for next query
  /auto       - Return to automatic routing
  /quit       - Exit Claudius
```

### 4. Claude Code Integration (Proxy Mode)

Claudius automatically starts a proxy server that Claude Code can use:

```bash
# Terminal 1
$ claudius
🏛️ Claudius starting...
   ├─ Proxy: localhost:4000 ✓
   ├─ Budget loaded ✓
   └─ Ready!

# Terminal 2 - Claude Code uses the proxy
$ export ANTHROPIC_BASE_URL=http://localhost:4000
$ claude   # All requests go through Claudius!
```

This gives you:
- ✅ All Claude Code features (skills, tools, file access)
- ✅ Budget tracking from Claudius
- ✅ Smart routing from Claudius

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLAUDIUS                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   CLI REPL   │  │    Proxy     │  │   Budget     │  │
│  │              │  │   Server     │  │   Tracker    │  │
│  │ - Interactive│  │   :4000      │  │              │  │
│  │ - Slash cmds │  │              │  │ - SQLite     │  │
│  │ - Progress   │  │ - Routes req │  │ - Rollover   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                 │                 │           │
│         └─────────────────┼─────────────────┘           │
│                           │                              │
│                  ┌────────┴────────┐                    │
│                  │  Smart Router   │                    │
│                  │                 │                    │
│                  │ - Heuristics    │                    │
│                  │ - Haiku classify│                    │
│                  │ - Model select  │                    │
│                  └────────┬────────┘                    │
│                           │                              │
└───────────────────────────┼──────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Anthropic API  │
                   │  (or LiteLLM)   │
                   └─────────────────┘
```

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python 3.11+ | LiteLLM compatibility, AI ecosystem |
| Config | TOML | Python standard, clean syntax |
| Storage | SQLite | Simple, portable, no setup |
| CLI | Rich | Beautiful terminal UI, progress bars |
| Proxy | LiteLLM or custom | Leverage existing work |
| HTTP | FastAPI | Async, fast, easy |

## Configuration

Location: `~/.claudius/config.toml`

```toml
[budget]
monthly = 90
daily_soft = 5
daily_hard = 10
rollover = true
max_rollover = 45  # Cap at 50% of monthly
currency = "EUR"

[routing]
default = "haiku"
escalate_to = ["sonnet", "opus"]
auto_classify = true

[routing.heuristics]
short_message_words = 20      # Under this → Haiku
code_block_minimum = "sonnet" # Code blocks → at least Sonnet
opus_keywords = ["architect", "design", "complex", "plan"]

[proxy]
host = "127.0.0.1"
port = 4000

[alerts]
daily_80_percent = true
monthly_80_percent = true
sound = false

[models]
# Override which models to use
haiku = "claude-3-5-haiku-20241022"
sonnet = "claude-sonnet-4-20250514"
opus = "claude-opus-4-20250514"
```

## Data Storage

Location: `~/.claudius/claudius.db`

### Tables

```sql
-- Track every API call
CREATE TABLE usage (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_eur REAL,
    routed_by TEXT,  -- 'heuristic', 'haiku', 'manual'
    original_query_preview TEXT
);

-- Track daily/monthly budgets
CREATE TABLE budget_periods (
    id INTEGER PRIMARY KEY,
    period_type TEXT,  -- 'daily', 'monthly'
    period_start DATE,
    period_end DATE,
    budget REAL,
    spent REAL,
    rollover_from REAL
);

-- Settings that might change
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

## CLI Commands Summary

| Command | Description |
|---------|-------------|
| `claudius` | Start interactive mode + proxy |
| `/status` | Show budget status |
| `/config` | Open config file |
| `/logs` | View usage history |
| `/logs 7d` | Last 7 days |
| `/opus` | Force Opus next query |
| `/sonnet` | Force Sonnet next query |
| `/haiku` | Force Haiku next query |
| `/auto` | Return to auto routing |
| `/models` | Show model costs |
| `/quit` | Exit |

## Progress Bar Color Coding

```
🟢 Under 50%:  ████████░░░░░░░░░░░░ 40%
🟡 50-80%:     █████████████░░░░░░░ 65%
🔴 Over 80%:   ██████████████████░░ 90%
```

## Future Features (v1.1+)

- [ ] `claudius serve --daemon` - Run as background service
- [ ] Web dashboard on `localhost:4200`
- [ ] Usage analytics and graphs
- [ ] Multiple profiles (work/personal)
- [ ] Cost predictions ("At this rate, you'll run out in 8 days")
- [ ] Export usage reports (CSV/JSON)
- [ ] Slack/Discord alerts

## Project Structure

```
claudius/
├── pyproject.toml
├── README.md
├── LICENSE (MIT)
├── src/
│   └── claudius/
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── cli.py           # Interactive REPL
│       ├── proxy.py         # API proxy server
│       ├── router.py        # Smart model routing
│       ├── budget.py        # Budget tracking
│       ├── config.py        # Config loading
│       ├── db.py            # SQLite operations
│       └── ui.py            # Rich UI components
├── tests/
│   ├── test_router.py
│   ├── test_budget.py
│   └── test_proxy.py
└── docs/
    └── README.md
```

## Installation (Target UX)

```bash
# Install from PyPI
pip install claudius

# Or with pipx (recommended)
pipx install claudius

# First run - creates config
claudius

# Configure your API key
export ANTHROPIC_API_KEY=sk-...

# Optional: Make Claude Code use Claudius
echo 'export ANTHROPIC_BASE_URL=http://localhost:4000' >> ~/.zshrc
```

## Success Metrics

1. **Works with Claude Code** - Full compatibility via proxy
2. **Saves money** - Users should see 30-50% cost reduction vs straight Opus
3. **Simple setup** - Under 5 minutes to first use
4. **Zero maintenance** - Set and forget

## Open Questions

1. Should we support other providers via LiteLLM, or stay Claude-only?
2. Should the proxy auto-start on system boot option?
3. Team features - shared budgets, multiple API keys?

---

*Designed by Doctor Biz & Opus • December 2024*
