---
akashic_id: art_20260711_t034-registry-dial-consolidation-claude_34a872
akashic_sha: 31d87deb7a68
status: draft
type: report
date: 2026-07-11
title: T034 Registry + Dial Consolidation -- claude design half (FENCED)
gist: "# T034 Registry + Dial Consolidation -- claude design half (FENCED) Date: 2026-07-11. Author: claude, one blind half of the fenced dual desi"
tenant: solo
visibility: fleet
seats: []
category: [security, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_t034-registry-dial-consolidation-deepsee_a65322
    rel: cites
created: "2026-07-11T03:45:29"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260711_t034-registry-dial-consolidation-claude_34a872 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T034 Registry + Dial Consolidation -- claude design half (FENCED)

# T034 Registry + Dial Consolidation -- claude design half (FENCED)

Date: 2026-07-11. Author: claude, one blind half of the fenced dual design.
DeepSeek's half: research/reviewed/deepseek-t034-registry-design-2026-07-11.md (unread at
authoring; his part 2 red-teams the approved sketch AFTER his blind part 1).
Brief (Daniel, verbatim): "keep things elegant with sensible connections and endpoints;
the coding equivalent of cleaning up a messy server rack; consolidate similar features into
components that would be better artifacts for those systems / pipings to live in."
Standing: DESIGN ONLY until the engine exam passes (engine-first directive). Build cites
the reconciled spec per T031 hook 1.

## Diagnosis (what the rack actually looks like)

Aurora already has five of six kernel organs (policy=acl+trust, events=bus+promoter+firehose,
state=Store+Ledger, experiments=experiment.py, introspection=doctor/status/boot). The mess is
ONE organ: dials live on three uncoordinated surfaces with no shared address, no provenance,
no single view --
  S1 env vars: 10 environ.get hits across 8 files (AKASHIC_*/DEEPSEEK_*/BIFROST_*).
  S2 module constants that are really dials: FLOOR_CHARS, REPLY_TIMEOUT_SEC, MAX_TOKENS,
     HINT_MAX_PER_AGENT, ack-UNHANDLED hours, proposed-stale days, the 4000 send clip.
  S3 Redis control keys: control.pause, per-agent halt, nudge/steer flags, narration dial.
Not every constant is a dial (see taxonomy). The count is modest (~30) -- that is a feature;
this arc must not inflate it.

## Design: three LAYERS with precedence, replacing three SURFACES with none

Zero new primitives: registry = a `settings:` namespace on the existing Store + `setting_flip`
Ledger events + the existing acl for authority. NOT a new kernel layer, NOT YAML config files
(a config file would be a FOURTH surface with its own sync problem).

Resolution order (settings.get(key), never raises, fail-open to defaults):
  L1 ENV override      -- ops/drill emergency layer; wins always; the medium that works when
                          Redis is down (timescale.scaled stays here by design).
  L2 STORE value       -- the fleet-flipped runtime deviation; CAS-written (RB-8 is the
                          foundation -- two sessions flipping one dial is the twin incident
                          in a different hat); short-TTL read cache (5-30s) for hot paths.
  L3 CODE default      -- declared in ONE in-repo manifest (see below), reviewable in git.

MANIFEST (the elegance artifact Daniel is asking for): one file, e.g. core/foundation/
settings_manifest.py -- every dial's key, type, default, owner module, and optional
`graded_by` pointer. The manifest IS the rack diagram: one place that names every dial,
where it lives, and what depends on it.

Write path: `py agent_cli.py setting-flip <key> <value> --reason "..."` ->
  acl gate (admin+; quarantined agents deny-by-default; a flip is a control-plane act,
  R15 lineage) -> type-check vs manifest -> CAS write -> `setting_flip` Ledger event
  {key, old, new, by, reason} (git-durable via the existing snapshot/mirror lane) ->
  boot/status render.

Introspection: a `settings` verb listing every dial with its EFFECTIVE value + source layer
(env/store/default) + last flip (who/when/why); boot adds one line only when deviations
exist: "N dials off-default: ...". Server-rack visibility without boot noise.

Guard (comprehensibility immune system extension, same pattern as REF_ALLOWLIST):
  G-a: a module-level dial-shaped constant (UPPERCASE bool/number) in core//scripts/ not
       named by the manifest = FAIL (dated allowlist for legit non-dials).
  G-b: a manifest entry whose owner module no longer reads it = FAIL (manifest rot is
       bidirectional).

## Taxonomy -- what consolidates and what STAYS code (the load-bearing judgment)

- BEHAVIOR FLAGS (narration level, retrieval toggles)          -> registry.
- TUNING NUMBERS (timeouts, caps, ages, clip lengths)          -> registry, default in manifest.
- KILL SWITCHES (AKASHIC_STOP_PROMISE=0, KILLPOINT)            -> ENV STAYS AUTHORITATIVE.
  A kill switch must work when the Store is down or lying; manifest lists them as env-layer
  so the rack diagram still shows them.
- GRADED DIALS (FLOOR_CHARS and anything a pre-registered corpus/battery graded)
  -> registry, BUT flip requires a re-grade receipt: manifest `graded_by` names the corpus
  test; the flip verb warns (or blocks, reconciliation Q4) without --regraded <evidence>.
  RB-23 made this concrete: the floor is graded AT 15; silently flipping to 25 voids the
  held-out result while the record still claims it. A registry without this rule LAUNDERS
  method-rot (R18) through a convenient verb.
- STRUCTURAL LOGIC (PROMISE_OPENERS/STOP_VERBS/MARKER_PATTERN regexes) -> stay code. They
  version with the logic that interprets them and are corpus-graded as a unit.
- SECRETS -> never (allow_secrets=False stands).
- LATENCY-CRITICAL CONTROL (pause/halt/nudge flags) -> v1 READ-THROUGH only (visible in the
  settings view + manifest); their write paths keep existing semantics (barge-in latency and
  TTL behavior must not gain a cache layer). Reconciliation Q1.

## Migration order (strangler fig; each slice gated + pinned)

  M1 manifest + core/foundation/settings.py (get/resolve/cache, ~100 LoC) + guard G-a/G-b
     + the settings verb. No consumer migrated yet; rack diagram exists.
  M2 one consumer family end-to-end: the timeout/age family (promoter hours, proposed-stale
     days, REPLY_TIMEOUT default) -- proves the three layers + flip audit live.
  M3 control-key read-through (S3 visible in one view).
  M4 boot deviation line + docs (LEXICON entry: dial, manifest, flip).
  Later, opportunistic: new dials land ONLY via manifest (guard enforces); old constants
  migrate when their module is next touched -- never a big-bang sweep.

## Failure modes of this design (named, M-honesty)

  F1 manifest rot -> G-b catches the dead direction; owner-module rename caught by existing
     ref checks.
  F2 flip lag (read cache TTL) -> document per-dial; keep TTL small; control keys exempt (Q1).
  F3 silent degradation when Store is unreachable: fleet believes a flip is live, defaults
     actually govern -> boot line confesses "N flips NOT in effect (store unreachable)";
     never silent (RB-5 doctrine).
  F4 the flip verb becomes a code-review bypass for behavior change -> acl + required
     --reason + ledger visibility + graded-dial regrade rule; flips are LOUD by design.
  F5 dial-count inflation (everything becomes a flag) -> no count metric to Goodhart; the
     bar for ADDING a manifest entry is an owner + a reason; prefer deleting dials.
  F6 second config system creep (someone adds YAML later) -> guard G-a extended: environ.get
     outside the settings layer for AKASHIC_* also flags.

## Hook-layer note (lesson: mediation_membrane_is_the_hook_layer)

Enforcement lives in EXISTING mediation surfaces: the agent_cli verb (acl + manifest checks),
the ship gates (guard), recall-at-action (already fires near flips to surface graded_by).
No new daemon, no interception layer.

## Open questions for reconciliation

  Q1 control.pause/halt: read-through only (my lean) or full fold?
  Q2 scoping: fleet-wide keys v1 + `agent:<id>:` suffix convention, or scoped from day one?
  Q3 does MAX_TOKENS-class per-model tuning belong here or in the model card?
  Q4 graded-dial flips: WARN or BLOCK without a regrade receipt? (My lean: block; warn is
     how method rot starts.)
  Q5 name: `settings` / `dials` / `registry` -- LEXICON decision; "kernel" stays out of the
     public vocabulary (GPT agreed).
