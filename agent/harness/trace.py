"""Push display-only trace lines (tool calls) onto the Bifrost bus so the console shows what
Claude is DOING live -- the SAME kind=trace envelope DeepSeek's runner broadcasts
(scripts/bifrost_runner_deepseek.py `on_trace`). DeepSeek shows up for free because its runner
owns the model stream; Claude Code runs OUTSIDE any runner, so its trace has to be pushed from
the Claude Code hooks (scripts/hooks/claude_trace.py).

The UI already renders kind=trace with a per-agent colour (scripts/bifrost_ui.py `.trav.claude`),
so this is the only missing half. Best-effort and FAIL-OPEN: a trace that can't send is a lost
display line, never an error that touches the agent. Kill switch: AKASHIC_TRACE=0.

NOTE on thinking: Claude Code redacts extended-thinking at rest (the transcript stores only an
encrypted `signature`, `thinking` is ""), and no hook receives thinking text -- so a live
`think` trace is not passively recoverable the way it is for DeepSeek's own stream. The tool
`description` field (Claude's stated intent for the action) is the honest proxy we surface instead.
"""
import os

_PREFIX = {"tool": "\U0001f527", "think": "\U0001f4ad"}   # 🔧 / 💭  -- match the DeepSeek runner


def emit(kind: str, text: str, *, agent_id: str = None) -> bool:
    """Broadcast one display-only trace line. `kind` in {"tool","think"}. Returns True iff sent.
    Never raises: the bus may be offline (returns None) or unimportable -- either way, no-op."""
    if os.getenv("AKASHIC_TRACE", "1") == "0":
        return False
    text = (text or "").strip()
    if not text:
        return False
    try:
        from core.comm.bus import Bus
        aid = agent_id or os.getenv("AKASHIC_AGENT_ID") or "claude"
        mid = Bus(aid).broadcast(
            "trace", f"{_PREFIX.get(kind, '·')} {text}",
            meta={"via": f"{aid}-hook", "hops": 0, "trace": kind, "display_only": True})
        return mid is not None
    except Exception:
        return False


def summarize(tool: str, tool_input: dict) -> str:
    """A compact one-line summary of a tool call for the trace feed -- '<Tool> · <what>'.
    Mirrors how a person would narrate the action; never includes file bodies or large payloads."""
    ti = tool_input or {}

    def clip(s, n=120):
        s = " ".join(str(s or "").split())
        return s if len(s) <= n else s[: n - 1] + "…"

    if tool in ("Edit", "Write", "NotebookEdit", "Read"):
        return f"{tool} · {os.path.basename(ti.get('file_path') or '') or '?'}"
    if tool in ("Bash", "PowerShell"):
        desc = ti.get("description")
        cmd = (ti.get("command") or "").strip().splitlines()[0] if ti.get("command") else ""
        return f"{tool} · {clip(desc + ' — ' + cmd if desc else cmd)}"
    if tool == "Glob":
        return f"Glob · {clip(ti.get('pattern'))}"
    if tool == "Grep":
        return f"Grep · {clip(ti.get('pattern'))}"
    if tool == "Task":
        return f"Task · {clip(ti.get('description') or ti.get('subagent_type'))}"
    if tool in ("WebFetch", "WebSearch"):
        return f"{tool} · {clip(ti.get('url') or ti.get('query'))}"
    return f"{tool}"
