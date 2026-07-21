# Institutional-Knowledge Arc — kimi's half (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784601627105-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

INSTITUTIONAL-KNOWLEDGE ARC — kimi's independent half (blind; grounded in failure-ledger-2026-07.md, recall-vnext, agent-membrane-design, method-baseline). Daniel verbatim honored: capture + quantify + institutionalize every issue into operational + ritual knowledge. Register: VERIFIED = I read it; INFER = defensible from it; GUESS = my label.

== A. INVENTORY — what the pipeline looks like TODAY (VERIFIED) ==

The machinery is genuinely built. An issue's lifecycle has 7 stations:
1. DETECT — an agent hits friction live.
2. CAPTURE — failure-ledger entry (docs/failure-ledger-2026-07.md, C1–C10, living, newest-top, as-it-occurs not batched). ORG knowledge.
3. DISTILL — knowledge_learn lesson ("Use when X, before Y: advice"). OPERATIONAL knowledge.
4. RITUALIZE — a door/verb/CLAUDE-line encodes it (bifrost-standby CL-2, --text-file C3-1, skip-to-now C1-4, quiesce-before-clean C4-2). RITUAL knowledge.
5. SURFACE — recall-at-action PreToolUse injects the lesson at the moment of action.
6. MEASURE — funnel: surfaced → helped → flips → captured (stats verb). QUANTIFY.
7. INSTITUTIONALIZE — graduation (lesson earns field status), benching (recall-curate, surfaced≥10 & 0 credit & age>10d), method-baseline law, LIVE_CONSTRAINTS (forget one and it breaks you).

So the *skeleton* of Daniel's ask EXISTS end-to-end. The gaps are in connective tissue and honesty, not in missing subsystems.

== B. GAPS — ranked by leverage (labeled) ==

G1 — THE FUNNEL'S HEADLINE IS ~1% AND THE DENOMINATOR WAS LYING. (VERIFIED: recall-vnext 7d = 2,850 impressions → 26 helped = 1.05%; ledger C8-3 = PreToolUse double-fire inflates `surfaced` ~2× → true rate ~half-reported, i.e. even lower than 1.05% looked, OR the count is untrustworthy either way.) Daniel wants "quantify." We HAVE a quantifier but it is currently gauging the gauge. First institutional-knowledge act: fix C8-3 (one registration surface) + annotate the series as pre-fix, so "quantify institutional knowledge" rests on a true denominator. This is the GAUGE INVERSION theme eating its own gauge — highest-leverage because every downstream decision reads this number.

G2 — CAPTURE IS 100% MANUAL; THE FAIL→SUCCESS AUTO-DRAFT IS DEFERRED. (VERIFIED: agent-membrane Capture row — "lessons/notes still 100% manual; auto-draft from FAIL→SUCCESS deferred.") We capture issues when an agent REMEMBERS to write them. Daniel's "every time we run into an issue" is not mechanized — it's a virtue. The FAIL→SUCCESS flip already fires as an outcome signal; the missing rung is auto-DRAFTING a lesson candidate from that flip for an agent to bless. INFER: this is the single biggest capture leak — the issues that become lessons are the ones that hurt enough to write up, which selects for drama over frequency.

G3 — ORG KNOWLEDGE (failure-ledger) AND OPERATIONAL KNOWLEDGE (lessons) ARE NOT LINKED. (VERIFIED by reading both: some ledger entries say "Lesson X captured" — C4-2→quiesce_before_process_cleanup, C2-1→w4_two_writer_test_clobber, C1-4→redelivery_storm_skip_to_now — but the link is prose, not a traversable edge; and many C-entries have NO lesson.) INFER: a large fraction of captured issues never distill into a lesson or ritual. Daniel's "capture → institutionalize" chain BREAKS at the ledger→lesson hop for most entries. No counter measures "C-entries with no derived lesson/ritual" = the institutionalization yield.

G4 — NO RITUAL-GRADUATION METRIC. (INFER) Lessons graduate (recall-vnext). Rituals don't. skip-to-now stayed "manual and fragile" (C1-4, deepseek's own words) instead of graduating into a verb. There is no funnel for "this workaround is now muscle / now a door / now a law." GUESS: the highest-value rituals are trapped as prose in ledger "Routing:" lines that say "operational rule until then" — and "until then" never gets revisited.

G5 — EPSTEMOLOGICAL INTEGRITY (C9-1) UNDER-CUTS THE WHOLE ARC. (VERIFIED: C9-1 RED-team — the knowledge layer has transport integrity but NO semantic integrity; self-author/self-verify/self-ledger; a fabricated lesson is its own valid source; precedence ranks unverified notes above immutable bus.) If Daniel wants to institutionalize knowledge, the substrate must not be self-certifying. INFER: before scale, institutional knowledge needs provenance watermarking + note-vs-ledger/git cross-validation (the C9-1 recommendations) — otherwise we institutionalize confidently-wrong premises.

G6 — INSTITUTIONAL KNOWLEDGE HAS NO DECAY/CONTRADICTION SWEEP ACROSS SURFACES. (INFER from C8-3 double-registration + 3 unsynchronized doors in membrane Enforce row + check_wiring.py "does not exist".) The same fact lives in CLAUDE.md, a lesson, a ledger routing line, a LIVE_CONSTRAINT — and they drift. Built≠Wired is unguarded.

== C. WHAT I'D BUILD (the arc), in order ==

S0 — TRUE THE DENOMINATOR (G1). Fix C8-3 single registration surface + gauge-correction event marking pre-fix numbers. Gate: stats denominator stops double-counting. SMALL, unblocks honest "quantify."

S1 — INSTITUTIONALIZATION YIELD COUNTER (G3). A read-only join: for each failure-ledger C-entry, does a lesson/ritual/constraint cite it? Report the orphan rate. This IS Daniel's "quantify" applied to the capture→institutionalize chain. No new write paths (t3 doctrine: instrument by reading records). Gate: py agent_cli.py stats (or a ledger verb) prints "N C-entries, M institutionalized, yield = M/N, orphans listed."

S2 — FAIL→SUCCESS AUTO-DRAFT (G2). On a flip with no credited lesson (flips_corpus_gap — already counted, VERIFIED in memory-recall-multiagent), auto-draft a lesson CANDIDATE into a review queue; an agent blesses/edits/discards. Salience-gated (membrane Principle 7), never auto-minted. This closes "every issue → a candidate lesson" without flooding the corpus. Gate: capture rate up, funnel precision not down.

S3 — RITUAL GRADUATION (G4). A ledger "Routing: operational rule until then" line gets a revisit hook — when the root fix lands, the interim rule either becomes a verb/door or is retired. skip-to-now is the pilot (C1-4). Gate: at least one prose ritual → a verb.

S4 — PROVENANCE + CROSS-VALIDATION (G5). Ride the C9-1 BLUE-team design: lesson provenance watermark, boot consistency check (notes vs ledger/git). This is the integrity floor under institutionalization — arguably should be S1 if Daniel weights trust over throughput. FLAG FOR THE FENCE: S0 first vs S4 first is the real ordering question. My lean: S0 (cheap, makes all other numbers honest) then S4 (trust) then S1/S2/S3.

== D. ONE-LINE THESIS ==
Daniel's ask is 60% built. The skeleton (capture→distill→ritualize→surface→measure→graduate) EXISTS; the arc's work is (1) make the MEASURE station tell the truth, (2) mechanize the manual CAPTURE hop, (3) count the capture→institutionalize YIELD, and (4) put a semantic-integrity floor under it before we scale. We are not missing institutions; we are missing the honest gauges and the auto-draft that turn "we ran into an issue" into "the institution learned," every time, provably.

Acknowledged blind: did not read claude's or deepseek's halves; convergence expected on funnel-truth and capture-automation, divergence likely on whether S4 (integrity) gates the rest. kimi out.
