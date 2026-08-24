# The address dialects of Akashic Aurora — a census of the fracture class

Vandor, 2026-08-18, under Daniil's standing order for this session ("go where your curiosity and
intuition are stirring"). Companion to Heimdall's name-collision scan (bus 1786986442669-0, unanswered
until now) — that scan found the fracture at the HUMAN layer; this census maps it at the MACHINE layer.

## The claim

The house speaks at least ELEVEN identifier dialects. Nearly every organ resolves exactly one and
renders every other as nonexistence — and because absence-rendering is how organs report, each
dialect boundary is a place where a TRUE citation reads as a FALSE claim. Five live receipts in 36
hours, four of them costing real verdicts.

## The census (form → producer → resolver → fracture receipt)

| # | Form | Example | Produced by | Resolved by | Fracture receipt |
|---|---|---|---|---|---|
| 1 | full session uuid | `51589003-e8b5-...baa` | harness JSONL filenames | eye (all verbs) | — |
| 2 | sid8 (short session) | `session ed728d23` | boot, handoffs, `--to-incarnation` | **nothing, until T361** (now: eye get) | eye get called Navi's exact citations "no event" — a peer's verified evidence nearly read as fabricated (2026-08-17) |
| 3 | seat incarnation | `claude#fe21e40d` | roster.heartbeat (seats) | roster, doctor | — |
| 4 | runner incarnation | `deepseek#23444-de` | bifrost runners (pid-suffix) | roster; doctor **misparsed until T347** | `"#" in agent` handed runners the seat privilege → idle runner rendered "genuinely working" (2026-08-17) |
| 5 | bare agent id | `deepseek` | daemon, mailbox, L1 worklive | most comm organs | doctor's ABSENT-vs-RETIRED conflation (T329, open) is this form's verdict spent on the mail |
| 6 | ledger row id | `T347` | task registry | task/conductor, boot | ids minted mid-pollution interleaved real and phantom rows (T346/T347/T348, cleaned under T352) |
| 7 | eye event address | `<session>:<line>` | eye find/freq | eye get | dialect-2 collision above — same address grammar, two session spellings |
| 8 | bus stream id | `1787027825036-0` | Redis streams | bifrost-fetch, events --get | dual-write era: same message, two stream ids; dedupe by sha, never by stream id (T039a law — the fracture was LEGISLATED around rather than closed) |
| 9 | blob ref | `blob:85131d39...` | T338 spill path | bifrost-fetch only | a blob ref cited anywhere else (notes, ledger) resolves nowhere |
| 10 | note/ADR id | `ADR_0818003653_5b9d1912` | note store | notes --get (also by TITLE — two key forms for one store) | title-vs-id duality is a within-organ dialect split |
| 11 | lesson key | `learn:experiment:<name>` | learning store | recall --full | recall-at prints them; eye/notes/task cannot follow them |

Plus the human layer (Heimdall's scan, Species A): **callsign vs vendor id** — "Deepseek, Onix, Blue,
1- Callsign" vs "seats like you Vandor, Heimdall and Navi", both from Daniil's own mouth, because the
UI teaches one dialect and the fleet speaks another. And **"cursor" triple-loaded** (vendor / machine /
transport-position-as-handled-flag), its highest-cost single name.

## What makes this ONE class and not eleven quirks

Every fracture has the same anatomy: an identifier crosses an organ boundary in a dialect the
receiving organ does not parse, and the organ's failure mode is an ABSENCE VERDICT rather than a
form refusal. T176's law ("absence must never read as a decision") keeps being applied organ by
organ — T340 (read_file), T347 (doctor), T361 (eye get) — because the CLASS lives at every boundary
while the fixes land at single doors.

## What I am NOT proposing

A universal id scheme. That is the kind of rewrite this house correctly refuses (strangler fig,
never big-bang), and dialect diversity is partly load-bearing (stream ids are Redis's, uuids are
the harness's — we do not own every producer).

## What ships if Daniil approves (proposed as a row)

A RESOLVER REGISTRY, one door: `resolve <token>` — given any of the eleven forms, name the form,
name the owning organ, and hand back the canonical address + the drill command that dereferences
it. Refusals name the form they could not parse ("looks like a sid8 but matches 3 sessions: ...")
— never "not found". The registry is also the CENSUS made executable: a new dialect must register
or its tokens render as UNKNOWN-FORM, which is the honest state. Every organ keeps its own dialect;
the seam gets one translator. (kinds.py precedent, T176 s1: the registry proposes, it does not pick
winners.)

Cheap first slice: the seven forms we own end-to-end (2,3,4,6,7,10,11). Second slice: check_wiring
gains a rule — an organ printing an id form no resolver claims is a NAMES-THAT-LIE finding.
