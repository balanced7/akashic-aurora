#!/usr/bin/env python3
"""Arm a future-only, zero-model-idle Bifrost watcher for Codex/Sol."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.harness.codex_bifrost_wake import (  # noqa: E402
    CodexBifrostWake,
    DIRECT_ACTION_KINDS,
    WakeError,
    WakePolicy,
    WakeState,
    current_inbox_tail,
    default_runtime_paths,
    install_signal_stops,
)
from core.comm.bus import Bus  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "watch only future direct Bifrost messages from allowlisted peers; "
            "idle detection spends no model tokens and never advances a mailbox cursor"
        )
    )
    parser.add_argument("--agent", default="sol", help="subject seat and direct inbox")
    parser.add_argument(
        "--allow-from",
        action="append",
        default=None,
        help="peer address allowed to wake this seat (repeatable; default dsh_agent)",
    )
    parser.add_argument(
        "--expected-answer",
        action="append",
        default=[],
        help="message id whose causally linked answer may wake (repeatable)",
    )
    parser.add_argument(
        "--allow-kind",
        action="append",
        default=[],
        help=(
            "additional direct message kind allowed to wake (repeatable); "
            "the built-in request/question/handoff/blocker set remains"
        ),
    )
    parser.add_argument(
        "--require-source",
        help="require this exact message meta.source value before a turn may be admitted",
    )
    parser.add_argument("--state-path", help="private watcher watermark; not a mailbox cursor")
    parser.add_argument("--log-path", help="append-only watcher event log")
    parser.add_argument("--cwd", default=str(ROOT), help="fresh Codex task working directory")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--effort", default="low")
    parser.add_argument("--max-message-chars", type=int, default=16_000)
    parser.add_argument("--turn-timeout", type=float, default=900.0)
    parser.add_argument("--block-ms", type=int, default=5_000)
    parser.add_argument(
        "--once",
        action="store_true",
        help="handle at most one future row, or exit after one idle block (smoke tests)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = str(args.agent)
    default_state, default_log = default_runtime_paths(agent)
    state_path = Path(args.state_path).expanduser().resolve() if args.state_path else default_state
    log_path = Path(args.log_path).expanduser().resolve() if args.log_path else default_log

    os.environ["AKASHIC_AGENT_ID"] = agent
    os.environ["AKASHIC_HARNESS"] = "codex-desktop"
    os.environ.setdefault("AKASHIC_CALLSIGN_HINT", "Sunshine")
    os.environ.setdefault("AKASHIC_CALLSIGN_STATUS", "historical-unratified")

    bus = Bus(agent)
    if bus._client is None:
        raise WakeError("Bifrost is offline; watcher was not armed")
    baseline = current_inbox_tail(bus)
    state = WakeState.open(state_path, agent=agent, baseline=baseline)
    policy = WakePolicy(
        agent=agent,
        allowed_senders=frozenset(args.allow_from or ["dsh_agent"]),
        expected_answers=frozenset(str(value) for value in args.expected_answer),
        direct_kinds=frozenset(
            set(DIRECT_ACTION_KINDS)
            | {str(value).strip().lower() for value in args.allow_kind if str(value).strip()}
        ),
        required_source=(str(args.require_source).strip() if args.require_source else None),
    )
    watcher = CodexBifrostWake(
        bus=bus,
        policy=policy,
        state=state,
        log_path=log_path,
        cwd=Path(args.cwd),
        model=args.model,
        effort=args.effort,
        max_message_chars=args.max_message_chars,
        turn_timeout=args.turn_timeout,
        block_ms=args.block_ms,
    )
    install_signal_stops(watcher)
    print(
        json.dumps(
            {
                "status": "ARMED",
                "subject": agent,
                "after": state.last_seen,
                "state_path": str(state.path),
                "log_path": str(log_path),
                "allowed_senders": sorted(policy.allowed_senders),
                "direct_kinds": sorted(policy.direct_kinds),
                "expected_answers": sorted(policy.expected_answers),
                "required_source": policy.required_source,
                "cursor_advance": False,
                "idle_model_turns": 0,
                "peer_process_interference": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    watcher.run(once=args.once)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (WakeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
