# ABOUTME: Entry point for Claudius CLI
# ABOUTME: Handles command-line invocation via `claudius` or `python -m claudius`

"""
Entry point for Claudius.

Usage:
    claudius          # Start interactive mode + proxy
    python -m claudius  # Same as above
"""

from claudius.cli import main

if __name__ == "__main__":
    main()
