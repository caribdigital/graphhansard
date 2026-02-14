"""Entry point for running graphhansard.brain as a module.

Usage:
    python -m graphhansard.brain <command> [args]
"""

import sys

from graphhansard.brain.cli import main

if __name__ == "__main__":
    sys.exit(main() or 0)
