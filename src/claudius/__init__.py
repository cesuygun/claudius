# ABOUTME: Claudius package initialization
# ABOUTME: Your AI Budget Guardian - Smart Claude API cost management

"""
Claudius - Your AI Budget Guardian

Smart Claude API cost management with auto-routing, budget limits,
and rollover tracking.
"""

__version__ = "0.1.0"
__author__ = "cesuygun"

from claudius.config import Config
from claudius.budget import BudgetTracker

__all__ = ["Config", "BudgetTracker", "__version__"]
