"""Which audience the CLI is printing for: an agent (TOON) or a human (colour and layout).

Order of precedence:
    1. `--output agent|human` on the command line (agent_cli.main() turns it into the env below)
    2. AURORA_OUTPUT=agent|human
    3. an agent harness in the environment (Claude Code, Codex, Cursor, Gemini CLI, OpenCode)
       -> agent
    4. stdout is a terminal -> human
    5. otherwise (a pipe, a file, the MCP door) -> agent

The default leans to agent because a misjudged agent pays for it in tokens and wrong answers on
every call, while a misjudged human sees plain text and can pass --human.
"""

from __future__ import annotations

import os
import sys

AGENT = "agent"
HUMAN = "human"
ENV = "AURORA_OUTPUT"

#: Variables an agent harness sets in the processes it runs.
AGENT_ENV = (
    "CLAUDECODE",
    "CLAUDE_CODE_SESSION_ID",
    "CODEX_SESSION_ID",
    "CODEX_THREAD_ID",
    "CURSOR_AGENT",
    "CURSOR_TRACE_ID",
    "GEMINI_CLI",
    "OPENCODE",
    "AI_AGENT",
)

#: The global flag agent_cli.main() accepts before or after any verb: --output agent|human.
#: (Not --agent: ten verbs already take --agent <id>.)
FLAG = "--output"


def resolve(stream=None) -> str:
    """The output mode for this process, per the order above."""
    explicit = (os.getenv(ENV) or "").strip().lower()
    if explicit in (AGENT, HUMAN):
        return explicit
    if any(os.getenv(name) for name in AGENT_ENV):
        return AGENT
    stream = sys.stdout if stream is None else stream
    try:
        if stream.isatty():
            return HUMAN
    except (AttributeError, ValueError):
        pass
    return AGENT


def is_agent(stream=None) -> bool:
    return resolve(stream) == AGENT


def take_flags(argv: list[str]) -> tuple[list[str], str | None]:
    """Remove `--output agent|human` (or `--output=...`) from argv, anywhere before a bare `--`,
    and return the mode it asks for; the last one wins. Any other value raises ValueError naming
    it, so the caller can say exactly what is wrong instead of it vanishing or being misread."""
    out, mode, i = [], None, 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            out.extend(argv[i:])
            break
        if arg == FLAG or arg.startswith(FLAG + "="):
            if arg == FLAG:
                value, step = (argv[i + 1] if i + 1 < len(argv) else ""), 2
            else:
                value, step = arg.split("=", 1)[1], 1
            value = value.strip().lower()
            if value not in (AGENT, HUMAN):
                raise ValueError(value)
            mode = value
            i += step
            continue
        out.append(arg)
        i += 1
    return out, mode
