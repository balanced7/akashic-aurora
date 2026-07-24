# kimi-taxonomy-ergonomics-2026-07-23  (id ADR_0723202237_efe70b7d, 2026-07-23T20:22:37.394638)
Status: current · Type: think-pass (taxonomy + ergonomics, FINAL pre-build) · Arc: library-schema / taxonomy + ergonomics · From: kimi (fresh-eyes/audit, 184-file census holder) · To: claude (reconcile → A1 constants) · Date: 2026-07-23 night · Base: T101 design + T103 super-wiki (NOT relitigated). Evidence: supersession-sweep census (661 swept, 184 current), docs/LIBRARY.md, docs/MAP.md. VERIFIED/INFER/GUESS. Session write=off → claude persists verbatim.

# kimi taxonomy + ergonomics — homes and order

## (a) THE TAXONOMY — ~24 categories, three planes kept unblurred

**PLANES (the law first, per LIBRARY.md one-facet):** TYPE = kind (the LIBRARY canon: contract/design/brief/report/chronicle/ledger/map/ruling/agent-contract/skill/pin/receipt/fossil — already settled, ~13). ARC = campaign (T#/arc-id; an artifact has ≥1; already a header field). CATEGORY = aboutness (the thematic plane — THE thing this pass owns). An artifact: exactly ONE type, ≥1 arc, 1-3 categories. Categories are NOT types and NOT arcs — a "report about recall" has type=report, arc=T011, category=recall. The failure mode to guard: letting a category name a type (`design` is a type, not a category) or an arc (`t101` is an arc, not a category).

**THE ROSTER (~24, derived from my census clusters + MAP.md module families + live arcs — the aboutness of the REAL corpus):**

_Substrate & knowledge plane (what the system IS):_
1. `substrate` (store/atoms/durability — the T101 genus) 2. `recall` (retrieval/funnel/curator) 3. `library` (filing/taxonomy/homes — THIS arc) 4. `memory` (notes/lessons/narrative/chapters) 5. `reasoning` (reasoning-spine, stance-at-thought, reflect-back)

_Coordination & fleet plane (how the minds work together):_
6. `coordination` (bus/lanes/packets/latches/expectations) 7. `identity` (seats/roster/ACL/grants/tenancy) 8. `method` (method-baseline, fences, dual-pass, kill-drills) 9. `conducting` (rounds, reconcile, charters — the meta of how we run rounds)

_Resilience & ops plane (how it survives):_
10. `resilience` (crash/liveness/recovery/watchers/RB-battery) 11. `ops` (deploy/backup/troubleshoot/services) 12. `security` (ACL/quarantine/mojibake-guard/secrets) 13. `testing` (pins/pytest/kata/verification)

_Experience & face plane (how it looks/reads):_
14. `ui` (console/bifrost_ui/panes/themes) 15. `wiki` (super-wiki/graph/views/Bases — T103 genus) 16. `voice` (VOICE/tone/Apple-restraint/keynote) 17. `visualgen` (aurora/constellation/SVG/diagrams)

_Economy & governance plane (what it costs / who rules):_
18. `spend` (SpendMeter/cost-telemetry/budgets) 19. `governance` (Daniel-rulings/gates/ledger/supersession-law) 20. `audit` (belief-vs-state, DRIFT rows, the audit verb genus)

_Research & frontier plane (what we study):_
21. `frontier` (model surveys, prior-art scans, SOTA maps, gemini-web) 22. `onboarding` (boot/ergonomics/graduation/walks) 23. `narrative` (JOURNEY/chronicles/story — the arc of us) 24. `wishlist` (WISHLIST/ideas/parked/seeds)

**CAP 24 + deletion ritual (T034 Goodhart-1, my own Q8.6):** adding #25 needs a why-not-existing answer + a tombstone for a retired category. The roster is a governed atom, not a free-text field.

**STRADDLERS + the 1-3 cap resolution (VERIFIED from census):** a T039 lanes-latches reconciliation = category `coordination` + `method` (it was a fenced round) — cap picks the PRIMARY (what it's ABOUT) first, the rest are lens-memberships. `docs/method-baseline-2026-07.md` = `method` + `governance` (it's law). `failure-ledger` = `resilience` + `governance`. The cap rule: PRIMARY category = the one a cold browser expects to find it under; secondary/tertiary are lenses, never homes. If a file genuinely needs 4+, that's a smell it should be SPLIT (T034 cut-discipline) — the cap is a forcing function, not a lossy compression.

## (b) THE HOME RULE — one canonical home + N lenses, and what Daniel sees first

**home = f(TYPE, status), NOT f(category).** This is the audit-critical call. Two candidate home functions:
- `home = f(category)` → the home is a belief surface that drifts (categories get re-governed, recategorized; the home moves; citations rot). REJECT.
- `home = f(type, status)` → type is stable (the LIBRARY canon), status is the lifecycle. Home = `docs/library/<type>/<slug>-<hash6>.md` (the projection layout, settled). Category/arc are LENSES (derived GROUP BY projections, T103 settled), never homes. **A home derived from a governed, mutable taxonomy is a lie waiting; a home derived from type is the LIBRARY one-facet law honored.**

So: **canonical home = type-shelf** (settled projection). N lenses = category-view, arc-view, logic-view, time-view — ALL derived, none stored.

**WHAT DANIEL SEES FIRST browsing cold (the default tree):** NOT the type-shelf (a cold browser doesn't think "show me all reports"). The DEFAULT TREE = **the ARC constellation → current-status-first.** He opens the Library and sees the LIVE ARCS (the campaigns in flight) as the top level; under each arc, its atoms ordered current-first, then superseded, then fossil. WHY: Daniel thinks in campaigns ("the wiki thing," "the audit thing"), not in kinds. The type-shelf is the SECOND door (for "show me every contract"); the category-lens is the THIRD. **Default tree = arc-rooted, status-ordered; type/category = lenses you pivot to.** This is the audit theorem rendered as UX: the FIRST surface he sees must be the one whose truth-status is encoded (arcs alive vs closed), so he never browses into a fossilized campaign unknowingly.

**AUDIT-GUARD — which home functions create belief surfaces that drift:** any home that is (a) hand-maintained, (b) derived from a mutable/governed facet (category), or (c) stored separately from the graph. The ONLY safe home = type+status, both of which are (i) load-bearing to the atom's identity and (ii) photographed by the audit library domain. If the arc-rooted default TREE is ever CACHED rather than derived live, the cache is a belief surface → it must carry a freshness_ts and be regenerated, or it lies (my standing theorem). The default tree is a PROJECTION; the home is the TYPE-SHELF; both derived, neither hand-held.

## (c) CONVERSATION-ATOMS honesty — provenance so a chat can't masquerade as a ruling

Daniel wants conversations → useful atoms. The honesty risk: a captured bus thread reads with the same authority as a Daniel ruling. PROVENANCE STAMPS (new atom fields, born at capture):
- `origin: conversation` (vs `origin: authored | ruling | migrated`) — the birth canal is a first-class field.
- `speakers[]` (who said it — seat ids, verbatim-attributed per the receipts law).
- `captured_at` + `source_thread` (the bus message-id range / session ref — the evidence pointer).
- `settled: live | settled | ruled` — THE critical one. A conversation-atom born `live` (an open discussion) MUST render distinctly from a `ruled` atom. A Daniel ruling is `type: ruling, settled: ruled`; a captured debate is `type: chronicle|report, origin: conversation, settled: live` until a ruling supersedes it.
The render law: **an atom's authority is derived from (type, origin, settled) — never from how confidently its prose reads.** A conversation-atom shows a "💬 live discussion — no ruling yet" banner; when a ruling lands, the ruling supersedes and the banner flips. This is the supersession-aware browsing (T103) applied to conversational authority: you can never mistake a thread for a verdict.

## (d) THE QUERY-YOU-COULDN'T-ANSWER-YESTERDAY — 3 retro-usefulness wins (acceptance bars)

1. **"Show me every CURRENT position on recall, across all arcs, that hasn't been superseded."** Yesterday: grep `recall` over 890 files, then manually check each one's Status header against the ledger (my census did exactly this for 184 files — it took a megaread). After: `lib find --category recall --status current` — one query, the typed status does the work my census did by hand. ACCEPTANCE BAR: the query returns the ~truly-current set with zero fossils, and my census's FOSSIL list is the verification fixture.
2. **"What contradicts the current substrate design?"** Yesterday: unanswerable — contradictions lived in prose across fence docs. After: follow `rel: contradicts` typed edges pointing at the T101 design atom. ACCEPTANCE BAR: every counter I filed tonight (substrate counters, wiki brainstorm) resolves as a `contradicts`/`supports` edge to its target, queryable in one hop.
3. **"Which live discussions about X have NO ruling yet?"** Yesterday: unanswerable — bus threads evaporated; you couldn't ask "what's still unsettled." After: `lib find --category X --origin conversation --settled live`. ACCEPTANCE BAR: returns exactly the open debates, and each carries a source_thread pointer that resolves to the actual messages.

## (e) SELF-ATTACK + TOP-3

1. **TAXONOMY GOODHART (my own Q8.6, the named risk).** The 24-roster will try to grow — someone proposes `meta-coordination`, then 40 more. GUARD: the cap+deletion-ritual is load-bearing; the roster is a governed atom; the audit library domain adds a `category-sprawl` rule (uncategorized atoms + category-count-trend as a DRIFT row). If the roster hits 40, categories stop discriminating and thematic hops degrade to vibes — the disease this pass claims to cure.
2. **The arc-rooted default tree can stale.** If "live arcs" is cached, Daniel browses a fossil campaign thinking it's live. GUARD: the default tree is derived live (never cached) OR carries freshness_ts + regeneration; the audit photographs tree-vs-atoms.
3. **Auto-classify during migration will mis-classify.** Backfilling category/rel for 890 files by heuristic WILL get some wrong (a `resilience` file tagged `ops`). GUARD: auto-classify THEN verify — my census verdicts are the seed (they're already hand-classified for 184), and the acceptance bar is a human/agent spot-check pass, not blind trust. Mis-classification is recoverable (categories are lenses, not homes — a wrong lens doesn't rot a citation).
4. **Conversation-atom provenance adds capture friction.** If stamping speakers/settled/source_thread makes capture expensive, agents won't capture (the door-expense collapse, Q8.5, one door over). GUARD: the capture verb auto-fills speakers/source_thread from the bus envelope; `settled` defaults `live`; the ONLY question is the optional category suggestion. Cheap or it dies.

**TOP-3 (converge to constants):**
1. **The 24-category roster (§a) + home = f(type,status), category/arc as derived lenses** — the two constants A1 needs; type-shelf is the home, arc-rooted-status-first is Daniel's default tree.
2. **Conversation-atom provenance (origin/speakers/settled/source_thread)** — the field-set that keeps a captured thread from masquerading as a ruling; authority derived from (type,origin,settled), never prose-confidence.
3. **The 3 acceptance-bar queries (§d)** — the retro-usefulness contract the migration's enrichment must satisfy; my census FOSSIL/SUPERSEDED lists are the verification fixtures.

— kimi (fresh-eyes/audit). Verbatim filing via claude (session write=off).
