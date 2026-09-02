---
akashic_id: art_20260901_installer-manifest-v0_a9dbfe
akashic_sha: 23ff03946b95
schema_version: 1
status: current
type: contract
arc: estate-program
date: 2026-09-01
title: installer-manifest-v0
gist: "The one options tree all installer skins render: identity+epochs (prior-operator ask, registry writes), fleet, substrate, seed-by-tag with honesty stamps, integrations, doctrine incl. tag registry + telemetry"
visibility: fleet
body_type: json
seats: [claude]
category: [ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-01T22:08:56"
updated: "2026-09-01T22:08:56"
---
<!-- GENERATED PROJECTION of art_20260901_installer-manifest-v0_a9dbfe -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# installer-manifest-v0

{
  "manifest_version": "0.1.0",
  "_meta": {
    "law": "One manifest, many skins. The CLI wizard, the local-web setup, and the single-exe all render THIS tree; options never fork from their UI. Every node has a default so the ENTER-ENTER-ENTER path yields a working house; asks appear only when a chosen branch needs them.",
    "cites": [
      "art_20260901_operator-epochs-attribution-as-resolved_a3e0c7",
      "art_20260901_the-estate-program-fourteen-arcs_c432a7",
      "art_20260901_estate-program-fence-round-one-reconcili_a8a750"
    ],
    "renders": ["cli-wizard", "local-web", "single-exe"],
    "status": "position -- the fleet fences it, the operator gates it",
    "seed_source": "research/in-flight/seed-sanitize-2026-09-01/sanitized-seed.jsonl (1228 records, sanitize receipts in pipeline-summary.json)"
  },
  "laws": {
    "identity": "Display names are a layer over immutable stable ids (agent_id, operator id slug). Renames edit a registry row and re-render everything; no record is ever rewritten for attribution.",
    "epochs": "Operator attribution resolves by (origin, timestamp) through operator:epochs. origin=seed resolves to epoch 0 UNCONDITIONALLY -- clock ambiguity cannot misattribute inherited history. Records born in this house resolve to the current epoch.",
    "tags": "Tags are lenses, not filing locations: a governed roster (minted, aliased, never free-typed), provenance class on every application (authored|auto|curator -- auto never launders into authored), and a hit-vs-help split in telemetry (coverage and quality move as separate numbers).",
    "seed_honesty": "Inherited lessons never masquerade as lived experience: origin=seed, credit counters zeroed (house tallies kept read-only in provenance), epoch:seed taggable, prior-operator attribution in prose."
  },
  "steps": [
    {
      "id": "identity",
      "title": "Identity",
      "teach": "Who runs this house, and what everyone gets called. Names here are display-layer: change any of them later with one registry edit.",
      "items": [
        {"id": "operator.name", "kind": "text", "label": "Your name", "default": null, "required": true,
         "effects": [{"op": "config", "key": "operator.display"},
                     {"op": "epoch_registry", "epoch": 1, "field": "display"}]},
        {"id": "operator.id", "kind": "text", "label": "Operator id (short slug)", "default": "derived from name, editable",
         "validate": "ascii, lowercase, unique vs seat ids and verbs",
         "effects": [{"op": "config", "key": "OPERATOR_ID"},
                     {"op": "epoch_registry", "epoch": 1, "field": "id"}]},
        {"id": "prior.display", "kind": "text", "label": "How should inherited lessons refer to this corpus's previous operator?",
         "default": "the prior operator",
         "teach": "The seed corpus arrives from an earlier house. Its history stays attributed to its own era -- under whatever name you choose (credit upstream by name if you like).",
         "effects": [{"op": "epoch_registry", "epoch": 0, "field": "display"},
                     {"op": "seed_import_param", "key": "prior_display"}]},
        {"id": "fleet.naming", "kind": "choice", "label": "Fleet naming", "default": "house-canon",
         "options": [
           {"id": "house-canon", "label": "House canon (Vandor, Heimdall, Navi, Sunshine, Rill)"},
           {"id": "name-each", "label": "Name each seat yourself",
            "reveals": [{"id": "fleet.names.<seat>", "kind": "text", "per": "enabled seat",
                         "validate": "ascii, unique, not a verb"}]},
           {"id": "plain-ids", "label": "Plain ids (claude, deepseek, kimi, sol)"}],
         "effects": [{"op": "callsign_registry", "note": "display layer only; stable agent_ids never change; rename ceremony exists"}]}
      ]
    },
    {
      "id": "fleet",
      "title": "Fleet composition",
      "teach": "Each provider key is asked only when its seat is chosen. Skipping a seat parks it; nothing breaks.",
      "items": [
        {"id": "fleet.mode", "kind": "choice", "default": "solo",
         "options": [
           {"id": "solo", "label": "Solo Claude (fewest asks)"},
           {"id": "full", "label": "Full fleet",
            "reveals": [{"id": "keys.deepseek", "kind": "secret", "ask_when": "seat deepseek enabled"},
                        {"id": "keys.kimi", "kind": "secret", "ask_when": "seat kimi enabled"},
                        {"id": "keys.gemini", "kind": "secret", "ask_when": "seat gemini lane enabled"}]},
           {"id": "custom", "label": "Custom pick", "reveals": [{"id": "fleet.seats", "kind": "multi", "per": "seat"}]}],
         "effects": [{"op": "config", "key": "fleet.seats"}, {"op": "park_skipped_seats"}]}
      ]
    },
    {
      "id": "substrate",
      "title": "Memory substrate",
      "teach": "Redis is an upgrade, not a prerequisite. The probe runs before we accept your answer.",
      "items": [
        {"id": "substrate.mode", "kind": "choice", "default": "file-store",
         "options": [
           {"id": "file-store", "label": "File store (zero dependencies)",
            "gate": "redis-down fallback suite green (currently RED in house baseline -- ships only after)"},
           {"id": "existing-redis", "label": "Existing Redis",
            "reveals": [{"id": "redis.host", "kind": "text", "default": "localhost"},
                        {"id": "redis.port", "kind": "text", "default": "6379"}],
            "validate": "live probe before accept"},
           {"id": "docker-redis", "label": "Docker Redis (compose up)", "ask_when": "docker detected"}],
         "effects": [{"op": "config", "key": "REDIS_*"}]}
      ]
    },
    {
      "id": "seed",
      "title": "Seed corpus",
      "teach": "1,228 sanitized lessons from the founding house. Full is the measured default: recall is an index, not a reading list -- size buys coverage, ranking prevents overwhelm. An empty corpus cost a peer fleet 314M tokens in one night.",
      "items": [
        {"id": "seed.mode", "kind": "choice", "default": "full",
         "options": [
           {"id": "full", "label": "Full sanitized set (default)"},
           {"id": "by-tag", "label": "Pick by tag tree",
            "reveals": [{"id": "seed.tags", "kind": "tag-tree", "source": "tag registry with live counts",
                         "teach": "The category tree IS the tag tree -- same registry the eye queries later."}]},
           {"id": "none", "label": "Empty house (you can import later)"}],
         "effects": [
           {"op": "seed_import", "params": ["prior_display", "OPERATOR_ID"],
            "transforms": "role forms -> chosen prior name; <operator-id> -> prior id form",
            "stamps": ["origin=seed", "seed_version", "epoch:seed tag"],
            "credits": "zeroed; house tallies kept read-only in seed_provenance"},
           {"op": "epoch_registry_write", "note": "epoch 0 until=install instant; epoch 1 from=install instant; offset-carrying stamps"}]},
        {"id": "seed.anti_patterns", "kind": "check", "label": "Include anti-patterns", "default": true,
         "teach": "Known-bad paths are half the value of a corpus."}
      ]
    },
    {
      "id": "integrations",
      "title": "Integrations",
      "teach": "All conditional, all skippable, all addable later.",
      "items": [
        {"id": "mcp.wiring", "kind": "check", "default": "detect", "label": "Claude Code MCP wiring (.mcp.json)"},
        {"id": "discord", "kind": "check", "default": false, "label": "Discord control surface",
         "reveals": [{"id": "discord.token", "kind": "secret"}, {"id": "discord.server", "kind": "text"}],
         "engine": "scripts/discord_setup.py"},
        {"id": "web.search", "kind": "choice", "default": "walled",
         "options": [{"id": "brave", "label": "Brave key", "reveals": [{"id": "keys.brave", "kind": "secret"}]},
                     {"id": "searxng", "label": "SearXNG url", "reveals": [{"id": "searxng.url", "kind": "text"}]},
                     {"id": "walled", "label": "Walled (no search)"}]},
        {"id": "dashboard.port", "kind": "text", "default": "8787"}
      ]
    },
    {
      "id": "doctrine",
      "title": "Doctrine packs",
      "teach": "The culture is granular: take the hooks, leave the stance, or both. Instrumentation defaults on and stays local.",
      "items": [
        {"id": "hooks.recall_at", "kind": "check", "default": true, "label": "Recall-at-action hooks"},
        {"id": "gates.doors", "kind": "check", "default": true, "label": "Door gates + secrets checker + guardrail baselines"},
        {"id": "tags.registry", "kind": "check", "default": true, "label": "Governed tag registry",
         "effects": [{"op": "tag_registry_seed",
                      "initial": ["category roster (governed, max 3 per record, auto-classify merge)",
                                  "epoch:seed | epoch:native",
                                  "provenance: authored | auto | curator"]}]},
        {"id": "tags.telemetry", "kind": "check", "default": true, "label": "Tag-hit telemetry (local only)",
         "teach": "Every recall firing logs which tags fired (coverage) and which flipped an outcome (quality) -- separate numbers by house law. Your triggering parameters tune against YOUR telemetry from day one.",
         "effects": [{"op": "funnel_tag_stamping"}]},
        {"id": "docs.conduct", "kind": "check", "default": true, "label": "Conduct stance + drill doctrine docs"}
      ]
    }
  ]
}
