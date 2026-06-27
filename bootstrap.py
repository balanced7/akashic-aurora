#!/usr/bin/env python3
"""
Bootstrap — system entry point & honest status check

Single command to orient and verify the stack. Reports what's actually wired up,
in the current vocabulary (see docs/LEXICON.md). Degrades gracefully: every check
fails soft, so a down Redis never crashes the bootstrap.

Usage:
    python bootstrap.py            # full status
    python bootstrap.py --brief    # status only, no extras
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GREEN, RED, YELLOW, CYAN, RESET = '\033[92m', '\033[91m', '\033[93m', '\033[96m', '\033[0m'


def log(msg, color=''):
    print(f"{color}{msg}{RESET}")


def check_redis():
    """Redis reachable via the fail-fast connector? Returns (ok, detail)."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        client = connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=3)
        if client is None:
            return False, f"not reachable at {DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT} (File fallback active)"
        return True, f"{DEFAULT_REDIS_HOST}:{DEFAULT_REDIS_PORT} ({client.info().get('used_memory_human', 'connected')})"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def check_foundation():
    """Are the Pillar 0 primitives importable? Returns (ok, detail)."""
    try:
        from core.foundation import Store, Ledger, create_store, create_ledger  # noqa: F401
        return True, "Store + Ledger present"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def check_context():
    """Does the project context load? (Currently needs Redis until Context pillar Wave 1.)"""
    try:
        from context.project_context import get_project_context_manager_instance
        ctx = get_project_context_manager_instance().derive_full_context_for_agent_repriming()
        if isinstance(ctx, dict) and "error" not in ctx:
            return True, "loaded"
        return False, "unavailable (needs Redis; Context pillar Wave 1 will make it File-backed)"
    except Exception as e:
        return False, f"unavailable ({type(e).__name__})"


def report_memory_counts():
    """Count what's actually stored, in the real namespaces (learn: / mem:)."""
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        client = connect_to_redis_with_fail_fast(
            host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT, timeout_seconds=3)
        if client is None:
            return None
        return {
            "learnings (learn:)": len(client.keys('learn:*')),
            "agent memory (mem:)": len(client.keys('mem:*')),
            "total keys": len(client.keys('*')),
        }
    except Exception:
        return None


def check_logging_available():
    """Is session logging importable? READ-ONLY -- bootstrap is a status check and
    must not write to the shared store (it used to log a session:* key to canonical
    on every run). Returns True/False."""
    try:
        from session_logger import get_logger  # noqa: F401
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Stack bootstrap & status check")
    parser.add_argument('--brief', action='store_true', help='Status only, no extras')
    args = parser.parse_args()

    print()
    log("=" * 64, CYAN)
    log("  STACK BOOTSTRAP", CYAN)
    log(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", CYAN)
    log("=" * 64, CYAN)
    print()

    has_logging = check_logging_available()
    log("[*] Session logging available (read-only check)" if has_logging
        else "[!] Session logging unavailable", GREEN if has_logging else YELLOW)
    print()

    # [1] Foundation (Pillar 0)
    log("[1/4] Foundation (Store + Ledger)...", CYAN)
    ok, detail = check_foundation()
    log(f"    [{'OK' if ok else 'XX'}] {detail}", GREEN if ok else RED)

    # [2] Redis (optional — File fallback always works)
    log("[2/4] Redis (optional; Hybrid falls back to File)...", CYAN)
    ok, detail = check_redis()
    log(f"    [{'OK' if ok else '!!'}] {detail}", GREEN if ok else YELLOW)

    # [3] Project context
    log("[3/4] Project context...", CYAN)
    ok, detail = check_context()
    log(f"    [{'OK' if ok else '!!'}] {detail}", GREEN if ok else YELLOW)

    # [4] Stored data (real namespaces)
    log("[4/4] Stored data...", CYAN)
    counts = report_memory_counts()
    if counts:
        for k, v in counts.items():
            log(f"    {k}: {v}", GREEN)
    else:
        log("    [..] Redis down — counts unavailable (data is in session_logs/ files)", YELLOW)

    # Orientation
    print()
    log("=" * 64, CYAN)
    log("  READY", CYAN)
    log("=" * 64, CYAN)
    print()
    if not args.brief:
        print("  Start here:")
        print("    docs/ROADMAP.md        - the plan + current wave")
        print("    docs/LEXICON.md        - the vocabulary (what each term means)")
        print("    docs/architecture.md   - the layered stack")
        print()
        print("  Verify boundaries:")
        print("    py scripts/check_boundaries.py")
        print()
        print("  Initialize an agent:")
        print("    from agent.initializer import derive_agent_context_from_startup_sources")
        print('    ctx = derive_agent_context_from_startup_sources("my_agent", task_keyword="my_task")')
        print()


if __name__ == "__main__":
    main()
