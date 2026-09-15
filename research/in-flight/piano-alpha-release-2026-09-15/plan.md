# Piano alpha release: plan

*Conductor: Vandor. Evidence: [census.md](census.md), read-only, with file:line citations. Status: DRAFT until Daniel answers the five questions at the bottom. Phases A0 and A1 are needed under every answer, so they can start now.*

## The ask, in Daniel's words

> "Lets see if we can't package what we have into an alpha release that is designed to work with any midi keyboard or midi USB adapter! Hopefully a single click install with instructions on how to integrate their preferred flavor of Ai assistant!"

## Where we stand

The census says we are closer than it looks:

- **MIDI.** Web MIDI in Chrome and Edge already talks to any class-compliant USB keyboard or MIDI adapter. Hot-plug, velocity-0 note-offs, sustain and panic all work.
- **Server.** It runs on the Python standard library alone.
- **Chord detection.** Chord, key, Nashville and key-signature detection all run in the browser.
- **Assets.** There are no audio, image or 3D model files to license. Everything is synthesized or built in code.
- **Assistant hook.** A generic REST route already lets any local program play and hover notes on the page (`POST /api/piano/cue`).

What stands between that and a stranger's double-click:

1. **Security.** The local server trusts any web page on some routes: no Origin check on practice-log POSTs, no Host check anywhere.
2. **State location.** State lives next to the code, which breaks any installer and writes into the install folder.
3. **KeyLab-shaped defaults.** The copy and the automatic device choice assume Daniel's board. All 16 channels are merged, with no pedal-polarity invert.
4. **Hidden status and online-only assets.** The MIDI status is hidden in the HUD. three and the fonts come from CDNs.
5. **Assistant integration gaps.** There is no live chord feed for assistants and no MCP server. The naming verbs need Node.
6. **House surfaces.** Conversation cards, probe seats and "Daniel" and "Claude" addressing are still in the UI.

## Decisions (Vandor, as driver)

- **Accept the census MUST list**, with three adjustments:
  - **House surfaces go behind a profile flag, not deleted.** Add `ARSENAL_PROFILE=alpha` (default `house`), which hides house-only surfaces and neutral-names the assistant and user. Nothing is removed from the house build.
  - **State root becomes configurable, with the house default unchanged.** `ARSENAL_STATE` sets it, and so does the per-user default in the alpha profile. `state/arsenal/...` stays where it is here, so no path moves under Daniel's feet.
  - **Security hardening lands for the house too.** The Origin and Host checks protect Daniel's machine today, not only strangers'.
- **Node: bundle a portable Node in the Windows alpha zip** rather than port the voicing bridge. About 30 MB buys every assistant verb working on day one; a Python or in-browser path can come later. Fetching the Node and embedded-Python archives at build time needs Daniel's OK.
- **The assistant kit is MUST, not SHOULD.** It is a third of the ask. The alpha ships:
  - a small stdlib-only stdio MCP server (`piano-mcp`);
  - templates for Claude Code, Codex, Cursor and Gemini;
  - a copy-paste prompt for ChatGPT and local models;
  - a REST doc;
  - a read route for the open session's recent chords, key and Nashville numbers.
- **Every phase ships with a drill**, per the drill doctrine. The alpha is not called ready until a clean-machine drill passes: a fresh folder at a new path, no Python or Node on PATH, a different Windows user profile, receipts dated.

## Phases

| Phase | What | Needs Daniel's answer? | Verification |
|---|---|---|---|
| **A0 House-safe hardening** | Origin and Host checks on every POST and private GET (with a 403 test page); `ARSENAL_STATE` state root; configurable `/` redirect; `.woff2` static type; the `ARSENAL_PROFILE` flag plumbing | no | pytest for each route, including a DNS-rebinding Host test and a `text/plain` cross-origin POST; the house run is unchanged (jam_verify A-lanes, classic frame hashes) |
| **A1 Any-keyboard MIDI** | MIDI status in the top bar; browser banners (Safari none, Firefox add-on, permission denied); deterministic device choice (hardware first, remembered by name); channel selector (omni) plus an ignore-channel-10 toggle; sustain-polarity invert; neutral copy in the alpha profile; a MIDI diagnostics panel | no | fixture MIDI streams (49- and 61-key ranges, channel 10 pads, inverted pedal, two devices hot-plugged) driven through the page's `midiMessage`; screenshots of each banner |
| **A2 Offline and privacy** | Vendor three r186 plus addons, Bravura and the chosen fonts; `THIRD-PARTY-NOTICES`; practice-log first-run notice plus "delete my practice data" button | vendoring needs a download OK | the page loads with the network blocked (headless, offline); licence notices diffed against what ships |
| **A3 Assistant kit** | `piano-mcp` (stdlib JSON-RPC stdio) with tools `status`, `now`, `sessions`, `brief`, `play`, `hover`, `progression`, `clear`; `GET /api/piano/now`; templates (CLAUDE.md, AGENTS.md, .cursor/rules, GEMINI.md), a copy-paste prompt, REST.md | Q1 | an MCP conformance smoke test (initialize, tools/list, each tool call) against a running server; each template tried with at least Claude Code and Codex |
| **A4 Package** | Allowlist export script producing the slim alpha folder or repo; `Start Piano.cmd` (embedded Python 3.11 plus portable Node, opens Edge `--app=http://127.0.0.1:8793/piano`); README (install, SmartScreen "unblock", supported browsers and keyboards, assistant setup) | Q3, Q5 | the export has zero files outside the allowlist; privacy grep (emails, names, session ids, state/); zip size |
| **A5 Clean-machine drill** | Unzip to a new path on a second Windows profile; no Python or Node on PATH; double-click; a real keyboard (Daniel's KeyLab, then any other MIDI device he has); connect one assistant from the README only | Daniel plays | a dated receipt: time from download to first note, every error seen, the assistant's first successful `play` |

**Suggested house split** (all through the bus, Vandor commits):
- Heimdall: A0 server hardening and state root, fenced with Vandor.
- Navi: A1 MIDI UX.
- Sunshine: README, assistant prompts and templates copy.
- Vandor: A3 `piano-mcp`, A4 export and launcher, drills.
- Asta: presentation polish of the first-run screens, if he is available.

## Running order after this plan

1. Final heat results, and Daniel picks the Synthesia look.
2. A0 and A1, which start without waiting on answers.
3. Daniel's answers unblock A2 to A4.
4. LS6 sheet music in /piano continues in parallel once A0 lands, because both touch piano.js and serve.py. Sequence the locks.

## Questions for Daniel (recommended default first)

1. **What ships in alpha-1?** *Recommended:* the 3D visualizer, every scheme and instrument, chord and Nashville reading, REC, the practice log, and the assistant kit (assistant can play, hover, progression and read your session). The jam band, deck and conversation cards stay behind a "labs" switch until later.
2. **Practice log for other people: on or off by default?** *Recommended:* on, stored only on their computer, with a first-run notice and a one-click "delete my practice data". It is what makes the assistant useful.
3. **First platform.** *Recommended:* Windows first, as an unsigned portable zip that opens Edge as an app window, with clear SmartScreen steps. Mac users run from source with Chrome until an Apple developer account ($99/yr) is approved. Consider a signed Electron build at beta.
4. **The KeyLab 88 mk3 model.** *Recommended:* keep it, but call it something generic in the menu (e.g. "88-key studio controller") and mention in the README that it was inspired by your own board. The real product name is Arturia's trademark.
5. **Where the alpha lives.** *Recommended:* a new slim public repo produced by an export script from this one, so people never download the whole house and private state can never leak by accident.

Also needed when A2/A4 start: your OK to download the Windows embeddable Python 3.11 zip, a portable Node LTS zip, and the three r186 plus font files for vendoring.
