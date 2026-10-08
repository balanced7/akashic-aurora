---
akashic_id: art_20261007_second-press-gentle-hints_db25d1
akashic_sha: bf78b9fcada1
schema_version: 1
status: current
type: design
arc: ergonomics
date: 2026-10-07
title: second-press-gentle-hints
gist: "The second press is a question: escalating, layer-naming hints that leave on success -- piano Rescan first, then the house's own surfaces"
visibility: fleet
body_type: markdown
seats: [claude]
category: [frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-07T21:25:18"
updated: "2026-10-07T21:25:18"
---
<!-- GENERATED PROJECTION of art_20261007_second-press-gentle-hints_db25d1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# second-press-gentle-hints

# The second press is a question

Status: design, co-designed live 2026-10-07 evening (Daniel + Vandor). Nothing is built yet.

## Where it came from

Daniel's KeyLab vanished from /piano in Brave, and Rescan did nothing. His first idea, verbatim:
"if a service is stopped perhaps rescan can have routines to relaunch it".

The walk down the stack found no stopped service. The USB device was OK, midisrv was running, and
Windows' MIDI 1.0 layer (WinMM) listed and opened both KeyLab ports alongside FL Studio. The KeyLab
reconnected at 21:09:48, while Brave had been running since 21:16 the night before. A fresh
headless Brave with a throwaway profile saw "KeyLab 88 mk3 MIDI [connected]" at once. Daniel
relaunched Brave and it worked. Rescan only re-reads the tab's existing MIDIAccess
(arsenal/web/piano.js refreshMidiInputs), so it could never have seen the keyboard.

Then Daniel, verbatim: "I was thinking of adding a gentle hint that pops up if a user presses the
rescan multiple times, or if the user presses it and there are no notes detected. something about
that kind of ui design really appeals to me"

And: "I love it! can you save it please? I am wondering how we can apply this principle to our own
ergonomics and interaction surfaces?"

## The principle

The first press is a command ("look again"). The second press is a question ("why didn't that
work?"). The third is a sigh. An interface that answers all three the same way leaves the person
pressing into the void. UX analytics calls the far end "rage clicks" and mostly studies them after
the fact. This design answers in the moment.

A good answer to the question:

- **Fires on strong signals only.** Examples: a repeat of the same action, a scan that finds
  nothing, a retry after a failure. Never a guess at intent from weak evidence (Clippy's "It looks
  like you're writing a letter").
- **Names the layer where the signal stops**, and offers one action for that layer.
- **Sits beside the thing pressed**, never over the work, never during a recording, never in a
  capture.
- **Escalates gently:** whisper, then specific, then the full picture. It is shown once per cause
  per session.
- **Leaves on success.** The moment the problem resolves, it turns into a small "There it is" and
  fades. Help you must dismiss feels like paperwork.
- **Can remember.** "Last time this happened, restarting Brave fixed it."

Prior art worth borrowing: New Super Mario Bros. Wii offers the Super Guide after eight deaths at
the same spot (noticed, offered, never forced). Professor Layton's tiered hint coins let the player
choose how much help they get.

## The piano Rescan hint (first design)

1. **Press 1:** rescan, as today.
2. **Press 2, or a scan that finds no keyboard:** a soft hint beside the button.
   - If the server can say what Windows sees, the hint names the layer. Example: "Your KeyLab is
     plugged in (Windows sees it), but Brave's list of MIDI devices is out of date. Restart Brave;
     brave://restart brings your tabs back." If Windows sees nothing, it says to check the cable and
     power.
   - If midisrv is stopped, the server tries to start it. Whether serve.py has the rights to do this
     is untested.
3. **Keyboard connected but silent:** the hint becomes a sound check. "Play any key, I'm listening."
   The key lights up with "Heard you", or after a few seconds the hint moves to the next rung.
4. **The signal chain view:** keyboard, USB, Windows MIDI service, Windows device list, Brave, this
   tab. Nodes light along the path, and the dim node is where the signal stops. It works like a
   routing view in FL.

Pieces needed:
- a read-only server endpoint that enumerates WinMM ports (ctypes, as in tonight's probe) and
  reports midisrv state;
- a small page module holding a pure decide() (testable with node --test) plus its render;
- a host hook on btn-midi.

The workbench.js move list must learn any new topbar control. serve.py changes need a server restart,
which is Daniel's call while his session is live.

## Applied to the house (first pass, Vandor, open for play)

1. **Recall-at-action speaks differently on the second press.** A retry after a failure is the
   strongest "I'm stuck" signal an agent gives. The 2026-10-06 credit-join work already joins a fixed
   command to its earlier failure, so that join is the detector. A retry would get a louder, more
   specific hint; first attempts stay quiet. Tonight, recall offered fence-verdict lessons while I
   probed MIDI ports: the weak-signal end of the same dial.
2. **A repeated whisper must change or go quiet.** "58 unread bus msg(s)" appeared identically on
   every turn tonight, and I treated it like a Rescan that does nothing. The boot reminder was the
   same. WISHLIST 2026-10-07 "the boot reminder is a whisper" is this ladder: whisper, then bounce
   once with the exact command. A repeat should get more specific instead, for example "3 of the 58
   are handoffs addressed to you, oldest 2 days".
3. **Doors answer "did you mean".** Tonight `recall ... --limit 3` dumped about 150 verb names. recall
   has no --limit; recall-at does. A gentle door names the nearest flag or verb.
4. **Organs that see must speak at the moment.** mem_watch has been writing "WARN host commit 85.7%"
   to a file every five minutes. It runs windowless (pyw), so its warnings reach no one. At 01:24 UTC
   on 2026-10-08, nonpaged pool was 10.0 GB (6.5 GB at the 2026-09-11 outage) and paged pool was
   23.4 GB (12.8 GB then). The pool tag "File" held 4.1 GB, up about 600 MB in 27 hours. A hint that
   crosses the outage line and names the layer would reach Daniel before the house falls over.
5. **"Nothing happened" gets a signal chain.** The same shape recurs:
   - piano: keyboard, USB, Windows MIDI, browser, tab;
   - fleet: Discord, gateway, bus, daemon, runner, model;
   - the 09-11 outage: kernel pool, WSL relay, Docker, Redis.

   One reusable view: show the chain, dim the node where the signal stops, offer one action.
6. **A receipt on success.** `learn` printed nothing tonight, and I had to query to confirm the
   lesson had landed. "There it is" is the success half of the same design.
7. **When the human asks twice.** The house already learned this once
   (learn:experiment:the_operator_re_asked_a_question_the_house_had_already_answered_in_full). A
   repeated question from Daniel is the second press, and the answer is "we decided this on <date>,
   here it is; what has changed?"

## Next

Daniel picks which surface to prototype first. The piano hint is self-contained and visible tonight.
The mem_watch voice protects the house. Recall's second-press mode carries the most leverage.
