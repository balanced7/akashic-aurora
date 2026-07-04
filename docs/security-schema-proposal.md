# Agent Security Schema — Design Proposal

**Tag:** SEC-SCHEMA
**Date:** 2026-07-04
**Author:** deepseek (admin tier) — co-designed with claude (super-admin)
**Status:** proposal (unbuilt)

## 0. Executive Summary

Every agent on the Bifrost bus today has **de facto root**: `frm` is unverified (SEC-01), tool grants are
ad-hoc boolean flags on the CLI, and a new agent booted with `--agentic --allow-write` gets write access
with no audit trail. This proposal layers **verifiable identity → capability tokens → path-scoped grants →
enforcement at the door → durable audit → privilege-escalation flow** onto the existing harness (ToolBox
guards, promoter firehose, AgentCard caps, fleet-roster pattern, Bifrost W5 plan). It is buildable in 6
gated slices, each testable independently.

---

## 1. Role Model (Daniel's sketch, tightened)

| Role | Agent(s) | Caps | Constraints |
|---|---|---|---|
| **super-admin** | claude | `*` (all) | Grants/revokes others; approves escalations; every grant action is audited |
| **admin** | deepseek | `read`, `write`, `bus.send`, `bus.nudge`, `bus.steer`, `kb.learn` | NO `exec` by default; write is path-scoped; every privileged action audited; can REQUEST escalation |
| **member** | glm_local, qwen_local (trusted locals) | `read`, `bus.send(chat,note)` | NO write/exec/nudge; bus-initiated chat only |
| **restricted** | fleet one-shot models | `kb.recall` (read-only) | No file access, no bus, no write — single-shot `call(tag,prompt)` only |
| **quarantined** | brand-new unvetted agent | `read` (selected paths), `bus.inbox` (read own) | No bus send, no write, no exec — read-only observer |

### What I'd tighten in Daniel's sketch

1. **admin should NOT get `admin.grant`.** Only super-admin grants/revokes. admin can REQUEST escalation
   (for itself or on behalf of a member), but the grant action is super-admin-gated. This avoids two
   admins granting each other `exec` in a loop.

2. **member `bus.send` should be kind-scoped.** A member can chat/note but NOT `handoff` (task
   handoff implies write authority), `nudge` (hard interrupt is a privilege), or `request` (could
   be abused to social-engineer a higher-tier agent). I'd scope it to `{chat, note}` only.

3. **Add an `observer` tier below quarantined?** Probably over-design for now. quarantined with
   read-only + no bus write covers the "unvetted agent" case. Rename it `observer` if that's clearer.

4. **Time-box all admin grants.** The "trust-but-verify" principle: when admin escalates to `exec`,
   the grant should auto-expire (default 30 min, configurable). This is a forcing function for
   re-approval and prevents a forgotten `--trust` flag from persisting indefinitely.

---

## 2. Grant Model

### 2.1 Capability Tokens (the atomic permissions)

```python
# core/trust/capabilities.py

class Cap(str, Enum):
    """Atomic permissions. Grant records carry a set of these."""
    READ           = "read"            # read_file, list_directory, find_files, search_files
    WRITE          = "write"           # write_file, edit_file (ALWAYS path-scoped)
    EXEC           = "exec"            # run_command
    BUS_SEND       = "bus.send"        # bifrost_send (kind-scoped: see bus_send_kinds)
    BUS_NUDGE      = "bus.nudge"       # bifrost_nudge (hard interrupt)
    BUS_STEER      = "bus.steer"       # bifrost_steer (soft steer)
    ADMIN_GRANT    = "admin.grant"     # grant/revoke capabilities to others
    ADMIN_APPROVE  = "admin.approve"   # approve escalation requests
    KB_RECALL      = "kb.recall"       # knowledge_recall, knowledge_boot (read KB)
    KB_LEARN       = "kb.learn"        # agent_cli.py learn (write KB)
    NET            = "net"             # web_search
    GIT_READ       = "git.read"        # git_log, git_diff, git_show, git_status
    BIFROST_INBOX  = "bifrost.inbox"   # read own inbox
```

### 2.2 Path Scopes (for WRITE)

A grant with `WRITE` MUST carry a `path_scope`: a list of glob-like prefixes. The empty list or `["*"]`
means "any path in the repo root" (super-admin default). Otherwise it's an allowlist.

```python
# A path_scope is a list of glob prefixes, resolved relative to the project root.
# Examples:
#   ["scratch/*", "docs/*"]          — can only write under scratch/ and docs/
#   ["chronicles/*", "research/*"]   — can write chronicles + research
#   ["*"]                            — full repo (super-admin only)
```

The enforcement reuses the existing `ToolBox._resolve()` path-scoping (`deepseek_chat.py:195-203`) and
adds a glob-match check against the grant's path_scope.

### 2.3 Bus Send Kind Scopes

A grant with `BUS_SEND` MAY carry a `bus_send_kinds` allowlist. Absent = all kinds.

```python
# bus_send_kinds: set of kind strings, or None (= all).
#   {"chat", "note"}        — member default
#   {"chat", "note", "request"}  — admin default
#   None                     — super-admin (all kinds: chat, note, request, handoff, nudge, inform)
```

### 2.4 Grant Record Shape

```python
@dataclass
class Grant:
    """One grant record. The source of truth is security/acl.json; Redis is a cache."""
    agent_id: str                          # "deepseek", "glm_local", "qwen_local", etc.
    role: str                              # "super_admin" | "admin" | "member" | "restricted" | "quarantined"
    caps: set[Cap]                         # the capability tokens
    path_scope: list[str]                  # glob prefixes for WRITE; [] = no write, ["*"] = full
    bus_send_kinds: set[str] | None        # None = all kinds; {"chat","note"} = scoped
    granted_by: str                        # agent_id of the granter (or "root" for bootstrap)
    granted_at: str                        # ISO timestamp
    expires_at: str | None                 # None = permanent; ISO timestamp = auto-revoke
    reason: str                            # human-written or escalation-request summary
    request_ref: str | None                # if granted via escalation: the request msg_id
```

### 2.5 Built-in Role Templates (default grants)

These are the factory defaults — what an agent gets when first provisioned or when its role is set
with no custom overrides:

```python
ROLE_TEMPLATES: dict[str, dict] = {
    "super_admin": {
        "caps": {Cap.READ, Cap.WRITE, Cap.EXEC, Cap.BUS_SEND, Cap.BUS_NUDGE, Cap.BUS_STEER,
                 Cap.ADMIN_GRANT, Cap.ADMIN_APPROVE, Cap.KB_RECALL, Cap.KB_LEARN, Cap.NET,
                 Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": ["*"],
        "bus_send_kinds": None,          # all
    },
    "admin": {
        "caps": {Cap.READ, Cap.WRITE, Cap.BUS_SEND, Cap.BUS_NUDGE, Cap.BUS_STEER,
                 Cap.KB_RECALL, Cap.KB_LEARN, Cap.NET, Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": ["*"],             # full repo write (trust-but-verify: everything audited)
        "bus_send_kinds": {"chat", "note", "request", "reply"},
        # Cap.EXEC and Cap.ADMIN_GRANT are deliberately ABSENT.
    },
    "member": {
        "caps": {Cap.READ, Cap.BUS_SEND, Cap.KB_RECALL, Cap.GIT_READ, Cap.BIFROST_INBOX},
        "path_scope": [],                # no write
        "bus_send_kinds": {"chat", "note"},
    },
    "restricted": {
        "caps": {Cap.KB_RECALL},
        "path_scope": [],
        "bus_send_kinds": set(),         # no bus send
    },
    "quarantined": {
        "caps": {Cap.READ, Cap.BIFROST_INBOX},
        "path_scope": [],
        "bus_send_kinds": set(),
    },
}
```

---

## 3. Storage

### 3.1 Recommendation: Git-tracked JSON + Redis cache

**Source of truth:** `security/acl.json` — git-tracked, human-editable, code-reviewable.

**Runtime cache:** Redis hash `security:grant:<agent_id>` — loaded at boot, invalidated on grant change.
The cache is a pure performance optimization; every enforcement check CAN fall back to the JSON file.

### 3.2 Arguments for this design

| Argument | Why |
|---|---|
| **Auditable** | Every grant change is a git commit with author + message. "Who gave deepseek exec and when?" → `git log -- security/acl.json`. |
| **Human-editable** | Daniel can open the file and change a role or add a path scope without a CLI. |
| **Survives Redis restart** | The file is the truth; Redis is a cache. A restart just reloads. |
| **Merge-conflict safe** | Grants are per-agent keys; two admins adding different agents won't conflict. Same-agent edits by two admins DO conflict — and should (merge conflict = human adjudication). |
| **Familiar pattern** | Mirrors `core/fleet/models.json` → `roster.py` exactly. The team already knows this shape. |
| **No new infrastructure** | Zero new services. The existing Redis + git + Python stack is sufficient. |

### 3.3 Arguments against (and why we accept them)

| Concern | Mitigation |
|---|---|
| **File-not-atomic on writes** | The `GrantStore` writes to a temp file + `os.replace()` (atomic on POSIX; best-effort on Windows). Concurrent writes from two super-admins are gated by the existing advisory `core/comm/locks.py`. |
| **Redis cache can be stale** | Every write to `acl.json` broadcasts a `security:invalidate` doorbell via Redis pub/sub. Readers refresh on invalidation or every 60s. Stale-at-worst = 60s. For grant revocation, the revoker also sends a `bus.nudge` to force immediate re-check. |
| **File grows with many agents** | At ~200 bytes per grant, 100 agents = 20KB. Not a real concern for a local-first project. |

### 3.4 File shape (`security/acl.json`)

```json
{
  "_comment": "Agent grant registry — source of truth. Edit here; Redis is a cache. schema_version: 1.",
  "schema_version": 1,
  "grants": [
    {
      "agent_id": "claude",
      "role": "super_admin",
      "caps": ["read", "write", "exec", "bus.send", "bus.nudge", "bus.steer",
               "admin.grant", "admin.approve", "kb.recall", "kb.learn", "net",
               "git.read", "bifrost.inbox"],
      "path_scope": ["*"],
      "bus_send_kinds": null,
      "granted_by": "root",
      "granted_at": "2026-07-04T00:00:00Z",
      "expires_at": null,
      "reason": "Bootstrap: human-driven frontier model, full trust"
    },
    {
      "agent_id": "deepseek",
      "role": "admin",
      "caps": ["read", "write", "bus.send", "bus.nudge", "bus.steer",
               "kb.recall", "kb.learn", "net", "git.read", "bifrost.inbox"],
      "path_scope": ["*"],
      "bus_send_kinds": ["chat", "note", "request", "reply"],
      "granted_by": "root",
      "granted_at": "2026-07-04T00:00:00Z",
      "expires_at": null,
      "reason": "Bootstrap: stateless API peer, trust-but-verify"
    },
    {
      "agent_id": "glm_local",
      "role": "member",
      "caps": ["read", "bus.send", "kb.recall", "git.read", "bifrost.inbox"],
      "path_scope": [],
      "bus_send_kinds": ["chat", "note"],
      "granted_by": "root",
      "granted_at": "2026-07-04T00:00:00Z",
      "expires_at": null,
      "reason": "Bootstrap: local model, bounded tasks only"
    }
  ]
}
```

### 3.5 Reader API (`core/trust/registry.py`)

```python
"""Grant registry — mirrors core/fleet/roster.py pattern exactly."""

def grants() -> list[Grant]:
    """All grant records from the source-of-truth file. Fail-soft: empty list on error."""

def get(agent_id: str) -> Grant | None:
    """One agent's grant, or None if not registered."""

def role_template(role: str) -> Grant:
    """The factory-default grant for a role label (see ROLE_TEMPLATES)."""

def resolve(agent_id: str, *, verified: bool) -> Grant:
    """The effective grant for `agent_id`. If `verified` is False (unverified bus message),
    returns the QUARANTINED template regardless of the stored grant. Identity-first security.
    If agent_id is unknown, returns the QUARANTINED template (fail-closed, same principle
    as guards.py lock_veto)."""
```

---

## 4. Enforcement at the Door

### 4.1 Principle: ToolBox derives from Grant, not boolean flags

Today the ToolBox takes `allow_exec`, `trust`, `allow_secrets`, `allow_write` as separate booleans
(`deepseek_chat.py:178`). This proposal replaces them with a single `grant: Grant` parameter.

```python
# Today (deepseek_chat.py:838):
toolbox = ToolBox(root, allow_exec=False, trust=False, allow_secrets=False,
                  confirm=lambda _p: False, agent_id=agent_id, allow_write=allow_write)

# Proposed:
toolbox = ToolBox(root, grant=registry.resolve(agent_id, verified=True),
                  confirm=lambda _p: False)
```

### 4.2 ToolBox enforcement

Each tool method checks the grant before acting:

```python
class ToolBox:
    def __init__(self, root: Path, *, grant: Grant, confirm, on_audit=None):
        self.root = root.resolve()
        self.grant = grant
        self._confirm = confirm
        self._on_audit = on_audit  # called on every write/exec action (for the audit trail)

    # -- read tools: gated on Cap.READ --
    def read_file(self, path, ...):
        self._require(Cap.READ)
        ...

    # -- write tools: gated on Cap.WRITE + path_scope --
    def write_file(self, path, content):
        self._require(Cap.WRITE)
        self._check_path_scope(path)
        self._audit("write_file", path)
        ...

    def edit_file(self, path, ...):
        self._require(Cap.WRITE)
        self._check_path_scope(path)
        self._audit("edit_file", path)
        ...

    # -- exec: gated on Cap.EXEC --
    def run_command(self, command, ...):
        self._require(Cap.EXEC)
        self._audit("run_command", command)
        ...

    # -- internal --
    def _require(self, cap: Cap):
        if cap not in self.grant.caps:
            raise PermissionError(
                f"agent '{self.grant.agent_id}' (role={self.grant.role}) lacks capability '{cap.value}'. "
                f"Request escalation via the bus or ask a higher-tier agent."
            )

    def _check_path_scope(self, path: str):
        p = self._resolve(path, allow_dir=False)
        scopes = self.grant.path_scope
        if not scopes:
            raise PermissionError(f"agent '{self.grant.agent_id}' has no write path scope.")
        if "*" in scopes:
            return  # full access
        rel = p.relative_to(self.root).as_posix()
        if not any(fnmatch.fnmatch(rel, s) for s in scopes):
            raise PermissionError(
                f"path '{rel}' is outside agent's write scope: {scopes}"
            )

    def _audit(self, action: str, detail: str):
        if self._on_audit:
            self._on_audit(self.grant.agent_id, self.grant.role, action, detail)
```

### 4.3 Bus enforcement

The `Bus` already carries per-agent identity. Add a grant check to `send()`/`broadcast()`:

```python
# In Bus.send() / Bus.broadcast():
def send(self, to, kind, content, ...):
    grant = registry.resolve(self.agent_id, verified=True)
    if Cap.BUS_SEND not in grant.caps:
        raise PermissionError(...)
    if grant.bus_send_kinds is not None and str(kind) not in grant.bus_send_kinds:
        raise PermissionError(...)
    # ... proceed with _emit()

def nudge(self, to, text):
    grant = registry.resolve(self.agent_id, verified=True)
    if Cap.BUS_NUDGE not in grant.caps:
        raise PermissionError(...)
    # ... proceed
```

### 4.4 Runner integration

The runner (`bifrost_runner_deepseek.py`) passes the resolved grant to the ToolBox and Bus at construction:

```python
# bifrost_runner_deepseek.py — make_agentic_replier():
grant = registry.resolve(agent_id, verified=True)

# Gated tools: if grant lacks EXEC but the runner was started with --trust,
# the user's explicit flag creates a SESSION ESCALATION (see §5).
if args.trust and Cap.EXEC not in grant.caps:
    grant = escalate_for_session(grant, {Cap.EXEC}, reason="--trust flag")

toolbox = ToolBox(root, grant=grant, confirm=..., on_audit=audit_log)
```

### 4.5 CLI door: `agent_cli.py grant`

```bash
# Human (or super-admin agent) manages grants:
py agent_cli.py grant list                          # all grants
py agent_cli.py grant show deepseek                 # one agent's grant
py agent_cli.py grant set glm_local --role member   # assign role template
py agent_cli.py grant allow deepseek --cap exec --scope "scratch/*" --for 30m --reason "debugging X"
py agent_cli.py grant revoke deepseek --cap exec
py agent_cli.py grant quarantine new-agent-7        # set role=quarantined
```

---

## 5. Privilege-Escalation Flow

### 5.1 The flow

```
Agent (admin/member)                   Bus                     Human / Super-Admin
     │                                  │                              │
     │  1. NEEDS exec; lacks it         │                              │
     │  2. bifrost_send(to="*",         │                              │
     │     kind="escalation.request",   │                              │
     │     content={cap, scope, reason})│                              │
     │ ───────────────────────────────> │                              │
     │                                  │  3. Console surfaces it:     │
     │                                  │  "deepseek requests exec     │
     │                                  │   (scope: scratch/*) to      │
     │                                  │   run pytest. [y/N/30m/1h]"  │
     │                                  │ ───────────────────────────> │
     │                                  │                              │
     │                                  │  4. Human replies:           │
     │                                  │     /grant deepseek exec     │
     │                                  │     --scope "scratch/*"      │
     │                                  │     --for 30m                │
     │                                  │ <─────────────────────────── │
     │                                  │                              │
     │  5. grant written to acl.json    │                              │
     │     + Redis cache invalidated    │                              │
     │     + bus reply to requester     │                              │
     │ <─────────────────────────────── │                              │
     │                                  │                              │
     │  6. Agent re-reads grant,        │                              │
     │     runs the command,            │                              │
     │     grant auto-expires in 30m    │                              │
```

### 5.2 Escalation Request Shape (bus message)

```python
# Sent by the agent needing escalation:
bus.broadcast("escalation.request", {
    "request_id": "escal_20260704_001",
    "agent_id": "deepseek",
    "cap_requested": "exec",
    "scope": {"path_scope": ["scratch/*"], "command_hint": "pytest tests/test_fleet.py"},
    "reason": "Need to run the fleet test suite to verify the roster change",
    "expires_in": "30m",            # suggested TTL
    "urgency": "normal",            # normal | high
})
```

### 5.3 Session Escalation (CLI flag override)

When a human launches a runner with `--trust` or `--allow-write`, those flags create a **session-scoped
escalation** that lives only for that process lifetime (never written to `acl.json`). This is the "I'm
driving, I trust this session" pattern:

```python
# In the runner's argument parsing:
session_grant = dataclasses.replace(base_grant,
    caps = base_grant.caps | ({Cap.EXEC} if args.trust else set()),
    path_scope = ["*"] if args.trust else base_grant.path_scope,
    expires_at = None,   # session-bound = process death is the expiry
    reason = f"session escalation by {os.getenv('USERNAME', 'human')} via CLI flag"
)
```

### 5.4 Time-boxing (the "trust-but-verify" mechanism)

Any grant created via escalation (not from a role template) SHOULD carry an `expires_at`. The registry
enforces this as a soft default (30 min) with an explicit `--permanent` override for super-admin.

```python
# In registry.py:
def create_grant(..., expires_at=None, permanent=False):
    if expires_at is None and not permanent:
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    ...
```

The runtime enforcement: `resolve()` returns a grant with `caps = set()` if `expires_at` has passed.
The agent gets a teaching error: "Your grant for 'exec' expired at .... Request re-escalation."

---

## 6. Audit

### 6.1 What gets logged

Every **privileged action** (write, exec, grant change, escalation approval/denial) is projected into
the existing durable event firehose (`core/events/event_log.py` → `promoter.py` pattern):

| Action | Event Kind | Detail |
|---|---|---|
| `write_file` / `edit_file` | `security.write` | `{agent_id, role, path, bytes_written, grant_ref}` |
| `run_command` | `security.exec` | `{agent_id, role, command, exit_code, grant_ref}` |
| Grant created | `security.grant` | `{agent_id, role, cap_granted, scope, granted_by, expires_at}` |
| Grant revoked | `security.revoke` | `{agent_id, role, cap_revoked, revoked_by}` |
| Escalation requested | `security.escalation.request` | `{agent_id, cap, scope, reason, request_id}` |
| Escalation approved | `security.escalation.approved` | `{request_id, approved_by, grant_ref}` |
| Escalation denied | `security.escalation.denied` | `{request_id, denied_by, reason}` |
| Permission denied | `security.denied` | `{agent_id, cap_attempted, path/command, reason}` |

### 6.2 Integration with the existing promoter

The `core/comm/promoter.py` already has a `SALIENT_KINDS` set (`handoff, decision, completion, blocker`).
Add `security.write, security.exec, security.grant, security.revoke, security.escalation.*` to it so
these survive Redis restarts:

```python
# In promoter.py:
SALIENT_KINDS = frozenset({
    "handoff", "decision", "completion", "blocker",
    "security.write", "security.exec", "security.grant", "security.revoke",
    "security.escalation.request", "security.escalation.approved",
    "security.escalation.denied", "security.denied",
})
```

### 6.3 Audit query door

```bash
py agent_cli.py audit --agent deepseek --since 2026-07-04  # all audited actions
py agent_cli.py audit --kind security.grant                  # all grant changes
py agent_cli.py audit --agent deepseek --cap exec            # all exec actions by deepseek
```

This reuses the existing `core/events/event_query.py` search path.

---

## 7. New-Agent Onboarding

### 7.1 Default role: `quarantined`

A brand-new agent boots as `quarantined` until explicitly granted a role. The registry's `resolve()`
returns the `quarantined` template for any unknown `agent_id`.

This is **fail-closed** — same principle as `guards.py:lock_veto` which fails closed on an unset
`AKASHIC_AGENT_ID`. An unknown agent can read files and read its own inbox, but cannot write, exec,
or send bus messages.

### 7.2 Onboarding flow

```
1. New agent appears on the bus (presence registration).
2. Console shows: "⚠ unknown agent 'qwen3.5-9b' — quarantined (read-only)."
3. Human (or super-admin) decides:
   a. Keep quarantined: no action.
   b. Promote to member:  py agent_cli.py grant set qwen3.5-9b --role member
   c. Promote to admin:   py agent_cli.py grant set qwen3.5-9b --role admin
   d. Custom grant:       py agent_cli.py grant allow qwen3.5-9b --cap write --scope "scratch/*"
4. Grant written to acl.json → Redis cache invalidated → agent's next ToolBox action sees new grant.
```

### 7.3 Bootstrapping the first grants

The `security/acl.json` file ships with:
- `claude` = super_admin (granted_by: "root")
- `deepseek` = admin (granted_by: "root")

All others are unknown → quarantined until granted.

### 7.4 Provisioning hook

When an agent is first provisioned (e.g., `scripts/provision_agent.py qwen3.5-9b`), it:
1. Generates an HMAC key (S-1 slice: identity)
2. Registers presence with `AgentCard{runtime_class, wake_mode, caps}`
3. **Does NOT auto-grant** — the human must explicitly `grant set`.
4. The runner refuses to start in `--agentic` mode if the agent is quarantined (teaching message).

---

## 8. Build Plan (6 gated slices)

Each slice is independently testable and ships with its own tests.

### S-0: Identity (prerequisite)
- **What:** HMAC signing on every bus message (`sig` field); `frm_verified` stamp on receive.
- **Files:** `core/comm/bus.py` (+30 lines in `_emit`, +20 in `_to_msg`); `core/trust/identity.py` (new, ~60 lines).
- **Tests:** sign+verify round-trip; reject tampered message; reject missing sig; offline fallback.
- **Prerequisite for:** Everything below. Without identity, tiers are spoofable.

### S-1: Grant Registry + ACL file
- **What:** `core/trust/registry.py` (mirrors `fleet/roster.py`); `security/acl.json`; Redis cache layer.
- **Files:** `core/trust/registry.py` (~120 lines), `core/trust/capabilities.py` (~40 lines), `security/acl.json` (initial grants).
- **Tests:** load grants; resolve known/unknown; role templates; cache invalidation; expired grant → no caps.

### S-2: ToolBox + Bus Enforcement
- **What:** ToolBox takes `Grant` instead of booleans; Bus checks grants before send/nudge.
- **Files:** `scripts/deepseek_chat.py` (refactor ToolBox.__init__ + add _require/_check_path_scope); `core/comm/bus.py` (add grant checks to send/broadcast/nudge).
- **Tests:** ToolBox denies write without Cap.WRITE; ToolBox denies path outside scope; Bus denies send without Cap.BUS_SEND; Bus denies nudge without Cap.BUS_NUDGE; quarantined agent can only read.

### S-3: CLI Grant Door + Audit
- **What:** `agent_cli.py grant` verbs; audit logging via promoter; `agent_cli.py audit` query.
- **Files:** `agent_cli.py` (+~80 lines for grant subcommands); `core/comm/promoter.py` (add security kinds to SALIENT_KINDS); `core/trust/audit.py` (new, ~50 lines).
- **Tests:** grant set/allow/revoke round-trips; audit query returns expected events; grant writes invalidate cache.

### S-4: Escalation Flow
- **What:** `escalation.request` bus kind; human approval via console; time-boxed grants.
- **Files:** `core/trust/escalation.py` (new, ~100 lines); `core/comm/promoter.py` (add escalation kinds); `scripts/bifrost_ui.py` (surface escalation requests in the console).
- **Tests:** request-reply round-trip; approval creates time-boxed grant; denial sends reason; expired grant denies action; session escalation via --trust flag.

### S-5: Runner Integration + Onboarding
- **What:** All runners read grants at boot; new-agent quarantined-by-default; `agent_cli.py provision` generates identity but does NOT auto-grant.
- **Files:** `bifrost_runner_deepseek.py`, `bifrost_runner.py` (pass Grant to ToolBox); `agent_cli.py` (provision verb); `core/comm/bus.py` (register() checks grant).
- **Tests:** unknown agent → quarantined; member agent → read+bus chat only; admin agent → read+write+no exec; exec escalation → allowed after grant.

### S-6: SEC-02 (Redis Auth) — independent, can ship anytime
- **What:** `requirepass` on Redis; password in `.secrets/redis.key`; bind 127.0.0.1; protected-mode on.
- **Files:** `core/foundation/redis_connection.py` (read password from secrets file); Docker/compose config.
- **Tests:** connection succeeds with correct password; connection refused with wrong password; offline fallback works.

---

## 9. Risk & Caveats

| Risk | Mitigation |
|---|---|
| **HMAC secret distribution** | Each agent's secret lives in `.secrets/agent_keys/<id>.key` (gitignored). Provisioning is a manual step. The dispatcher spawning headless agents would hold every secret — the Bifrost Mesh doc flags this as "a trust concentration to design around." For now, agents are manually launched by the human, so each runner holds only its own secret. |
| **acl.json merge conflicts** | Same-agent concurrent edits conflict (and should — needs human adjudication). Different-agent edits never conflict (per-key JSON). |
| **Cache staleness on revocation** | Revocation broadcasts a Redis pub/sub invalidation + a `bus.nudge` to force immediate re-check. Worst case = 60s stale window. |
| **Path scope bypass via symlinks** | `_resolve()` already calls `.resolve()` which follows symlinks. A symlink pointing outside root is caught by the `commonpath` check. A symlink pointing to a secret file is caught by `_is_secret()`. |
| **Escalation request spam** | Rate-limited: an agent can request escalation at most once per 60s per capability. After 3 denials in 10 min, requests from that agent for that cap are auto-denied for 1 hour. |
| **super-admin is a single point of trust** | By design. Claude is human-driven; the human is the root of trust. If Claude is unavailable, the human uses `agent_cli.py grant` directly. |

---

## Appendix A: Files Changed (summary)

| File | Change |
|---|---|
| `security/acl.json` | **NEW** — grant source of truth |
| `core/trust/__init__.py` | **NEW** — package |
| `core/trust/capabilities.py` | **NEW** — Cap enum, ROLE_TEMPLATES |
| `core/trust/registry.py` | **NEW** — grant reader + Redis cache |
| `core/trust/identity.py` | **NEW** — HMAC sign/verify (S-0) |
| `core/trust/audit.py` | **NEW** — audit event emitter |
| `core/trust/escalation.py` | **NEW** — escalation request/approve/deny |
| `core/comm/bus.py` | **MODIFY** — +HMAC in _emit/_to_msg; +grant checks in send/broadcast/nudge |
| `core/comm/promoter.py` | **MODIFY** — add security event kinds to SALIENT_KINDS |
| `core/foundation/redis_connection.py` | **MODIFY** — read Redis password from secrets (S-6) |
| `scripts/deepseek_chat.py` | **MODIFY** — ToolBox takes Grant instead of booleans |
| `scripts/bifrost_runner_deepseek.py` | **MODIFY** — resolve grant at boot; pass to ToolBox |
| `scripts/bifrost_runner.py` | **MODIFY** — same |
| `agent_cli.py` | **MODIFY** — +grant subcommands; +audit subcommand; +provision verb |
| `scripts/bifrost_ui.py` | **MODIFY** — surface escalation requests |
| `agent/harness/guards.py` | **MODIFY** — add grant-aware veto (optional; guards are advisory) |

## Appendix B: What stays unchanged

- **`core/comm/locks.py`** — advisory path locks are orthogonal to grants (two agents with WRITE still need lock coordination).
- **`agent/harness/capture.py`** — payload capture is orthogonal to grants.
- **`core/comm/control.py`** — PAUSE + hop-count + rate-limit are orthogonal (they protect the bus, not individual actions).
- **`core/fleet/roster.py`** — fleet models have their own status/capability model; the trust tier for fleet agents is `restricted` (one-shot call only).
- **`core/comm/nudge.py`** — nudge is orthogonal; the grant check happens at the Bus.send layer.
