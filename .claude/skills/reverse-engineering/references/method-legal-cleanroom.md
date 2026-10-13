# Method, legal map and clean room — the operator's guide

The shared spine under every other playbook: the discipline, the legal ground, the clean-room
protocol, and host safety. Distilled from `research/reviewed/reverse-engineering-2026-10-13/` —
`house-inventory.md` (the discipline table, the gap list) and the legal/clean-room sections of
`teardown-toolkit-and-practice.md`, `software-binaries.md` and the others. **Not legal advice.**

## The discipline (the skill is the notebook, not the disassembler)

Three kinds of evidence, kept apart in every note:

- **Observation** — a tool or a person directly saw it, reproducible from the same input
  ("bytes 0–3 are `52 49 46 46`"). Gets an evidence ID, not a likelihood.
- **Inference** — a conclusion from observations plus assumptions ("so it is a RIFF container").
  Names the observations it rests on, how likely it is on one fixed scale, and how much confidence
  its basis deserves.
- **Unknown** — a question not yet answered ("what happens above level 60?"). A finding too: it tells
  the next person where the map ends.

A **likelihood scale** so readers do not guess (ICD 203's expressions of likelihood, descended from
Sherman Kent's estimative words): almost no chance (1–5%), very unlikely (5–20%), unlikely (20–45%),
roughly even chance (45–55%), likely (55–80%), very likely (80–95%), almost certain (95–99%). These
words say how probable a judgment is. They are not a confidence scale: ICD 203 keeps them apart from
**analytic confidence** (low / moderate / high: how good the sources and reasoning behind the
judgment are) and advises against putting the two in one sentence. A ledger's Confidence column
gives both, each stated on its own ("likely" and "moderate confidence").

**The search boundary** fences every negative: "no network calls found in the 412 functions Ghidra
identified, searching 6 API names, in build sha256 abc…" — never "there are none." Drill B in the
practice report is the cautionary tale: a model exact on levels 1–10 was 2.7× wrong at level 40
because a soft cap at level 25 lay outside the searched range.

**Observed behaviour vs design choice** when rebuilding: "the file has to parse / the error has to
return / the jump has to feel like the reference" (required) stays apart from "variable names, code
structure, exact numbers not forced by compatibility" (design, free to differ). *NEC v. Intel*
proved the point: an independent engineer (Gary Davidian) who saw neither side wrote microcode
similar in the same places, showing those similarities were dictated by the hardware, not copied.

**Never infer behaviour from a name.** A function called `Encrypt` may only copy bytes; a file called
`config.json` may be ignored; a preset called "Hall" tells you its name, not its reverb. A finding
earns OBSERVED only from a falsifiable check (the declared chunk length lands on the next record; the
byte-rate equals rate×channels×bits/8; the parser re-derives the length exactly).

The house already does this per subsystem: fence verdict tags (CERTAIN/DESIGN/INFERRED/UNCERTAIN),
`ask --preset findings` (FINDINGS/REASONING/CHECK/BLIND), every `arsenal.media` result's `blind`
field, `eye trace` edges labelled recorded/derived/inferred, `forecast`'s mandatory "dies when",
`tests/test_find_bounded_is_not_absent.py` (an unsearched space is not an empty one).

## The method, step by step

1. Permission and scope first; read the EULA/terms; unclear → ask Daniel; never pick an example on
   the user's behalf.
2. Write the question checklist, each question beside the evidence that would answer it.
3. Fingerprint the target: SHA-256, size, version, provenance, tool versions.
4. Route the target to its first tool from *what it is*; start summary-first (inventory before drill).
5. Static before dynamic; dynamic triggers the VM rule and the legal rule.
6. Register a prediction, then look; score it (ties to the house `forecast` registry).
7. Follow one question from entry to result; batch checks around one hypothesis; widen only on a
   concrete gap.
8. Inspect resources and configuration alongside code; never infer behaviour from a name.
9. Corroborate with the evidence type the claim needs.
10. Do not repeat an identical analysis without a changed input (cache by content hash).
11. Ledger every finding (claim, O/I/U, evidence IDs, likelihood and confidence, boundary, what would
    change your mind); revisit the checklist; mark each question answered / partial / unresolved.
12. When rebuilding, write the spec with required behaviour and design choices in separate sections.

### Note formats (plain Markdown so any seat writes them and any generator parses them)

- **Question checklist:** `| Q | Question | Evidence that would answer it | Status |` — status ∈
  open / answered / partial / unresolved(bounded: …).
- **Evidence register:** `| E-ID | Artifact (sha256/12) | Tool + version | Exact input/command |
  Output kept at | When / who |`.
- **Finding ledger:** `| F-ID | Claim | Kind (O/I/U) | Evidence | Confidence | Search boundary |
  Would change my mind if… |`.
- **Behaviour spec (crosses the clean-room wall):** RFC 2119 words (MUST/SHOULD/MAY), each
  requirement with its evidence and a test vector; the strongest form is conformance tests (Wine's
  suite passes on real Windows first, so the tests *are* the description).
- **Report (ICD 203 habits):** bottom line first; judgments with confidence; alternatives considered
  (an ACH grid — hypotheses across, evidence down, keep the hypothesis with the fewest
  inconsistencies); how it changes earlier findings; source quality visible; what was *not* looked at
  (the boundary) and how to reproduce.

## The legal map (jurisdiction-aware; not legal advice; dated 2026-10-13)

The shape of the law so the house knows when to stop and ask a lawyer. Reverse engineering for
understanding, interoperability and analysing what you own is broadly lawful in the US and EU; the
traps are DRM circumvention, contract terms, and copying expression.

**United States**
- *Interoperability can be fair use.* **Sega v. Accolade**, 977 F.2d 1510 (9th Cir. 1992): disassembly
  is fair use when it is the only way to reach unprotected functional elements and there is a
  legitimate reason. **Sony v. Connectix**, 203 F.3d 596 (9th Cir. 2000): intermediate copying of the
  PlayStation BIOS to build an emulator was fair use, "modestly transformative." **Atari v. Nintendo**
  (Fed. Cir. 1992): how you obtained the copy matters — Atari's deception defeated its defence.
- *DMCA §1201* (17 U.S.C. 1201) bans circumventing a technological measure that controls access to a
  work (§1201(a)(1)(A)) and trafficking in circumvention tools (§1201(a)(2), (b)). Whether a
  violation needs a link to infringement depends on the circuit: the Ninth Circuit declined to require
  an "infringement nexus" (*MDY v. Blizzard*, 629 F.3d 928, 9th Cir. 2010), while the Federal Circuit
  requires one (*Chamberlain v. Skylink*, 381 F.3d 1178, Fed. Cir. 2004). Plan as if circumvention is
  unlawful on its own. Statutory exemptions: **§1201(f)** interoperability of an independently created
  program; **§1201(g)** encryption research; **§1201(j)** security testing with authorisation. The
  triennial exemptions in **37 C.F.R. §201.40** (current rule effective 2024-10-28) excuse only the
  *act* of circumvention under §1201(a)(1)(A), never trafficking in tools, and each applies only under
  the conditions in its own text: (b)(18) good-faith security research, (b)(15) diagnosis, maintenance
  and repair, and (b)(19) video games whose outside server support has ended. Within (b)(19),
  (i)(A) lets an individual restore personal, local play of a lawfully acquired copy; the preservation
  parts ((i)(B), (ii), (iii)) are for eligible libraries, archives and museums only. Read the
  paragraph itself before relying on any exemption. **This is the line the house does not cross or
  teach across.**
- *Contracts can take away fair use.* **Bowers v. Baystate** (Fed. Cir. 2003) and **Davidson v. Jung**
  (8th Cir. 2005, the bnetd case): a EULA/TOS no-reverse-engineering clause can be enforced. Read the
  EULA before any code-level teardown of something bought.
- *Online games.* **MDY v. Blizzard** (9th Cir. 2010): a bot evading Warden violated §1201. **Van
  Buren v. United States** (U.S. Supreme Court, 2021) read the CFAA's "exceeds authorized access" as
  a gates-up-or-down test, but its footnote 8 left open whether the gates must be technological or
  can also be contract or policy limits — so whether breaking a game's terms of service can count as
  unauthorised access is unsettled. We do not touch live online-game protections, clients or traffic.
- *Trade secrets.* 18 U.S.C. §1839(6)(B) excludes reverse engineering of a lawfully obtained product
  from "improper means" — but a contract can still forbid it, and breaching an NDA is improper.

**European Union (often more permissive for software; the core study and interoperability rights
cannot be waived by contract, with the exception noted below)**
- *Software Directive 2009/24/EC.* Art. 5(3): a lawful user may observe, study and test a program to
  find its ideas and principles. Art. 6: decompilation only for interoperability of an independently
  created program, by a lawful user, limited to necessary parts, and the information may not be used
  to build a program "substantially similar in its expression". **Art. 8: contract terms contrary to
  art. 6 or to art. 5(2)–(3) are null and void.**
- *The exception:* art. 5(1) (acts necessary for the lawful acquirer to use the program, including
  error correction) applies "in the absence of specific contractual provisions" and is not on art. 8's
  list, so a contract can shape it. **Top System** (C-13/20, 2021): a lawful acquirer may decompile to
  correct errors under art. 5(1), subject to that contractual caveat.
- **CJEU SAS v. World Programming** (C-406/10, 2012): functionality, programming language and data
  file formats are not protected.
- *Trade Secrets Directive 2016/943* art. 3(1)(b): observing, studying, disassembling or testing a
  lawfully acquired product is lawful acquisition, absent a contrary contract.

**UK:** CDPA 1988 ss. 50B (decompilation), 50BA (observe/study/test), 296A (contrary terms void).
**Canada:** Copyright Act ss. 41.12 (interoperability) and 41.121 (maintenance/repair).

**Game assets vs mechanics (the basis for clean-room game-building; US law).** 17 U.S.C. 102(b)
excludes any idea, procedure, process, system or method of operation from copyright. The Copyright
Office applies that to games on its games registration page (copyright.gov/register/tx-games.html):
the idea for a game, its name or title, and its method of play are not protected, but the **text of
the rules** and the artwork can be registered — so the method of play is free, while rule *text*,
art, audio, audiovisual expression and code are protectable. (Circular 33, "Works Not Protected by
Copyright", restates the general exclusions and does not discuss games.) **Feist v. Rural** (1991):
in the US, facts — numbers you observe — are not copyrightable, and a compilation is protected only
in its original selection and arrangement. **Caveat on republishing facts:** in the EU the database
right (Directive 96/9/EC) can protect a substantial extraction from a database built with
substantial investment, so a table of extracted values can be protected even when each fact is
free; and community wiki tables carry their own licence (Fandom text is CC BY-SA), so republishing
one brings attribution and share-alike duties. Measuring is fine; republishing someone's table is a
separate question. **Tetris Holding v. Xio** (D.N.J. 2012): the game's rules and functional elements
were free to copy, but copying the specific
visual expression (piece shapes and colours, board dimensions, ghost piece, garbage lines, the
overall look) infringed, and was trade-dress infringement too. **Spry Fox v. LOLApps** (W.D. Wash.
2012): a reskinned clone of the *expression* survived dismissal and settled. Both courts looked at
what was copied taken together, so check distance against the whole combination of borrowed
elements, not one element at a time. Mechanics can also be **patented** (Warner's Nemesis system,
US 10,926,179 B2) — rare and narrow, but run a patent search on any distinctive, recent mechanic
before shipping.

**Media-specific extras** (audio): two copyrights in a song — composition and sound recording;
17 U.S.C. 114(b) lets you re-make a sound from scratch without copying the recording, but not the
composition. Sampling law is unsettled: in the US the circuits split — *Bridgeport v. Dimension
Films* (6th Cir. 2005) allows no de minimis defence for sound recordings, *VMG Salsoul v. Ciccone*
(9th Cir. 2016) applies one; in the EU *Pelham* (C-476/17, 2019) makes even a very short sample a
reproduction if it is recognisable to the ear, and *Pelham II* (C-590/23, Grand Chamber, 14 April
2026) defines the pastiche exception (it is not authority that a licence is always needed). In
practice the industry clears samples, and the house does not sample recordings it does not own or
license (`research/reviewed/reverse-engineering-2026-10-13/audio-music.md` §10.2). Imitating an
identifiable voice raises publicity rights (Midler, Waits, the Tennessee ELVIS Act). Radio: receive
publicly accessible transmissions, never intercept private/cellular/encrypted traffic (18 U.S.C.
2511; UK WTA 2006 s.48), never transmit without a licence or outside a device's certification.

**Open-source licences are terms too.** GPL code is study material; copying it into a closed product
brings GPL duties. AGPL reaches network use. CC BY-NC-SA (most of the shader corpus, Shadertoy's
default) forbids commercial use. Model weights often carry a different licence from the code (umxl,
madmom, Essentia non-commercial; Demucs weights unverified). "Study only" means study only.

**Tool policies.** RenderDoc is for debugging your own programs; its author declines to discuss
captures of software you did not create. IDA Free / Binary Ninja free tiers are non-commercial.
A future commercial game needs commercial licences or Ghidra (Apache-2.0).

## The clean room (the lawful way to build on what you learn)

Roles (from the Phoenix BIOS and *NEC v. Intel* record, Contreras/Handley/Yang 1990):

| Role | Sees the original? | Produces | Must never |
|---|---|---|---|
| Analyst (dirty) | Yes | Observations, the finding ledger | Write any of the new implementation |
| Spec writer | Yes | Functional specification + conformance tests, neutral words, no code/assets/verbatim text | Paste code, decompiler output or assets into the spec |
| Monitor / reviewer | Reads what crosses (Daniel, who has also seen the original, or a seat that is not the document's author) | Reviews each crossing for expression, approves or strips it; keeps the log | Review a document they wrote; let expression (not behaviour) cross |
| Implementer (clean) | **Never** | The new thing, from the spec only | Look at the original, its decompilation, leaks or "helpful snippets" |
| Verifier | Behaviour only | Pass/fail per conformance test to the implementer; failing test vectors go to the monitor, who decides whether they cross as a spec amendment | Hand a test vector or any other detail straight to the implementer |
| Record keeper | Logs only | The taint register (who saw what, when) | Lose a record |

### House isolation (this host: a fresh session is not a separate room)

On this machine every session in or near the repo receives shared context it did not ask for: `boot`
surfaces lessons, handoffs and unread Bifrost mail; the SessionStart whisper, plan-time recall and
recall-at-action hooks inject lessons automatically (AGENTS.md: recall-at-action is automatic for any
session cwd); the auto-memory (`%USERPROFILE%\.claude\memory\`, one folder for every session, named by
`autoMemoryDirectory` in the user-level settings) loads its index into the first turn of every Claude
session wherever it was launched, and the harness can write to it in the background; the harness can
list and message other local Claude sessions; and the SessionEnd hook folds each session into a
shared `session_signals` event while transcripts are archived. So "separate sessions are separate
rooms" is false here unless it is made true. The rules:

1. **Dirty-side material lives only in the private case folder `state/re/<case>/`.** Findings, the
   ledger, recordings, decompiler output, spec drafts and notes go there (`state/*` is gitignored;
   confirm with `git check-ignore -v state/re/<case>/<file>`). Never in `learn`, `note`, `handoff`,
   `log`, the Bifrost bus, the auto-memory, `chronicles/`, a commit message (the repo is public, and
   `boot` shows recent commit subjects to every seat), a message to another Claude session, or any
   tracked file (`fences/`, `research/`, `docs/`, `.claude/`, `tests/`, `state/coord/`,
   `state/drills/`). Some hooks write to shared planes by themselves, so every dirty seat's session
   sets `AKASHIC_SESSION_SIGNALS=0` (the SessionEnd fold), `AKASHIC_TRACE=0` (the trace hook
   otherwise broadcasts every tool call's file name, first command line or search pattern onto the
   Bifrost bus), `AKASHIC_TOUCH=0` (PostToolUse otherwise records each touched path on the event
   stream) and `AKASHIC_RECALL_AT_ACTION=0` (otherwise snapshots of tool and subagent results, each
   string cut to 400 characters, are saved in `%TEMP%\akashic_recall\payloads`). The harness can
   write to the auto-memory by itself as well: Claude Code 2.1.280 ships a background
   memory-extraction pass and a consolidation ("dream") pass whose defaults are set on Anthropic's
   side (whether either runs on this host was not checked). So every dirty seat is launched from a
   shell that sets `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, which in that version's code stops the session
   reading or writing the auto-memory. Set it in the launching shell, not only in a settings `env`
   block: the CLI reads it from its own process environment, and whether a settings block is applied
   before the memory loads was not checked. A dirty seat's `boot --task` text is neutral ("case
   work", never the target's name), because boot writes it to the event ledger. Dirty seats never run
   in trial mode, so nothing of theirs reaches the trial database. After the case the monitor searches
   `%USERPROFILE%\.claude\memory\` for case terms (rule 6).
2. **The implementer is a separate agent id, used for nothing else (for example `clean-<case>`), in a
   CLI session the monitor sets up for it.** Every item below is needed; none is enough alone; rule 6
   checks them.
   - **A CLI session, never the desktop app.** The desktop app gives its sessions tools that search
     and export other sessions' transcripts and read the terminal (`mcp__ccd_session_mgmt__*`,
     `mcp__terminal__*`). The CLI can also list and message other local Claude sessions
     (`ListAgents`, `SendMessage`, `FetchInboxMessage`); the settings below deny those.
   - **Its own folder.** The clean build folder sits outside the repo and outside the home folder
     (`C:\Users\L5`), and the session is launched from it. The house hooks are registered for every
     session. Outside those two places their recall, trace and touch work stays off
     (`agent/harness/scope.py`), except for a shell command that names the repo path or
     `agent_cli.py`. The parts that run everywhere (the session-start recall cache, presence records,
     the Stop hook) are redirected or switched off by the environment below.
   - **Its own environment**, set in the shell that launches the session and repeated in that folder's
     `.claude/settings.local.json` `env` block:
     - `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, with `"autoMemoryEnabled": false` at the top level of the
       same settings file. The user-level settings point every session's auto-memory at one shared
       folder (`"autoMemoryDirectory": "~/.claude/memory"`), whose `MEMORY.md` index of house notes the
       CLI otherwise loads into the first turn of every session, wherever it was launched. In Claude
       Code 2.1.280's code (read 2026-10-13) either switch stops the session reading or writing that
       folder, and a folder's local settings outrank the user-level ones; both are set because neither
       was tried on its own here, and rule 6 checks the result.
     - `AKASHIC_AGENT_ID=clean-<case>`. The user-level settings set it to `claude`; the house hooks
       that still run file what they record under the clean id instead.
     - `REDIS_DB=15`, the trial database (AGENTS.md "Trial mode").
     - `AI_SETUP=<an empty folder outside the repo>`, a throwaway data root. `REDIS_DB` isolates Redis
       only: the store writes every record to its file tier as well (`HybridStore`,
       `core/foundation/store.py`), and on this host that tier is otherwise the house's own
       `session_logs/store_state.db`. `LearningStore` also copies `session_logs/learnings.jsonl` from
       the data root into the store on first use.
     - The house's own isolation flags: `_AISETUP_TEST_ISOLATED=1`, plus `AKASHIC_RECALL_STATE_DIR`
       (its own recall state; the shared cache in `%USERPROFILE%\AppData\Local\Temp\akashic_recall` is
       rewritten at every session start), `AKASHIC_SPILL_DIR`, `AKASHIC_TASKS_PATH` and
       `AKASHIC_SECRETS_DIR`, all pointing inside that throwaway folder. These come from the house's
       tested recipes, `_probe_env` in `core/comm/door_probe.py` and `tests/isolate_canonical.py`.
     - The hooks off: `AKASHIC_AUTOBOOT=0`, `AKASHIC_PLAN_RECALL=0`, `AKASHIC_RECALL_AT_ACTION=0`,
       `AKASHIC_TRACE=0`, `AKASHIC_TOUCH=0`, and `AKASHIC_STOP_WAKE=0` (the Stop hook fires in every
       session, wherever it was launched, and otherwise blocks the turn until the session arms a
       Bifrost wake listener).
   - **No house verb at all.** The clean seat runs no `agent_cli.py` command: not `boot`, not
     `recall`, and never `eye`, `find`, `web` or `ask`. On an empty trial store boot and recall
     return nothing it needs, and boot also prints house state the environment above does not
     redirect: the deferred-queue count, the test-suite baseline, a slice of `docs/`, the doctor's
     findings and, from its second run on, recent commit subjects that any seat may have written.
   - **No akashic MCP door at all.** A door started under `REDIS_DB=15` still serves tools that never
     touch Redis: the eye (`eye`, `eye_find`, `zoom`, `trace`) reads `state/eye/eye.db` and the
     transcript archive, `find` searches file names across the disk, and `web_fetch` and
     `ask_gemini_web` reach the web. Launch the session with `claude --strict-mcp-config --mcp-config
     <a file listing no servers>`, and deny the server's tools in the folder's settings as well.
   - **No web, no messaging and no house roots, written into the settings.** Beside its `env` block,
     the same settings file carries these exact rules. In Claude Code 2.1.280's code a rule path that
     starts with `//` is absolute, and a Windows path is turned into the form `/c/Users/...`, so `C:\`
     is written `//c/`; the Temp folder is spelled out in full, because a rule is not known to expand
     environment variables. These strings were read off the code, not tried: rule 6's smoke test is
     what shows they match.

     ```json
     "autoMemoryEnabled": false,
     "permissions": {
       "deny": [
         "WebFetch", "WebSearch",
         "mcp__akashic-aurora", "mcp__Claude_Browser", "mcp__claude-in-chrome",
         "SendMessage", "ListAgents", "FetchInboxMessage",
         "Read(//e/AI-Setup/**)", "Read(//e/AI-Setup-*/**)",
         "Read(//e/Akashic Aurora/**)", "Read(//f/Akashic Aurora/**)",
         "Read(//c/Users/L5/.claude/**)", "Read(//c/Users/L5/AppData/Local/Temp/**)"
       ]
     }
     ```

     The roots are denied whole because the shared records sit all over them. `E:\AI-Setup` holds
     `state/re/`, `state/eye/`, `state/spill/` (clipped note and handoff bodies), `session_logs/`
     (lessons, the ledger), `chronicles/` (handoffs, lessons) and `research/`. `E:\AI-Setup-*` covers
     the repo's clones (Sandbox, Alpha, Beta, publish). `E:\Akashic Aurora` and its `F:\` twin hold the
     transcript archive and the ephemeral exports (Bifrost mail, spill and session-log copies).
     `%USERPROFILE%\.claude` holds the auto-memory, the live transcripts (`projects/`), every typed
     prompt (`history.jsonl`) and pre-edit backups from every session (`file-history/`). The Temp
     folder holds the recall cache and every session's scratchpad and background-task output, so the
     clean seat keeps all its own files in its build folder. `Read` rules are meant to cover `Grep`
     and `Glob` as well; rule 6's smoke test checks all three.

   **What these settings do not guarantee.** The deny rules cover the harness's own file tools only:
   a shell command can still read any file this Windows user can. Whether the CLI ignores letter case
   when it matches a rule was not checked, so a path spelled with different capitals may slip past
   one. No setting was found that refuses a message another local session sends to the clean session:
   denying its messaging tools stops it asking, not being told. And no setting reaches what the model
   learned in training (the caveat below). The rules narrow the doors; what the clean seat actually
   saw is established by rule 6's checks and audit, never assumed. Its records in the trial database
   are disposable: the database is shared with tests and other trial runs, and the test suite flushes
   it (`tests/isolate_canonical.py`). The monitor checks it holds nothing from the case before the
   clean session starts.
3. **Only the functional specification crosses, reviewed by a third party for expression first.** The
   reviewer is a different seat from the analyst and the spec writer, or Daniel; never the spec's own
   author. They strip code, decompiler output, assets, verbatim text, distinctive names and the
   arrangement of screens, then copy the approved spec into the implementer's folder. Each crossing is
   logged: spec hash, from, to, reviewer, date.
4. **Daniel has seen the original and directs the build, so his direction crosses as words.** He gives
   the implementer mechanics, numbers and feel in words ("the dash covers about two player-widths in a
   quarter of a second"; "the boss telegraph should feel generous"), never reference images, footage,
   audio or assets of the original. His direction goes in as a spec addendum or a copied message and is
   logged as a crossing like any other; when Daniel wrote it, a seat reviews it.
5. **The taint register records who saw what**: person or agent id, what they saw (target hash,
   document hash), when, the direction of any crossing, and the reviewer. It lives at
   `state/re/<case>/taint.jsonl` (later the case ledger's stream). Dirty seats and the monitor write
   to it; **the clean seat is never given read access to it.**
6. **Verify the isolation, do not assume it.** The settings in rule 2 are not trusted until checked.
   - **Before the specification crosses**, in the clean session itself, the monitor:
     - reads what the harness injected into the first turn and checks it for any case term and for
       any auto-memory block (on this host such a block names
       `%USERPROFILE%\.claude\memory\MEMORY.md`);
     - checks the session's tool list: no `mcp__` tool at all, no web or browser tool, and none of
       `SendMessage`, `ListAgents` or `FetchInboxMessage`;
     - runs a smoke test: one `Read`, one `Grep` and one `Glob` against each denied root, aimed at a
       file or pattern there that holds no case material (for example `LICENSE` in the repo). Each
       must be refused. A rule that matches nothing fails silently, so a probe that is not refused
       stops the setup before any case material reaches the session: fix the rule, start a fresh
       session, test again.
   - **When the session ends**, the monitor reads the whole clean transcript and flags any file
     access outside the clean build folder by any tool, the shell included; any command that names a
     house root (`E:\AI-Setup`, `E:\AI-Setup-*`, `E:\Akashic Aurora`, `F:\Akashic Aurora`,
     `%USERPROFILE%\.claude`, the Temp folder) or `agent_cli.py`; any web use; and any message that
     arrived from another session. A transcript records commands, not every file a command opened (a
     script or a variable can hide a path), so the monitor reads what each command does, not only
     the paths it names.
   - **After the case**, the monitor searches `%USERPROFILE%\.claude\memory\` for case terms, the
     check on rule 1's background-write risk.

   A hit is a contamination entry in the taint register, and that seat is retired from the case.

Until a clean-session launcher exists (gap below), these settings are made by hand for each clean
session, and the monitor records that they were.

**The caveat with teeth.** A model's training data may already hold a well-known project's source
(very likely for popular open source, possible for leaked closed source). The 2026 chardet dispute
(Heather Meeker's analysis) is the warning: exposure cannot be scrubbed. So claim "clean room" **only
with the logs to prove it**, never rebuild a well-known open-source project to relicense it, and get
human legal review before shipping anything whose origin is a rebuild. Wine and ReactOS are the
working models: black-box conformance tests, signed IP agreements, no NDA material, the record of the
process is part of the product.

## Host safety (the binding constraint on this machine)

Defender off and updates blocked by the owner's choice; no safety net. Therefore:

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

- The parser is attack surface, not just the sample (binwalk CVE-2022-4510 ran code on extraction; a
  media decoder carries the same risk), so opening an untrusted file in any parser or decoder is VM
  work. Hashing a file on intake is not parsing.
- **Daniel's decision, never an ordinary step:** enabling Windows Sandbox or Hyper-V, creating or
  importing a VM, installing any tool, package or driver (an `npx <package>` run included), adding a
  certificate to a trust store, enabling USB debugging on a device, or changing any other security
  setting. No disposable VM or sandbox is enabled today (Windows Sandbox off, Hyper-V off; WSL and
  Docker are not sandboxes — WSL mounts C:/E: and launches Windows programs, Docker hosts
  `akashic-redis`). FLARE-VM / REMnux are the standard analysis builds, VM-only, snapshot first, once
  Daniel has decided on a VM.
- Do not run or wrap **Universal Extractor 2** (`%USERPROFILE%\Desktop\unorg desktop\`; unverified
  provenance, parts of it exist to unpack protected executables and decrypt game archives;
  `house-inventory.md`).
- Keep samples out of the repo (not on X:\). Hash on intake, delete when done. Uploading is publishing
  (Decompiler Explorer retains uploads; upload only our own or already-public samples).
- **The repo is public, and `state/` is not uniformly private.** Decompiler output, disassembly,
  third-party code and target excerpts never go into a tracked file: `fences/` is tracked and public
  (house-inventory F4), as are `research/`, `docs/`, `.claude/` and `tests/`; cite private evidence by
  path and hash. `.gitignore` re-includes `state/coord/**`, `state/drills/**`, `state/rewrites/`,
  `state/authorship/` and named files under `state/ci/`, so "under `state/`" is not enough: case files
  and recordings (Daniel's own included) go in `state/re/<case>/`, checked with
  `git check-ignore -v <path>`. `state/coord/web_fetch_receipts.jsonl` logs every URL the web door
  fetches and is committable (house-inventory F2): after case work, stage files by name, never
  `git add -A` or `git add .`.
- **TLS interception** decrypts only our own client's traffic, inside the VM, or on the host by
  trusting the proxy's certificate for that one client process (`NODE_EXTRA_CA_CERTS`,
  `SSL_CERT_FILE`); never by adding it to a host certificate store, where it would stay trusted after
  the session on a machine with no antivirus.
- Static-first is a safety feature: reading bytes never executes the target, though the reader can
  still be exploited, so static reading of an untrusted sample is VM work too. Browser-hosted grounds
  (Compiler Explorer, pwn.college, Microcorruption) run nothing locally.

## The gaps this domain names (build proposals, Daniel's/Vandor's call)

- **A disposable analysis environment** (Windows Sandbox `.wsb` with networking off and no folder
  mapping, or a Hyper-V/VirtualBox VM with host-only networking and snapshots; a Linux VM for
  binwalk/unblob/tshark). Blocks every untrusted-target drill. The house keeps only the recipe and an
  intake script; samples live in a quarantine folder outside the repo, hashed on intake.
- **A reverse-engineering case ledger** (`re case open / observe / infer / unknown / close`) built on
  `core/library/college.py` (hash chain) and `core/coord/fence_workspace.py` (tag checks), recording
  the target's identity and **permission basis** before any finding; `close` refuses until every
  checklist question is marked.
- **A read-only triage router** (`re triage <file>`): `python-magic` + `pefile` (both installed,
  imported nowhere today), stdlib zip/tar, hashes, an entropy map, strings with offsets; never
  executes the target; refuses repo paths except fixtures we wrote.
- **The clean-room wall generalised:** extend `arsenal/shaders/licence_line.py` (the 12-token shared-run
  check) to any registered private study corpus, plus a dirty-room/clean-room fence template (the
  template only: case content never goes in `fences/`, which is public).
- **A taint register** with a writer for dirty seats and the monitor, and a "clean session" launcher
  that applies the house-isolation settings above (a CLI session from its own folder and settings
  file, the auto-memory off, the throwaway data root and the trial database, the hooks off, no house
  verb, no MCP door, no web, no messaging tools, the denied roots), runs rule 6's first-turn checks and
  smoke test, and records that it did.

## Sources

Full report and URLs: `research/reviewed/reverse-engineering-2026-10-13/house-inventory.md` and
`teardown-toolkit-and-practice.md`. Key primary sources: 17 U.S.C. 1201 / 102(b) / 1839 and 37 C.F.R.
201.40 (law.cornell.edu, ecfr.gov); Directive 2009/24/EC arts. 5/6/8 and 2016/943 art. 3; the court
opinions named above; the US Copyright Office games page (copyright.gov/register/tx-games.html) and
Circular 33; Directive 96/9/EC (databases); ICD 203 (ODNI); RFC 2119; the Phoenix/NEC
clean-room history (Contreras, Handley, Yang, Harv. J.L. & Tech. 1990); Heather Meeker on the chardet
AI clean-room dispute. Discipline credited to **morluto/rea** (https://github.com/morluto/rea).
