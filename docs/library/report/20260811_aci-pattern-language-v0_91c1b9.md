---
akashic_id: art_20260811_aci-pattern-language-v0_91c1b9
akashic_sha: 5dbdb2f6bbe8
schema_version: 1
status: current
type: report
date: 2026-08-11
title: aci-pattern-language-v0
gist: "# The ACI Pattern Language v0 — MCP tools & skills as ergonomics evidence (T289 slice 1) **Charter (Daniil, verbatim, note `beat-priori-and-"
visibility: fleet
body_type: markdown
seats: []
category: [migration, memory, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-11T10:44:11"
updated: "2026-08-11T10:44:11"
---
<!-- GENERATED PROJECTION of art_20260811_aci-pattern-language-v0_91c1b9 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# aci-pattern-language-v0

# The ACI Pattern Language v0 — MCP tools & skills as ergonomics evidence (T289 slice 1)

**Charter (Daniil, verbatim, note `beat-priori-and-ergonomics-directive-2026-08-11`):**
"We can take inventory of all types of MCP tools and skills and classify them. then we can
analyze each for what they say about agentic ergonomics."

**Method, slice 1 (in-house census):** three surfaces enumerable WITH RECEIPTS today —
our own door (AST-counted), priorish (live-audited 2026-08-10), and this session's harness
surface (servers, tools, skills present in a working Claude Code session). Slice 2 = the
public-ecosystem sweep (registries, awesome-lists, vendor directories) per T276 shape.
**Null exhibit, recorded:** the session's own MCP-registry door returned empty for the ten
most common categories (memory/github/slack/database/browser…) — a registry that answers
empty is itself an ergonomics datum: discovery surfaces fail silent, and a caller cannot
distinguish "nothing exists" from "nothing visible to me" (the degraded-flag law, violated
at ecosystem scale).

---

## 1 · The census (what a working agent session actually holds)

| Surface | Count | Receipt |
|---|---|---|
| akashic-aurora MCP | **37 tools** | AST count over `ai_setup_mcp.py`, this session |
| priorish MCP | **7 tools** | live `tools/list`, 2026-08-10 audit |
| Claude Code built-ins | ~16 core tools | this session's tool roster |
| Browser pane server | 17 tools | session listing |
| claude-in-chrome | 22 tools | deferred listing |
| computer-use | 27 tools | deferred listing |
| ccd_session_mgmt + ccd_session + ccd_directory | 12 tools | deferred listing |
| visualize / mcp-registry / scheduled-tasks / terminal | 10 tools | deferred listing |
| **Session MCP+builtin total** | **~148 tools** | (~130 deferred until ToolSearch-loaded) |
| **Skills** | **26** | this session's skills listing |

## 2 · Classification (the axes that carried information)

- **Function class:** read (sense) · write (durable) · act-on-world (browser/computer/send)
  · meta (ToolSearch, spawn_task, request_access — tools about tooling).
- **Granularity — the three-rung ladder:** atomic verb → **batch composite** → skill
  (workflow document). The ecosystem invented batching independently at least three times
  in one session (`browser_batch`, `computer_batch`, `teach_batch`): round-trip cost is a
  universal pressure, and the answer converges.
- **Coaching depth:** bare schema → description-as-prompt (every skill trigger is an
  elaborate WHEN-clause; the harness skill list is a coaching corpus) → handshake
  instructions (priorish's "go STRAIGHT to series_by_key"; our server instructions) →
  full skill document loaded on demand.
- **Addressing:** stable ids (event addresses, atom ids, priorish uuids) · paths ·
  refs-from-prior-reads (browser `ref_N` — addresses MINTED BY READING) · natural language
  (find/search inputs).
- **Safety posture:** graduated capability tiers (computer-use read/click/full BY APP
  CATEGORY), approval gates, access-request verbs — permissions as a first-class UX, not
  an error path.
- **Surface management:** eager (small doors) vs **deferred-with-ToolSearch** (130+ tools
  lazy-loaded here) — the second answer to bloat besides curation.

## 3 · The principles (each with its exhibit — nothing without a receipt)

1. **Two answers to surface bloat, and they compose:** curate the door (priorish: 7) OR
   defer-and-search (this harness: ~130 lazy). Our 37-tool door does neither yet — T289's
   first adopt/adapt verdict feeds the door-curation debt (parity manifest's `gap` class).
2. **Batching is convergent evolution.** Three independent batch tools in one session.
   Principle: any door whose verbs are called in sequences owes a batch composite. (Our
   ask door's `--prompts-file` is this; the eye door will owe one.)
3. **Coaching lives at four depths, and the deepest is a document.** Skills are
   descriptions-as-prompts grown into files loaded on demand — the same shape as our
   boot/handshake coaching. Principle: coach at the shallowest depth that changes caller
   behavior; reserve documents for workflows.
4. **Refs minted by reading** (browser `ref_N` from `read_page`) are the strongest
   addressing pattern in the session: the READ step yields the handles the ACT step needs,
   so hallucinated targets are structurally impossible. Our eye does this (find → event_id
   → get); T288 chips are this pattern as citation.
5. **Graduated capability beats binary permission.** computer-use's per-app-category tiers
   (read/click/full) let the same tool surface serve untrusted and trusted contexts.
   Principle for our ACL: tiers per capability class, not per agent alone (L4's dimmer,
   independently converged).
6. **Meta-tools are load-bearing** — ToolSearch, request_access, spawn_task: the session's
   most ergonomic moves were tools-about-tooling. A door above a size threshold owes a
   discovery verb (our `/relation-types` analog at the tool plane).
7. **Sub-agent spawning is the context-boundary pattern productized** (spawn_task chips,
   Agent tool): fresh context + a self-contained prompt = the fan doctrine's partition
   geometry, shipped as UX.
8. **Discovery must fail loud** (the null-registry exhibit): an empty answer from a
   discovery surface without a `degraded` signal is indistinguishable from absence — the
   grammar's silent-empty law, violated at ecosystem scale, and the strongest argument
   that our envelope contract generalizes beyond our own doors.

## 4 · Adopt / adapt verdicts for OUR doors (first pass)

- **ADOPT batching at the eye door** (find+get in one call — chips harvesting did N round
  trips that one batch verb collapses).
- **ADOPT a discovery verb on the akashic door** (37 tools, no `tools-about` surface;
  Gemini's walk succeeded on instructions alone — a discovery verb makes that robust).
- **ADAPT the deferred-loading pattern** for the MCP curation debt: an agent-tier
  essential-verbs subset (priorish-style) + the full surface behind a search verb
  (harness-style) — both answers, composed.
- **KEEP skills-as-documents** for workflow coaching (the T275 report verb is already
  this pattern internally).

## 5 · Slice 2 (queued): the public-ecosystem sweep

Web sweep of the real registries (official MCP registry, awesome-mcp-servers lists, vendor
directories), classify by the §2 axes at scale, verify every named server against a live
listing (census-claims-vs-listings law), and fold the results into pattern-language v1 with
Heimdall's fence. The in-house v0 above supplies the axes; the ecosystem supplies the
distribution.
