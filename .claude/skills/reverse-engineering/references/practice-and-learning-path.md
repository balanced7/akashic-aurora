# Practice, note formats and a learning path — the operator's guide

How to get good at legitimate reverse engineering: legal practice grounds, the note formats that turn
observations into a buildable spec, the clean-room roles, and a twelve-week path. Distilled from
`research/reviewed/reverse-engineering-2026-10-13/teardown-toolkit-and-practice.md` (the full report,
four drills run 2026-10-13 with code in its Appendix A, every source). **Not legal advice**; the
legal note is below, the full map in `method-legal-cleanroom.md`.

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

No VM is enabled today (**Daniel's decision:** enabling one), so until one is, practice runs in
browser-hosted grounds and on our own code.

## Six findings before any theory

1. **The skill is mostly the notebook, not the disassembler.** Every strong practitioner keeps "what I
   saw" apart from "what I think it means" and "what I don't know yet" (ICD 203 standard 3; REA's
   observations/inferences/unknowns; Tridgell's Samba notebook of overheard "words"; NEC won *NEC v.
   Intel* partly because its clean engineer's every page was kept). The house has the instinct
   (forecast registry, predict-before-look in Forest Walks); it lacks a `teardown` notebook verb.
2. **Prediction before looking is the feedback loop that makes practice "deliberate."** Writing a
   prediction down before checking turns every step into feedback. Drill B: a reconstruction perfect on
   ten observed levels still predicted level 40 at 23,292 gold against a true 8,528 (2.7× overshoot),
   because of a soft cap at level 25 the first ten levels could not reveal — the commonest teardown
   mistake (extrapolating past the search boundary) caught by the cheapest habit.
3. **There are plenty of legal practice grounds, and the best one is our own code.** Compile a small
   function, read it back, compare with the source you already have (the answer key).
4. **A clean room is a staffing pattern that agent seats make cheap but not automatically clean.** A
   model that has seen the original is not clean however the session is drawn (the 2026 chardet dispute),
   and on this host shared memory reaches every session unless the clean seat is isolated — claim
   "clean room" only with the logs to prove it.
5. **For the Archero-style game the teardown that matters is a design teardown, by playing and reading
   published analyses, not by opening anyone's APK.** (See `games-design-teardown.md` and
   `archero-design-seed.md`.)
6. **This machine has no disposable VM or sandbox switched on today.** Every drill touching an
   untrusted binary waits until one exists (**Daniel's decision**). Until then: browser grounds and our
   own code.

## Deliberate practice, translated

Ericsson's ingredients → teardown mechanisms: a well-defined task (one question per session, not
"understand this program") → the question checklist; the right difficulty (crackme 1–2 of 6 at first,
never a level you solve without effort) → a difficulty ladder; informative feedback (a written
prediction checked against the answer key) → the forecast registry and predict-before-look; repetition
with correction (redo with one variable changed) → the "one changed input" rule; a coach (a hint, not
the answer) → a five-rung hint ladder. (The honest footnote: the deliberate-practice effect is
disputed — Macnamara & Maitra's 2019 replication found ~26% of variance, not ~48% — so *how* you
practise, with feedback and correction, matters more than hours logged.)

**The hint ladder** (the house "second press is a question" principle): 1 "Which question are you
answering right now?" → 2 "Which evidence settles it, and what is the cheapest tool that produces it?"
→ 3 "Look at offset/function/frame X." → 4 "The mechanism is in this family (a checksum, a lookup
table, an exponential curve)." → 5 the answer with the reasoning, then a similar exercise with one
variable changed.

## Legal practice grounds (built to be reversed; terms still apply; host-safety noted)

| Ground | Practise | Cost / terms | Host safety |
|---|---|---|---|
| **Compiler Explorer** (godbolt.org) | Write C/C++/Rust/Go, see the assembly live | Free, BSD-2 | Runs in their cloud |
| **Decompiler Explorer** (dogbolt.org) | Compare a dozen decompilers on one small binary | Free; **uploads retained** — our own/public only | Remote |
| **OpenSecurityTraining2** (p.ost2.fyi) | Arch1001 x86-64 (ends with a bomb lab), RISC-V, OS internals, C++ | Free | Our own code; lab binaries in a VM |
| **challenges.re** (Yurichev) | 87 listings across x86/ARM/MIPS/.NET/JVM | Free, CC BY-SA 4.0; **no solutions by design** | Listings need no execution |
| **crackmes.one** | Thousands of small programs, difficulty 1–6 | Free; rules ban cheats/cracks/keygens/malware/DRM tools/protectors | **VM only**, snapshot, network off |
| **Flare-On** (flare-on.com) | A hard annual series, Windows/Linux/.NET/JS/UEFI/Verilog/Web3 | Free; archives + official solutions 1–12 | **VM only** (malware-like tricks) |
| **pwn.college / picoCTF / Microcorruption** | Browser workspaces; Microcorruption is a simulated MSP430 lock in-browser | Free | Browser (zero local risk) |
| **Ghidra's own class** | Beginner → BSim, with exercise files | Free, Apache-2.0 | Exercise binaries in a VM |

**Not on the list, deliberately:** game trainers, cheat forums, keygen archives, cracked software,
malware zoos beyond analysis training, any online game's client or traffic.

**Crackmes train reading, not defeating.** Prefer challenges whose question is "what does this
compute?" (challenges.re listings, Flare-On's analysis puzzles, our own compiled code) over "find the
serial". A check-defeating skill learned on a crackme is never applied to a real product, and no
keygen, patch or write-up that defeats a check is published, even for a crackme.

**The best target is our own code.** Compile a small function, read the machine's version, compare with
the source; repeat with one thing changed (`-O0` vs `-O2`, GCC vs Clang, `switch` vs `if`-chain). After
~50, a disassembly stops looking like noise. Open-source games/engines worth reading (licences matter —
GPL is study material, not to be copied into a closed product): Celeste `Player.cs` (MIT, coyote time /
jump buffering / the state machine), Shattered Pixel Dungeon (GPL-3.0, the closest open cousin to an
Archero-like progression), Godot (MIT), id's Quake III / Doom (GPL-2.0, no game data), OpenMW (the
"reimplement the engine, user brings their own data" model), Dexed (a DX7 FM emulation), the house
shader corpus (CC BY-NC-SA, study only).

## Note formats (plain Markdown; see `method-legal-cleanroom.md` for the full set)

The question checklist (`| Q | Question | Evidence that would answer it | Status |`), the evidence
register (`| E-ID | Artifact sha256/12 | Tool+version | Exact input/command | Output kept at | When/who
|`), and the finding ledger (`| F-ID | Claim | Kind O/I/U | Evidence | Confidence | Search boundary |
Would change my mind if… |`) with ICD 203's likelihood words kept apart from analytic confidence (see
`method-legal-cleanroom.md`). Diagrams earn their place when they
show a relationship a table would hide (a call graph of the path under study, a byte map / Kaitai
`.ksy`, a pass graph + film strip, a core-loop and sources-and-sinks diagram, a signal-flow block
diagram). The behaviour spec uses RFC 2119 words (MUST/SHOULD/MAY), each requirement with evidence and
a test vector; the strongest form is conformance tests (Wine's suite passes on real Windows first, so
the tests *are* the description). The report leads with the bottom line, shows judgments with
confidence, names the alternatives considered (an ACH grid — keep the hypothesis with the fewest
inconsistencies), says how it changes earlier findings, keeps source quality visible, and states what
was *not* looked at.

## The four drills (method, not a blind test — one seat wrote both sides; a real blind drill needs another seat)

- **Drill A — a file format from bytes alone** (a WAV we generated): each structural guess must predict
  a number you can check (bytes 4–7 = file size − 8; byte-rate = rate×channels×bits/8). U-A1 is the
  classic trap: one sample does not tell you whether other files carry extra chunks.
- **Drill B — a game's upgrade-cost curve through its interface only:** observe 1–10, fit ×1.15,
  **register the prediction** (level 40 → 23,292), differential-test 1–60 (diverges at level 25, ratio
  drops to ×1.08), bisect the edge (last answering level 9,145; then `OverflowError`), treat errors as
  behaviour. Ten points prove nothing outside their range; a soft cap is visible from outside but not
  explicable from outside (an unknown).
- **Drill C — an audio "plugin" measured from outside:** small-signal impulse for the linear picture
  (a −3 dB point + ~6 dB/oct slope = a one-pole low-pass), sines at four levels for THD (even
  harmonics >97 dB down = a symmetric saturator), and compression at 200 Hz/1 kHz/4 kHz to tell
  filter→saturator from the reverse (Heuer's ACH in one line: design the test whose result differs
  between rival hypotheses).
- **Drill D — compile our own code, read the lowered form:** a critical-hit function in Python
  bytecode — a compare, a conditional jump, two return paths — the same shape a C compiler gives an
  `if`. Names survive here; in a stripped native binary they do not, which is why REA warns against
  trusting names even when they exist.

## Clean-room roles

Analyst (sees the original, writes the ledger) · spec writer (neutral words, no code/assets) · monitor
(reviews each crossing for expression, keeps the log; never the document's own author) · implementer
(**never** sees the original, builds from the spec) · verifier (pass/fail per test to the implementer;
failing vectors go to the monitor) · record keeper (the taint register).

Staffing it with house seats needs the house isolation rules in `method-legal-cleanroom.md`, because a
fresh session on this host is not a separate room: boot, the recall hooks, Bifrost mail and the
auto-memory reach every session. In short: dirty-side findings live only in `state/re/<case>/`, never
in `learn`, `note`, `handoff`, the bus, a commit message, the auto-memory or any tracked file, and
dirty seats switch off the hooks that report to shared planes and the harness's auto-memory
(`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`); the implementer is a separate agent id in a CLI session (never
the desktop app) launched from its own folder outside the repo, with the auto-memory off, on the trial
database (`REDIS_DB=15`) **and** a throwaway data root (`AI_SETUP=<an empty folder outside the repo>`
plus the house's isolation flags), with the hooks off, no house verb (not even `boot` or `recall`),
no akashic MCP door at all, no web, no tools that message other sessions, and reads denied on whole
roots (the repo and its clones, the transcript archive, `C:\Users\L5\.claude`, the Temp folder); the
monitor verifies that isolation before the specification crosses (first turn, tool list, a refused
read of each denied root) and audits the transcript at the end, because the settings are not a wall
(a shell can still read any file); only the functional specification crosses,
reviewed for expression by a different seat or Daniel; Daniel, who has seen the original, directs the
build in words, numbers and feel, never with images, footage or assets of the original; and a taint
register records who saw what, which the clean seat can never read.

The caveat: a model may already have seen a well-known project's source — claim "clean room" only with
the logs, never rebuild a known open-source project to relicense it, get human legal review before
shipping a rebuild.

## A twelve-week path (Daniel + two to four agent seats; roles rotate weekly)

Rhythm: Monday the checklist + a registered prediction; Tue–Thu the drill; Friday the ledger, a
one-page report, the prediction score, and a teach-back (a Forest Walk). Rule: every week produces a
ledger and a scored prediction; hours alone do not count. Prerequisite for weeks 4, 9, 11: a disposable
VM exists (**Daniel's decision**).

| Wk | Track | Goal | Do (legal target) |
|---|---|---|---|
| 1 | All | The method and the notebook | Drill A on three of our own files; fill checklist, register, ledger |
| 2 | Software | Read what compilers write | 30 Compiler Explorer pairs, predict-then-compare, vary one thing |
| 3 | Formats | Formats as executable specs | A Kaitai `.ksy` for the WAV, then a file type we own but don't know; round-trip |
| 4 | Software | First real binaries (VM) | crackmes.one difficulty 1–2; challenges.re listings |
| 5 | Graphics | See a frame | Spector.js on one of our own `arsenal/web` pages; a pass graph; predict each pass |
| 6 | Graphics/feel | Recreate an effect | One corpus shader or a hit-flash: spec from frames, build, A/B |
| 7 | Games (code) | Game feel in source | Celeste `Player.cs` state machine; list every forgiveness timer |
| 8 | Games (design) | The design teardown | A play log of a game we own + a deconstruction; answer the §7.5 questions for *our* game |
| 9 | Audio | Measure a black box | Drill C on one of our own plugins/patches |
| 10 | Audio | Recreate a sound | Rebuild three reference sounds by ear, check against spectrograms |
| 11 | Protocols | The Samba method | Differential-test two of our own implementations; Flare-On challenge 1 (VM) |
| 12 | Capstone | A clean room end to end | Analyst specs an effect/mechanic (ours or MIT/Apache); third-party monitor; an isolated implementer (house isolation rules); verifier runs conformance tests |

Graduation check: explain what a difficulty-2 crackme computes, in a VM, within two hours, with a
ledger (and publish no keygen or patch); produce a
frame-referenced effect spec another seat can build to pass an A/B; place a measured audio box's corner
frequency within 5% and say correctly whether it is linear; run one clean room with no contamination
entries; show prediction calibration improving across the twelve weeks.

## Routing table (practice)

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| "What did the compiler do with my code?" | Compiler Explorer | The exact instructions per source line | Behaviour of other compilers/flags (change one, recompile) |
| An unknown format (ours/open) | Hex view (ImHex or Python `struct`), then a Kaitai `.ksy` | Field layout, sizes, internal invariants | Opaque field meaning; variants not in the sample |
| A practice binary (crackme, Flare-On, our compiled program), VM | Detect It Easy, then Ghidra | Compiler/packer identity; functions, strings, pseudocode | Runtime values (debugger); intent; names may lie |
| A .NET assembly we own | ILSpy | Near-source C# | Obfuscated names; native interop |
| An audio plugin/patch we own (black box) | Test signals + measurement (numpy, Plugin Doctor) | Frequency response, THD vs level, even/odd harmonics, block order via a discriminating test | Exact internal algorithm; untested signals |
| A sound in a recording (trusted on host; untrusted → VM) | Spectrogram (Audacity, Sonic Visualiser), rebuild by ear | Partials, envelopes, modulation rates | The original patch (many fit one sound) |
| A protocol between our own components | Capture on our own machine, then differential testing | Message vocabulary and sequences; mismatches | Rare unexercised paths; intent |
| "Is our rebuild equivalent?" | Conformance/differential tests (Wine/Samba) | Every mismatch in the tested domain | Equivalence outside the sampled domain |
| "What changed between two versions?" (ours) | BinDiff / Diaphora, or a source diff | Which functions changed and how much | Why |

## Lessons (trigger-phrased)

- Use when starting any teardown, before opening a tool: write the question checklist with the evidence
  each answer needs, and fingerprint the target (hash, version, tool versions). Don't when the
  "teardown" is just reading a complete source repository.
- Use when about to check any guess, before looking: register the prediction (forecast registry), then
  score it. Don't when the check is a pure lookup with no guess.
- Use when a model fits the observed range, before relying on it outside that range: run a differential
  test well beyond the range, including errors, and state the tested domain in the claim. Don't when
  the claim is explicitly scoped to the observed range.
- Use when a name/string/filename suggests what code or data does, before writing it as behaviour:
  confirm with a parse, a run or a test. Don't when the name is all the question asks about.
- Use when practising, before choosing a target: pick a ground built to be reversed (our own code,
  crackmes.one, challenges.re, Flare-On archives, OST2, open-source games). Don't when the target is a
  commercial product's protection, an online game, or anything whose terms forbid it.
- Use when a drill involves any untrusted binary/document/firmware/capture, before opening it: apply
  the never-on-host rule above (a disposable VM with a snapshot and networking off; the sample out of
  the repo). Don't when the work is static reading of something we built.
- Use when a learner is stuck, before giving the answer: walk the five-rung hint ladder. Don't when the
  clock matters more than the learning (a production incident).
- Use when measuring an audio box, before reading a frequency response: drive it small for the linear
  picture and large for the nonlinear one, and design one test whose result differs between rival
  hypotheses. Don't when the device is known linear and you only need a gain.

## Gaps (build proposals)

A `teardown` verb scaffolding the four tables under `state/teardowns/<name>/`; the disposable VM/sandbox
(the blocking gap, **Daniel's decision**); a differential-testing harness (two callables/commands + an input
generator, errors as outputs, edge bisection, the tested domain printed); an audio measurement verb in
`arsenal.media` (`media measure`); an A/B comparison verb (`media ab <ref> <ours>`); a taint register
and a clean-session launcher; a drill-generator seat (blind targets with sealed answer keys); a
toolchain install list for Daniel's approval; prediction scoring tied to the existing forecast registry.

## Legal note (not legal advice; US, EU and UK orientation, dated 2026-10-13)

In the **US**, studying a program to reach its unprotected ideas can be fair use (*Sega v.
Accolade*, 9th Cir. 1992; *Sony v. Connectix*, 9th Cir. 2000), but a EULA or terms of service can
forbid reverse engineering and be enforced (*Bowers v. Baystate*, Fed. Cir. 2003; *Davidson v.
Jung*, 8th Cir. 2005), and DMCA §1201 separately bans circumventing access controls; its exemptions
(§1201(f), (g), (j); 37 C.F.R. §201.40) excuse only the act, under their stated conditions, never
tools. In the **EU and UK**, a lawful user may observe, study and test a program (Directive
2009/24/EC art. 5(3); CDPA s.50BA) and decompile for interoperability within art. 6's limits (CDPA
s.50B), and contract terms against those rights are void (art. 8; CDPA s.296A). In **both**,
trade-secret law allows reverse engineering a lawfully obtained product unless a valid contract
forbids it (18 U.S.C. 1839(6)(B); Directive 2016/943 art. 3(1)(b)), and ideas, methods and observed
facts are free, while code, art, audio and text are protected and a distinctive look may be protected
(*Tetris Holding v. Xio*, D.N.J. 2012, including as trade dress; republishing a whole extracted table
is a separate question in
the EU, where a database right can apply). **For this domain:** a practice ground permits analysis
of its own targets under its own rules (crackmes.one bans cracks, keygens, DRM tools and
protectors); that permission covers those targets only, never a real product. Uploading a sample is
publishing (Decompiler Explorer retains uploads), and course and challenge material carries its own
licence (challenges.re is CC BY-SA 4.0). The full map with its caveats is
`method-legal-cleanroom.md`; anything we ship that leans on someone else's product goes past a
lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/teardown-toolkit-and-practice.md` (the
four drills with code in Appendix A, the twelve-week path, all sources). Authors/grounds credited there:
Ericsson/Krampe/Tesch-Römer and Macnamara/Maitra; Dennis Yurichev (challenges.re, *RE for Beginners*);
crackmes.one; Mandiant FLARE (Flare-On); Xeno Kovah (OST2); Matt Godbolt (Compiler Explorer); bunnie
Huang (Name that Ware); Maddy Thorson & Noel Berry (Celeste); Evan Debenham (Shattered Pixel Dungeon);
Fabien Sanglard (Game Engine Black Books); Ken Shirriff (DX7 die teardown); Chester Lam (cache
microbenchmarks); Andrew Tridgell (Samba); the Wine and ReactOS projects; ODNI ICD 203; Richards Heuer
(ACH); Scott Bradner (RFC 2119); Contreras/Handley/Yang and Heather Meeker (clean rooms); and
**morluto/rea** for the evidence discipline.
