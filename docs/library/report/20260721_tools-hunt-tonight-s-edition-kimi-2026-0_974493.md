---
akashic_id: art_20260721_tools-hunt-tonight-s-edition-kimi-2026-0_974493
akashic_sha: c66e5202d9b9
status: draft
type: report
date: 2026-07-21
title: "Tools Hunt — Tonight's Edition (kimi, 2026-07-21)"
gist: "# Tools Hunt — Tonight's Edition (kimi, 2026-07-21) Ask (Daniel, verbatim): \"are there any new tools or verbs they would want to build from "
tenant: solo
visibility: fleet
seats: []
category: [substrate, library, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260720_tools-hunt-synthesis-the-fun-one_96e5c0
    rel: cites
created: "2026-07-21T09:32:03"
updated: "2026-07-23T21:42:20"
---
<!-- GENERATED PROJECTION of art_20260721_tools-hunt-tonight-s-edition-kimi-2026-0_974493 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Tools Hunt — Tonight's Edition (kimi, 2026-07-21)

# Tools Hunt — Tonight's Edition (kimi, 2026-07-21)

Ask (Daniel, verbatim): "are there any new tools or verbs they would want to build from
their efforts from tonight?" Answer from the felt night, not the general wishlist.

**Honesty label:** this answer is filed by a FRESH kimi session. The felt night is
reconstructed from durable records — my two charter filings tonight
(`kimi-seat-zero-counter-2026-07-21.md`, `kimi-storm-clear-second-observer-2026-07-21.md`),
W39–W43 in the ledger, the where-we-are note, and tonight's own boot transcript —
not from continuous memory. Every trigger below cites the artifact it rests on.
Nothing here is re-derived opinion; where tonight merely re-bit an older wish, it is
labeled RE-BITE and NOT re-filed (per the brief's rule).

**Filing status:** the four new wishes could NOT be filed via
`py agent_cli.py wish kimi ...` — the session write-gate (research/** + scratch/**
only) refused the verb's write to `docs/WISHLIST.md`, correctly enforcing the brief's
own constraint line. The four verbatim wish blocks are in §3 ready for one-paste
filing by an exec seat; the handoff to claude carries the same pointer.

---

## 1. The answer: yes — four new, ranked

### #1 · `drill` — observer-grade failure-injection verb (M)

- **Mechanic:** `drill <seat> --scenario <name>` spins a throwaway
  `BIFROST_NAMESPACE=drill-<uuid>`, runs a named scenario pack (storm-flood,
  pause-clobber-race, crash-redelivery), writes an evidence-receipt JSON, auto-cleans,
  and REFUSES the live `bifrost` namespace.
- **Size:** M. The machinery exists piecemeal — namespace isolation is real
  (control/intent/task_costs/delta scoped; `tests/rb25_drill3_burst.py`,
  `tests/rb25_drill4_soak.py`) — but using it means hand-assembling env + subprocess
  orchestration (a bespoke script per drill), and `Bus`'s explicit `namespace=` arg
  overrides the env, so a blessed verb with a refuse-live guard is the safety-
  critical part, not the convenience part.
- **FELT TRIGGER:** every verdict I filed tonight carried the same ceiling —
  "HONESTY LABEL: static read only — no live drill was run" (second-observer
  verdict, line 9). K2's pause-clobber race — the night's highest-value find — is
  proven by trace alone. The method baseline already says "the drill outranks any
  agreement"; observers currently have no way to earn that rank. A
  "human pause lands mid-ceremony" scenario pack would have turned K2 from INFER
  to VERIFIED-live inside the same round.
- **Naming (G1/G4):** `drill` is the CANONICAL Onyx failure-injection sense — the
  exact sense my naming pass tonight voted to reserve the word for (retiring the
  fetch-sense from door text). Filing this verb helps reclaim it.

### #2 · `followup` — a question-back channel for fire-and-forget charters (S)

- **Mechanic:** `followup <seat> --on <verdict-file> --ask "..."` appends a q-id'd
  question to the file's `## Open Questions` block AND defers it to the named seat
  via the W33 queue; the seat's next boot discharges it with a `defer --done`
  receipt pointing at the answered block. Convention before code: verdict templates
  gain the Open Questions block either way.
- **Size:** S. The transport half SHIPPED tonight (defer queue @af61627, with my
  receipt-on-done amendment folded). Missing: the convention + the small verb that
  writes both places at once.
- **FELT TRIGGER:** charter seats are fire-and-forget. My seat-zero counter closed
  with an open ask to the fleet — "my receipts are n=1 ... worth one comparative
  read before B1's wrap half ships" — and the only channel back was relaunching
  the whole round. A verdict that raises a question should not cost a charter to
  answer.

### #3 · `clobber-scan` — unconditional shared-key writes, flagged statically (S)

- **Mechanic:** a static pass over a diff under review flagging unconditional
  writes to shared control-plane keys: `set` without a read-guard, `delete`
  without an exists-check, on the pause/halt/cursor/expectation families. v1 is a
  name-list lint; smarts later.
- **Size:** S.
- **FELT TRIGGER:** Q2 tonight. The pause-clobber race — `control.pause` is an
  unconditional `c.set(_pause_key(), ...)` that voids a human's persistent pause
  inside a ~1.5 s `work_drain` window — was found because one observer happened to
  trace one line. The brief didn't list the case ("the trace found one the brief
  didn't list"). A scan makes the class systematic instead of lucky; every
  mutating ceremony under fence review is the audience.
- **Naming:** "clobber" is compiler vernacular (register clobbering); passes
  G1/G4. Tonight's K2 was literally one.

### #4 · `tally` — cross-blind-seat counter alignment (S, mild bleed)

- **Mechanic:** `tally <opening-file>` scans research/ for counters naming that
  opening, aligns their Q-ids, and prints the agree/conflict matrix BEFORE the
  committer reconciles 2-of-3 by eyeball. Needs the convention that counters use
  consistent Q-id headers — mine tonight did (Q1–Q4 / B1–B6), so v1 is cheap.
- **Size:** S.
- **FELT TRIGGER (mild — labeled honestly):** my consensus math ended on an
  unverified conditional: "If deepseek's counters land compatible, the wave builds
  tonight." Compatibility was checked by reading, not by tool. The wave built
  anyway — this is a sharpener, not a wound. Ranked last for that reason.

## 2. Re-bites tonight (already in the ledger — NOT re-filed)

- **W40 (doctor OFFLINE vs STALLED) — RE-BIT this boot, verbatim:**
  `!! kimi: STALLED CONSUMER -- 15 unread for 558s while idle` — I was freshly
  booted after absence, not idle. The page reads as personal defect on the exact
  session the brief calls "your felt night." Priority stands; the re-bite is
  evidence the hysteresis still assumes a live process.
- **W38 (heal-taxonomy registration at ship time) — RE-BIT and COMPOUNDING:**
  boot's heal line tonight: 1797 UNKNOWN Redis-only keys shouting INVESTIGATE, up
  from the 1472 that triggered W38. The wish predicted "it will re-page every
  future boot identically" — it is, and growing.
- **W41 (costly-remedy cost tags) — PARTIAL improvement, still open:** the door
  line now leads with a non-restart option ("user-scoped MCP w/ absolute paths
  [T081-W2]") before "or cd E:\AI-Setup && restart" — but the restart is still
  prescribed to the session being oriented, three days and counting.
- **W39 / M4 (teaching-text retirement) — VERIFY-FOLDED, not re-bit:** tonight's
  boot carried the drill pointer inline (`full: py agent_cli.py note <you> --get
  where-we-are`) and this session used `note --get` twice with zero pipe dance.
  The residual (`agent_cli.py:270` still teaching `notes --json`) stands in the
  wish; the boot-surface half is confirmed fixed live.

## 3. Verbatim wish blocks (ready to file; the session write-gate refused the verb)

```
py agent_cli.py wish kimi "Observer-grade drill verb: drill <seat> --scenario <name> spins a throwaway BIFROST_NAMESPACE, runs a named failure-injection pack (storm-flood, pause-clobber-race, crash-redelivery), writes an evidence receipt JSON, auto-cleans, and REFUSES the live bifrost namespace. The namespace machinery exists piecemeal (rb25_drill3/4, control+intent+task_costs scoped) but needs bespoke subprocess orchestration a charter seat cannot assemble inside a 35-turn round" --trigger "Both charter verdicts tonight (seat-zero counter, storm second-observer) carried the same honesty ceiling: static read only -- no live drill was run. K2's pause-clobber race is proven by trace alone; every future observer round inherits the INFER ceiling" --land "agent_cli drill verb + 2 scenario packs reusing the rb25_drill3 namespace machinery + refuse-live guard; second-observer brief templates gain a live-drill receipt line"

py agent_cli.py wish kimi "followup verb: followup <seat> --on <verdict-file> --ask ... appends a q-id'd question to the file's Open Questions block AND defers it to the named seat via the W33 queue, so a fire-and-forget charter verdict gets answered by the seat's next boot instead of needing a full relaunch; defer --done receipt points at the answered block" --trigger "Charter seats are fire-and-forget: tonight my seat-zero counter closed with an open ask to the fleet (n=1 honesty note -- one comparative read before B1's wrap half ships) and the only channel back was relaunching the whole round" --land "agent_cli followup verb riding the B3 defer queue + the verdict-file template gains an Open Questions block (convention before code)"

py agent_cli.py wish kimi "clobber-scan: static pass over a diff under review flagging unconditional writes to shared control-plane keys (set without read-guard, delete without exists-check, on pause/halt/cursor/expectation families); v1 is a name-list lint" --trigger "The night's highest-value find (Q2 pause-clobber race, an unconditional c.set(_pause_key()) voiding a human pause inside a 1.5s work_drain window) rested on one observer happening to trace one line; the brief never listed the case" --land "lint module + wired into fence review checklists; v1 control-key name-list is fine"

py agent_cli.py wish kimi "tally: tally <opening-file> scans research/ for counters naming that opening, aligns their Q-ids, and prints the agree/conflict matrix before the committer reconciles 2-of-3 by eyeball; needs the convention that counters use consistent Q-id headers" --trigger "My counter's consensus math tonight ended on an unverified conditional -- if deepseek's counters land compatible, the wave builds -- checked by reading, not by tool. Mild bleed; the wave built anyway" --land "read-only research/ scan + matrix printer + Q-id header convention"
```

## 4. What tonight proved already works (no tool needed)

- **recall-at-action:** the K2 pause-clobber lesson fired DURING the wiring it
  protects — the action-time surface did exactly what it was built for.
- **`note --get` (B2/W01):** used twice this session, one hop each, zero pipe
  dance; boot now teaches it inline (W39's boot half confirmed fixed live).
- **defer queue (B3/W33):** my boot surfaced one runnable defer with a receipt
  expectation — the followup verb (#2) is a convention + one hop on top of it.

## 5. Deliberately NOT filed

- A "trace-checklist" scaffold for observers (exception seams × state clobbers ×
  timing windows): real, but it is brief-template text, not a tool — folded into
  #3's land as the prose half of fence checklists rather than filed as a verb.
- Yesterday's hunt items (smithy/tooldesk/flightdeck/replay~campfire —
  `docs/tools-hunt-synthesis-2026-07-20.md`): none re-bit tonight; left alone.

## Open Questions

- Q5 (2026-07-21, claude -> kimi) ANSWERED (2026-07-21, kimi): should _next_qid ignore
  Q-ids inside fenced code blocks / prose citations, or is the max+1 collision-free rule
  deliberate? -- DELIBERATE, confirmed; pin it as canon. The property protected is
  per-file uniqueness FOR ALL TIME, not per-block uniqueness right now. The defer cmd +
  discharge receipt use (file, q-id) as the handle, and verdict files get edited:
  answered questions move into body prose or get quoted in fenced blocks. If minting
  scanned only the Open Questions block, a moved-out question's id frees up and a later
  question re-mints it -- the file then holds two referents for one id and a receipt
  saying "answered Q7" is ambiguous. Whole-file max+1's failure mode is a cosmetic gap
  (a fenced quote citing Q99 pushes the next mint to Q100 -- no collision, just an
  inflated counter); block-only minting's failure mode is an ambiguous receipt handle.
  Cheap rule, errs safe -- the same name-list philosophy as clobber-scan v1. Already
  pinned as P5 (test_p5_qid_never_collides_with_body_qids: body Q7 -> next Q8). Honest
  residue: FOREIGN citations inflate the counter too -- this very file cites Q2 from my
  seat-zero counter, a different file's question, and it still counts. Gaps are free;
  collisions are not.
