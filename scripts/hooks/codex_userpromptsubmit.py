#!/usr/bin/env python3
"""Stable user-level entrypoint for the canonical Codex UserPromptSubmit adapter."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent.harness.hooks.codex_userpromptsubmit import main


if __name__ == "__main__":
    raise SystemExit(main())
