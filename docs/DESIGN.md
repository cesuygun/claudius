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

### 1. Pre-flight Cost Estimation

Before every request, Claudius shows you what it will cost:

```
You: How do I implement authentication in FastAPI?

📊 Estimated cost: €0.02 - €0.08
   Input: €0.01 (exact) | Output: €0.01-0.07 (estimated)
   Model: Haiku (auto-selected)

[Send] [Change Model] [Cancel]
```

**How it works:**
- **Input tokens**: 100% accurate - counted before sending using tokenizer
- **Output tokens**: Estimated range based on:
  - Query type heuristics (yes/no → short, code gen → long)
  - Model tendencies (Haiku concise, Opus verbose)
  - Your historical usage patterns
- **Display**: Always show a range, never a false precision single number

**In proxy mode (Claude Code):**
- Cost tracked and shown in status line after response
- Pre-flight estimation available via `claudius estimate` command

### 2. Smart Model Routing (Haiku Gatekeeper)

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

### 3. Budget Management

| Feature | Description |
|---------|-------------|
| Monthly limit | Hard cap (e.g., €90/month) |
| Daily soft limit | Warning threshold (e.g., €5/day) |
| Daily hard limit | Downgrades to cheaper models (e.g., €10/day) |
| Rollover | Unused budget carries to next month |
| Daily → Weekly pool | Unused daily allowance accumulates |

### 4. Interactive CLI with Slash Commands

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

### 5. Claude Code Integration (Proxy Mode)

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

### 6. Claude Code Status Line Integration

Claude Code supports custom status lines! Claudius can show budget info directly in Claude Code's UI:

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code                                              │
│                                                          │
│ You: Help me refactor this...                           │
│ 🤖: Sure, let me...                                     │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ 💰 €2.30/€5 today | €73/€90 month | [Haiku] | main      │
└─────────────────────────────────────────────────────────┘
```

**Setup:** Add to `~/.claude/settings.json`:
```json
{
  "statusLine": {
    "type": "command",
    "command": "claudius status-line"
  }
}
```

**How it works:**
1. Claude Code sends JSON with token/cost data to stdin
2. `claudius status-line` reads it, adds budget tracking info
3. Outputs formatted status line to stdout
4. Updates in real-time (max every 300ms)

**Data available from Claude Code:**
- `cost.total_cost_usd` - Running session cost
- `cost.total_duration_ms` - Session duration
- `context_window.total_input_tokens` / `total_output_tokens`
- `context_window.current_usage` - Current context state

### 7. Rate Limit Handling

Claudius handles Anthropic API rate limits gracefully:

```
⏳ Rate limited - retrying in 5s (attempt 1/3)
⏳ Rate limited - retrying in 15s (attempt 2/3)
✓ Request succeeded after retry
```

**Features:**
- **Automatic retry**: Exponential backoff (5s → 15s → 45s)
- **Queue management**: Requests queue instead of failing
- **Transparent to user**: Claude Code doesn't see errors, just slightly delayed responses
- **Configurable**: Max retries, backoff multiplier in config

**Why this matters:**
- Heavy Claude Code sessions hit rate limits
- Currently you get cryptic errors and have to retry manually
- Claudius absorbs this complexity

### 8. Claude Code Hooks Integration

Use hooks for advanced tracking:

**PostToolUse Hook** - Track after each tool call:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "*",
      "command": "claudius track-usage"
    }]
  }
}
```

**Stop Hook** - Log when response finishes:
```json
{
  "hooks": {
    "Stop": [{
      "command": "claudius log-response"
    }]
  }
}
```

**Potential uses:**
- Real-time cost alerts ("⚠️ This response cost €0.50!")
- Session summaries
- Usage logging to external systems

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

## 🧠 Brainstorm: Ideas to Consider Before Building

### Smart Routing Enhancements

| Idea | Description | Priority |
|------|-------------|----------|
| **Context-aware routing** | If conversation already used Opus, stay with Opus for continuity | Medium |
| **File-type routing** | Python files → Sonnet, architecture docs → Opus | Low |
| **Time-of-day routing** | Cheaper models during non-work hours | Low |
| **Retry with escalation** | If Haiku fails/gives poor answer, auto-retry with Sonnet | High |
| **User feedback loop** | "Was this answer good?" → improves routing over time | Future |

### Budget Features

| Idea | Description | Priority |
|------|-------------|----------|
| **Budget inheritance** | Daily unused → weekly pool → monthly pool | High |
| **Emergency reserve** | Keep €5 always available for urgent queries | Medium |
| **Project budgets** | Different budgets per git repo/project | Medium |
| **Spending velocity alerts** | "You're spending 3x faster than usual today" | Medium |
| **Predicted runout** | "At this rate, budget runs out in 6 days" | High |

### Cost Optimization Features (v1.1)

| Idea | Description | Priority |
|------|-------------|----------|
| **Semantic caching** | Cache responses to identical/similar queries. Different from Anthropic's prompt caching (which caches conversation context). This caches actual responses across sessions. | High |
| **Cache similarity threshold** | How similar must queries be to return cached response? (exact match vs fuzzy) | Medium |
| **Cache TTL** | How long to keep cached responses valid | Medium |
| **Cache storage** | SQLite for small, Redis for large deployments | Low |

### UX Ideas

| Idea | Description | Priority |
|------|-------------|----------|
| **Quick budget check** | `claudius` with no args shows status, doesn't start REPL | High |
| **Desktop notifications** | macOS/Linux notifications for budget alerts | Medium |
| **Sound alerts** | Optional beep when hitting limits | Low |
| **Color themes** | Match terminal theme (dark/light) | Low |
| **Compact mode** | Minimal UI for small terminals | Medium |

### Integration Ideas

| Idea | Description | Priority |
|------|-------------|----------|
| **Claude Code plugin** | Package as official plugin for easy install | High |
| **VS Code extension** | Show budget in VS Code status bar | Future |
| **Raycast/Alfred** | Quick budget check from launcher | Low |
| **iOS Shortcut** | Check budget from phone | Future |
| **Telegram/Discord bot** | Budget alerts and status | Low |

### Data & Analytics

| Idea | Description | Priority |
|------|-------------|----------|
| **Usage patterns** | "You use most tokens on Mondays" | Future |
| **Model efficiency** | "Haiku handled 73% of your queries" | Medium |
| **Cost per project** | Track spending by git repo | Medium |
| **Export to CSV** | For expense reports | Medium |
| **Grafana dashboard** | For power users | Future |

### Security & Privacy

| Idea | Description | Priority |
|------|-------------|----------|
| **Query preview opt-out** | Don't store query text, only metadata | High |
| **Local-only mode** | Never send anything to external services | Default |
| **API key rotation** | Support multiple keys, rotate on limits | Medium |
| **Encrypted storage** | Encrypt SQLite db | Low |

### Edge Cases to Handle

| Scenario | How to Handle |
|----------|---------------|
| Proxy crashes mid-request | Queue request, restart proxy, retry |
| API returns error | Don't count against budget |
| Clock/timezone changes | Use UTC internally |
| Multiple Claudius instances | File lock on SQLite |
| Very long responses | Stream cost updates |
| Offline mode | Queue requests? Or just fail gracefully |

### CLI Subcommands to Add

```bash
claudius                    # Interactive mode + proxy (default)
claudius status             # Quick budget check (no REPL)
claudius status-line        # For Claude Code integration (stdin/stdout)
claudius history [days]     # Show usage history
claudius export [format]    # Export to CSV/JSON
claudius config             # Open config in $EDITOR
claudius reset-daily        # Manual daily reset (for testing)
claudius doctor             # Diagnose issues
```

### Things NOT to Build (Keep It Simple)

- ❌ Web dashboard (v1) - CLI is enough
- ❌ User accounts/auth - It's a local tool
- ❌ Multi-provider support (v1) - Claude-only first
- ❌ Complex ML routing - Heuristics + Haiku is enough
- ❌ Mobile app - Overkill
- ❌ Cloud sync - Local-first philosophy

---

## Implementation Priority for v1.0

### Must Have (MVP)
1. Proxy server that works with Claude Code
2. Basic budget tracking (daily/monthly)
3. SQLite storage ✅ (implemented)
4. Simple config file ✅ (implemented)
5. Status line command for Claude Code
6. **Pre-flight cost estimation** (input exact, output range)
7. **Rate limit handling** (automatic retry with backoff)

### Should Have (v1.0)
1. Smart routing (Haiku gatekeeper)
2. Rollover budgets
3. Interactive REPL mode
4. Progress bars and nice UI

### Nice to Have (v1.1+)
1. **Semantic caching** - Cache responses to avoid paying twice for identical queries
2. Hooks integration
3. Export functionality
4. Desktop notifications
5. Project-based budgets

---

*Designed by Doctor Biz & Opus • December 2024*
*Updated: December 2025 - Added pre-flight estimation, rate limit handling, semantic caching roadmap*
