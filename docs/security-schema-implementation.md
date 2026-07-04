# Security Schema — Implementation Guide

**Tag:** SEC-SCHEMA-IMPL
**Date:** 2026-07-04
**Author:** deepseek (admin) — implementation guidelines for the security schema
**Prerequisite:** `docs/security-schema-proposal.md` (the design — read first)

---

## 0. The Core Principle

> **One TrustGate. Every door. No exceptions.**

Every agent action that touches files, the bus, or the shell passes through a single
`TrustGate.allow(agent_id, cap, context) -> (allowed, reason)` call. If a new door is
added (a new MCP tool, a new CLI verb, a new runner), it inherits enforcement for
free by calling `TrustGate`. The gate is the bottleneck, and that's the point —
there's exactly one place to audit, one place to test, one place where "did we forget
to check?" is visible.

This mirrors the existing `guards.py` pattern: `git_veto(command)` and
`lock_veto(path, agent_id, id_hint)` are called from Claude hooks, Cursor hooks, and
the CLI — identical policy, different adapters. TrustGate is the same idea, for all
capabilities, not just git/lock.

---

## 1. Enforcement Surfaces (complete map)

There are **six distinct surfaces** where agent actions enter the system. Every one
must call TrustGate:

| # | Surface | Agent(s) | What's Gated | Enforcement Mechanism |
|---|---|---|---|---|
| 1 | **ToolBox** | DeepSeek (agentic) | read_file, write_file, edit_file, run_command, bifrost_send, bifrost_nudge, bifrost_steer, web_search, KB write | ToolBox method calls `self._gate.require(Cap.XXX)` before acting |
| 2 | **Bus** | All agents with Bus handle | bus.send, bus.broadcast, bus.nudge | `Bus._emit()` / `Bus.send()` calls `_gate.allow()` before XADD |
| 3 | **MCP server** | Claude (via MCP), Cursor (via MCP) | bifrost_send, bifrost_broadcast, knowledge_learn | MCP tool functions call `_gate.allow()` before acting |
| 4 | **CLI** | Human, scripts | bifrost_send, bifrost_nudge, knowledge_learn | CLI command functions call `_gate.allow()` before acting |
| 5 | **Harness hooks** | Claude (native tools), Cursor (native tools) | Write/Edit/Bash (Claude), Shell/Write (Cursor) | PreToolUse hooks consult `TrustGate` for Cap.WRITE/Cap.EXEC before allowing |
| 6 | **Runners** | DeepSeek, Gemini | Initial grant resolution at boot | Runner passes resolved Grant to ToolBox/Bus at construction |

### Surface 5 is the hardest case

Claude and Cursor have their OWN tool implementations — Claude's `Write`/`Edit`/`Bash`,
Cursor's `Shell`/`Write`. They do NOT go through our ToolBox. The harness hooks
(`claude_pretooluse.py`, `cursor_pretooluse.py`, `cursor_beforeshell.py`) are the ONLY
point where we can intercept these native tools.

**What we CAN do:** The PreToolUse hook, before emitting `permissionDecision: "allow"`,
also calls `TrustGate.allow(agent_id, cap, context)`. For Claude (super_admin), this
always returns `(True, "")`. For a local model running through the Claude Code harness
(e.g., `glm_local` with `AKASHIC_AGENT_ID=glm_local`), it checks the grant and can
DENY.

**What we CANNOT do:** Force Claude to use our ToolBox. Claude has its own tool
implementations that are not swappable. The hook is our enforcement seam.

**The design rule for surface 5:** The harness hook's job is to map Claude/Cursor tool
names → Cap tokens → TrustGate.allow(). The existing `guards.py` already does this
for git/lock; we add the TrustGate check alongside it.

---

## 2. The TrustGate Class (one file, one truth)

```python
# core/trust/gate.py

from dataclasses import dataclass
from typing import Any, Optional
from core.trust.capabilities import Cap
from core.trust.registry import Grant, resolve


@dataclass
class GateContext:
    """Optional context for scoped capability checks. All fields are optional — the
    gate checks whatever context is provided; absent context means 'check the cap only,
    not the scope.'"""
    path: Optional[str] = None          # for WRITE path_scope check
    command: Optional[str] = None       # for EXEC audit (the command text)
    bus_kind: Optional[str] = None      # for BUS_SEND kind_scope check
    reason: Optional[str] = None        # for escalation requests (why do you need this?)


class TrustGate:
    """One gate, called from every surface.

    Usage:
        gate = TrustGate(agent_id)
        allowed, reason = gate.allow(Cap.WRITE, GateContext(path="docs/foo.md"))
        if not allowed:
            raise PermissionError(reason)   # or emit a deny verdict

    The gate is STATELESS: it reads the grant from the registry on every call (the
    registry itself may serve from a short-lived cache, but the gate never caches
    internally — a grant revocation takes effect on the next call, worst case ~60s)."""

    def __init__(self, agent_id: str, *, verified: bool = True):
        self.agent_id = str(agent_id)
        self.verified = verified

    @property
    def grant(self) -> Grant:
        """The effective grant RIGHT NOW. Not cached in the gate — re-reads from the
        registry on every invocation so grant changes take effect immediately."""
        return resolve(self.agent_id, verified=self.verified)

    def allow(self, cap: Cap, ctx: Optional[GateContext] = None) -> tuple[bool, str]:
        """Check whether `agent_id` has `cap`, scoped by `ctx` if provided.

        Returns (allowed: bool, reason: str). When allowed, reason is "".
        When denied, reason is a teaching message suitable for the agent or human."""
        grant = self.grant

        # 1. Capability check
        if cap not in grant.caps:
            return False, (
                f"agent '{self.agent_id}' (role={grant.role}) lacks capability "
                f"'{cap.value}'. Current caps: {sorted(c.value for c in grant.caps)}. "
                f"Request escalation via 'bifrost_send kind=escalation.request' "
                f"or ask a higher-tier agent."
            )

        # 2. Expiry check
        if grant.is_expired():
            return False, (
                f"grant for '{self.agent_id}' expired at {grant.expires_at}. "
                f"Re-request escalation."
            )

        # 3. Path scope check (Cap.WRITE only)
        if cap == Cap.WRITE and ctx and ctx.path:
            if not grant.path_scope:
                return False, (
                    f"agent '{self.agent_id}' (role={grant.role}) has Cap.WRITE "
                    f"but no path_scope — write is globally denied."
                )
            if "*" not in grant.path_scope:
                if not any(_match_scope(ctx.path, s) for s in grant.path_scope):
                    return False, (
                        f"path '{ctx.path}' is outside agent's write scope: "
                        f"{grant.path_scope}"
                    )

        # 4. Bus kind scope check (Cap.BUS_SEND only)
        if cap == Cap.BUS_SEND and ctx and ctx.bus_kind and grant.bus_send_kinds is not None:
            if ctx.bus_kind not in grant.bus_send_kinds:
                return False, (
                    f"agent '{self.agent_id}' (role={grant.role}) cannot send bus "
                    f"kind '{ctx.bus_kind}'. Allowed kinds: {sorted(grant.bus_send_kinds)}"
                )

        # 5. SECRET-BLOCK (always, regardless of grant — same as existing ToolBox)
        if cap == Cap.READ and ctx and ctx.path:
            if _is_secret_path(ctx.path):
                return False, (
                    f"refusing to access a secret/credential path: {ctx.path}. "
                    f"This is a system-level block, not a grant restriction."
                )

        return True, ""

    def require(self, cap: Cap, ctx: Optional[GateContext] = None) -> None:
        """Like allow(), but raises PermissionError on denial (convenience wrapper)."""
        allowed, reason = self.allow(cap, ctx)
        if not allowed:
            raise PermissionError(reason)


def _match_scope(path: str, scope: str) -> bool:
    """Does `path` match a scope glob? 'docs/*' matches 'docs/foo.md' but not
    'docs/sub/foo.md' (single-level). 'docs/**' matches recursively."""
    import fnmatch
    # Normalize to forward slashes for cross-platform matching
    p = path.replace("\\", "/")
    s = scope.replace("\\", "/")
    return fnmatch.fnmatch(p, s)


def _is_secret_path(path: str) -> bool:
    """Mirrors ToolBox._is_secret exactly. System-level block, not grant-based."""
    from pathlib import Path
    p = Path(path)
    parts = [x.lower() for x in p.parts]
    if ".secrets" in parts:
        return True
    name = p.name.lower()
    if name == ".env" or name.startswith(".env.") or name in {"id_rsa", "id_dsa", "credentials", "credentials.json"}:
        return True
    return p.suffix.lower() in {".key", ".pem", ".crt", ".pfx", ".p12", ".der"}
```

---

## 3. Integration at Each Surface

### Surface 1: ToolBox (deepseek_chat.py)

**Change:** Replace boolean flags with a `TrustGate` instance.

```python
# BEFORE (today):
class ToolBox:
    def __init__(self, root, *, allow_exec, trust, allow_secrets, confirm,
                 agent_id=None, allow_write=False):
        self.allow_exec = allow_exec
        self.allow_write = allow_write
        ...

# AFTER:
class ToolBox:
    def __init__(self, root, *, gate: TrustGate, confirm, on_audit=None):
        self.root = root.resolve()
        self._gate = gate
        self._confirm = confirm
        self._on_audit = on_audit

    def write_file(self, path, content):
        self._gate.require(Cap.WRITE, GateContext(path=path))
        p = self._resolve(path, allow_dir=False)
        self._audit("write_file", path)
        ...

    def run_command(self, command, ...):
        self._gate.require(Cap.EXEC, GateContext(command=command))
        self._audit("run_command", command)
        ...

    def bifrost_send(self, to, text, kind="chat"):
        self._gate.require(Cap.BUS_SEND, GateContext(bus_kind=kind))
        ...

    def bifrost_nudge(self, to, text):
        self._gate.require(Cap.BUS_NUDGE)
        ...

    def _resolve(self, path, *, allow_dir):
        # EXISTING path-scoping (inside root) stays — it's defense-in-depth.
        # The TrustGate checks the GRANT's path_scope; _resolve checks the
        # TOOLBOX's root boundary. Both must pass.
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        p = p.resolve()
        if os.path.commonpath([str(self.root), str(p)]) != str(self.root):
            raise ValueError(f"path is outside allowed root ({self.root})")
        if _is_secret_path(str(p)):
            raise ValueError("refusing to access a secret/credential path")
        return p
```

**Key insight:** `_resolve()` (root boundary) and `TrustGate.allow()` (grant boundary) are
separate checks. Both must pass. `_resolve` is the physical boundary; TrustGate is the
role-based boundary. This is defense-in-depth.

### Surface 2: Bus (core/comm/bus.py)

**Change:** Add a gate check in `send()`, `broadcast()`, and `nudge()` on the Bus object.

```python
# In Bus:
def __init__(self, agent_id, ...):
    self.agent_id = str(agent_id or "unknown")
    self._gate = TrustGate(self.agent_id)   # verified=True for local bus handles
    ...

def send(self, to, kind, content, ...):
    self._gate.require(Cap.BUS_SEND, GateContext(bus_kind=str(kind)))
    return self._emit(...)

def broadcast(self, kind, content, ...):
    self._gate.require(Cap.BUS_SEND, GateContext(bus_kind=str(kind)))
    return self._emit(...)

# nudge() is called externally or by the console — it goes through Bus too:
# (Currently nudge lives in core/comm/nudge.py and creates its own Bus handle.
#  That's fine — the Bus constructor applies the gate.)
```

**Gate for `_emit` itself? No.** `_emit` is the internal transport; the gate lives at
the semantic boundaries (`send`, `broadcast`). If someone bypasses `send` and calls
`_emit` directly from within `bus.py`, that's a code-review catch, not a runtime guard.

### Surface 3: MCP server (ai_setup_mcp.py)

**Change:** Add gate checks to bus-affecting MCP tools.

```python
# In ai_setup_mcp.py:

@mcp.tool()
def bifrost_send(from_agent: str, to: str, kind: str = "chat", text: str = "") -> str:
    from core.trust.gate import TrustGate, GateContext
    from core.trust.capabilities import Cap
    gate = TrustGate(from_agent)
    gate.require(Cap.BUS_SEND, GateContext(bus_kind=kind))
    # ... existing logic

@mcp.tool()
def bifrost_broadcast(from_agent: str, kind: str = "announce", text: str = "") -> str:
    from core.trust.gate import TrustGate, GateContext
    from core.trust.capabilities import Cap
    gate = TrustGate(from_agent)
    gate.require(Cap.BUS_SEND, GateContext(bus_kind=kind))
    # ... existing logic
```

**Does the MCP `knowledge_learn` tool need a gate?** Yes. Currently `agent_cli.py learn`
writes to the KB. If a quarantined agent calls it via MCP, they shouldn't be able to
pollute the knowledge base. The gate check happens inside `agent_cli.cmd_learn` (see
Surface 4) which the MCP server delegates to via `_run()`. So if we add the gate to
the CLI command, the MCP path inherits it for free through the `_run()` delegation.

### Surface 4: CLI (agent_cli.py)

**Change:** Add gate checks to bus-affecting and KB-writing CLI commands.

```python
# In agent_cli.py:

def cmd_bifrost_send(args):
    from core.trust.gate import TrustGate, GateContext
    gate = TrustGate(args.agent_id)
    gate.require(Cap.BUS_SEND, GateContext(bus_kind=args.kind))
    # ... existing logic

def cmd_bifrost_nudge(args):
    from core.trust.gate import TrustGate
    gate = TrustGate(args.agent_id)
    gate.require(Cap.BUS_NUDGE)
    # ... existing logic

def cmd_learn(args):
    from core.trust.gate import TrustGate
    gate = TrustGate(args.agent_id or os.getenv("AKASHIC_AGENT_ID", "unknown"))
    gate.require(Cap.KB_LEARN)
    # ... existing logic
```

**Which CLI commands do NOT need a gate?** Read-only commands (`recall`, `status`,
`boot`, `story`) are always allowed — they don't write. The gate for `Cap.READ` is
applied at the ToolBox level (Surface 1), not the CLI level (the CLI doesn't do
file I/O; it delegates to the knowledge store).

### Surface 5: Harness hooks (Claude/Cursor PreToolUse)

**This is the most nuanced surface.** The hooks intercept Claude/Cursor's NATIVE tools —
we can't swap their implementations, only veto or allow.

```python
# In claude_pretooluse.py — add to the existing _check_bash / _check_file flow:

def _trust_check(tool: str, data: dict, agent_id: str) -> str:
    """Consult the TrustGate before allowing a native Claude tool action.
    Returns "" if allowed, or a deny reason."""
    from core.trust.gate import TrustGate, GateContext
    from core.trust.capabilities import Cap

    gate = TrustGate(agent_id, verified=True)
    ti = data.get("tool_input") or {}

    # Map Claude tool names -> Cap tokens
    if tool in ("Write", "Edit", "NotebookEdit"):
        path = ti.get("file_path") or ""
        allowed, reason = gate.allow(Cap.WRITE, GateContext(path=path))
        if not allowed:
            return f"TrustGate: {reason}"

    elif tool in ("Bash", "PowerShell"):
        command = ti.get("command") or ""
        # Only check EXEC — git-veto is separate (existing guards.py)
        allowed, reason = gate.allow(Cap.EXEC, GateContext(command=command))
        if not allowed:
            return f"TrustGate: {reason}"

    return ""  # allowed


# In the main() flow, AFTER the existing git_veto / lock_veto checks:
reason = _check_bash(data) or _check_file(data)  # existing guards
if not reason:
    reason = _trust_check(tool_name, data, agent_id)  # NEW: trust gate
```

**For Cursor hooks** — same pattern in `cursor_pretooluse.py` and `cursor_beforeshell.py`:

```python
# In cursor_pretooluse.py — add alongside git_veto / lock_veto:
if not reason and command:
    reason = git_veto(command)  # existing
if not reason and path and file_in_scope(path):
    reason = lock_veto(path, ...)  # existing
# NEW:
if not reason and command:
    from core.trust.gate import TrustGate, GateContext
    from core.trust.capabilities import Cap
    gate = TrustGate(os.getenv("AKASHIC_AGENT_ID", "unknown"))
    allowed, reason2 = gate.allow(Cap.EXEC, GateContext(command=command))
    if not allowed:
        reason = f"TrustGate: {reason2}"
if not reason and path:
    allowed, reason2 = gate.allow(Cap.WRITE, GateContext(path=path))
    if not allowed:
        reason = f"TrustGate: {reason2}"
```

**Important:** The gate check is ADDITIVE to the existing guards, not a replacement.
Both must pass: git-veto + lock-veto + trust-gate.

**For Claude specifically (super_admin):** The TrustGate always returns `(True, "")`
because Claude's grant includes all caps. The gate is a no-op for super_admin — but
it's still CALLED, so it appears in the audit trail, and if Claude's grant were ever
accidentally changed, the gate would catch it.

### Surface 6: Runner initialization (bifrost_runner_deepseek.py)

**Change:** Pass a TrustGate to the ToolBox instead of boolean flags.

```python
# BEFORE:
toolbox = ToolBox(root, allow_exec=False, trust=False, allow_secrets=False,
                  confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write)

# AFTER:
from core.trust.gate import TrustGate
gate = TrustGate(agent_id)
toolbox = ToolBox(root, gate=gate, confirm=lambda _p: False, on_audit=audit_log)
```

**Session escalation via CLI flags:** If the human passes `--trust`, the runner creates
a session-scoped grant that adds Cap.EXEC. This is a transient grant that lives only in
the process memory (never written to acl.json):

```python
if args.trust:
    from dataclasses import replace
    from core.trust.capabilities import Cap
    session_grant = replace(gate.grant,
        caps = gate.grant.caps | {Cap.EXEC},
        reason = f"session escalation by human via --trust flag"
    )
    gate = TrustGate(agent_id, _session_grant=session_grant)
```

---

## 4. Audit Integration

### 4.1 What gets audited

Every gate denial AND every privileged action (write/exec/grant change) is projected
into the durable ledger. The TrustGate doesn't do the audit itself — it returns
`(allowed, reason)`. The CALLER decides whether to audit, and at what level.

**Rule:** Audit on DENIAL (always) and on ALLOW for write/exec/grant (the privileged
actions). Read-only actions on ALLOW are not audited (noise).

### 4.2 Audit helper

```python
# core/trust/audit.py

def audit_action(agent_id: str, cap: str, allowed: bool, reason: str = "",
                 *, path: str = "", command: str = "", bus_kind: str = "",
                 surface: str = "") -> None:
    """Record a security decision in the durable event firehose.
    Best-effort: never raises, never blocks the action."""
    if not allowed:
        # DENIAL is always audited — it's a security signal
        _capture("security.denied", agent_id, {
            "cap_attempted": cap, "reason": reason, "surface": surface,
            "path": path, "command": command, "bus_kind": bus_kind,
        })
    elif cap in ("write", "exec", "admin.grant", "admin.approve", "kb.learn"):
        # Privileged ALLOW — audited for the trail
        _capture(f"security.{cap}", agent_id, {
            "path": path, "command": command, "bus_kind": bus_kind,
            "surface": surface,
        })
    # else: read/bus.send on ALLOW — no audit (volume)

def _capture(kind: str, agent_id: str, detail: dict) -> None:
    try:
        from core.events.event_log import get_event_log
        summary = f"{agent_id}: {kind} | {detail.get('path') or detail.get('command') or detail.get('bus_kind') or ''}"
        get_event_log().capture(kind, summary[:200], agent_id=agent_id, detail=detail)
    except Exception:
        pass
```

### 4.3 Promoting security events

Add to `core/comm/promoter.py`'s `SALIENT_KINDS`:

```python
SALIENT_KINDS = frozenset({
    "handoff", "decision", "completion", "blocker",
    "security.write", "security.exec", "security.grant", "security.revoke",
    "security.escalation.request", "security.escalation.approved",
    "security.escalation.denied", "security.denied",
})
```

This ensures all security events survive Redis restarts (they're in the File ledger).

---

## 5. Testing the Enforcement

### 5.1 TrustGate unit tests (core/trust/)

```python
# tests/test_trust_gate.py

def test_super_admin_can_do_everything():
    gate = TrustGate("claude")
    for cap in Cap:
        assert gate.allow(cap)[0], f"super_admin should have {cap}"

def test_admin_cannot_exec():
    gate = TrustGate("deepseek")
    allowed, reason = gate.allow(Cap.EXEC, GateContext(command="rm -rf /"))
    assert not allowed
    assert "lacks capability" in reason

def test_admin_can_write_in_scope():
    gate = TrustGate("deepseek")
    allowed, _ = gate.allow(Cap.WRITE, GateContext(path="docs/foo.md"))
    assert allowed  # admin has path_scope=["*"]

def test_member_cannot_write():
    gate = TrustGate("glm_local")
    allowed, reason = gate.allow(Cap.WRITE, GateContext(path="scratch/test.md"))
    assert not allowed

def test_member_can_chat_but_not_nudge():
    gate = TrustGate("glm_local")
    assert gate.allow(Cap.BUS_SEND, GateContext(bus_kind="chat"))[0]
    assert not gate.allow(Cap.BUS_SEND, GateContext(bus_kind="handoff"))[0]

def test_quarantined_can_only_read():
    gate = TrustGate("unknown_agent")
    assert gate.allow(Cap.READ)[0]
    assert not gate.allow(Cap.WRITE)[0]
    assert not gate.allow(Cap.BUS_SEND)[0]
    assert not gate.allow(Cap.EXEC)[0]

def test_expired_grant_denies_all():
    gate = TrustGate("temp_admin")  # grant with expires_at in the past
    assert not gate.allow(Cap.WRITE)[0]

def test_unverified_agent_is_quarantined():
    gate = TrustGate("deepseek", verified=False)
    # Even if deepseek has admin grants, unverified -> quarantined
    assert not gate.allow(Cap.WRITE)[0]
    assert not gate.allow(Cap.BUS_SEND)[0]

def test_secret_path_blocked_even_for_super_admin():
    gate = TrustGate("claude")
    allowed, reason = gate.allow(Cap.READ, GateContext(path=".secrets/deepseek.key"))
    assert not allowed
    assert "secret" in reason.lower()

def test_path_scope_enforcement():
    # Admin with scope ["scratch/*", "docs/*"] cannot write to core/
    gate = TrustGate("scoped_admin")  # custom grant
    allowed, _ = gate.allow(Cap.WRITE, GateContext(path="scratch/test.md"))
    assert allowed
    allowed, reason = gate.allow(Cap.WRITE, GateContext(path="core/comm/bus.py"))
    assert not allowed
    assert "outside" in reason
```

### 5.2 Integration tests (each surface)

```python
# tests/test_trust_toolbox.py — Surface 1
def test_toolbox_denies_write_for_member():
    gate = TrustGate("glm_local")
    tb = ToolBox(root, gate=gate, confirm=lambda p: False)
    with pytest.raises(PermissionError, match="lacks capability"):
        tb.write_file("scratch/test.txt", "hello")

# tests/test_trust_bus.py — Surface 2
def test_bus_denies_send_for_quarantined():
    bus = Bus("unknown_agent")
    with pytest.raises(PermissionError):
        bus.send("claude", "chat", "hello")

# tests/test_trust_cli.py — Surface 4
def test_cli_bifrost_nudge_denied_for_member(monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "glm_local")
    # ... call cmd_bifrost_nudge with a test namespace, expect PermissionError

# tests/test_trust_hooks.py — Surface 5
def test_pretooluse_denies_bash_for_member():
    # Simulate a Claude PreToolUse payload for a Bash command with AKASHIC_AGENT_ID=glm_local
    # The _trust_check function should return a deny reason
    ...
```

### 5.3 The "forgotten door" test

A meta-test that ensures every tool in the ToolBox, every bus method, every CLI
bus verb, and every MCP bus tool calls TrustGate:

```python
# tests/test_trust_coverage.py
def test_every_toolbox_write_calls_gate():
    """If someone adds a new write tool to ToolBox, this test catches it."""
    # Use inspection/reflection to find all methods that modify state
    # and assert each one calls self._gate.require() or self._gate.allow()
    ...

def test_every_bus_send_path_calls_gate():
    """send, broadcast, nudge — all must call TrustGate."""
    ...
```

---

## 6. Build Sequence (mapped to the proposal's slices)

| Slice | What to Build | Files Changed | Tests |
|---|---|---|---|
| **S-0** | HMAC identity | `core/trust/identity.py` (new), `core/comm/bus.py` (+sig in _emit/_to_msg) | sign/verify round-trip, tamper detection |
| **S-1** | Grant registry + acl.json + TrustGate class | `core/trust/registry.py`, `core/trust/capabilities.py`, `core/trust/gate.py`, `security/acl.json` | all the TrustGate unit tests above |
| **S-2** | ToolBox + Bus enforcement | `scripts/deepseek_chat.py` (ToolBox takes Gate), `core/comm/bus.py` (send/broadcast checks Gate) | Surface 1 + 2 integration tests |
| **S-3** | CLI + MCP + audit | `agent_cli.py` (grant/audit verbs + gate checks), `ai_setup_mcp.py` (gate checks), `core/trust/audit.py`, `core/comm/promoter.py` (SALIENT_KINDS) | Surface 3 + 4 integration tests, audit round-trip |
| **S-4** | Escalation flow | `core/trust/escalation.py`, `scripts/bifrost_ui.py` (UI surface) | request→approve→grant→expire cycle |
| **S-5** | Runner + harness hooks | `bifrost_runner_deepseek.py`, `bifrost_runner.py`, `claude_pretooluse.py`, `cursor_pretooluse.py`, `cursor_beforeshell.py` | Surface 5 + 6 integration tests |
| **S-6** | "Forgotten door" coverage test | `tests/test_trust_coverage.py` | meta-test that every surface is gated |

---

## 7. Migration Path (backward compatibility)

### Phase 1: Ship S-1 (TrustGate exists, but not wired)

The TrustGate class and registry exist and are tested, but no surface calls them yet.
All existing boolean flags in ToolBox and Bus continue to work. This is a **latent**
capability — exists, tested, not yet kinetic.

### Phase 2: Ship S-2 (ToolBox + Bus wired)

ToolBox and Bus now DERIVE their behavior from the grant, but the existing boolean
flags still work as OVERRIDES. If a grant says "no exec" but the human passes
`--trust`, the session escalation adds exec. The grant is the base; the flags are
overrides.

```python
# Transitional ToolBox constructor:
def __init__(self, root, *, gate=None, allow_exec=None, allow_write=None, ...):
    self._gate = gate or TrustGate("unknown")
    # Legacy flags override the grant for backward compat:
    if allow_exec is not None:
        self._gate = _override_gate(self._gate, Cap.EXEC, allow_exec)
    if allow_write is not None:
        self._gate = _override_gate(self._gate, Cap.WRITE, allow_write)
```

### Phase 3: Ship S-5 (harness hooks wired)

All surfaces are now gated. The boolean flags in runners print a deprecation warning:
"`--allow-exec` is deprecated; use `agent_cli.py grant allow <agent> --cap exec` or
pass `--trust` for a session escalation."

### Phase 4: Remove boolean flags (future slice)

After all runners and callers have migrated, remove the legacy boolean flags from
ToolBox. The Grant is the sole source of truth.

---

## 8. Design Rules (to prevent drift)

1. **Every new tool added to ToolBox MUST call `self._gate.require()` or
   `self._gate.allow()` before acting.** The "forgotten door" coverage test enforces
   this mechanically.

2. **Every new bus method that sends messages MUST call `self._gate.require()`.** If
   someone adds `bus.invite()` or `bus.kick()`, it must be gated.

3. **Every new MCP tool that writes or sends MUST call TrustGate.** The MCP server
   delegates to `agent_cli` cmd_* functions via `_run()`, so adding the gate to the
   CLI function covers both doors automatically. Only native MCP tools (like
   `bifrost_send` which has its own implementation) need explicit gate checks.

4. **New capability tokens are added to `Cap` enum, ROLE_TEMPLATES, and the grant
   records.** If a new tool doesn't fit an existing Cap, a new Cap is created. The
   "forgotten door" test checks that every tool maps to a Cap.

5. **TrustGate.allow() never raises — it returns (bool, str).** The caller decides
   how to handle denial: raise PermissionError, emit a deny verdict, or surface to
   the user. This keeps the gate usable in contexts where raising would be wrong
   (e.g., a hook that must emit JSON, not a traceback).

6. **The gate is stateless per-call.** It reads the grant from the registry on every
   `allow()` call. No internal caching. A grant revocation takes effect on the next
   call, bounded only by the registry's own cache TTL (60s, with pub/sub
   invalidation for immediate effect).

7. **Fail-open on infrastructure errors (registry unreachable, Redis down).** If the
   registry can't load grants, `TrustGate` logs a warning and returns `(True, "")` —
   the action is ALLOWED. This prevents a Redis outage from bricking all agents. The
   audit trail captures the fail-open event. This matches the existing advisory lock
   model in `guards.py`.

8. **Fail-CLOSED on unverified identity.** If `verified=False` (bus message with
   failed HMAC), the gate returns the quarantined template regardless of the stored
   grant. Identity-first security — same principle as `guards.py:lock_veto` which
   fails closed on an unset `AKASHIC_AGENT_ID`.

---

## Appendix: Complete file manifest

| File | Kind | Purpose |
|---|---|---|
| `core/trust/__init__.py` | NEW | Package |
| `core/trust/capabilities.py` | NEW | Cap enum + ROLE_TEMPLATES |
| `core/trust/registry.py` | NEW | Grant reader + Redis cache + resolve() |
| `core/trust/gate.py` | NEW | TrustGate class (THE enforcement point) |
| `core/trust/identity.py` | NEW | HMAC sign/verify (S-0) |
| `core/trust/audit.py` | NEW | audit_action() helper |
| `core/trust/escalation.py` | NEW | Escalation request/approve/deny flow |
| `security/acl.json` | NEW | Grant source of truth |
| `core/comm/bus.py` | MODIFY | +HMAC, +grant checks in send/broadcast |
| `core/comm/promoter.py` | MODIFY | +security kinds to SALIENT_KINDS |
| `scripts/deepseek_chat.py` | MODIFY | ToolBox takes Gate instead of booleans |
| `scripts/bifrost_runner_deepseek.py` | MODIFY | Gate passed to ToolBox; session escalation |
| `scripts/bifrost_runner.py` | MODIFY | Gate passed (for future Gemini agentic mode) |
| `agent_cli.py` | MODIFY | +grant/audit verbs; +gate checks in bifrost/learn |
| `ai_setup_mcp.py` | MODIFY | +gate checks in bifrost_send/broadcast |
| `scripts/hooks/claude_pretooluse.py` | MODIFY | +trust_check() alongside existing guards |
| `scripts/hooks/cursor_pretooluse.py` | MODIFY | +trust gate check |
| `scripts/hooks/cursor_beforeshell.py` | MODIFY | +trust gate check |
| `tests/test_trust_gate.py` | NEW | TrustGate unit tests |
| `tests/test_trust_coverage.py` | NEW | "Forgotten door" coverage meta-test |
