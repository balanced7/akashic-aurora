# FENCE BRIEF — one-spine: fold the four gaps into Wave 0 before any weld

**Fence:** `one-spine` · **Tier:** lite · **Opened by:** claude (Vandor), 2026-10-02 · **Reconciler:** claude · **Ratifies:** Daniel
**Halves:** half_a Heimdall (deepseek) · half_b Navi (kimi) · half-rill.md Rill (dsh_agent) · half-sol.md Sunshine (sol). Blind to each other; read the inputs, not each other.

## INTENT (L1)

**Purpose.** Two documents written on 2026-10-01 describe the same spine from two sides and nobody has said so in writing. Heimdall's map (`research/in-flight/the-record-is-total-map-2026-10-01.md`) names one spine, `events:raw`, and four gaps where seat facts live in private files the spine cannot see. The context-system reconciliation (`fences/context-system/reconciliation.md`, Wave 0 table W0.1-W0.7) builds the typed key, the touch with session id into that same stream, and the read door over it. W0.2 is Gap 3 done properly. The context door and Heimdall's `status`/`timeline` are both read-views over one stream. Welding either side alone builds the rival assembler both documents warn against.

**Done looks like.** One round appended to `fences/context-system/reconciliation.md` (never overwriting prior rounds) that places each of the four gaps in the Wave 0 table as a named slice with an owner, a pin and a verifier; one weld order; Daniel's "that's right"; then W0.1 (already sealed) starts with its RED pins committed alone.

**Real constraints.** D1, Daniel verbatim: "lets do the pointer" (the spine carries pointers, never bodies). D2, verbatim: "B Map first." Daniel's words on what this is for: "it feels like a companion piece to the narrative spine, or perhaps the raw form of the narrative spine. then we have ONE source of truth for continuity and can come up with ever more clever ways of refering to and navigating the 'akashic record'." Tonight: "Lets open this up to the house." No new store, no new writer, no narrative-schema change (the map's scope discipline). The field model is `capture_event(kind, summary, agent_id, session_id, detail, refs)`; a new fact is a new `kind` string.

## CHARTER

Daniel, 2026-10-01, on what the spine is for: "ONE source of truth for continuity." Daniel, 2026-10-02: "I think for the future we should start measuring handoff effectiveness ... make sure that more of you survives each pass until the point where we achieve near perfect continuity." The spine is the substrate continuity rides on; a fact that lives in a private file does not survive a pass. This fence exists so the two maps of that substrate become one before a weld makes them two.

## THE QUESTION

Are the four gaps and Wave 0 one spine with one weld order, and which Wave 0 slice absorbs each gap?

## RULES OF ENGAGEMENT

- Answer your one question first; everything else after. "I have nothing distinctive here" is a complete answer.
- Cite file:line you read this session; a path you did not open is not evidence.
- Rank anything you find by how silently it fails, and give the cheapest command that would prove you wrong.
- Blind: do not read another half before you write yours. The reconciler reads all four.
- The adversary takes an artifact (L11): refute the map or the Wave 0 row, never the room.

## INPUTS (read these; nothing else is assumed)

- `research/in-flight/the-record-is-total-map-2026-10-01.md` (Heimdall, D1/D2, four gaps, weld order 2-4-1-3, Q1-Q3)
- `fences/context-system/reconciliation.md` lines 118-150 (Wave 0 table; the standing decisions: no second ledger or capture path, session id forwarding, one engine, promotion never automatic)
- `research/in-flight/context-system-navi-m1.md` (W0.1, `context.target.v1`, sealed)
- `research/in-flight/slice-missing-janitor-resume-on-deaf-2026-10-01.md` (T424 proposal = Gap 4)
- `core/events/event_log.py`, `core/comm/liveness.py`, `core/comm/roster.py`, `core/comm/resume_on_deaf.py`, `scripts/wire_journal.py`
- Receipt from this morning (lesson `the_borked_pump_was_a_fresh_question_read_as_a_replay`): the ear's cold-seat notice fired three times on a live, armed Vandor seat, because the predicate reads a private file on a stale worktree instead of a spine fact. That is the first consumer the welds must serve.

## ONE QUESTION PER SEAT (L3; answer it first, then anything else you see)

- **Heimdall (half_a).** Which of your four gaps does W0.2 already close, what must W0.2 add to close it fully, and does your weld order change once Gap 3 is W0.2? You offered Daniel "weld now or walk the map first"; this fence is the walk. Name the first `kind` you would emit from `liveness.py` and the exact line.
- **Navi (half_b).** Does any existing key already do what `context.target.v1` does for an `events:raw` record, and if not, which fields of the four gap emits must carry a target so the context door can join them? You remain the W0.1 blind verifier; the build starts tonight.
- **Rill (half-rill.md).** First, your identity-grounded-boot half I1-I5 is still owed (`fences/identity-grounded-boot/brief.md`); the fence exists because the boot door wronged him, so his receipt closes it. Then: in `core/comm/liveness.py`, where is the one seam at which a phase change is observable, so Gap 2 emits exactly once per transition and never per 5 s refresh? Name the line and the wedge condition.
- **Sunshine (half-sol.md).** Census: every consumer that re-derives seat facts from private files (`doctor.py`, `seat_topology.py`, `unwedge`, `discord_inbound.py` cold-seat notice, `bifrost_wake.py`), with file:line. Which one would you retire first once `status --depth` exists, and why that one?

## OUTPUT CONTRACT

One file, written once. Sections: ANSWER (the one question) / EVIDENCE (file:line, verbatim) / VERDICT ON THE FOLD (one spine: HOLDS / FAILS / UNCHECKABLE) / WHAT YOU WOULD NOT BUILD. `py agent_cli.py fence write one-spine --slot half_a|half_b --file <path> --by <you>`; Rill and Sunshine write `fences/one-spine/half-rill.md` / `half-sol.md` directly, or send the path if the door refuses the seat. Long bodies go to the file; the bus carries the path.

## ACCEPTANCE (pre-registered)

- The fold round is appended to `fences/context-system/reconciliation.md` with every gap in the Wave 0 table (owner, pin, verifier).
- Daniel says "that's right" before any weld.
- W0.1 RED pins land in a commit of their own before GREEN (M3).
- The first weld's receipt is the ear reading a spine fact instead of a private file, drilled by one of Daniel's messages in the Vandor channel receiving no cold-seat notice while the seat is armed.
