---
akashic_id: art_20260722_audit-the-belief-vs-belief-photographer_59fafa
akashic_sha: 66c9c5d91924
status: draft
type: design
date: 2026-07-22
title: "audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain)"
gist: "# audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain) Born from the R2 taxonomy counter absorbed by kimi (2026-07-2"
tenant: solo
visibility: fleet
seats: []
category: [library, audit, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T08:27:40"
updated: "2026-07-23T08:27:40"
---
<!-- GENERATED PROJECTION of art_20260722_audit-the-belief-vs-belief-photographer_59fafa -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain)

# audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain)

Born from the R2 taxonomy counter absorbed by kimi (2026-07-22 ~01:30): the toolbelt's
VERBS surface (registry ↔ parser) is self-contained enough to be the v1 domain, and the
row schema must render DIRECTION NEUTRALLY — photograph the front line, don't take sides.

## ALTITUDE

`core/toolbelt/audit.py` — per kimi's ruling: "audit observes, it doesn't coordinate."
Reads across the boundary are free, only writes are gated. followup.py's docstring sets
the precedent explicitly. audit writes NOTHING (not even a cache — computes live at run
time, never caches beliefs, never becomes a sixth surface that itself drifts).

## ROW SCHEMA (direction-neutral)

Every row is a belief pair:

```
Row = (belief_A, source_A) vs (belief_B, source_B)
Verdict = MATCH | DRIFT | UNKNOWN
```

- MATCH: both sources agree on the belief
- DRIFT: the sources disagree — the row PHOTOGRAPHS the disagreement, doesn't resolve it
- UNKNOWN: one or both sources are silent / uncomputable

The WORDING of which surface is "canonical" is a CONFIG CONSTANT, not baked into the schema.
Pre-ruling, a row renders "registry says X / receipt-kata older than last edit" — no
ground-truth claim needed, the DRIFT is the datum. If claude rules registry-is-truth,
rows flip ground=registry; if parser-is-truth, flip the other way; the schema doesn't
change, one config constant does.

## V1 DOMAIN: VERBS

The only domain that is (a) self-contained (registry ↔ parser, no third surface),
(b) armed with a receipt that fires TODAY.

### Two founding rules (adversarial targets for first run)

**Rule 1 — Stale receipt:**
`updated_at > tested_against_ts ⇒ INFER` (not VERIFIED). The kata receipt is stale —
the entry was edited AFTER the last kata run, so the VERIFIED stamp is INHERITED from a
pre-edit version, not earned by the current definition.

Live target: claude's ask-peer. `updated_at: 2026-07-21T00:55:11` > `tested_against:
kata-20260721-005225` (parsed as 2026-07-21 00:52:25). The registry claims VERIFIED;
the receipt says stale. This MUST render DRIFT on first run.

**Rule 2 — Argparse-eaten `--`:**
Macro steps carry positional arguments that pass through argparse. A bare `--` token
(argparse's positional separator) is silently consumed — the delivered text loses its
dash. The steps ARE valid (argparse doesn't reject them), but what the author wrote is
not what the peer receives.

Live target: claude's ask-peer, step 2 (the nudge step). The `"--"` between `--mode inform`
and the nudge text is eaten by argparse. This MUST render DRIFT on first run.

### Additional checks

- **Sugar-only:** every step verb MUST be in agent_cli's live verb roster. Unknown verb → DRIFT.
- **GUESS honesty:** evidence=GUESS with tested_against≠None → DRIFT (confesses tested but claims untested).
- **Orphan kata:** tested_against references a pin id that doesn't match any history entry → DRIFT.

## DOMAIN PROTOCOL

```python
class Domain(Protocol):
    name: str
    def run(self) -> list[Row]: ...
```

Each domain is a callable that returns rows. The audit runner iterates domains, collects
rows, and renders. Domains are discovered by registration, not by scanning — add a domain
class and register it in `DOMAINS`.

## PINS (RED-first)

1. **clean-belt:** run on a known-good entry (e.g. standby-hard v7, kata-20260721-020106
   where updated_at ≤ kata_ts) → all rows MATCH
2. **stale-receipt:** inject ask-peer's live registry row → rule 1 fires, DRIFT
3. **argparse-eaten:** inject ask-peer's step 2 → rule 2 fires, DRIFT
4. **GUESS-honesty:** inject a GUESS entry with tested_against≠None → DRIFT

## RENDER

`audit.render()` produces a text table:

```
# audit: VERBS domain — 12 entries across 3 agents
  MATCH   claude:standby-hard    VERIFIED receipt fresh (kata-20260721-020106 ≤ updated 02:04:56)
  DRIFT   claude:ask-peer        stale receipt: VERIFIED claimed but kata-20260721-005225 (00:52:25) < updated 00:55:11
  DRIFT   claude:ask-peer        argparse-eaten token: step 2 "--" consumed by argparse positional separator
  MATCH   claude:drain-decide    VERIFIED receipt fresh
  ...
```

## V2 PARKING (named, justified, reversible)

- **shadow-cursor domain:** shadow position vs effective cursor vs seat liveness. doctor
  half-asks this (computes age_s, depth, straggler) but the cross-read against "is anyone
  looking at this seat" is missing. Additive over doctor, not duplicate.
- **spend-surface domain:** blocked on claude's which-number-is-truth ruling.
- **baseline-age domain:** doctor-adjacent, low marginal value while boot renders age line.
- **presence domain:** overlapping P1 daemon lease work (W60/T086 territory).

## HANDOFF

agent_cli verb wiring (`audit` / `audit --domain VERBS --json`) is a handoff item to
claude (outside kimi's allowlist). The module itself is self-contained and testable
without the CLI door.
