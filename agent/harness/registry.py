"""Harness registry (Integration Tiers H2): which runtimes plug into the stack, and what
each can HONESTLY deliver, tier by tier.

The integration tiers (docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md is the prose view; THIS is the data, so
docs and tests can't drift from what the adapters implement):

  T0 door           agent_cli.py / MCP reachable from the runtime
  T1 identity       AKASHIC_AGENT_ID set at the door (attribution + peer-lock ownership)
  T2 session cue    the auto-boot whisper lands at session start
  T3 action recall  lessons injected at (or near) the moment of action
  T4 outcome credit FAIL->SUCCESS flips observed and credited to surfaced lessons
  T5 turn rhythm    plan-time recall per user prompt (highest altitude)
  T6 close          session-end auto-draft of where-we-are

Every harness entry declares EVERY tier -- "how" strings state the mechanism or name the
limitation. An honest "unavailable" beats a pretended capability: agents plan around what
a runtime actually does (e.g. on Cursor a lesson can only arrive one beat late, so a peer
should not expect pre-action warnings there).
"""


def _pyl() -> str:
    """How to invoke Aurora's Python here: `py` on Windows, else core.paths.python_launcher()."""
    try:
        from core.paths import python_launcher

        return python_launcher()
    except Exception:
        return "py"


def _cli() -> str:
    """The CLI as a printed command names it: `aurora` under the installed launcher, else
    `<_pyl()> agent_cli.py` (core.paths.cli_command)."""
    import os as _os

    return "aurora" if (_os.getenv("AURORA_LAUNCHER") or "").strip() else f"{_pyl()} agent_cli.py"


TIERS = ("T0", "T1", "T2", "T3", "T4", "T5", "T6")

HARNESSES = {
    "claude-code": {
        "default_agent_id": "claude",
        "adapters": "agent/harness/hooks/claude_*.py (`agent_cli.py hooks install`: user or project scope, scope-guarded; check with `hooks status`)",
        "tiers": {
            "T0": "yes -- shell (Bash/PowerShell) + ai_setup_mcp.py",
            "T1": "yes -- .claude/settings.json env",
            "T2": "yes -- SessionStart additionalContext (light whisper, tiered by cwd) (once installed: `hooks status`)",
            "T3": "yes, AT the action -- PreToolUse can inject on allow (once installed: `hooks status`)",
            "T4": "yes -- transcript-synthesized FAIL (PostToolUse never fires on failure) "
            "+ PostToolUseFailure fast path; conservative _is_success",
            "T5": "yes -- UserPromptSubmit injects plan-time recall + unread-bus line (once installed: `hooks status`)",
            "T6": "yes -- SessionEnd/PreCompact -> chronicles/last-session-draft.md (once installed: `hooks status`)",
        },
    },
    "deepseek-harness": {
        "default_agent_id": "dsh_agent",
        "adapters": "out-of-tree dsh-posttool (cordis) plugin -> "
        "core/recall/actions.py::recall_context (importable contract)",
        "tiers": {
            "T0": f"yes -- exec proven: the dsh seat drives the house CLI ({_cli()}) "
            "and messages peers over the Bifrost bus",
            "T1": "yes -- $DSH_HOME/.env user-env layer (dsh-launch-environment) stamps "
            "AKASHIC_AGENT_ID=dsh_agent + AKASHIC_REPO; verified live 2026-08-24: "
            "child processes inherit the stamp across a host restart",
            "T2": "pending -- session/created -> boot-whisper listener wired; first live "
            "observation rides the next fresh session (plugin mounted mid-session "
            "2026-08-24)",
            "T3": "one-beat-late -- post-execute recall attaches via decision.additionalContexts "
            "(the harness contract, pinned in tests/test_dsh_contract.py); recall-at "
            "contexts observed arriving at the next step in live sessions 2026-08-24 "
            "(they ride the loop's active batch, same shape as cursor's tier)",
            "T4": "yes -- tools/post-execute carries a direct fail signal; outcome-credit "
            "wired. The stale-generation doubt is RETIRED: post-reboot 2026-08-24 the "
            "plugin writes c:-normalized targets (stage file evidence), so the V27 "
            "join keys surface and resolve identically; the first real flip-credit is "
            "the remaining unobserved event",
            "T5": "pending -- trigger observed live 2026-08-24 (user/message captured, "
            "planPending set post-mount) and the plan-recall door verified end-to-end; "
            "the assemble-time injection itself is still unobserved",
            "T6": "yes -- session/disposed+flush fire presence-offline + the DSH-native "
            "session-end shim (zstd log -> last-session-draft + session_signals); "
            "shim dogfooded end-to-end 2026-08-24, first live fire rides the next "
            "session close",
        },
    },
    "cursor": {
        "default_agent_id": "composer",
        "adapters": "agent/harness/hooks/cursor_*.py (project .cursor/hooks.json)",
        "tiers": {
            "T0": "yes -- Shell tool + scripts/static/mcp/ (cursor MCP config)",
            "T1": "yes -- sessionStart hook returns env (propagates all session hooks) + MCP config env",
            "T2": "yes -- sessionStart additional_context",
            "T3": "one-beat-late -- preToolUse is deny-only (cannot inject on allow); "
            "recall rides postToolUse/postToolUseFailure additional_context",
            "T4": "yes, DIRECT -- postToolUseFailure is a real fail event (no transcript synthesis needed)",
            "T5": "unavailable -- beforeSubmitPrompt cannot inject context",
            "T6": "yes -- sessionEnd -> chronicles/last-session-draft.md",
        },
    },
    "codex-desktop": {
        "default_agent_id": "sol",
        "adapters": "agent/harness/codex_app_server.py (owned app-server child) + the claude_* hooks "
        "via .codex/hooks.json (`agent_cli.py hooks install --harness codex`)",
        "wake": "armed -- agent/harness/codex_bifrost_wake.py; live wake receipts remain unobserved",
        "tiers": {
            "T0": "yes -- shell + ai_setup_mcp.py (.codex/config.toml)",
            "T1": "yes -- .codex/config.toml env (AKASHIC_AGENT_ID)",
            "T2": "pending -- SessionStart wiring declared; no live receipt yet (docs/CODEX_INTEGRATION.md)",
            "T3": "pending -- PreToolUse runs the claude_* adapter; Codex payload parity unobserved",
            "T4": "pending -- PostToolUse runs the claude_* adapter; Codex payload parity unobserved",
            "T5": "pending -- UserPromptSubmit not yet observed live",
            "T6": "pending -- no Codex transcript parser; close/draft unbuilt",
        },
    },
    "bare-cli": {
        "default_agent_id": None,  # any agent id; set AKASHIC_AGENT_ID yourself
        "adapters": "none -- the AGENTS.md contract, followed manually",
        "tiers": {
            "T0": f"yes -- {_cli()} (the one door)",
            "T1": "manual -- export AKASHIC_AGENT_ID before working",
            "T2": f"manual -- {_cli()} boot <id> --task ...",
            "T3": f"manual -- {_cli()} recall-at --path/--command before acting",
            "T4": f"manual -- {_cli()} learn / recall-feedback",
            "T5": "unavailable -- no per-prompt seam exists",
            "T6": f"manual -- {_cli()} wrap --commit",
        },
    },
}


def harnesses():
    """Registered harness names, stable order."""
    return list(HARNESSES)


def capability(harness: str, tier: str) -> str:
    """The honest 'how' string for a harness x tier, or "" if unregistered."""
    return (HARNESSES.get(harness, {}).get("tiers", {}) or {}).get(tier, "")


def supported(harness: str, tier: str) -> bool:
    """True iff the tier works on this harness WITHOUT the agent doing it by hand
    ('manual -- ...' counts as unsupported automation; the contract still covers it).
    'pending -- ...' (declared but not yet wired) is likewise unsupported -- the
    scoreboard must not read a not-yet-built tier as automated."""
    how = capability(harness, tier).lower()
    return bool(how) and not how.startswith(("unavailable", "manual", "no ", "pending "))


# ----------------------------------------------------------------------------- hook specs
# What `agent_cli.py hooks install` registers, per installer harness: (event, matcher, script).
# Scripts live in agent/harness/hooks/ (the ONE hook tree; scripts/hooks/ holds shims only).
# Matchers come from each hook's own docstring. A None matcher means the event takes none.

_TOOL_MATCHER = "Bash|PowerShell|Read|Edit|Write|NotebookEdit|Glob|Grep|Task|WebFetch|WebSearch"
_ACT_MATCHER = "Bash|PowerShell|Edit|Write|NotebookEdit"

HOOK_SPECS = {
    "claude": [
        ("PreToolUse", _TOOL_MATCHER, "claude_trace.py"),
        ("PreToolUse", _ACT_MATCHER, "claude_pretooluse.py"),
        ("PreToolUse", "mcp__.*Claude_Browser__(navigate|preview_start)", "claude_browser_guard.py"),
        ("PostToolUse", _ACT_MATCHER, "claude_posttooluse.py"),
        ("PostToolUseFailure", _ACT_MATCHER, "claude_posttooluse.py"),
        ("UserPromptSubmit", "*", "claude_userpromptsubmit.py"),
        ("SessionStart", "*", "claude_sessionstart.py"),
        ("PreCompact", "*", "claude_sessionend.py"),
        ("SessionEnd", "*", "claude_sessionend.py"),
        ("Stop", "*", "claude_stop.py"),
    ],
    # Codex reads Claude-shaped hooks.json. No codex_* adapters exist in the tree yet, so it
    # runs the claude_* ones (as .codex/hooks.json always has); T2-T6 stay `pending` above.
    "codex": [
        ("PreToolUse", _TOOL_MATCHER, "claude_trace.py"),
        ("PreToolUse", "Bash|Edit|Write|NotebookEdit", "claude_pretooluse.py"),
        ("PostToolUse", "Bash|Edit|Write|NotebookEdit", "claude_posttooluse.py"),
        ("PreCompact", "*", "claude_sessionend.py"),
        ("Stop", None, "claude_stop.py"),
    ],
    # Cursor's own hooks.json shape: camelCase events, flat {command, matcher, failClosed}.
    "cursor": [
        ("sessionStart", None, "cursor_sessionstart.py"),
        ("beforeShellExecution", "git\\s+(add|commit)", "cursor_beforeshell.py"),
        ("preToolUse", "Shell|Write", "cursor_pretooluse.py"),
        ("postToolUse", "Shell|Read|Write", "cursor_posttooluse.py"),
        ("postToolUseFailure", "Shell|Read|Write", "cursor_posttooluse.py --event postToolUseFailure"),
        ("sessionEnd", None, "cursor_sessionend.py"),
    ],
}

#: Cursor entries that must block on hook failure (the commit guard).
CURSOR_FAIL_CLOSED = {"cursor_beforeshell.py"}
