# deepseek-taxonomy-ergonomics-2026-07-23  (id ADR_0723202250_ad0777a7, 2026-07-23T20:22:50.908981)
# HOMES-AND-ORDER THINK PASS — deepseek (builder, doc-new + gen_library owner) — 2026-07-23

Response to research/briefs/taxonomy-ergonomics-think-pass-2026-07-23.md
Base: docs/artifact-substrate-design-2026-07.md (T101, G1-G3 approved) + docs/super-wiki-experience-design-2026-07.md (T103, G4-G6 approved)
Evidence: docs/SHELVES.md (17 types, 140+ files), docs/LIBRARY.md (header contract + zone canon), agent_cli.py:1490-1560 (doc-new current impl), scripts/arc_thread.py (arc extraction), research/briefs/*.md heading scan

---

## A. THE TAXONOMY — 24 governed categories covering our real corpus

Evidence: scanned ~200 headings across research/briefs, research/drafts, docs/, chronicles/. Clustered by what artifacts are actually ABOUT, not what folder they're in.

Three planes per the brief:
- TYPE (what KIND of artifact, from LIBRARY canon): ~14 canonical, settled
- ARC (which campaign): ~15 active arcs in the header corpus
- CATEGORY (what it's ABOUT — THIS is the new governed roster)

### Proposed category roster (24, evidence-cited)

| # | Category | What it covers | Evidence (sample) |
|---|----------|----------------|-------------------|
| 1 | **bus** | lanes, routing, packet-spec, dedup, at-least-once delivery | T039-T045-T047, packet-routing-design, T043-build-plan |
| 2 | **coordination** | advisory locks, control plane, pause/resume, namespace isolation | control-plane-ns-isolation, coordination-plan-synthesis |
| 3 | **agent-lifecycle** | daemons, wake/sleep, runner lock, hooks, seat health | P1-daemon-lifecycle, T086 seat/wake/hook, liveness-tier |
| 4 | **memory** | recall engine, knowledge_map, boot, learning-store, agent_memory | T094 recall-heuristics, knowledge_full/knowledge_recall |
| 5 | **knowledge-stack** | notes, lessons, decisions, snapshot, supersession mechanics | note verb, learning_store, snapshot_knowledge |
| 6 | **library** | filing, taxonomy, zones, naming canons, home rules, SHELVES | LIBRARY.md, library-schema-reconciliation, gen_library |
| 7 | **substrate** | artifact atoms, projection, JSONL, store, migration, citations | T101 artifact-substrate, deepseek/kimi halves, advisory scan |
| 8 | **search** | Fuse.js integration, /library/search, facets, Gmail grammar, indexes | super-wiki brainstorm, T103 experience design |
| 9 | **ui** | bifrost_ui, :8787 console, glass/card/iso renders, viz, SSE | deepseek-UI-now-card, ui-plan-*, T002 collapsible cards |
| 10 | **optics** | portfolio face, public GitHub, README, crown docs, JOURNEY | Daniel directive, "professional repo face" |
| 11 | **security** | operator traffic, authorization, grants, trust chain, admin scope | remote-steering, security-schema, R001 deepseek-trust |
| 12 | **secrets** | credential scanning, .env, API key handling | security-schema-proposal, secrets-at-door |
| 13 | **tooling** | self-tooling, verb registry, fence, mint, sugar, kit.py | T099 v0 toolbelt, fence-v0-t099, ask-peer macro |
| 14 | **ergonomics** | agent DX, tool budgets, boot primer, method-baseline, kill drills | method-baseline-2026-07, night-friction-program |
| 15 | **mcp** | MCP door, concurrency, tool bridges, stdin/jsonrpc transport | mcp-concurrency-*, MCP-leverage-map, ai_setup_mcp.py |
| 16 | **conducting** | leadership doctrine, interview protocol, Daniel's directives, delegate | continuity-of-mode, conducting-interview, CONDUCT.md |
| 17 | **voice** | tone, quiet/casino guard, Goodhart, design language, typography | VOICE.md, T034 Goodhart-1, super-wiki keynote discipline |
| 18 | **testing** | probes, pins, mojibake guard, comprehensibility, contract checks | check_comprehensibility, mojibake_signatures, test suite |
| 19 | **bench** | performance, latency, throughput, cold-open, graph perf numbers | Obsidian perf forum numbers, bifrost cold-open targets |
| 20 | **fleet** | multi-agent collaboration, message bus, handoff, barge-in, steer | live bus, bifrost_send, handoff semantics, T026 ack |
| 21 | **research** | prior-art sweeps, web search, outside voices, bakeoff, Gemini | gemini-T086-prior-art, advisory-scan, bakeoff corpus |
| 22 | **design** | design rounds, blind halves, reconciliation, counters, fence | (high-overlap with TYPE:design but distinct — a brief can ALSO be about design methodology) |
| 23 | **migration** | file→atom migration, supersession sweep, P0-P3 phases, verification | T101 migration phases, kimi 184-file census, retro-enrichment |
| 24 | **story** | chronicles, session reflections, night plans, JOURNEY, narrative | session-reflection-*, night-plan-*, JOURNEY.md |

### Caps + governance

- Capped at 24. Adding one requires: (a) a brief proposing it, (b) ≥3 existing artifacts that would be BETTER categorized with the new category than any existing one, (c) Daniel gate. The "propose a category" door is `doc new --propose-category <name>` which mints a brief-atom with status:draft — the lint gate fires on it.
- Deletion ritual (T034 law): before removing a category, every atom carrying it must be re-categorized. The audit library domain flags orphaned categories (in use but not in the taxonomy atom).
- NO free-text tags. Category-sprawl is the .md sprawl one facet over (kimi's Goodhart warning, adopted).

---

## B. THE HOME RULE — one canonical shelf, N lenses

### Home function

```
home(atom) = primary_shelf(atom.type, atom.categories[0])
```

The TYPE determines the top-level shelf. The FIRST category determines the subsection. Status determines visual treatment (current = full weight, superseded = dimmed, fossil = archived texture, draft = dashed).

### Shelf layout (what Daniel sees browsing cold)

```
LIBRARY (root)
├── CONTRACTS           (type: contract)
│   ├── bus             (category: bus)
│   ├── coordination
│   ├── security
│   ├── voice
│   └── ...
├── DESIGNS             (type: design)
│   ├── bus
│   ├── agent-lifecycle
│   ├── library
│   ├── substrate
│   └── ...
├── REPORTS             (type: report)
│   ├── mcp
│   ├── security
│   └── ...
├── BRIEFS              (type: brief)
│   ├── fleet
│   ├── tooling
│   └── ...
├── CHRONICLES          (type: chronicle)
│   └── story
├── RULINGS             (type: ruling)
│   └── security
├── LEDGERS             (type: ledger)
│   └── fleet
└── MAPS                (type: map — generated)
```

**Why type-first, category-second:** TYPE is a small closed set (~14) that agents already know. The first question a browser asks is "what KIND of thing is this?" — a contract, a design, a report. CATEGORY narrows within that. ARC is a separate lens (the Arc view), not the shelf.

**Order within a shelf:** `status` desc (current → draft → superseded → fossil), then `date` desc. The living stuff is always at the top.

### The lenses

The same atom appears in N lenses but has exactly ONE canonical home:
- **Arc lens:** every atom with `arc: X` appears in Arc view, ordered by date
- **Category lens:** atoms with `category: [Y]` appear under that category cross-type
- **Temporal lens:** date-ordered, no subdivision
- **Graph/rel lens:** citations_out[] → navigation surface, not a shelf

The home rule is: shelf position = f(type, category[0]). It is idempotent and deterministic. An atom with no category → shelf is type-only (top-level under that type, flagged by library lint).

---

## C. DOOR ERGONOMICS — cheaper than Write-a-file, felt not claimed

### The ideal `doc new` moment

Agent finishes a piece of analysis in a session. Wants to file it. Today: `doc new --type design --title "my-counter" --arc "substrate" --seats "deepseek"`. The agent must KNOW type, arc, seats, and a good title — five decisions, zero help.

**Proposed:** auto-inference does 3 of 5; the agent provides 1 (title), confirms 1 (the inferred type/arc/categories).

```
py agent_cli.py doc new --title "mcp-concurrency-counter"
```

That's it. The door infers:

1. **TYPE from invocation context.** If the agent is in a session whose current ledger task is T101 (artifact-substrate, type=design), the door infers `--type design`. Other inference rules: if the --body-file's first 200 chars match a brief template → `--type brief`. If the session's recent bifrost handoffs were `kind:counter` → `--type design`. Fallback: `--type draft` (no inference possible — the agent specifies, or it lands in draft).

2. **ARC from the seat's current ledger task.** The T101 task ledger entry carries `arc: library-schema / artifact-substrate`. The door reads the active claim for this seat and infers `--arc library-schema`. Zero guesswork — the task ledger IS the arc authority. If the seat has no active claim, the arc is omitted (not guessed).

3. **CATEGORY from title keywords.** A tiny classifier (~15 lines, no ML): 
   - title matches `bus|packet|routing|lane|dedup|stream` → `[bus]`
   - title matches `ui|console|card|render|viz|pane` → `[ui]`
   - title matches `security|grant|auth|trust|admin` → `[security]`
   - title matches `fence|audit|lint|check|guard|mojibake` → `[testing]`
   - title matches `recall|memory|boot|knowledge|learn` → `[memory]`
   - title matches `mcp|concurrency|tool.*bridge` → `[mcp]`
   - title matches `substrate|atom|projection|jsonl|migrat` → `[substrate]`
   - title matches `library|shelf|taxonomy|home|filing` → `[library]`
   - title matches `conduct|directive|gate|charter.*seat` → `[conducting]`
   - title matches `voice|goodhart|tone|casino` → `[voice]`
   - title matches `story|chronicle|session|reflection|night` → `[story]`
   - title matches `fleet|handoff|barge|steer|bifrost` → `[fleet]`
   - DEFAULT: `[]` (no inference — deferred to `--draft` or the ONE question)

4. **REL EDGES from recent file reads.** If the agent read `docs/artifact-substrate-design-2026-07.md` in this session (known via the ToolBox's file-read log), the door suggests: `cites: [art_<date>_artifact-substrate-design_<hash6>]` with `rel: supports` or `rel: derives-from`. This is SUGGESTED, not auto-applied — it appears in the confirmation prompt.

### The ONE question

The door prints what it inferred and asks exactly ONE confirmation:

```
[doc] inferred from context:
  type: design   (from T101 ledger claim)
  arc:  library-schema   (from T101 ledger claim)
  categories: [substrate, mcp]   (from title keywords)
  cite: art_20260723_artifact-substrate-design_a1b2c3  as derives-from
         (from session reads)
  seats: deepseek

Proceed? [Y/n/edit] 
```

If the agent types `n`, the atom is born as `status: draft` — the agent can refine later. If `edit`, the agent provides overrides. This is the entire interaction. One prompt, one response. Faster than `Write(file, content)` because the content rides `--body-file` (already written during the analysis); the door handles metadata.

### What happens when inference is WRONG

The atom is born with wrong metadata. The library lint catches: category that doesn't match content (via the audit library domain), arc mismatch (atom's arc vs the arc thread it cites), type mismatch (a "report" body that reads as a design). These are POST-HOC corrections, not write-time blocks — same posture as the existing wrap census. The agent can fix at any time with `doc edit <id> --category X --arc Y`. The cost of a wrong inference is cheaper than the cost of typing five flags.

### The --draft escape hatch

`--draft` skips ALL inference and ALL questions. The atom is born with `status: draft`, no categories, no arc, no citations. The library lint sweeps it later. This is the "I just need to dump this and go" path — strictly cheaper than `touch file.md`.

---

## D. THE CONVERSATION DOOR — bus thread → atom with edge

### What exists

The `capture` verb (agent_cli.py:4244) already captures events to the event log. But there's no "turn this bus thread into a document" path. The gap: Daniel said "I want our conversations about things to be useful" — today, a handoff thread is ephemeral; the ideas scatter.

### The cheapest path

```
py agent_cli.py capture --thread <bus-thread-id> --as-doc --title "X" --cites <art_id>
```

This:
1. Reads the bus thread (all messages with `reply_id` or `thread_id` matching)
2. Extracts the text bodies, preserving attribution (deepseek: "...", claude: "...")
3. Mints an atom with:
   - type: `design` (or `--type` override)
   - body: the thread's text, formatted as an attributed transcript
   - `citations_out: [{target: <art_id>, rel: discusses}]`
   - `category: [conversation]` (or inferred from title)
   - status: `draft` (the agent refines after)
4. Output: `[capture] atom art_<id> minted from thread <thread-id> — cites <art_id>`

### The habit surface

The agent MUST be able to do this mid-conversation. The pattern: "I just discussed X with claude in a bifrost thread; I want that discussion filed as an artifact that cites the design doc we discussed." The command is ONE line — it must be cheaper than copy-pasting the thread into a file.

For ToolBox agents (the fleet): a new `bifrost_capture` door:
```
bifrost_capture(thread_id="...", title="X", cites="art_<id>")
```
This calls the same `capture --as-doc` path. The agent invokes it from its tool bag; no CLI needed.

### What makes it SUPER (Daniel's word)

The thread → atom path creates CITATION EDGES. After capturing three threads that all discuss `art_<substrate-design>`, the graph shows: "this design was discussed in 3 conversations." The backlinks panel on the design's reading page lists those threads. The conversations GAIN usefulness — they're not just chat history; they're evidence of deliberation, connected to the artifact they shaped.

---

## E. RETRO-ENRICHMENT — the ~890 files GET their categories + rel edges

### Phase R0: auto-classify (run ONCE, verified by Daniel spot-check)

Pipeline (`py scripts/enrich_corpus.py --dry-run`):

1. **TYPE:** already present in ~80% of files via header parsing (gen_library's `_extract()`). The remaining ~20% (~178 files) are `unmarked` or `untyped` — they need manual classification OR kimi's 184-file census verdicts as seed.

2. **CATEGORY:** the same keyword classifier as the door inference (§C.3), applied to `title + heading + first 500 chars of body`.

3. **ARC:** already present in ~60% of files via header `Arc:` field. The remaining ~40% get: (a) arc_thread.py reconstruction from commit messages mentioning the file, (b) title-keyword matching (files with "remote-steering" in title → arc: security-schema).

4. **CITATIONS_OUT:** backfill from grep-able path references. Every `docs/foo.md` or `research/bar/baz.md` in the body text → candidate citation. The migration table (old-path → new-ID) resolves these to `art_<id>`. REL TYPE defaults to `discusses` (the weakest claim — honest about uncertainty).

### Real numbers

| Signal | Recoverable from | Coverage estimate | Error rate |
|--------|------------------|-------------------|------------|
| TYPE | Header `Type:` field | ~80% | ~2% (mis-typed in header) |
| ARC | Header `Arc:` field + title keywords + commits | ~85% | ~5% (arc naming drift over 4 weeks) |
| CATEGORY | Title/heading keyword classifier | ~75% | ~10% (false positives on generic titles) |
| CITATIONS | grep path references | ~40% of files cite another (avg 1.2 citations); ~90% of those are path-resolvable | ~5% (typos in paths, stale paths) |

**What the classifier CANNOT recover:** ~15-20% of files will land with no category (unclassifiable by keyword). These get `category: []` and the library lint flags them. Daniel spot-checks 20 random unclassified files from the dry-run report — if they're actually classifiable, the classifier rules get sharper.

### What makes the OLD corpus MORE useful after migration

Query you could NOT answer yesterday but CAN after enrichment:

> "Show me every design that discussed packet routing AND was superseded by a later design in the security-schema arc, ordered by the number of conversations that cite it."

Yesterday: grep `packet.*routing` over filenames, read each file manually for supersession hints, guess which arc it belongs to. Today (after enrichment): `/library/search?q=packet+routing&type=design&arc=security-schema&status=superseded` → sorted by `citations_in` count. Two seconds.

---

## F. SELF-ATTACK + TOP-3

### 1. The keyword classifier WILL mis-categorize — harm assessment

A design about "bus security" gets category `[bus]` but not `[security]`. The keyword classifier picks the FIRST match (bus before security in the rule list), not the BEST. **Mitigation:** the classifier returns ALL matching categories (up to 3), sorted by match confidence (exact word match > substring match). "Bus security" → `[bus, security]`. The ONE question shows the agent all matches; the agent confirms or edits.

### 2. Auto-inferred arc from ledger task is WRONG for cross-arc documents

An agent working on T101 (library-schema arc) files a document about UI design — the door infers `arc: library-schema` but the document is actually in the `interface/optics` arc. **Mitigation:** the ONE question shows the inferred arc, and the agent hits `edit` to override. The cost of the override (typing `--arc interface/optics`) is the same as today — we only save work when the inference is CORRECT. The door is never WORSE than today.

### 3. The capture --as-doc path needs bus message bodies to be retrievable

Today bus messages are ephemeral — the work lane consumes them, they're gone. The capture verb needs a `--thread` resolver that can read CONSUMED messages. **Mitigation:** the dual-write (T039a/T044) means every message exists on both legacy and work lanes. The legacy stream IS the archive. `capture --thread` reads from the legacy stream (not consumed). If the legacy TTL has expired, the capture fails LOUD: `[capture] thread <id> expired — cannot reconstruct`. Acceptable for v1; the archive window is the TTL.

### 4. The home rule produces a deep tree that's tedious to browse

TYPE (14) × CATEGORY (24) = 336 possible shelf positions for ~890 files → most shelves have 1-3 items. That's sparse and tedious to click through. **Mitigation:** the Library pane has a FLAT search as the primary surface — the tree is the "I don't know what I'm looking for" fallback. And the tree collapses empty shelves. The Obsidian folder view does this natively with the projection folder.

### 5. 24 categories is too many for agents to remember

Agents won't memorize 24 categories. They'll type the title and trust inference. If inference gets it wrong (20% error rate), ~178 files land with wrong categories — and the library lint's post-hoc correction creates a backlog. **Mitigation:** the ONE question shows the inferred categories EVERY time. The agent sees them and fixes wrong ones before birth. Over 50-100 births, the agent learns the categories that matter for their lane (a deepseek agent learns `[bus, ui, library, substrate]` — not all 24).

---

## TOP-3 RANKED

1. **Ship the ONE-QUESTION `doc new` with keyword inference + ledger-task arc auto-read.** This is the ergonomics kill-shot. Cost: ~40 lines in agent_cli.py (inference rules + prompt) + ~15 lines keyword classifier. The ledger-task arc reader is a one-liner: `task_ledger.current_claim(seat).arc`.

2. **Ship the 24-category roster as the taxonomy atom + the keyword classifier as the enrichment pipeline.** The roster governs; the classifier seeds. Post-migration, the library lint sweeps stragglers. Cost: ~30 lines for the enrichment pipeline + ~10 lines for the taxonomy atom.

3. **Defer the capture --as-doc thread resolver to v1.5 (after P0-P1 migration).** The conversation door is the right shape but needs the legacy-stream archive window verified. Ship the ONE-QUESTION doc-new first; the capture path adds citation edges when the graph is populated. Cost estimate: ~50 lines, low risk.

### What ships tonight (A1 constants)

```
CATEGORY_ROSTER = [
    "bus", "coordination", "agent-lifecycle", "memory", "knowledge-stack",
    "library", "substrate", "search", "ui", "optics",
    "security", "secrets", "tooling", "ergonomics", "mcp",
    "conducting", "voice", "testing", "bench", "fleet",
    "research", "design", "migration", "story"
]

HOME_RULE = lambda atom: f"{atom.type}/{atom.categories[0] if atom.categories else '_uncategorized'}"

AUTO_ARC = lambda seat: task_ledger.current_claim(seat).arc if task_ledger.current_claim(seat) else None
```

— deepseek (builder seat; doc-new + gen_library owner)

