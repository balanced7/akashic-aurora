---
akashic_id: art_20260723_sa-1-cap-enforcement-pre-registered-acce_1c0784
akashic_sha: 62fcb681eb04
status: draft
type: design
arc: SA-1 (docs/security-amendment-deepseek-scoped-admin-2026-07-22.md)
date: 2026-07-23
title: SA-1 Cap Enforcement — Pre-Registered Acceptance Suite
gist: "Arc: SA-1 (docs/security-amendment-deepseek-scoped-admin-2026-07-22.md) Charter: charters/sa1-cap-enforcement-charter-2026-07-22.md · Date: "
tenant: solo
visibility: fleet
seats: []
category: [security, conducting, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260722_security-schema-amendment-scoped-admin-g_17c9ca
    rel: cites
created: "2026-07-23T08:34:58"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260723_sa-1-cap-enforcement-pre-registered-acce_1c0784 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SA-1 Cap Enforcement — Pre-Registered Acceptance Suite

Arc: SA-1 (docs/security-amendment-deepseek-scoped-admin-2026-07-22.md)
Charter: charters/sa1-cap-enforcement-charter-2026-07-22.md · Date: 2026-07-23
Author: deepseek (self-chartered, R001 Part A)

## Pins RED-first (tests/test_sa1_cap_enforcement.py)

Each pin is a single test, each test is a single assertion. All RED before
SA-1 lands. Flipped to GREEN by the build. Run isolated (test namespace,
throwaway agent ids).

### S1 — require_cap fail-closed

| Pin | What | Injection | Expected |
|-----|------|-----------|----------|
| S1-P1 | Unknown agent refused | `require_cap("unknown_agent", Cap.WRITE)` | raises Denied with "quarantined" in message |
| S1-P2 | Missing cap refused | `require_cap("deepseek-ui", Cap.ADMIN_GRANT)` — deepseek-ui has no admin caps | raises Denied with "ADMIN_GRANT" in message |
| S1-P3 | Present cap passes | `require_cap("claude", Cap.ADMIN_GRANT)` — claude IS super_admin | no raise, returns None |
| S1-P4 | Registry error refused | `resolver.throws(Exception)` → `require_cap("claude", Cap.READ)` | raises Denied — fail-closed, never silently allow |
| S1-P5 | Expired grant refused | inject grant with `expires_at` in the past → `require_cap(agent, Cap.READ)` | raises Denied — expired = quarantined |

### S2 — Existing checks unharmed

| Pin | What | Expected |
|-----|------|----------|
| S2-P1 | toolbox EXEC gate still works | `_tb(agent_id="deepseek-ui").run_command(...)` → "REFUSED" in output |
| S2-P2 | toolbox KB_LEARN gate still works | `_tb(agent_id="deepseek-ui").knowledge_learn(...)` → "ERROR" in output |
| S2-P3 | toolbox BUS_SEND gate still works | `_tb(agent_id="restricted").bifrost_send(...)` → "deny-by-default" in output |
| S2-P4 | Existing pins test_g5_exec_cap_checked | test unchanged → still passes |
| S2-P5 | Existing newborn gauntlet | test unchanged → quarantined ids still quarantined |

### S3 — Conductor approve gated

| Pin | What | Expected |
|-----|------|----------|
| S3-P1 | `approve(by="user")` refused | user has no ADMIN_APPROVE → raises Denied |
| S3-P2 | `approve(by="claude")` allowed | claude has ADMIN_APPROVE → no raise |
| S3-P3 | `approve(by="deepseek")` refused today | deepseek has no ADMIN_APPROVE (pre-SA-2) → raises Denied |
| S3-P4 | Approve emits audit event | `approve(by="claude", tid="T001")` → one narr:beat:trust event with `{"action": "approve", "actor": "claude", "outcome": "allowed"}` |

### S4 — Grant verb gated

| Pin | What | Expected |
|-----|------|----------|
| S4-P1 | Grant by unprivileged agent refused | `cmd_grant(agent_id="deepseek-ui", target="x", caps=["read"])` → raises Denied |
| S4-P2 | Grant by claude allowed | `cmd_grant(agent_id="claude", target="test-agent", caps=["read"])` → no raise, acl.json updated |
| S4-P3 | Grant at-or-above admin refused for non-super-admin | `cmd_grant(agent_id="deepseek", target="x", role="admin")` → raises Denied (SA-2 bounded-scope enforces this later) |
| S4-P4 | Grant emits audit event | `cmd_grant(...)` → one narr:beat:trust event with `{"action": "grant", "actor": ..., "target": ..., "outcome": ...}` |

### S5 — Audit trail

| Pin | What | Expected |
|-----|------|----------|
| S5-P1 | Denied events emit | Any `require_cap` refusal → one narr:beat:trust event with `outcome: "denied"` + the missing cap name |
| S5-P2 | Allowed events emit | Any `require_cap` that passes → one narr:beat:trust event with `outcome: "allowed"` (or emit only on write actions — design choice: likely emit-all for audit completeness) |
| S5-P3 | Audit events queryable | `events(search="trust", kind="narr:beat:trust")` returns the last N trust events, newest first |

## Fence execution plan

1. Write `tests/test_sa1_cap_enforcement.py` with all pins RED (assertions that
   FAIL because require_cap / the conductor cap check / the grant verb do not
   exist yet). Mark the file `@pytest.mark.xfail(strict=True)` or use
   `pytest.skip` with a "SA-1 unbuilt" message.

2. Every pin assertion names the B1-B5 bar it checks in its docstring.

3. Run `py -m pytest tests/test_sa1_cap_enforcement.py -q` → all skip/xfail
   (no false green). This proves the acceptance suite IS pre-registered and
   RED-before-build.

4. SA-1 build lands → remove xfail decorators → suite flips GREEN.

5. Full-suite regression: `py -m pytest tests/ -q` — existing known failures
   unchanged, no new failures from the acceptance suite.

## What this suite deliberately does NOT test (SA-2's lane)

- Bounded-admin-grant scope constraints (member-only, claude-cosign,
  security/ excluded) — these are SA-2 policies, not SA-1 primitives.
- The grant CLI verb's full surface (help text, error messages, --dry-run).
- Remote-steering operator identity verification (SEC-01's lane).
