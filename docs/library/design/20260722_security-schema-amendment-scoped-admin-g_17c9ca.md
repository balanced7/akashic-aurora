---
akashic_id: art_20260722_security-schema-amendment-scoped-admin-g_17c9ca
akashic_sha: 93eb00164dfe
status: draft
type: design
date: 2026-07-22
title: Security-schema amendment — scoped admin.grant for deepseek
gist: "**Authorization:** ruling R001 (docs/rulings/R001-deepseek-trust-2026-07-22.md) — Daniel: \"scoped admin grant … via the security-schema amen"
tenant: solo
visibility: fleet
seats: []
category: [identity, security, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_agent-security-schema-design-proposal_cdccf1
    rel: cites
  - target: art_20260722_ruling-r001-deepseek-trusted-with-more_3b86eb
    rel: cites
  - target: art_20260722_remote-steering-security-design-reconcil_120f70
    rel: cites
created: "2026-07-22T21:37:44"
updated: "2026-07-23T21:42:07"
---
<!-- GENERATED PROJECTION of art_20260722_security-schema-amendment-scoped-admin-g_17c9ca -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Security-schema amendment — scoped admin.grant for deepseek

**Authorization:** ruling R001 (docs/rulings/R001-deepseek-trust-2026-07-22.md) — Daniel:
"scoped admin grant … via the security-schema amendment path."

## The problem this amendment must solve FIRST (the honest blocker)

`admin.grant` and `admin.approve` are declared in `core/trust/capabilities.py` but **enforced
nowhere** — no action site checks the cap before performing a grant or approving an escalation.
Verified 2026-07-22: the only occurrences are the enum definition and the super_admin role
template (capabilities.py:52). The ACL is currently an honor-system document, not a runtime gate.
kimi's remote-steering audit independently found the sibling facts: `frm` is self-asserted, the
ledger's human gate takes an unauthenticated `by="user"`, S-0 (identity signing) is unbuilt.

**Therefore a scoped admin.grant cannot be delivered as an ACL edit alone — the scope would be
documentation with no teeth.** This amendment's first slice is to BUILD the enforcement; the
grant to deepseek activates only once its bounds are enforceable.

## Convergence (why this is worth building well, not hacking)

Two Daniel-directed threads now point at ONE missing primitive:
- **Remote-steering** (research/reviewed/remote-steering-reconciliation-2026-07-22.md): needs
  operator effects keyed on a verified signature, not `frm` — i.e. enforced identity (SEC-01/S-0).
- **deepseek scoped admin.grant** (R001): needs cap-checks enforced at grant sites — i.e.
  enforced capabilities.

Build enforced-identity-and-caps ONCE and both threads land. This amendment is scoped to the
capability half; it cites the remote-steering doc as its identity sibling.

## Proposed slices (each independently gateable; NOTHING built before Daniel ratifies bounds)

- **SA-1 · Cap enforcement at grant sites.** A `require_cap(actor, cap)` check wired into every
  grant/escalation/approve action site (the CLI grant verb, conductor escalation, any ACL write).
  Fail-closed: no cap → refused + audited event. Pins: an actor without the cap is refused; with
  it, allowed; every attempt emits a ledger event. This is the primitive both threads need.
- **SA-2 · Bounded admin.grant for deepseek.** With SA-1 live, grant deepseek:
  - `admin.approve` — may approve escalation REQUESTS from other agents; every approval audited.
  - `admin.grant` **bounded by enforced construction**: may grant only up to **member tier +
    scoped-write**; may NOT grant `admin`/`super_admin`, exec beyond the established families, or
    any path under `security/` or `.claude/`; any grant at member-or-above requires **claude
    cosign** (dual-control, enforced not documented). Bounds are CHECKED by SA-1's machinery, not
    just written in the reason.
  - **Not time-boxed** (07-05 lesson: a whole-grant time-box silently quarantined the role at
    expiry). Revoke by editing the record. Review date noted in the reason, not an `expires_at`.
- **SA-3 · Audit surface.** `admin.grant`/`admin.approve` uses render in a dedicated audit view
  (who granted what to whom, when, cosigned by whom) — the operator can review deepseek's grants
  the way the remote-steering `op_audit` stream lets Daniel review operator events.

## What this amendment REFUSES

- No unenforced cap flip (the whole reason this is an amendment, not an ACL edit tonight).
- No admin/super_admin-tier grants by deepseek — it can lift agents to member+scoped-write, never
  to peer-super-admin.
- No grants touching `security/` or `.claude/` — the fleet's own trust substrate stays
  super-admin+human only.
- No time-box (revoke-by-edit only).

## For Daniel's gate

1. Ratify the bounds in SA-2 (or dial them — tighter: approve-only-first; looser: higher tier /
   no cosign).
2. Approve SA-1 as the enabling build (it is also the remote-steering identity primitive — one
   build, two payoffs).
3. Sequencing: SA-1 (enforcement) → SA-2 (deepseek's bounded grant activates) → SA-3 (audit view).
   Part A of R001 (whole-arc default) is already live and independent of all of this.

*Scoped and filed by claude a4fa8f8d. The honest version of "scoped admin.grant": the scope is
only real when it is enforced, so enforcement is slice one.*
