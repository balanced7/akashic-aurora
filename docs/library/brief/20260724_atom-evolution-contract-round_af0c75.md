---
akashic_id: art_20260724_atom-evolution-contract-round_af0c75
akashic_sha: 58a82de3fe40
schema_version: 1
status: current
type: brief
arc: atom-evolution
date: 2026-07-24
title: atom-evolution-contract-round
gist: "Daniel: iterate atom revisions without breaking things, packet-spec style. 3-voice round -> the atom evolution contract; archival-not-wire framing"
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, governance, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_atom-design-reconciled-v1-1_fd2275
    rel: discusses
created: "2026-07-24T08:05:07"
updated: "2026-07-24T08:05:07"
---
<!-- GENERATED PROJECTION of art_20260724_atom-evolution-contract-round_af0c75 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-evolution-contract-round

DANIEL'S ASK (verbatim, 2026-07-24 morning): "Are we able to design future atom revisions and enhancements without breaking things like we can with the packet spec? I want us to build our system in such a way that we can iterate and design improvements without bringing the whole house down, can you three think on this?"

INTENT: an EVOLVABILITY CONTRACT for the atom substrate -- the ratified rules by which future schema revisions land without breaking any reader, the way Packet Spec v1 (T040/T043) made bus evolution safe (versioned envelope, unknown-keys preserved, consumers downgrade-never-drop, dual-version migration rule, capped rosters w/ deletion rituals).

GROUND (read first):
- What v1.1 already built (tonight): schema_version on every atom, absent reads as 1, readers REFUSE-LOUD on newer-than-known (fail-closed); read-time folds as the deprecation mechanism (cites->discusses, tenant demotion, category folds); segments[] pre-named as schema-v2 at the pane trigger with a migrate_schema door named but NOT built.
- The packet precedent: docs/library/design/20260701_packet-spec-v1-reconciled-build-spec-dua_a50b94.md (v, unknown-key preservation at T043, v1->v2 dual-version rule).
- THE HONEST DIFFERENCE to reason from: packets are EPHEMERAL (TTL'd streams; version skew is transient) -- atoms are FOREVER (append-only JSONL replayed at every rebuild; every shape ever minted must stay readable for the life of the project). Atom evolvability is an ARCHIVAL-format problem (Avro/Protobuf/Parquet class), not a wire-format problem. Respect the difference; steal what transfers.

AXES (explore all; add your own):
1. THE COMPATIBILITY LAWS: which rules are LAW? Candidates: additive-optional-fields never bump the version (semantic changes only); unknown-key round-trip preservation (a v1 writer flipping status on a v2 atom must not strip v2 fields); refuse-loud beyond known (built); replay-totality (rebuild handles every historical shape forever via pure per-version upgrade shims chained at read -- history is never rewritten).
2. THE CONSUMER BLAST-RADIUS REGISTRY: name every atom reader (family, projection renderer, gen_library census+verify, recall ingest, A2 audit, export, the future pane, MCP doors) and the version-bump checklist each must tick -- T104's per-move blast radius, applied to schema moves.
3. THE MIGRATE DOOR: what does migrate_schema actually do (pure transforms, append version-events never edit lines, projections regenerate, --verify green between stages, rollback story)?
4. THE DRILL: how do we PROVE safety before any v2 lands -- a fixture v-next atom run against every consumer, refuse-loud verified where unshimmed (the fire-verification law applied to schema)?
5. WHAT DOES NOT TRANSFER from the packet spec -- name the false friend (e.g. dual-WRITE has no atom analog; what replaces it?).

DELIVERABLE: independent position (no cross-coordination), TOP-5 ranked laws/mechanisms w/ costs + a kill-list of over-engineering, filed AS AN ATOM through the door (doc new --type design --arc atom-evolution, cite this brief atom) + reply on bus citing your atom id. QUEUE: after your T106 fence counter -- fence first, this second.

FLOW: independent positions -> claude reconciles -> the ATOM EVOLUTION CONTRACT lands as a contract-type atom at Daniel's gate. Calibrated questions: deepseek -- which law would the IMPORTER you built tonight have most wanted six months from now? kimi -- which consumer breaks FIRST under an unshimmed v2, and what drill catches it before it ships?
