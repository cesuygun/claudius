# Claudius Completion Plan - Bugs & Missing Features

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all bugs and implement missing features to complete Claudius MVP as designed.

**Architecture:** Fix cost tracking first (critical for testing), then build the Haiku gatekeeper router (core value prop), then polish UI and add remaining features.

**Tech Stack:** Python 3.11+, FastAPI, Rich, SQLite, httpx

---

## Summary of Issues

### Bugs (Broken)
| Issue | Severity | Root Cause |
|-------|----------|------------|
| Cost shows €0.00 in REPL | CRITICAL | Token counts may not be parsed from SSE |
| Rollover always 0 | HIGH | TODO comment in budget.py:170 |
| Banner looks wrong | MEDIUM | Terminal font issue (code is correct) |

### Missing Features
| Feature | Priority | Impact |
|---------|----------|--------|
| Smart Router (Haiku Gatekeeper) | CRITICAL | Core value proposition |
| Pre-flight cost estimation in REPL | HIGH | Show cost before sending |
| /models command | LOW | Show model pricing |
| Budget alerts (80% warnings) | MEDIUM | Warn before overspend |
| Daily hard limit enforcement | MEDIUM | Auto-downgrade models |

---

## Task 1: Debug and Fix Cost Tracking

**Goal:** Ensure costs are properly tracked and displayed in the REPL.

**Files:**
- Debug: `src/claudius/chat.py:115-147` (SSE parsing)
- Debug: `src/claudius/repl.py:93-104` (cost recording)
- Test: `tests/test_integration.py` (new)

**Step 1: Add debug logging to trace the issue**

Create a simple test script to verify SSE parsing:

```python
# debug_cost.py (temporary)
import asyncio
from claudius.chat import ChatClient

async def test():
    client = ChatClient(api_key="your-key")
    response = await client.send_message("Say hello in 5 words")
    print(f"Model: {response.model}")
    print(f"Input tokens: {response.input_tokens}")
    print(f"Output tokens: {response.output_tokens}")
    print(f"Cost: {response.cost}")

asyncio.run(test())
```

**Step 2: Fix SSE parsing if needed**

The issue may be in `chat.py:126` - `input_tokens` is read from `message_start` but may be under different path. Check actual Anthropic SSE format.

**Step 3: Verify cost flows through to tracker**

After `record_usage()` is called, verify database has the record:
```bash
sqlite3 ~/.claudius/claudius.db "SELECT * FROM usage ORDER BY id DESC LIMIT 5"
```

**Step 4: Commit fix**
```bash
git add src/claudius/chat.py
git commit -m "fix: correct SSE parsing for token counts"
```

---

## Task 2: Implement Rollover Budget Calculation

**Goal:** Calculate and display rollover from previous month.

**Files:**
- Modify: `src/claudius/budget.py:148-172`
- Test: `tests/test_budget.py`

**Step 1: Write the failing test**

```python
# In tests/test_budget.py
def test_rollover_calculation():
    """Rollover should be unused budget from previous month."""
    tracker = BudgetTracker(db_path=temp_db)

    # Simulate last month: budget 90, spent 70 = 20 rollover
    # (Insert records with last month timestamp)

    status = tracker.get_status(monthly_budget=90.0, daily_budget=5.0)
    assert status.rollover == 20.0  # 90 - 70 = 20
```

**Step 2: Implement rollover calculation**

```python
# In budget.py, update get_status method
def get_status(self, monthly_budget: float, daily_budget: float) -> BudgetStatus:
    # ... existing code ...

    # Calculate rollover from previous month
    rollover = self._calculate_rollover(monthly_budget)

    return BudgetStatus(
        # ... existing fields ...
        rollover=rollover,
        days_until_reset=days_until_reset,
    )

def _calculate_rollover(self, monthly_budget: float) -> float:
    """Calculate rollover from previous month."""
    now = datetime.now()

    # Get previous month
    if now.month == 1:
        prev_year, prev_month = now.year - 1, 12
    else:
        prev_year, prev_month = now.year, now.month - 1

    prev_spent = self.get_monthly_spent(prev_year, prev_month)
    unused = monthly_budget - prev_spent

    # Cap rollover at max_rollover (default 50% of monthly)
    max_rollover = monthly_budget * 0.5
    return max(0, min(unused, max_rollover))
```

**Step 3: Run test**
```bash
pytest tests/test_budget.py::test_rollover_calculation -v
```

**Step 4: Commit**
```bash
git add src/claudius/budget.py tests/test_budget.py
git commit -m "feat: implement rollover budget calculation"
```

---

## Task 3: Create Smart Router with Haiku Gatekeeper

**Goal:** Implement the core routing logic that makes Claudius valuable.

**Files:**
- Create: `src/claudius/router.py`
- Test: `tests/test_router.py`
- Modify: `src/claudius/chat.py` (integrate router)

**Step 1: Write failing tests for heuristics**

```python
# tests/test_router.py
import pytest
from claudius.router import SmartRouter, RouteDecision

class TestHeuristics:
    def test_short_message_routes_to_haiku(self):
        router = SmartRouter()
        decision = router.classify("What time is it?")
        assert decision.model == "haiku"
        assert decision.reason == "heuristic:short_message"

    def test_code_block_routes_to_sonnet(self):
        router = SmartRouter()
        message = "Review this code:\n```python\nprint('hello')\n```"
        decision = router.classify(message)
        assert decision.model == "sonnet"
        assert decision.reason == "heuristic:code_block"

    def test_opus_keywords_route_to_opus(self):
        router = SmartRouter()
        decision = router.classify("Design a complex distributed system architecture")
        assert decision.model == "opus"
        assert decision.reason == "heuristic:opus_keyword"

    def test_medium_message_needs_haiku_classification(self):
        router = SmartRouter()
        decision = router.classify("Explain how authentication works in web applications")
        assert decision.needs_classification == True
```

**Step 2: Implement SmartRouter class**

```python
# src/claudius/router.py
# ABOUTME: Smart model routing with heuristics and Haiku gatekeeper
# ABOUTME: Routes queries to cheapest capable model to save costs

"""
Claudius Smart Router.

Implements intelligent model routing:
1. Free heuristics layer (word count, code blocks, keywords)
2. Haiku classification for ambiguous cases
3. Model selection based on complexity
"""

from dataclasses import dataclass

@dataclass
class RouteDecision:
    """Result of routing decision."""
    model: str  # "haiku", "sonnet", "opus"
    reason: str  # "heuristic:short_message", "haiku:self_handle", etc.
    needs_classification: bool = False  # True if Haiku should classify

class SmartRouter:
    """Smart model router with heuristics and Haiku gatekeeper."""

    OPUS_KEYWORDS = ["architect", "design", "complex", "plan", "analyze", "comprehensive"]
    SHORT_MESSAGE_WORDS = 20

    def __init__(self):
        pass

    def classify(self, message: str) -> RouteDecision:
        """Classify message and decide which model to use.

        Routing logic:
        1. Very short message (<20 words) → Haiku
        2. Contains code blocks → Sonnet minimum
        3. Contains opus keywords → Opus
        4. Otherwise → needs Haiku classification
        """
        words = message.split()
        word_count = len(words)
        message_lower = message.lower()

        # Rule 1: Short messages go to Haiku
        if word_count < self.SHORT_MESSAGE_WORDS:
            return RouteDecision(model="haiku", reason="heuristic:short_message")

        # Rule 2: Code blocks need at least Sonnet
        if "```" in message:
            return RouteDecision(model="sonnet", reason="heuristic:code_block")

        # Rule 3: Opus keywords
        for keyword in self.OPUS_KEYWORDS:
            if keyword in message_lower:
                return RouteDecision(model="opus", reason=f"heuristic:opus_keyword:{keyword}")

        # Rule 4: Ambiguous - needs Haiku to classify
        return RouteDecision(
            model="haiku",
            reason="needs_classification",
            needs_classification=True
        )

    async def classify_with_haiku(self, message: str, api_key: str) -> RouteDecision:
        """Ask Haiku if it can handle this query or needs escalation.

        Returns decision with model and reason.
        """
        # Call Haiku with classification prompt
        classification_prompt = f'''You are a query classifier. Analyze this user query and decide:
- "HAIKU" if you can handle it (simple questions, basic info, short tasks)
- "SONNET" if it needs more capability (code review, medium complexity)
- "OPUS" if it needs deep reasoning (architecture, complex analysis, planning)

Reply with ONLY one word: HAIKU, SONNET, or OPUS

Query: {message}'''

        # Make lightweight call to Haiku
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": classification_prompt}]
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                answer = data["content"][0]["text"].strip().upper()

                if "OPUS" in answer:
                    return RouteDecision(model="opus", reason="haiku:classified_opus")
                elif "SONNET" in answer:
                    return RouteDecision(model="sonnet", reason="haiku:classified_sonnet")
                else:
                    return RouteDecision(model="haiku", reason="haiku:self_handle")

            # Fallback to Sonnet on error
            return RouteDecision(model="sonnet", reason="haiku:classification_error")
```

**Step 3: Run tests**
```bash
pytest tests/test_router.py -v
```

**Step 4: Commit**
```bash
git add src/claudius/router.py tests/test_router.py
git commit -m "feat: add SmartRouter with heuristics and Haiku gatekeeper"
```

---

## Task 4: Integrate Router into Chat Client

**Goal:** Use SmartRouter to automatically route messages.

**Files:**
- Modify: `src/claudius/chat.py`
- Modify: `src/claudius/repl.py`
- Test: `tests/test_chat.py`

**Step 1: Update ChatClient to use router**

```python
# In chat.py, add router integration
from claudius.router import SmartRouter

class ChatClient:
    def __init__(self, ...):
        # ... existing init ...
        self.router = SmartRouter()

    async def send_message(
        self,
        message: str,
        model_override: str | None = None,
        console: Console | None = None,
        use_routing: bool = True,  # New parameter
    ) -> ChatResponse:
        # Determine model to use
        if model_override:
            target_model = model_override
            routed_by = "manual"
        elif use_routing:
            decision = self.router.classify(message)
            if decision.needs_classification and self.api_key:
                decision = await self.router.classify_with_haiku(message, self.api_key)
            target_model = decision.model
            routed_by = decision.reason
        else:
            target_model = "sonnet"
            routed_by = "default"

        # Map to actual model ID
        model_id = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
        }.get(target_model, "claude-sonnet-4-20250514")

        # Update payload with routed model
        payload = {
            "model": model_id,
            # ... rest of payload ...
        }
```

**Step 2: Update REPL to show routing decision**

```python
# In repl.py, show which model was selected
response = await self.chat_client.send_message(...)

# Show routing info
self.console.print(f"[dim]Routed to {response.model} via {response.routed_by}[/dim]")
self.console.print(render_response(response.model, response.text))
```

**Step 3: Update ChatResponse to include routed_by**

```python
@dataclass
class ChatResponse:
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    cost: float
    routed_by: str = "default"  # Add this field
```

**Step 4: Test and commit**
```bash
pytest tests/test_chat.py tests/test_router.py -v
git add src/claudius/chat.py src/claudius/repl.py
git commit -m "feat: integrate SmartRouter into chat flow"
```

---

## Task 5: Add Pre-flight Cost Estimation to REPL

**Goal:** Show estimated cost before sending message.

**Files:**
- Modify: `src/claudius/repl.py`
- Modify: `src/claudius/ui.py`
- Test: `tests/test_repl.py`

**Step 1: Create estimation display function**

```python
# In ui.py, add new function
def render_cost_estimate(
    input_cost: float,
    output_cost_min: float,
    output_cost_max: float,
    model: str,
    currency: str,
) -> RenderableType:
    """Render pre-flight cost estimation.

    Shows:
    📊 Estimated cost: €0.02 - €0.08
       Input: €0.01 (exact) | Output: €0.01-0.07 (estimated)
       Model: Haiku (auto-selected)
    """
    symbol = get_currency_symbol(currency)
    total_min = input_cost + output_cost_min
    total_max = input_cost + output_cost_max

    text = Text()
    text.append("📊 ", style="bold")
    text.append("Estimated cost: ", style="dim")
    text.append(f"{symbol}{total_min:.3f} - {symbol}{total_max:.3f}", style="cyan bold")
    text.append("\n   Input: ", style="dim")
    text.append(f"{symbol}{input_cost:.3f}", style="green")
    text.append(" (exact)", style="dim")
    text.append(" │ Output: ", style="dim")
    text.append(f"{symbol}{output_cost_min:.3f}-{symbol}{output_cost_max:.3f}", style="yellow")
    text.append(" (estimated)", style="dim")
    text.append(f"\n   Model: ", style="dim")
    text.append(f"{model.title()}", style="cyan")
    text.append(" (auto-selected)", style="dim")

    return Panel(text, border_style="dim", padding=(0, 1))
```

**Step 2: Integrate into REPL before sending**

```python
# In repl.py, before sending message
from claudius.estimation import estimate_cost
from claudius.ui import render_cost_estimate

# After getting user input, before sending:
if user_input and not user_input.startswith("/"):
    # Get routing decision first
    decision = self.chat_client.router.classify(user_input)

    # Estimate cost
    estimation = estimate_cost(
        prompt=user_input,
        model=decision.model,
        conversation_history=self.chat_client.conversation,
    )

    # Show estimate
    self.console.print(render_cost_estimate(
        input_cost=estimation.input_cost,
        output_cost_min=estimation.output_cost_min,
        output_cost_max=estimation.output_cost_max,
        model=decision.model,
        currency=self.config.budget.currency,
    ))

    # TODO: Add [Send] [Change Model] [Cancel] prompt
```

**Step 3: Commit**
```bash
git add src/claudius/ui.py src/claudius/repl.py
git commit -m "feat: add pre-flight cost estimation display"
```

---

## Task 6: Add /models Command

**Goal:** Show available models and their pricing.

**Files:**
- Modify: `src/claudius/commands.py`
- Test: `tests/test_commands.py`

**Step 1: Add models command handler**

```python
# In commands.py, add to command dispatch
elif command == "/models":
    return self._handle_models()

def _handle_models(self) -> CommandResult:
    """Show available models and pricing."""
    from claudius.pricing import PRICING

    output = "📊 Available Models:\n\n"
    output += "| Model  | Input (per 1M) | Output (per 1M) |\n"
    output += "|--------|----------------|------------------|\n"

    for model_key, prices in [
        ("haiku", PRICING["claude-3-5-haiku-20241022"]),
        ("sonnet", PRICING["claude-sonnet-4-20250514"]),
        ("opus", PRICING["claude-opus-4-20250514"]),
    ]:
        output += f"| {model_key:6} | €{prices['input']*1_000_000:,.2f}       | €{prices['output']*1_000_000:,.2f}         |\n"

    output += "\nUse /haiku, /sonnet, /opus to force a model."

    return CommandResult(output=output)
```

**Step 2: Add test**

```python
# In tests/test_commands.py
def test_models_command_shows_pricing():
    handler = CommandHandler(tracker, config, console)
    result = handler.handle("/models")
    assert result is not None
    assert "haiku" in result.output.lower()
    assert "sonnet" in result.output.lower()
    assert "opus" in result.output.lower()
```

**Step 3: Update /help to include /models**

**Step 4: Commit**
```bash
git add src/claudius/commands.py tests/test_commands.py
git commit -m "feat: add /models command to show pricing"
```

---

## Task 7: Add Budget Alerts (80% Warnings)

**Goal:** Warn user when approaching budget limits.

**Files:**
- Modify: `src/claudius/repl.py`
- Modify: `src/claudius/ui.py`
- Test: `tests/test_repl.py`

**Step 1: Create alert rendering function**

```python
# In ui.py
def render_budget_alert(alert_type: str, percent: float, currency: str, spent: float, budget: float) -> RenderableType:
    """Render budget warning alert."""
    symbol = get_currency_symbol(currency)

    if alert_type == "daily":
        emoji = "⚠️"
        label = "Daily budget"
    else:
        emoji = "🚨"
        label = "Monthly budget"

    text = Text()
    text.append(f"{emoji} ", style="bold yellow")
    text.append(f"{label} at {percent:.0f}%! ", style="bold yellow")
    text.append(f"({symbol}{spent:.2f}/{symbol}{budget:.2f})", style="dim")

    return Panel(text, border_style="yellow", padding=(0, 1))
```

**Step 2: Check and display alerts in REPL after each response**

```python
# In repl.py, after recording usage
status = self.tracker.get_status(
    self.config.budget.monthly,
    self.config.budget.daily_soft
)

# Check for alerts
if status.daily_percent >= 80:
    self.console.print(render_budget_alert(
        "daily", status.daily_percent,
        self.config.budget.currency,
        status.daily_spent, status.daily_budget
    ))

if status.monthly_percent >= 80:
    self.console.print(render_budget_alert(
        "monthly", status.monthly_percent,
        self.config.budget.currency,
        status.monthly_spent, status.monthly_budget
    ))
```

**Step 3: Commit**
```bash
git add src/claudius/ui.py src/claudius/repl.py
git commit -m "feat: add budget alerts at 80% threshold"
```

---

## Task 8: Fix Banner Display

**Goal:** Ensure banner renders correctly in all terminals.

**Files:**
- Modify: `src/claudius/ui.py`

**Step 1: Simplify banner (remove Panel wrapper)**

The current banner wraps in a Panel which may cause alignment issues. Try simpler approach:

```python
def render_banner() -> RenderableType:
    """Render the ASCII art banner for startup."""
    # Use raw text without Panel for better compatibility
    banner = """
   ⚔️  ╔═╗╦  ╔═╗╦ ╦╔╦╗╦╦ ╦╔═╗  🛡️
      ║  ║  ╠═╣║ ║ ║║║║ ║╚═╗
      ╚═╝╩═╝╩ ╩╚═╝═╩╝╩╚═╝╚═╝

   Your AI Budget Guardian • v1.0.0
"""
    text = Text(banner)
    text.stylize("bold cyan", 0, len(banner))
    return text
```

**Step 2: Test in terminal**
```bash
claudius
```

**Step 3: Commit**
```bash
git add src/claudius/ui.py
git commit -m "fix: simplify banner for better terminal compatibility"
```

---

## Execution Order

| # | Task | Priority | Dependencies |
|---|------|----------|--------------|
| 1 | Fix Cost Tracking | CRITICAL | None |
| 2 | Implement Rollover | HIGH | None |
| 3 | Create Smart Router | CRITICAL | None |
| 4 | Integrate Router | CRITICAL | Task 3 |
| 5 | Pre-flight Estimation | HIGH | Task 3, 4 |
| 6 | /models Command | LOW | None |
| 7 | Budget Alerts | MEDIUM | None |
| 8 | Fix Banner | MEDIUM | None |

---

## Testing Checklist

After all tasks complete:

- [ ] `claudius` starts without error
- [ ] Banner displays correctly with box-drawing chars
- [ ] Short messages ("Hi") route to Haiku
- [ ] Code blocks route to Sonnet
- [ ] Complex queries ("Design an architecture...") route to Opus
- [ ] Cost shows non-zero after response
- [ ] `/models` shows pricing table
- [ ] `/status` shows correct rollover
- [ ] 80% budget warning appears when appropriate
- [ ] All 250+ tests pass

---

*Plan created: 2025-01-01*
*Author: Opus & Doctor Biz*
