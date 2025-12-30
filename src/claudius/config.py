# ABOUTME: Configuration management for Claudius
# ABOUTME: Loads and validates TOML config from ~/.claudius/config.toml

"""
Claudius Configuration.

Handles loading, validation, and defaults for Claudius settings.
Config file location: ~/.claudius/config.toml
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

DEFAULT_CONFIG_PATH = Path.home() / ".claudius" / "config.toml"

DEFAULT_CONFIG = """
[api]
key = ""  # Your Anthropic API key (optional - can also use ANTHROPIC_API_KEY env var)

[budget]
monthly = 90
daily_soft = 5
daily_hard = 10
rollover = true
max_rollover = 45
currency = "EUR"

[routing]
default = "haiku"
escalate_to = ["sonnet", "opus"]
auto_classify = true

[routing.heuristics]
short_message_words = 20
code_block_minimum = "sonnet"
opus_keywords = ["architect", "design", "complex", "plan", "analyze"]

[proxy]
host = "127.0.0.1"
port = 4000

[rate_limit]
max_retries = 3
initial_delay = 5
backoff_multiplier = 3

[alerts]
daily_80_percent = true
monthly_80_percent = true
sound = false

[models]
haiku = "claude-3-5-haiku-20241022"
sonnet = "claude-sonnet-4-20250514"
opus = "claude-opus-4-20250514"
"""


@dataclass
class ApiConfig:
    """API configuration."""

    key: str = ""  # Optional - can be empty


@dataclass
class BudgetConfig:
    """Budget-related settings."""

    monthly: float = 90.0
    daily_soft: float = 5.0
    daily_hard: float = 10.0
    rollover: bool = True
    max_rollover: float = 45.0
    currency: str = "EUR"


@dataclass
class RoutingConfig:
    """Model routing settings."""

    default: str = "haiku"
    escalate_to: list[str] = field(default_factory=lambda: ["sonnet", "opus"])
    auto_classify: bool = True


@dataclass
class ProxyConfig:
    """Proxy server settings."""

    host: str = "127.0.0.1"
    port: int = 4000


@dataclass
class RateLimitConfig:
    """Rate limit retry settings."""

    max_retries: int = 3
    initial_delay: int = 5  # seconds
    backoff_multiplier: int = 3


@dataclass
class Config:
    """Main configuration container."""

    api: ApiConfig = field(default_factory=ApiConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from TOML file."""
        config_path = path or DEFAULT_CONFIG_PATH

        if not config_path.exists():
            cls._create_default_config(config_path)

        data = toml.load(config_path)
        return cls._from_dict(data)

    @classmethod
    def _create_default_config(cls, path: Path) -> None:
        """Create default configuration file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_CONFIG)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        return cls(
            api=ApiConfig(**data.get("api", {})),
            budget=BudgetConfig(**data.get("budget", {})),
            routing=RoutingConfig(**data.get("routing", {})),
            proxy=ProxyConfig(**data.get("proxy", {})),
            rate_limit=RateLimitConfig(**data.get("rate_limit", {})),
        )
