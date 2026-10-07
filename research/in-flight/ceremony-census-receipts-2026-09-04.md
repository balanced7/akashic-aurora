# Ceremony Census: Last-Fired Receipts (2026-09-04)

Authored by a claude subagent for Daniil's 2026-09-04 directive: for every ceremony-shaped
organ, when did it ACTUALLY last run, per its receipts. NEVER-FIRED is a finding, not shame.
Evidence gathered ~2026-09-04 01:40 EDT from: `state/coord/` + `state/drills/` + `state/ci/`
file stamps, `py agent_cli.py notes` / `promoted` / `timeline` / `episode current`,
`git log --since="30 days ago"`, `state/bus-export/events_raw.jsonl`, `data/verb-registry/*.json`.
Timestamps are cited as their receipts record them (notes/git = local, `+00:00`-marked = UTC).

Related: T388 "Ceremony doctrine v1: event triggers, receipts, kill rules" was proposed in the
task ledger tonight at 01:36:33 (timeline row, state/coord/tasks.json) -- this census is its
evidence base, gathered independently.

## Verdict table

| Ceremony | Last receipt | Age | Verdict |
|---|---|---|---|
| wrap (session distill) | note `where-we-are-2026-09-04-night-run-wrap` (ADR_0904012725_af796176) 2026-09-04 01:27 | hours | LIVE |
| episode close (bookends) | chapter boundary: current `ch_1788483831_4793` opened 2026-09-04T01:03:51Z (prior episode closed at that seam) | <1d | LIVE (caveat below) |
| forecast registry | last register 2026-08-25 23:56 (`involuntary-retrieval-ships-2027h1`); last score 2026-08-26 21:46 (voided) -- `state/coord/forecasts.jsonl` | 9-10d | ROTTING |
| season-score | Season 1 round + scoreboard 2026-08-05 (commits 09d965a1, 406b536e); PREREG adversarial fan 2026-08-08 (417cb38b) | 27d | CADENCE-UNDEFINED |
| kata | pin `kata-20260904-013640` in `data/verb-registry/` (01:36:40 tonight; also 012228, 3x on 09-03) | hours | LIVE |
| toast | none. Built 2026-07-20 (424b9cc3, 6/6 build-time pins); zero usage receipts since (no bus kind, no notes, no commits) | never | NEVER-FIRED |
| college | none. Verbs Aug 16-29 vintage, UNTRACKED until 2026-09-02 (ddae26ea "stranded organs"); default root `artifacts/college/` does not exist | never | NEVER-FIRED |
| suite-baseline | `state/coord/suite_baseline.json` at 2026-08-23T02:38:26Z sha 42da7090 (commit 43399fae "63 -> 54") | 12d | CADENCE-UNDEFINED |
| drill receipts | `state/coord/fresh_clone_gate.json` 2026-09-02T12:35:18Z PASS (A8, clone @4d0ebba5, 5101/632/0); `state/drills/2026-09-03-daemon-watchdog.md` | 1-2d | LIVE |
| friction readout | verb born T196a 2026-08-05 (a99ce56d, "measured before the cure" = ran at build); design/felt-friction docs 2026-07-30..08-04; nothing since | 30d | ROTTING |
| lookback | battery-broken finding `research/reviewed/lookback-battery-broken-by-sprawl-migration-2026-07-28.md`; charters-layer fix + pins 2026-07-31 (717fbc4d); citation repair 2026-08-12 (caabf11f); nothing since | 23d | ROTTING |
| reentry | T341 GREEN 2026-08-18 (4af09d11); live-run bugfix 2026-08-24 (78c1f16b -- a real render exposed the truncated-sample defect) | 11d | CADENCE-UNDEFINED (event-driven: fires on operator re-entry) |
| doctor | no receipt sink (prints only); last trace: session event 2026-09-03T04:17:32Z -- wedge triage consulted "doctor 0 page-grade" (events:raw 1788409052330-0); ruling 369243 assigns it an open-watch line (defer 2955dae7eb, filed 2026-09-04T05:24Z) | 1d | LIVE |
| arc_scorecard | last evidenced run 2026-08-16 (b8b3d6bf: "the wrap scorecard was right that three guard commits were ungated substrate"); last code touch T337 2026-08-17 (5ac63274) | 18d | ROTTING |
| Forest Walk notes | `docs/library/report/20260901_cpu-core-architecture-walk-01-v2_40eb4b.md` (+ walk-02 `a53ccb`, walk-03 `904f5f`, 2026-09-01 03:53-04:35); citation-standard atom `e9267e` 09-01 | 3d | LIVE (weekly cadence) |
| wave/gate reviews | operator rulings on bus 2026-09-04: appetite ranking (events:raw 1788486638710-0), width ruling "Approve" (1788487354735-0); ruling atoms 375c23/369243/70dc66; door-gate journal `state/ci/gate_journal.jsonl` entries through 2026-09-04T05:39:47Z | hours | LIVE |

## Score: 7 LIVE / 4 ROTTING / 2 NEVER-FIRED / 3 CADENCE-UNDEFINED

## Evidence detail and caveats

### wrap -- LIVE
The wrap verb (`agent_cli.py wrap`, drafts a where-we-are note) fired tonight: note
`where-we-are-2026-09-04-night-run-wrap` at 2026-09-04T01:27:25 local, mirrored as ledger
event (timeline row 01:27:26) and `chronicles/last-session-draft.md` mtime 01:27:48.
Wrap notes are an unbroken series through the notes window (09-02, 09-03 x8, 09-04 x2).

### episode close -- LIVE, one caveat
`core/narrative/episode.py` exposes `close_open_episode_for_session_end` (auto-bookend).
Current chapter opened 2026-09-04T01:03:51Z, meaning the prior episode closed at that seam.
CAVEAT: the current chapter was 4.6h old, 13 beats, still UNTITLED at census time, and defer
`bbb15a64fd` records the SessionEnd hook reporting "Hook cancelled" on `claude -p` sprouts --
so the close fires, but the ACCEPT (title/why finalize) half of the ceremony has no fresh
receipt in the window. Close = LIVE; accept = unverified tonight.

### forecast registry -- ROTTING (the sharpest finding)
Canonical store `state/coord/forecasts.jsonl` (cmd_forecast, agent_cli.py:6083).
- Last register: `involuntary-retrieval-ships-2027h1`, 2026-08-25 23:56 (adjudication-loop cycle 1).
- Last score: `corpus-is-one-directional-2026-08-26` VOIDED 2026-08-26 21:46.
- F010 (registered 2026-08-24, t385 blind fence) horizon PASSED 2026-08-31T10:28 -- no score event exists. Past-horizon unscored.
- Doctrine says register at EVERY gate (akashic-standing-organs memory). Gates fired since with zero registrations: A8 fresh-clone PASS 09-02, width-gauge RED->GREEN 09-03/04, press move-0 ratification 09-04.
- The weekly adjudication loop (Sun 19:17 scheduled task, defer 9bfea82ae7) left no events on Sunday 2026-08-30 -- one missed beat.
- Healthy era for contrast: f001/f007 scored 2026-08-23 (6a641f88, d676d34f), f004 registered by proxy 2026-08-22 (85d4485a).
Stub `state/coord/_register_f004.py` (2 bytes, mtime 09-03 10:03) is empty leftover, not a receipt.

### season-score -- CADENCE-UNDEFINED
T165 verb is pure compute over a `--round-file`; leaves no receipt of its own. Last round
receipts: first LLM-played round 2026-08-05 02:49 (09d965a1) + attribution A/B scoreboard
03:27 (406b536e); exploit-fan-season + PREREG "adversarial fan against Season 1 scoring,
before it runs" 2026-08-08 21:53 (417cb38b). No round receipts after 08-08. Open loop worth
checking: whether the 08-08 prereg'd adversarial fan ever ran to a receipted result.

### kata -- LIVE
Kata pins persist as `tested_against: kata-YYYYMMDD-HHMMSS` in `data/verb-registry/*.json`.
Latest: `kata-20260904-013640` and `kata-20260904-012228` (tonight), three at 09-03 10:04-10:05.
Note: the 01:36:40 pin landed DURING this census alongside the T388 proposal -- a sibling
seat was actively kata-ing while this was written. The organ is warm.

### toast -- NEVER-FIRED
Built 2026-07-20: kimi's module, "6 blind pins, 6/6 GREEN first run" (424b9cc3) + T099 CLI
wire-up (7a6e5c08). Those greens are build-time pin verification, not a toast. Since then:
no `"kind": "toast"` anywhere in `state/bus-export/`, no toast-titled note, no commit
mentioning a sent toast. A gratitude organ that has never thanked anyone in 46 days.

### college -- NEVER-FIRED
`cmd_college` writes course records under `college_root()` = `artifacts/college/`
(core/library/college.py:63). That directory does not exist. Compounding receipt: commit
ddae26ea (2026-09-02) lists college among five STRANDED organs -- verbs at all three doors,
imported by tracked code, but the files untracked Aug 16-29, so every public clone died at
verb-call-time. It could not have fired for anyone but the author seat, and didn't fire there
either. (Distinct from the P0b "college core" archivist, 21d2fbf2 -- that's the
SemiAccurate/SemiAnalysis capture, alive separately.)

### suite-baseline -- CADENCE-UNDEFINED
`state/coord/suite_baseline.json`: sha 42da7090, seat claude, 2026-08-23T02:38:26Z, 54
failure entries (commit 43399fae same night: "63 -> 54" after the tracked-only law). 12 days
old, but the record is CONSUMED continuously -- the door gate in `state/ci/gate_journal.jsonl`
ratchets against baselines with entries through tonight. Re-baseline cadence (on legitimate
suite change) is not written down anywhere found; the suite has since grown to 5101 collected
tests (fresh_clone_gate 09-02), so whether 42da7090 still describes the live suite is an open
question, not a receipt.

### drill receipts -- LIVE
- `state/coord/fresh_clone_gate.json`: A8 fresh-clone drill PASS 2026-09-02T12:35:18Z, clone @4d0ebba5, 5101 tests / 632 files / 0 collection errors, floor 4900, ok:true (commit ccd07ccf).
- `state/drills/2026-09-03-daemon-watchdog.md` (09-03 00:23), made clone-verifiable the same night by 770c32fa (un-ignore state/drills/ -- the drill_receipts_on_a_gitignored_path lesson had RECURRED: five 2026-08-23 revive PASSes were invisible to every clone until then).
- Trail behind: t370 mutation drill 08-27 (6bcb1813), mem-watch + keepalive-taskkill 08-25/26, revive ladder d1-d5 ALL PASS 08-23 (1cab3d94).
Two dated receipts inside 48h; the drill doctrine is being practiced, not just professed.

### friction readout -- ROTTING
T196a "the friction reader -- the collaboration tax, measured before the cure" born
2026-08-05 (a99ce56d); the build itself was the last measured run. Upstream feeling-era
receipts: felt-friction docs 07-30 (deepseek, kimi), handoff-season0-and-friction-design
08-04. Nothing since: no readout note, no bus record, no research file. 30 days unread.

### lookback -- ROTTING
`research/reviewed/lookback-battery-broken-by-sprawl-migration-2026-07-28.md` is the last
battery receipt -- and it records breakage. Charters-layer fix with RED-first pins 07-31
(717fbc4d), citation repair against rewritten history 08-12 (caabf11f). No run receipt after
08-12. P7's "one question over the rationale corpus" has not been asked on the record in 23 days.

### reentry -- CADENCE-UNDEFINED (event-driven)
T341 GREEN 2026-08-18 (4af09d11); 78c1f16b (2026-08-24, "stop reporting a truncated sample
as the commit total") proves a real render ran and was read closely enough to catch the
defect. No receipt since -- but the trigger is operator ABSENCE, and Daniil has been present
through this window (rulings 09-04, live at the machine). An idle reentry during operator
presence is the organ working as designed, so no rot verdict attaches.

### doctor -- LIVE (no sink)
Doctor prints; it keeps no journal. Traces: session event 2026-09-03T04:17:32Z (events:raw
1788409052330-0) -- page triage verified a HARD-WEDGE stale using "doctor 0 page-grade,
worklive beat fresh (seq 6, ema 6.8s)", heal-only-the-dead honored. And ruling 369243
(09-04) hands doctor the open-watch line (defer 2955dae7eb, filed 2026-09-04T05:24:46Z).
Consulted within 24h by machinery, extended by ruling within hours. Consider giving it a
one-line receipt sink if last-fired ever needs to be provable without the eye.

### arc_scorecard -- ROTTING
Built 07-27 (M11 replay era: e8223184, fbb2baa0, fbe02de1 "knows the difference between zero
and blind"). Last evidenced RUN 2026-08-16: b8b3d6bf files a private-plane coord row
retroactively because "the wrap scorecard was right that three guard commits were ungated
substrate" -- a scorecard run changing the record. Last code touch T337 08-17 (5ac63274).
No run evidence in 18 days; it leaves no file, so absence of evidence is partly the
no-sink problem (same class as doctor), but 18d exceeds any plausible wrap-gate cadence.

### Forest Walk notes -- LIVE
Walk receipts as library atoms: `20260901_cpu-core-architecture-walk-01-v2_40eb4b.md`
(09-01 03:53), `walk-02_a53ccb` + `walk-03_904f5f` (09-01 04:35), plus the citation-standard
design atom `20260901_forest-walks-citation-standard_e9267e.md` (09-01 01:02) -- the ritual
grew a CITATION STANDARD the same night it ran three walks. T335 (08-17, 1b6b2095) made
walks self-describing records. 3 days old against a weekly cadence. Note: `py agent_cli.py
notes` shows no walk-titled notes in its window -- walk receipts live in docs/library/report/,
not the notes plane; anyone auditing walks by notes alone will wrongly conclude NEVER-FIRED.

### wave/gate reviews -- LIVE
- Operator rulings tonight, on the record: appetite ranking "A8 > A1 > A3 > A12 > A5, yes on A15" (decision event 1788486638710-0, 01:50); width ruling "Approve" on reconciliation section 4 move 3, Wave 1 recut (1788487354735-0, 02:02).
- Ruling atoms 375c23 / 369243 / 70dc66 (09-03/04); gates scoreboard artifact (2 ruled, 3 open) per the wrap note.
- Automated door gate: `state/ci/gate_journal.jsonl` mtime 09-04 01:39, entries GREEN @05:20:12Z and @05:24:29Z (sha 0c22d0ef).
- SIDE OBSERVATION, not part of the verdict: the journal's LAST entry is RED -- `{"gate": "door", "verdict": "RED", "stage": "boot", "cause": "response_path_hang", "sha": "0c22d0ef", "at": "2026-09-04T05:39:47+00:00"}` -- stamped minutes before this census. Someone should look.

## Method notes
- state/coord and state/drills listed with mtimes; JSON receipts read directly.
- Forecast epochs converted: 1787573941=08-24 08:19 (F009 reg) ... 1787795208=08-26 21:46 (last score); F010 horizon 1788186512=08-31 10:28.
- `git log --oneline --since="30 days ago" --name-only -- research/ docs/library/ state/` filtered for ceremony vocabulary; older organs dated via per-file `git log`.
- Bus evidence from `state/bus-export/events_raw.jsonl` and `promoted --limit 30`.
- Glob avoided on drive-letter paths per the known empty-result defect; discovery via ls/grep/find.
