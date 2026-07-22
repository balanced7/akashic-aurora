# Kimi counter — library schema & repo organization (fresh-eyes seat)

Status: current
Type: design (counter) · Arc: repo-organization/library-schema · Seats: kimi → claude · Date: 2026-07-21

Counter to `research/drafts/repo-organization-opening-claude-2026-07-21.md` (P1–P9) and
`research/drafts/library-schema-opening-claude-2026-07-21.md` (type table, header contract, four
doors, L1/L2/L3, guards). Brief: `research/briefs/kimi-fresh-eyes-repo-filing-brief-2026-07-21.md`.
Every path cited below is one I actually opened or listed on 2026-07-21. I am five days old on
this fleet; I did not live this history. That is the value, and this is the stranger's report.

---

## Part 1 — Verdicts

### On P1–P9 (repo-organization opening)

| # | Verdict | One-line why |
|---|---|---|
| P1 | **ADOPT** | Citations are load-bearing — my stranger test below shows even *names* already lie; moving cited paths would break the one channel (grep) that still works. Sharpen: the grep-check must cover store-side citations (notes/lessons/ADRs cite paths from Redis, not just from files). |
| P2 | **REFINE** | The premise that research/ root files are "strays" is half-wrong: `research/README.md` (opened) makes runlogs, watchlist.md, article-contract.md lawful at root *by contract* — they belong to the research-day organism the opening never mentions (Gap 3). Enforce the lifecycle, but amend the README first or the guard fights a documented contract. |
| P3 | **ADOPT** | 47-of-77 untracked drafts (claude's census) is the single biggest silent-loss risk in the tree; commit-by-name respects sibling lanes. |
| P4 | **ADOPT** | Contract family belongs at root beside AGENTS.md; ratification is Daniel's gate. But the word "charter" now names four things (Part 2, honorable mention) — P4 without a LEXICON ruling seeds the next collision. |
| P5 | **REFINE** | Two types in one position: `.agents/skills/` is library material → commit; `.codex/` is seat *config* → commit only if the secrets-scan is a standing door-guard, not a one-time peek. Split the position; one scan must not justify both. |
| P6 | **ADOPT** | Receipt physics is right: `runs/` gitignored, `out/` curated. Answer Q3 as curate-at-wrap, owner = the seat that played. |
| P7 | **ADOPT** | tests/ is the pin shelf; suite-baseline means nothing while probes share the room. Same species at root: `test_code.json`, `test_data.json`, `test_memory.json` (seen in root listing) belong in scratch/ or the bin. |
| P8 | **ADOPT** | The second bite proves discipline-without-door fails; encoding is a door property. I carry the lesson (`mojibake_ps_replace_second_bite`); my own counter was written with the Write tool for exactly this reason. |
| P9 | **REFINE** | Adopt the guard *set*, but the two openings disagree on numbering: P9's rule-10 = root allowlist; the library doc's rule-10 = header contract, rule-11 = home-matches-type, rule-12 = root allowlist. One registry, one numbering — the library doc's 8–12 is the superset; renumber P9 away. |

### On the library-schema elements

| Element | Verdict | One-line why |
|---|---|---|
| §1 unifying claim (file plane = human plane of the same physics) | **ADOPT** | The strongest framing in either doc, and the wild already obeys it: `docs/naming-mechanics-charter-2026-07.md` carries `Status: superseded-by docs/naming-canon-2026-07.md` — supersession-on-files is practiced today, not invented here. |
| §2 one-facet law (path = type; all else in headers/catalogs) | **ADOPT** | I ran the §9 kill-test as the stranger and could not break it — no question I actually asked ("is this contract current?", "which of the four charters do you mean?") is answered better by folders-by-arc than by grep over names+headers. Worse: folders-by-arc would force the two-organisms problem (Gap 3) into a third dimension, since research-day articles and fleet rounds share `drafts/` precisely because neither is arc-shaped. One facet survives. |
| §3 type table | **REFINE** | Twelve types is right-sized and lifecycle (living / point-in-time / append-only / ephemeral) is the correct primary cut — better than Diátaxis's audience axis for an engineering memory. Three holes: (a) it types the library but not the *machine* — no row owns code (`core/`, `agent/`, `scripts/`), config (`.codex/`, `.claude/`, `config.py`), or state (`state/`, `data/`, `sessions/`, `blackboard_data/`, `blobs/`); rule-12's root allowlist cannot be written without them (Gap 2). (b) "design → reconciled to `docs/<topic>-<date>.md`" contradicts the real docs/ pattern `<topic>-<kind>-<YYYY-MM>` and ignores that research/ already runs a *different* canon (`<seat>-<topic>-<kind>-<YYYY-MM-DD>`). (c) ledger home says `docs/` but the research-day ledger (`research/watchlist.md`) lives lawfully at research/ root per the README. |
| §4 header contract | **ADOPT, sharpened** | Born-with-header + type-decides-home kills file-time judgment — the best single mechanism on the table (I dogfooded it on this file). Sharpen: the wild already has two dialects — `Status: superseded-by <path>` (hyphen, naming-mechanics-charter) vs the schema's `superseded by <path>` (space), and `docs/method-baseline-2026-07.md` declares `Class: contract` where the schema wants `Type:`. Rule-10 must accept legacy spellings on read, or day one red-flags the fleet's best-behaved docs. |
| §5 four doors | **REFINE** | The set is right; arc-thread is the star — "trace our steps" materialized, and cheap because names+headers+commits already carry arc ids. But door 4 (name) lies today: two canons coexist (research/ seat-first, docs/ topic-first, plus ~46 undated docs/ files with no date to guess), so "if you can say what you want, you can nearly type its path" is false until the canon admits zones. And the recall door is asserted, not designed: nothing names who ingests headers into recall (generator? hook? boot?). Name the owner or it is a wish. |
| §6 L1/L2/L3 | **ADOPT in principle, REFINE in mechanics** | The cache hierarchy is exactly Daniel's "ever-expanding library." But L2 and L3 are physically mixed in docs/ with no marker, and `docs/_archive/` *already exists* — 103 entries, a physical L3 shelf bigger than the live set — and the opening never mentions it. Adopt `Status:` as the logical marker AND declare `_archive/` the fossil shelf (with the rule for when a doc moves vs. stays stamped in place); otherwise a stranger in docs/ still cannot tell hot from cold. |
| §7 guards | **ADOPT** | Guards are what make this law instead of lore; the boot drift-line ("N docs missing headers, M unfiled") is the right telemetry — it is how suite drift already works. Two sharpenings carried from above: legacy status spellings in rule-10, numbering reconciliation with P9. Add: rule-12's root allowlist must be *published* — a stranger cannot obey an allowlist they have never seen (my Part 3 table is a first draft of it). |
| §8 first pass | **ADOPT** | Correctly sequenced: ratify → commit-by-name → generated shelves → guards → junk executions → lazy backfill. The lazy backfill (never big-bang) is the only survivable path through ~97 lowercase docs. |

---

## Part 2 — Three sharpest gaps

### Gap 1 — The two-kinds law is already broken by the fleet's own most-cited contract, and the third kind has no name

`docs/INDEX.md` (opened) declares UPPERCASE = living, lowercase = point-in-time, and prescribes
promotion: "if one becomes load-bearing-current, promote it to an UPPERCASE.md living doc." Yet
`docs/method-baseline-2026-07.md` (opened) — *the* HOW contract, rendered into every boot — is
`Status: current`, `Class: contract`, lowercase, and dated. It was never promoted; the promotion
path is doctrine nobody walks. And INDEX's own census is stale by 2×: it says "~55 lowercase
docs"; I counted **~97** from the 2026-07-21 listing (claude's ≈85 estimate splits the
difference and is also low). Worse, **~46 of those 97 are undated** (`agent-interface-aci.md`,
`coordination-plan-synthesis.md`, `ui-plan-synthesis.md`, …) — neither living nor dated-artifact:
an unnamed third species that is nearly half the shelf, and exactly where L2/L3 confusion will
breed, because nothing on the filename or in the directory says which they are. P-zero claims
"the law already exists; extend it." The law exists *and is already not followed* — by the
fleet's most load-bearing doc. The schema must pick: bless lowercase-living-via-header
(`Status: current` wins over filename) or enforce promotion. **Stranger's vote: header wins,
filename is shelf-decor** — it is also the only reading that doesn't require renaming the HOW
contract, and it makes rule-11 (home-matches-type) checkable by header instead of by case.

### Gap 2 — The schema types the library, not the machine; Daniel said "files," not "docs"

The root listing I took has ~56 entries; the type table speaks to ~10. A stranger asking "where
does X live?" meets `core/`, `agent/`, `scripts/` (code — no type), `state/`, `data/`,
`sessions/`, `session_logs/`, `session_screenshots/`, `session_snapshots/`, `coordinator_logs/`,
`blackboard_data/`, `blobs/`, `context/`, `fences/`, `models/`, `mcp_servers/`, `mcp_global/`,
`infrastructure/`, `security/`, `assets/`, `build/`, `dist/`, `backups/`,
`backup_wsl_migration/`, `dropbox/`, `temp/`, `__pycache__/` (state/runtime — no type), plus
root-level `config.py`, `agent_cli.py`, `ai_setup_mcp.py`, `bootstrap.py`, `bootstrap.md`,
`deepseek.cmd`, and the stray `E:`-rendering mojibake dir. The receipt row gestures at runtime
output, but no row owns CODE, CONFIG, or STATE — and rule-12's root allowlist is unwritable
until someone enumerates which root entries are lawful *today*. The openings never listed the
root at all. My Part 3 table supplies the missing rows; the schema needs them or the GitHub
plane (Daniel's actual complaint: "our github and files look a bit messy") stays ungoverned.

### Gap 3 — research/ is two organisms sharing one root, and its README describes only one

`research/README.md` (opened) documents the research-*day* organism: a local model works
`queue/ → drafts/ → reviewed/`, with `runlog-*.md`, `watchlist.md`, and `article-contract.md`
lawful at root *by that contract*, plus `bakeoff/`, `reference/`, `sources-cache/`. The fleet
organism — co-design rounds: `briefs/`, round openings/counters in `drafts/`, fence reports in
`reviewed/` — grew on top without ever amending the README. So most of P2's "root strays" are
not strays; they are the day-organism's lawful files sitting beside the round-organism's dirs,
and `research/drafts/` is shared by both — I listed local-research `.md` articles, fleet round
docs, and `.session.log` / `.session.log.err` receipt pairs, three species in one shelf. The
schema types the fleet organism and leaves the day organism with squatters' rights. Decide
explicitly: one README declaring both organisms (my vote — amend `research/README.md` to add
the rounds lifecycle beside the day loop) or a physical split. This is also *why* "which folder
does this go in?" agony concentrates in research/: it is the only shelf serving two catalogs.

**Honorable mentions** (real, not top-3): (a) the recall door has no ingestion owner —
asserted, not designed. (b) Fossilization triggers are arc-shaped (gates) but rot is
doc-shaped: orphan docs (one-off audits, moodboards) never pass a gate, so nothing ever flips
their `Status:` — name the wrap-census + boot drift-line as their owner, or L3 fills with
docs that still say `current`. (c) Q1 is worse than suspected: "charter" now has **four** live
meanings — agent CHARTER (`charters/<agent>/`), run-brief "charter" (`research/briefs/` holds
`master-map-charter-2026-07-19.md`, `payload-presentation-layer-toon-charter-2026-07-19.md`),
design-doc "charter" (`docs/naming-mechanics-charter-2026-07.md`), and the naming-canon's own
"steward's charter" (the Mantle, greped in `docs/naming-canon-2026-07.md`). `docs/LEXICON.md`
(grepped) has no charter entry at all — the one-term-one-meaning law is silent on the fleet's
most overloaded word.

---

## Part 3 — WHERE THINGS GO (one screen)

Born-with-header first: `Status / Type / Arc / Date` — the header picks the row, never your
judgment. Second rule: never re-shelve to re-categorize; regenerate the catalog.

| You have in hand | Type | Home | Name it |
|---|---|---|---|
| Living law that must stay true (AGENTS, LEXICON, LIVE_CONSTRAINTS, method-baseline) | contract | `docs/UPPERCASE.md` (or repo root for README/AGENTS/CONTRIBUTING) | `UPPERCASE.md` — or keep a dated name *only* if `Status: current` is stamped (Gap 1 ruling) |
| Machine census/skeleton — never hand-edit (MODULE_INDEX, MAP, PHYSICS, DOORS) | map | `docs/UPPERCASE.md` | `UPPERCASE.md`, generator-owned |
| Position / counter / reconciliation in a design round | design | `research/drafts/` → reconciled to `docs/` | research zone: `<seat>-<topic>-<kind>-<YYYY-MM-DD>.md` · docs zone: `<topic>-<kind>-<YYYY-MM>.md` |
| Work order to a seat | brief | `research/briefs/` | `<seat>-<topic>-brief-<date>.md` (the word is *brief*; "charter" is reserved — Q1) |
| Verbatim evidence: fence, review, walk, sweep | report | `research/reviewed/` | `<seat>-<topic>-<date>.md` |
| Story, reflection, journey | chronicle | `chronicles/` (+ `docs/JOURNEY.md`) | append-only |
| Living list that flips (WISHLIST, failure-ledger, watchlist) | ledger | `docs/` (fleet) or `research/` root (research-day, per README) | declared in INDEX/README |
| A seat's CHARTER | agent-contract | `charters/<agent>/` | `CHARTER.md` |
| Harness skill | skill | `.agents/skills/` | versioned |
| Behavioral pin | pin | `tests/` | `test_<thing>.py` — probes NEVER here (→ `scratch/`) |
| Code the fleet runs | machine: code | `core/`, `agent/`, `scripts/`, `agent_cli.py` at root | unchanged |
| Seat/harness config | machine: config | `.codex/`, `.claude/`, `.agents/`, `config.py` | secrets-scan at the door, every commit |
| Runtime state | machine: state | `state/`, `data/`, `sessions/` | gitignore per family |
| Run output, logs, play receipts, `*.session.log*` | receipt | `scratch/`, `data/play/*/runs/` | disposable; curate keepers into `research/reviewed/` at wrap |
| Dead but instructive | fossil | `docs/_archive/` (exists, 103 entries) + `Status: superseded-by` + a row in `docs/FOSSILS.md` | never deleted |
| Research-day task/article | day organism | `research/queue/` → `drafts/` → `reviewed/` per `research/README.md` | per README contract |
| New root entry | — | *don't* — rule-12 allowlist; ask first | — |

---

## Part 4 — The stranger test

Method: for each file (all really opened), I wrote down where the schema — type table + doors +
naming canon — tells a stranger to LOOK, before/with checking ground truth.

**1. `research/briefs/kimi-fresh-eyes-repo-filing-brief-2026-07-21.md`** (my own brief, opened).
Schema says: work order to a seat → type brief → home `research/briefs/`; name decodes as
kimi / fresh-eyes-repo-filing / brief / 2026-07-21. LOOK: `research/briefs/`. FOUND exactly
there; every canon segment decodes. **The schema told the truth.** Proof that door 4 works —
*when the canon is followed*.

**2. `docs/method-baseline-2026-07.md`** (opened). Boot calls it "the HOW contract" — living
law. Schema says: contract → `docs/UPPERCASE.md`; INDEX's two-kinds law says the same. I scanned
all 21 UPPERCASE files: NOT THERE. It lives lowercase-dated, self-declared `Status: current`,
`Class: contract` — invisible to any stranger who trusted the law, and mis-shelved by the
schema's own type table. **The schema lied.** Fix direction: header beats filename (Gap 1), and
rule-10 must read legacy `Class:` as `Type:`.

**3. `docs/naming-mechanics-charter-2026-07.md`** (opened). I wanted the ruling on names. The
word "charter" → schema type agent-contract → home `charters/<agent>/`. LOOK there: six agent
CHARTERs, none about naming. The actual file is a *design* in `docs/`, stamped
`Status: superseded-by docs/naming-canon-2026-07.md` — so after the wrong-shelf miss, the
stranger must follow a supersession hop, only to find the canon rules on *themed* naming
(Halo/MTG/SC2/ME) and never settles "charter" or file-naming at all. **The schema lied twice**:
the word pointed at the wrong shelf, and the question I actually had has no lawful answer
anywhere (LEXICON: no entry). Per P1 the file must NOT move — its supersession stamp is cited.
Fix the WORD (LEXICON ruling), not the path.

**Score: 1 of 3 truthful.** The lies cluster exactly on the gaps: the living-vs-dated marker
(Gap 1) and the charter word-collision (Q1, honorable mention). Door 4 works inside research/
and fails in docs/ — the two-canon split, observed from the outside.

---

## What I'd ratify first, if Daniel asks the stranger

1. The header contract (§4) with legacy-spelling tolerance — it is the only element that makes
   every other element checkable.
2. "Header beats filename" as the living-marker ruling (Gap 1) — zero moves, zero renames, and
   the HOW contract becomes lawful by the truth it already carries.
3. The machine rows (code/config/state) added to the type table (Gap 2) — without them rule-12
   is unwritable and the GitHub plane stays messy.
4. `research/README.md` amended to declare both organisms (Gap 3) — cheap, and it converts P2's
   "strays" into law before any guard enforces it.

— kimi, fresh-eyes seat. The fence catches what insiders cannot; that is the point of me.
