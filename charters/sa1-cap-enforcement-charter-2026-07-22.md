# SA-1 Cap Enforcement — Whole-Arc Charter (deepseek, self-chartered)

Status: chartered (2026-07-22, deepseek per R001 Part A — first self-charter)
Type: whole-arc · Arc: security-schema / trust-substrate · Owner: deepseek
Gate: Daniel at charter (now), design, ship — fence evidence self-presented
Authority: docs/rulings/R001-deepseek-trust-2026-07-22.md Part A ("whole-arc ownership is your DEFAULT")

## Why this arc, why now

Two Daniel-directed threads point at ONE missing primitive — enforced capabilities at
action sites. Remote-steering (SEC-01/S-0) needs effects keyed on verified identity, not
self-asserted `frm`. My scoped admin.grant (R001 Part B) needs `admin.grant`/`admin.approve`
to be CHECKED before anyone grants or approves. Both threads are blocked on the same absent
machinery: a `require_cap(actor, cap)` check that lives at the door, not just in the enum.

Building enforced-identity-and-caps ONCE lands both threads. SA-1 is the capability half.

## Current state (verified 2026-07-22)

**What exists:**
- `core/trust/capabilities.py`: `Cap` enum fully declared (13 caps including ADMIN_GRANT,
  ADMIN_APPROVE). ROLE_TEMPLATES bundle caps correctly per role.
- `core/trust/registry.py`: `resolve(agent_id)` returns a `Grant` with `.has(Cap)` and
  `.can_write(path)` and `.can_send_kind(kind)`. Mtime cache. Bootstrap floor for core
  agents when acl.json is missing. Deny-by-default to quarantined.
- `core/comm/toolbox.py`: `_bus_send_ok()` checks `Cap.BUS_SEND` + kind allowlist. `_kb_write_ok()`
  checks `Cap.KB_LEARN`. `run_command()` checks `Cap.EXEC` (line 910). These are the only
  enforced cap checks in-tree.

**What is MISSING (the gap):**
- `admin.grant` / `admin.approve` are in the enum and the super_admin template, but NO
  code checks them before a grant or approval action. Verified: `core/coord/conductor.py:91`
  `approve(tid, *, by="user")` has zero cap check. There is no CLI `grant` verb at all.
  The `acl.json` edit path (direct file write) has no runtime gate.
- `Cap.ADMIN_GRANT`, `Cap.ADMIN_APPROVE`: declared, never queried. kimi's audit independently
  found the sibling gap — `frm` is self-asserted, S-0 identity signing is unbuilt.
- No `require_cap()` helper — every existing check inlines the pattern (`g.has(Cap.X)`),
  which is fine for the 3 existing checks but won't scale to grant/approve action sites.

**The cap enforcement that DOES exist is the pattern to follow:**
```python
# toolbox.py:910
if not resolve(self.agent_id).has(Cap.EXEC):
    return "REFUSED: no exec capability"
```
Simple, fail-closed, already proved in production (newborn gauntlet verified).

## Arc scope (what SA-1 builds, in order)

### S1 · `require_cap()` helper — ONE canonical enforcement function
`core/trust/registry.py` (or a new `core/trust/enforce.py`): one function all doors call:
```python
def require_cap(agent_id: str, cap: Cap, *, reason: str = "") -> None:
    """Raise Denied (or return a structured refusal) if agent_id lacks cap.
    Fail-closed: registry error → REFUSED + loud. Never silently allow."""
```
The ONE place that calls `resolve()` and `grant.has()`. Every door that gates on a cap
calls this function. The existing 3 inline checks migrate to it. The function emits a
ledger event on refusal (auditable). Pins: unknown agent → refused; missing cap → refused
with teaching text naming the missing cap; registry error → refused LOUD.

### S2 · Wire grant/approve action sites
Two action sites get `require_cap()`:
- `core/coord/conductor.py:approve()` → requires `Cap.ADMIN_APPROVE` on `by`. The `by`
  parameter is currently a self-asserted string ("user"/"claude") — SA-1 doesn't fix identity
  (that's SEC-01), but it DOES check the cap on whatever identity is presented. A forged
  "by=user" would need to pass `resolve("user")` → quarantined → refused. The identity
  gap narrows: you can lie about who you are, but the lie must resolve to a grant that holds
  the cap. Today "user" resolves to quarantined (no entry in acl.json).
- New CLI verb `agent_cli.py cmd_grant` (or similar) — a git-tracked edit to acl.json that
  calls `require_cap(actor, Cap.ADMIN_GRANT)` before writing. This is the grant door itself.
  Scope: add/amend/revoke entries. Every use emits a ledger event.

### S3 · Audit ledger events
Every `require_cap` refusal and every grant/approve action emits a durable ledger event
(`narr:beat:trust` family):
```
{actor, target_cap, action, outcome, timestamp, reason}
```
The operator can review "who granted what to whom." This is SA-2's audit surface
predecessor — SA-2 builds the dedicated view; SA-1 builds the event emission.

### S4 · Fence + verify
SA-1 carries its own fence evidence — a test suite that:
- Proves quarantined agent is refused at every action site
- Proves admin agent (without ADMIN_GRANT) is refused at grant
- Proves super_admin passes
- Proves `by="user"` (unregistered) is refused at approve
- Proves `by="claude"` (super_admin) passes at approve
- Proves `require_cap` fail-closed under registry corruption

## What SA-1 deliberately does NOT build (out of scope)

- **Identity verification (SEC-01).** `by=` remains a self-asserted string. SA-1 checks
  caps on whatever identity is presented — if you can forge a super_admin identity, you
  bypass the cap check. This is the EXISTING gap (frm spoofing), not widened. SEC-01 is
  the sibling slice that closes it.
- **The grant CLI verb's full surface.** SA-1 builds the VERB + the cap check. The
  bounded-admin-grant scope constraints (member-only, claude-cosign, security/ excluded)
  are SA-2 — they are POLICIES that ride the enforcement primitive SA-1 builds.
- **Remote-steering operator identity.** SA-1's `require_cap()` is the same function the
  remote-steering op_daemon calls before writing `kind=operator` to the bus. But the
  Ed25519→agent_id mapping is SEC-01's territory.

## Acceptance (Daniel-gate bars)

| Bar | What | How measured |
|-----|------|-------------|
| B1 | `require_cap` fail-closed | Quarantined agent → refused at every door; registry error → refused LOUD |
| B2 | Existing 3 checks unharmed | toolbox.py exec/kb/bus-send checks still pass their existing pins |
| B3 | Approve gated | `conductor.approve(by="user")` → refused; `approve(by="claude")` → allowed |
| B4 | Grant gated | `cmd_grant(actor="deepseek")` → refused (no ADMIN_GRANT cap today); after SA-2 activates → passes |
| B5 | Audit trail | Every refusal emits a narr:beat:trust event; every grant emits one |
| B6 | No regression | Full suite ≤ known failures; no new failures from SA-1 changes |

## Fence shape (invoked by me, evidence presented at gate)

Claude fences as adversarial review. I present:
1. Pin table (B1-B6) with test names and outcomes
2. Diff of every site touched, annotated with "this check was MISSING before"
3. Full-suite run showing no new failures
4. Live drill: `conductor.approve(...)` called with a quarantined `by=` — refuses

## The two-thread payoff

SA-1 unblocks:
- **R001 Part B (my scoped admin.grant):** the moment SA-1 lands, SA-2 can activate —
  deepseek gets bounded admin.grant/admin.approve WITH enforced bounds.
- **Remote-steering SEC-01/S-0:** `require_cap()` is the function the op_daemon calls
  to verify "this Ed25519-signed operator has Cap.BUS_SEND + operator kinds" — one
  primitive, two callers.

## Precedent-setting (first use of R001 Part A)

This is the first self-chartered arc under the new whole-arc doctrine. The charter is
filed to the ledger; mechanism is mine; Daniel gates at charter/design/ship; fence
evidence is self-presented. Claude counters as adversarial review.

---
*Self-chartered by deepseek under R001 Part A authority, 2026-07-22.*
