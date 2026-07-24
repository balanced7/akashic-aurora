---
akashic_id: art_20260711_t034-registry-dial-consolidation-reconci_6c7925
akashic_sha: 975498017f98
status: current
type: design
date: 2026-07-11
title: "T034 Registry + Dial Consolidation -- reconciled build spec (dual-half, dated)"
gist: "Class: build-spec (design PARKED until the engine exam passes -- engine-first directive; this is the artifact the eventual gated ship must c"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_t034-registry-dial-consolidation-claude_34a872
    rel: cites
  - target: art_20260711_t034-registry-dial-consolidation-deepsee_a65322
    rel: cites
created: "2026-07-11T04:59:57"
updated: "2026-07-23T21:42:07"
---
<!-- GENERATED PROJECTION of art_20260711_t034-registry-dial-consolidation-reconci_6c7925 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T034 Registry + Dial Consolidation -- reconciled build spec (dual-half, dated)

Class: build-spec (design PARKED until the engine exam passes -- engine-first directive;
this is the artifact the eventual gated ship must cite, T031 hook 1)
Governs: T034 (approved by Daniel 2026-07-11).
Halves: research/reviewed/claude-t034-registry-design-2026-07-11.md (blind)
+ research/reviewed/deepseek-t034-registry-design-2026-07-11.md (blind part 1 + red-team
part 2; delivered across 7 durable notes after a silent ~4k tool-arg clip on its side --
that clip is its own spun-off fix task).
Brief (Daniel, verbatim): "keep things elegant with sensible connections and endpoints;
the coding equivalent of cleaning up a messy server rack; consolidate similar features into
components that would be better artifacts for those systems / pipings to live in."

## CONVERGED blind (the strongest gate this fleet produces)

Both halves, independently: the problem is NOT "build a kernel" -- five of six kernel organs
already exist; the gap is dial DISCOVERY/COORDINATION/AUDIT/CREEP (deepseek's A-D naming
adopted). The fix: ONE manifest as source of truth, ONE read path with three-layer
resolution (env -> Store -> code default), ONE audited write path, a creep guard. NOT a new
layer, NOT YAML/TOML (a config file is another uncoordinated surface). Kill-switch/env
carve-out and the graded-dial hazard were found by both halves from different lenses.

## The dial declaration (deepseek shape, claude manifest role)

`core/registry/dials.py` -- the rack diagram Daniel asked for. One frozen dataclass per dial:
key (dotted namespace), kind, default, env (DECLARED override name or None -- deepseek's
key divergence, adopted: no hidden fallback chains; every override is listable), desc,
authority ("operator" | "admin" -- two tiers, his own cut of three), introduced (the slice
that created it -- provenance for WHY a dial exists), deprecates, and per red-team:
env_only (dated reason + review_date for carve-outs like timescale), removed (tombstone
with date+reason -- deletion ritual as easy as registration, Goodhart-1 counter),
hot (hot-path dials get a local refresh thread, never per-call Store reads, Goodhart-2
counter).

## Read path

`dial(key)` in `core/registry/resolver.py`: declared-env override -> Store `settings:` value
(CAS-written; RB-8 is the foundation) -> manifest default. Never raises; Store-down =
defaults + a boot confession line "N flips NOT in effect" (RB-5 doctrine, claude F3).
Short-TTL cache; hot dials exempt via the manifest field. During migration, an import-time
dev/test assertion pins manifest default == the not-yet-deleted module constant (deepseek
Leak-3 bridge -- the assertion IS the migration safety).

## Write path

`agent_cli.py setting-flip <key> <value> --reason "..."`: acl gate by the dial's authority
tier (quarantined agents deny-by-default; a flip is a control-plane act, R15 lineage) ->
kind/type check vs manifest -> CAS write -> `setting_flip` Ledger event {key, old, new, by,
reason} (git-durable via snapshot) -> visible in `settings` + boot deviation line.
Drift-2 counter (deepseek): the wrap/Forge report surfaces flip volume ("N flips this week,
M without a linked commit"); a rising flip-to-commit ratio is a named finding, not a vibe.

GRADED DIALS (claude rule, deepseek coupling direction): the grading system declares what
it grades (grades_dials list in the corpus/battery manifest -- the registry stays
consumer-blind); the flip verb CONSULTS that declaration at flip time and BLOCKS a graded
dial's flip without a --regraded <evidence> receipt. RB-23 made this concrete: FLOOR_CHARS
is graded AT 15; a silent flip to 25 voids a held-out result the record still claims.
(Block not warn -- claude Q4 resolved by its own argument: warn is how method rot starts.)

## What stays OUT (both halves, merged taxonomy)

- Grammar/algorithmic constants (PROMISE_OPENERS, STOP_VERBS, MARKER_PATTERN): they define
  what a detector IS; they version with code and are corpus-graded as a unit.
- Derived runtime values (PULSE_GEN, locks, cursors, session ids).
- Import-time test seams (AKASHIC_TIMEOUT_MULTIPLIER): env_only WITH dated justification.
- Secrets: guard G-c rejects kind=secret and *_API_KEY/*_TOKEN/*_SECRET env names outright.
- KILL SWITCHES: env stays authoritative (must work when the Store is down or lying);
  listed in the manifest as env_only so the rack diagram still shows them.
- CONTROL KEYS (pause/halt/nudge/steer): deepseek cut #3 ADOPTED over claude Phase-3
  read-through -- hard real-time barge-in signals are NOT dials; they keep their own
  semantics and surface in `doctor --control`; the manifest cross-references without
  absorbing. [Daniel veto window: this reverses the approved sketch's read-through.]

## Guards (immune-system extension; credibility over strength)

- G-a bright line (deepseek Leak-1, adopted over claude's constant-shape heuristic): the
  resolver is the ONLY sanctioned env reader in core//scripts/; ANY os.environ/os.getenv/
  environ[] access outside it FAILS, dated allowlist for the named non-dials. Covers all
  access patterns instead of pattern-matching key names.
- G-b manifest rot, noiseless form (deepseek Drift-1): owner optional (multi-owner list
  supported); when absent the check weakens to "some module reads this" -- a noisy guard
  gets disabled and then catches nothing (immune-system TRUSTWORTHY property).
- G-c no secrets (above).
- G-d dated-exemption expiry: checked at SHIP TIME and at BOOT (boot runs at least daily in
  practice -- deepseek cut #4's honesty concern met without a new daemon; if boot cadence
  ever thins, promote to the scheduled-review surface and name it then). [Daniel veto
  window: deepseek argued for a true periodic checker.]
- Manifest size TREND is a ship-gate report line; monotonic growth is a finding
  (Goodhart-1). No dial-count target exists in either direction.

## Introspection

`agent_cli.py settings`: DEVIATIONS ONLY by default (deepseek cut #2 = claude boot line,
converged); --all renders the full rack diagram (every dial: effective value, source layer,
last flip who/when/why). Listing respects acl visibility by authority tier (deepseek
Leak-4). Boot: one line, only when deviations exist.

## Build slices (deepseek's phasing adopted -- more granular than claude M1-M4)

  P1 manifest + resolver + guards WARN-only + settings verb. Nothing migrated.
  P2 one consumer family end-to-end (timeout/age family) + flip audit proven live
     (env override wins; Store flip visible within TTL; Ledger event in the snapshot).
  P3 boot deviation line + doctor cross-ref of control keys (NOT absorption).
  P4 guards harden WARN->FAIL; new dials manifest-only from here.
  P5 opportunistic migration forever after (a module touched = its dials move); no big bang.
Each slice gated + pinned per the battery discipline; deepseek [verify] per slice.

## Divergences resolved on technical merit (Daniel veto open until build)

  1. graded-dial coupling DIRECTION: deepseek's inversion adopted (grading system declares;
     registry consumer-blind); claude's BLOCK-without-receipt enforcement kept. Better
     dependency direction, same teeth.
  2. control keys: deepseek's keep-out-with-cross-ref adopted (see What stays OUT).
  3. expiry checking: boot-time + ship-time (claude) instead of a new periodic daemon
     (deepseek), with the escalation path named. Honesty preserved by declaring the bound.

## Named risks carried into build

All six claude failure modes (F1-F6) + deepseek's four leaks / two drifts / two Goodharts
are acceptance-relevant: P1's pre-registered tests must cover at minimum -- undeclared-dial
FAIL (all three env access patterns), manifest/constant drift assertion, flip-without-acl
refused, graded-flip blocked without receipt, secrets rejected, deviations-only listing,
Store-down confession line. Corpus-of-record: this spec + both halves verbatim.
