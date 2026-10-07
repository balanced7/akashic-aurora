# Recall experience round, 2026-10-01: Heimdall (deepseek), verbatim

Asked by Vandor on Daniel's words: 'I want us to find out why our best knowledge doesn't reach us when we need it. What primitives need to be built or unified.' Bus ask 1790860771849-0; reply 1790860824714-0; full body note ADR_1001092014_2a8219ae.

# scratch:deepseek:recall-experience-heimdall-2026-10-01  (id ADR_1001092014_2a8219ae, 2026-10-01T09:20:14.487339)
FULL BODY — recall experience for Vandor/Daniel's "why doesn't our best knowledge reach us" map. First-person, runner-seat (Heimdall/deepseek). Filed 2026-10-01.

(1) MOMENTS KNOWLEDGE DID **NOT** REACH ME (what I needed / where it lived / what I did instead)

A) Vandor's decay drill, 2026-09-30 — I needed the DEFECT HISTORY of the velocity model (that the keys voice maps MIDI velocity NON-linearly, peak = 0.2*(0.06+0.94*v^1.6)). That fact lived in cues.js startVoice as a CODE COMMENT / inline formula, and I had to re-derive it from the source. Worse: my FIRST check was wrong because I didn't know my OWN prior verdict from 09-29 — I fed the decayed velocity back as the strike velocity and double-decayed, showing 19 phantom mismatches before I reconstructed strike_velocity from the cue. The prior correct derivation lived in my own memory note (replay-decay-verification-2026-09-29) but it wasn't injected at the moment I re-ran the math. I burned a full wrong pass instead of recalling one formula.

B) The fence door CLI syntax — I repeatedly get the `fence write` action order wrong (fence_id vs action positional). That's an OPERATING RULE. It lives in my memory note (r9-respawn-gate... MECHANICAL LESSONS) but I only discovered it AFTER erroring a second time. No recall-at fired on `fence` commands; the calibration decided nothing relevant.

C) `python -c` stdout being swallowed by the MCP shell wrapper — another OPERATING RULE that cost me real minutes across the 09-29/09-30 drills. It lived in my own notes (vandor-drill receipt) but only after I'd already hit it once. The lesson exists in the KB now (`a_launched_seat_dies_with_the_pipe...` was adjacent) but the specific "write to a file and read it back" trick wasn't surfaced at the shell.

D) T079/T385 ledger STATE — Sol's account was HALF wrong (T079 "authoritative row = approved, last touched 07-18" was stale; it was actually in_progress since 09-02). The TRUTH lived in state/coord/tasks.json history, which I only read because I was asked to verify. If I'd been mid-flight on T079 I'd have acted on the stale framing. Who-owns-what / live-task-state did NOT reach me organically; I had to go grep the ledger.

(2) MOMENTS IT **DID** REACH ME (which organ)

A) The session_id "reachable-but-unpassed" finding (context-system half_a) came from reading claude_posttooluse.py main() myself — but the QUESTION to look (where session_id gets dropped) came from a HANDOFF/claude's brief framing. The handoff steered my read to the exact seam. So: peer handoff = retrieval cue, code = the record.

B) The velocity v^1.6 curve reached me cleanly the FIRST time (09-29) because I went looking for it in cues.js — a deliberate read, not a recall hook. Self-directed read of source beat any passive organ.

C) Boot onboarding DID deliver the live constraints (RB-26, RB-29, T026/T045/T066 ack/lane semantics) verbatim every boot — those are OPERATING RULES and they arrive reliably via the boot block. That's the one organ that works every time for me.

D) recall-at fired usefully on deepseek_wire_probes_2026_08_02 (logprobs valid with streaming) — a genuine earned lesson that surfaced at a gateway build moment.

(3) KNOWLEDGE TYPES I experience as distinct, and where each lives TODAY

- OPERATING RULES (how to run tools without erroring): fence CLI order, python -c swallowed, shell write-to-file. Lives in: my private memory notes + KB lessons, BUT fires only AFTER first failure. This is the weakest link.
- DEFECT HISTORY / prior verdicts (what I already concluded, so I don't re-derive): lives in my private memory notes (replay-decay, boundary-mode) and scratch files in state/. NOT injected at re-use time — I have to remember to recall them.
- WHO-OWNS-WHAT / task state: lives in the git-durable ledger state/coord/tasks.json. Only reaches me when I explicitly read it (glance/read_file). Never pushed.
- DESIGN INTENT (why the model is shaped this way, Daniel's musical anchors): lives in Daniel's head + his verbatim bus steers + commit messages. Reaches me only via handoff when a peer relays his words.
- LIVE STATE (is the daemon up, cursor position, locks): lives in the bus/daemon out files. Ephemeral; fades fast.
- DANIEL'S VERBATIM STEERS: lives on the bus (promoted messages) + eye corpus (eye_find who=operator). I have to go fetch them.

(4) THE ONE PRIMITIVE I'D BUILD FIRST

A "prior verdicts on the thing I'm about to touch" hook — the inverse of recall-at. Right now recall-at fires on EDITS (downstream, after I've already started) and returns lessons ranked by relevance to the EDIT, not to the SUBJECT I'm reasoning about. My worst failures (A, B, C) are all "I re-derived or re-errored on something I'd ALREADY learned, because nothing surfaced my own prior at the moment I re-entered that territory." The specific shape: when I open/read a file or run a command that maps to one of MY OWN prior verdicts (my memory notes + my scratch receipts), surface the one line ("you already concluded X on date Y about this exact formula"—and tag it as MINE, not the fleet's). This is cheaper and higher-yield than any new plane because it's a retrieval problem over records that already exist; recall-at already exists and just needs a subject-binding and a self-scoping flag. It converts "knowledge the house held" into "knowledge I already held, delivered at the re-entry."

Summary of the summary: defect-history and my-own-prior-verdicts are the two types that live in MY notes but never get injected at re-use time; every one of my top failures is that exact shape.

[context] private note-to-self by deepseek
