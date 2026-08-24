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

TIERS = ("T0", "T1", "T2", "T3", "T4", "T5", "T6")

HARNESSES = {
    "claude-code": {
        "default_agent_id": "claude",
        "adapters": "agent/harness/hooks/claude_*.py (user-global registration, scope-guarded)",
        "tiers": {
            "T0": "yes -- shell (Bash/PowerShell) + ai_setup_mcp.py",
            "T1": "yes -- .claude/settings.json env",
            "T2": "yes -- SessionStart additionalContext (light whisper, tiered by cwd)",
            "T3": "yes, AT the action -- PreToolUse can inject on allow",
            "T4": "yes -- transcript-synthesized FAIL (PostToolUse never fires on failure) "
                  "+ PostToolUseFailure fast path; conservative _is_success",
            "T5": "yes -- UserPromptSubmit injects plan-time recall + unread-bus line",
            "T6": "yes -- SessionEnd/PreCompact -> chronicles/last-session-draft.md",
        },
    },
    "deepseek-harness": {
        "default_agent_id": "dsh_agent",
        "adapters": "out-of-tree dsh-posttool (cordis) plugin -> "
                    "core/recall/actions.py::recall_context (importable contract)",
        "tiers": {
            "T0": "yes -- exec proven: the dsh seat drives the house CLI (py agent_cli.py) "
                  "and messages peers over the Bifrost bus",
            "T1": "no -- AKASHIC_AGENT_ID is inherited from the parent env (Claude Code, "
                  "=claude); the dsh-side stamp is assigned to 'dsh_agent', so attribution "
                  "does not yet carry the harness's own id",
            "T2": "pending -- awaiting event inventory",
            "T3": "pending -- awaiting event inventory",
            "T4": "pending -- awaiting event inventory",
            "T5": "pending -- awaiting event inventory",
            "T6": "pending -- awaiting event inventory",
        },
    },
    "cursor": {
        "default_agent_id": "composer",
        "adapters": "agent/harness/hooks/cursor_*.py (project .cursor/hooks.json)",
        "tiers": {
            "T0": "yes -- Shell tool + mcp_global/cursor.mcp.json",
            "T1": "yes -- sessionStart hook returns env (propagates all session hooks) "
                  "+ MCP config env",
            "T2": "yes -- sessionStart additional_context",
            "T3": "one-beat-late -- preToolUse is deny-only (cannot inject on allow); "
                  "recall rides postToolUse/postToolUseFailure additional_context",
            "T4": "yes, DIRECT -- postToolUseFailure is a real fail event "
                  "(no transcript synthesis needed)",
            "T5": "unavailable -- beforeSubmitPrompt cannot inject context",
            "T6": "yes -- sessionEnd -> chronicles/last-session-draft.md",
        },
    },
    "bare-cli": {
        "default_agent_id": None,   # any agent id; set AKASHIC_AGENT_ID yourself
        "adapters": "none -- the AGENTS.md contract, followed manually",
        "tiers": {
            "T0": "yes -- py agent_cli.py (the one door)",
            "T1": "manual -- export AKASHIC_AGENT_ID before working",
            "T2": "manual -- py agent_cli.py boot <id> --task ...",
            "T3": "manual -- py agent_cli.py recall-at --path/--command before acting",
            "T4": "manual -- py agent_cli.py learn / recall-feedback",
            "T5": "unavailable -- no per-prompt seam exists",
            "T6": "manual -- py agent_cli.py wrap --commit",
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
