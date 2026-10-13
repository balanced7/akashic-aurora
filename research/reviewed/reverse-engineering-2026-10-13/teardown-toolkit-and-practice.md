# Teardowns as a skill: how to practise, take notes, staff a clean room, and learn in twelve weeks

Status: current
Class: research
Arc: reverse-engineering-2026-10-13 (one of eight researcher lanes; this lane is the PRACTICE of teardowns: how people get good, legal practice grounds, note and report formats, clean-room roles, and a 12-week path)
Written: 2026-10-13, Vandor (claude seat), for Daniel's "I want us to have the whole reverse engineering arsenal" request

Everything below is in my own words. Sources are linked in section 15, and people are credited by name where their
work is used. The discipline this report teaches is adapted from the REA skill by **morluto/rea**
(github.com/morluto/rea, MIT licence). We adopt its habits of mind, not its server machinery, and nothing of its text is copied.
The four practice drills in section 7 ran on this machine today, on artifacts we made ourselves; their code is in Appendix A.

**Not legal advice.** Section 10 is a map of the legal ground so we know where the fences are. Anything we intend
to ship or sell that was informed by someone else's product goes past a lawyer first.

---

## 0. The outcome, in one screen

**What this lane delivers.** A practice system for becoming good at legitimate reverse engineering across four
domains (software, graphics, games, audio). It has five parts. (1) The plain idea of what a teardown is and what
counts as evidence. (2) The practice grounds where it is legal to train. (3) The notebook formats that turn a pile
of observations into a spec someone else can build from. (4) The roles that keep a clean-room rebuild clean. (5) A
twelve-week path with a deliverable every week.

**Six findings that matter before any theory:**

1. **The skill is mostly the notebook, not the disassembler.** Every strong practitioner whose method I read
   ends up in the same place: they keep "what I saw" apart from "what I think it means" and from "what I don't know yet". The
   names vary. US intelligence calls it analytic tradecraft standard 3 (ODNI ICD 203). The REA skill calls it
   observations, inferences and unknowns with evidence IDs. Andrew Tridgell built Samba with it as a notebook
   of overheard "words". Courts have rewarded it too: NEC won *NEC v. Intel* partly because its clean-room engineer's every page
   and message had been kept. The house already has the instinct (forecast registry, predict-before-look in
   Forest Walks). What it lacks is a `teardown` notebook verb (section 14).

2. **Prediction before looking is the feedback loop that makes practice "deliberate".** Anders Ericsson's research
   on expert performance names four ingredients: a well-defined task, the right difficulty, informative feedback,
   and repetition with correction. Writing a prediction down before checking it turns every teardown step
   into feedback. In today's Drill B, my reconstruction fitted ten observed levels perfectly and still predicted level 40
   at 23,292 gold against a true 8,528 (a 2.7x overshoot), because of a soft cap at level 25 that the first ten
   levels could not reveal. That is the single most common teardown mistake (extrapolating past the search
   boundary) caught by the cheapest possible habit.

3. **There are plenty of legal practice grounds, and the best one is our own code.** Crackmes.one bans cheats,
   cracks, keygens for paid software, malware and commercial protectors. Mandiant's FLARE team publishes
   twelve years of Flare-On challenges with official solutions. Dennis Yurichev's challenges.re has 87 exercises
   (CC BY-SA 4.0). OpenSecurityTraining2, pwn.college and Compiler Explorer are free. The cheapest and safest
   target of all is a program we wrote, compiled and then read back, because the source is the answer key.

4. **A clean room is a staffing pattern, and agent seats make it cheap but not automatically clean.**
   The classic shape, a specification team, a design team and a coordination team, comes from the Phoenix BIOS and
   NEC v. Intel era. The house can staff it with seats in separate sessions, with Daniel as the monitor. The 2026
   chardet dispute (Heather Meeker's analysis) is the warning. A model, or a person, that has already seen the
   original is not clean however the session is drawn. So we claim clean-room status only with the logs to prove it.

5. **For the Archero-style game, the teardown that matters is a design teardown, done by playing and reading
   published analyses, not by opening anyone's APK.** Game mechanics are not protected by copyright; the US
   Copyright Office says so plainly in its games guidance. Expression is protected, and so is a
   close copy of a game's look and feel (*Tetris Holding v. Xio*, *Spry Fox v. Lolapps*). The public teardowns of
   Archero (Eva Grillova and Abhimanyu Kumar at Deconstructor of Fun, 2019; Grillova at Naavik, 2022) already point
   at the exact problem Daniel wants to solve. Run power and permanent power fight each other, and the meta turns
   into a grind. Section 7.5 turns that into design questions; our weapons, numbers, art and names stay ours.

6. **This machine has no disposable VM or sandbox switched on today** (Windows Sandbox is present in the component
   store but not enabled; Hyper-V is not enabled; WSL is not a sandbox for Windows binaries). Every drill that
   touches an untrusted binary (crackmes, Flare-On, anything downloaded) waits until one exists. Enabling one is a system setting and
   Daniel's call. Until then, practice runs in browser-hosted grounds (Compiler Explorer, pwn.college,
   Microcorruption, picoCTF's successor) or on our own code, which is what today's drills used.

---

## 1. The concepts, plainly

### 1.1 What a teardown is

A teardown is working backwards from a finished thing to the decisions that made it. The finished thing can be a
chip, a program, a frame of a game, a sound or a game economy. Daniel already reads teardowns every week. When
SemiAnalysis or Locuza annotate a die shot, they look at the silicon and say "this block is the L2, this is the
memory controller, this is why the cache got bigger". Three kinds of teardown appear in that world, and the
same three exist in software:

| Hardware version | Software/media version | What it gives you |
|---|---|---|
| **Read the silicon.** Ken Shirriff photographs a Yamaha DX7 sound chip under a microscope, stitches 100+ photos, and traces the circuits. He finds the chip does its maths in logarithms, so it never has to multiply | **Static analysis**: read the program, file or shader without running it (disassembler, decompiler, hex editor, source if it is open) | Structure: what is there and how it connects. Says nothing for certain about what happens at runtime |
| **Probe it while it runs.** A logic analyser on a bus, an oscilloscope on a pin | **Dynamic analysis**: run it under a debugger, a frame capture (RenderDoc, Spector.js) or a packet capture, and watch values move | What actually happened on the runs you watched, and nothing about the runs you didn't |
| **Treat it as a black box and measure.** Chester Lam at Chips and Cheese does this with pointer-chasing benchmarks. Each time the test's working set outgrows a cache level, latency jumps a step, and the steps reveal each level's size and latency without any documentation | **Black-box testing**: feed chosen inputs, record outputs, infer the rule (frequency sweeps for audio, frame-stepping a video for an effect, level-by-level costs for a game economy) | The input-output rule over the range you tested. The internal mechanism only where a test can tell rival mechanisms apart |

Experts mix all three, and they start with whichever is **cheapest for the question asked**. Tridgell's account
of how Samba was written puts public documentation first and packet sniffing second. Exhaustive scanning comes
third, and differential testing against the real server comes last. None of the four methods involves reading
Microsoft's code.

### 1.2 Evidence comes in three kinds, and the notebook must keep them apart

- **Observation**: something a tool or a person directly saw, which anyone else can reproduce from the same input.
  For example: "bytes 0-3 of the file are `52 49 46 46`".
- **Inference**: a conclusion drawn from observations plus assumptions. For example: "this is a RIFF container,
  so bytes 4-7 are probably a size". Every inference names the observations it rests on, and how confident it is.
- **Unknown**: a question we know we have not answered. For example: "what happens above level 60?". Unknowns are
  findings too, because they tell the next person where the map ends.

This split is not new. The US intelligence community's analytic standards (ICD 203, 2015, amended 2022) require
products to keep statements of underlying information apart from statements of assumption or judgment, and to say
what would change the judgment. The REA skill asks for the same thing in reverse-engineering form: cite evidence
IDs, preserve limits and incomplete coverage, and never imply that static analysis watched code execute. A
decompiler's output is an **inference** (a tool's guess at source), not an observation of source.

### 1.3 The search boundary

Every negative finding has a fence around it. "No network calls found" really means "no network calls found in
the 412 functions Ghidra identified, by searching for these 6 API names, in build sha256 abc…". REA calls this
keeping bounded negative searches bounded. Drill B in section 7 shows the cost of forgetting it. A model that
was exactly right on levels 1-10 was 2.7x wrong at level 40.

### 1.4 Observed behaviour versus design choice

When you rebuild something, every property of the original falls into one of two piles:

- **Required behaviour**: what the rebuild must do to be compatible or to deliver the experience. The
  file has to parse, the API has to return the right error, and the jump arc has to feel like the reference.
- **Design choice**: how the original happened to do it, which we are free (and often legally wise) to do
  differently. Variable names, code structure, exact art, exact numbers that are not forced by compatibility,
  even the order of internal steps.

The law draws a similar line. In *NEC v. Intel* (N.D. Cal. 1989) the court found that similarities between NEC's
and Intel's microcode were likely **dictated by the hardware and compatibility constraints**. The proof was a third
version written by an independent engineer, Gary Davidian, who never saw either; it came out similar in the same places.
In Europe, the Court of Justice in *SAS Institute v World Programming* (C-406/10, 2012) held that a program's
functionality, its programming language and its data file formats are not protected expression. The REA skill
asks for the same separation whenever someone builds from a teardown.

### 1.5 The clean room

A clean room is a rebuild in which the people who **write** the new thing never **saw** the old thing's
protected expression. The classic case is Phoenix Technologies' PC BIOS of 1984. One group of engineers studied
IBM's BIOS and wrote a description of what it did. A second group, who had never seen IBM's code, wrote a new BIOS from
that description. The description is the only thing allowed through the wall. Section 5 covers staffing.

### 1.6 Deliberate practice

Ericsson, Krampe and Tesch-Römer (1993) studied violinists and argued that expert performance comes from years of
practice designed to improve a specific weakness, with feedback, at the edge of current ability. That is different from
time spent just playing. In Ericsson's later handbook chapter (2006), the key point for us is that everyday skills go
**automatic** and then stop improving. Experts avoid this by deliberately choosing tasks that are slightly too
hard, so they keep improving.

The honest footnote: the size of the effect is disputed. Brooke Macnamara and Megha Maitra's 2019 preregistered
replication found deliberate practice explained about 26% of the variance in violin skill (the original
claimed about 48%). And in their sample, the best violinists had not practised more than the good ones. So practice
matters a lot but it is not the whole story, and **how** you practise (feedback, difficulty, correction) matters
more than hours logged. That is the design principle of section 8.

---

## 2. How experts get good: the practice loop

### 2.1 Ericsson's ingredients, translated for teardowns

| Ingredient | What it means for a teardown | The house mechanism |
|---|---|---|
| A well-defined task | One question per session ("what is the third field of this header?", "what curve does the upgrade cost follow?"), not "understand this program" | The question checklist (section 4.1) |
| The right difficulty | Crackme difficulty 1-2 of 6 at first; never stay at a level you solve without effort | Difficulty ladder per track (section 8) |
| Informative feedback | A written prediction checked against the answer key (our own source, an official solution, a test) | Forecast registry and calibration; predict-before-look in Forest Walks |
| Repetition with correction | Redo the same kind of target with one variable changed (optimisation level, compiler, file version) | The "one changed input" rule (REA: never repeat identical analysis without a changed input) |
| A coach | Someone who has solved it gives a hint, not the answer | A hint ladder (section 2.6) |

### 2.2 Legal practice grounds

All of these are built **to be reverse engineered**, which is what makes them legal to practise on. The terms of
each still apply. "Host safety" says where the code runs.

| Ground | Who runs it | What you practise | Cost / terms | Host safety |
|---|---|---|---|---|
| **Compiler Explorer** (godbolt.org) | Matt Godbolt and contributors, since 2012 | Write C/C++/Rust/Go, see the assembly each compiler emits, live | Free; BSD-2-Clause; can be self-hosted | Runs in their cloud; nothing executes here |
| **Decompiler Explorer** (dogbolt.org) | Open-source project | Upload one small binary, compare a dozen decompilers' output side by side (Ghidra, Hex-Rays, Binary Ninja, angr, RetDec and others) | Free; files under 2 MB; **uploaded binaries are retained**, so only upload our own or public samples | Runs remotely |
| **OpenSecurityTraining2** (p.ost2.fyi) | Non-profit started by Xeno Kovah | Arch1001 x86-64 assembly (ends with a binary bomb lab), Arch1005 RISC-V, Arch2001 OS internals, debugger classes, RE3011 C++ binaries, RE3201 symbolic analysis | Free, self-paced | Mostly your own code; run course-supplied lab binaries (the bomb lab) in a VM |
| **challenges.re** | Dennis Yurichev (also author of the free book *Reverse Engineering for Beginners*) | 87 short exercises on x86, x64, ARM, ARM64, MIPS, .NET, JVM; most are assembly listings you read, not run | Free, CC BY-SA 4.0; **no solutions on purpose**, and he asks solvers not to publish theirs | Listings need no execution; executables go in a VM |
| **crackmes.one** | Community successor to crackmes.de | Thousands of small programs made to be solved; difficulty 1 (very easy) to 6 (insane); write-ups after you solve | Free; archive password published; rules ban cheats, trainers, cracks of commercial software, keygens for paid programs, malware, DRM circumvention tools and commercial protectors | **Untrusted binaries: VM only.** Their own FAQ says VM, snapshot, network off |
| **Flare-On** (flare-on.com) | Mandiant's FLARE team (Google Cloud Security), every autumn since 2014 | A single-player series of hard puzzles across Windows, Linux, .NET, JavaScript, UEFI, Verilog, Web3 | Free; archives and official solutions for every year 1-12 | **VM only**; challenges deliberately use malware-like tricks |
| **pwn.college** | Arizona State University | Dojos from the Linux basics up; runs much of ASU's security curriculum | Free | Browser workspace (not re-verified today) |
| **picoCTF / CyLab Security Academy** | Carnegie Mellon University | Beginner CTF with a reverse-engineering category; the site is being folded into CyLab Security Academy (logins and progress carry over) | Free | Browser webshell for most tasks (not re-verified today) |
| **Microcorruption** | Built by Matasano, now hosted by NCC Group (not re-verified today) | A browser-based debugger for a simulated MSP430 smart lock; embedded reversing with zero local risk | Free | Entirely in the browser |
| **Ghidra's own class** | NSA Research Directorate | `GhidraDocs/GhidraClass`: Beginner, Intermediate, Advanced, Debugger, BSim, with exercise files | Free, Apache-2.0 | Exercise binaries in a VM |
| **Name that Ware** (bunniestudios.com) | Andrew "bunnie" Huang, monthly for over a decade | Identify a circuit board from a photo: chip markings, layout, clues | Free | Photos only |

**Not on the list, deliberately:** game trainers and cheat forums, keygen archives, "cracked" software, malware
zoos for anything beyond analysis training, and any online game's client or traffic. Those are either illegal,
against our rules, or both. (Section 10 explains why.)

### 2.3 Compile, then read it back: the best practice target is our own code

The fastest feedback loop in the whole field needs no download at all. Write a small function, compile it,
read the machine's version, and compare with the source you already have. Compiler Explorer does it in the
browser, colour-matching each source line to its assembly. Repeat with one variable changed: `-O0` against `-O2`,
then GCC against Clang, a `switch` against a chain of `if`s, a struct against an array. After about fifty of these, a disassembly
listing stops looking like noise. You start recognising the shapes compilers leave behind for loops, calls
and branches. Yurichev's book is built on this idea.

Drill D in section 7 shows the same loop in Python's own lowered form (bytecode), which this machine can do
without installing a compiler. The ideas carry over: a comparison, a conditional jump, two return paths.

### 2.4 Open-source games and engines worth reading

Reading code that is meant to be read is legal and fast. For a game we will build, it is also the best way to learn
what "game feel" is made of. The licences matter: GPL code is study material, but copying it into a closed
product would bring the GPL's duties with it.

| Source | What to read it for | Licence |
|---|---|---|
| **Celeste `Player.cs`** (Maddy Thorson, Noel Berry; github.com/NoelFB/Celeste) | ~5,400 lines of a famous platformer's movement: coyote time, jump buffering, the state machine. Released as a learning resource | MIT for the released classes; the game and its assets are not included |
| **Shattered Pixel Dungeon** (Evan Debenham, from Watabou's Pixel Dungeon) | A complete roguelike with item upgrade systems, randomised runs, and run-versus-meta balance. The closest open cousin to an Archero-like progression | GPL-3.0 (Java, libGDX) |
| **Godot** | A whole modern engine: renderer, physics, scene tree; plus its demo projects as safe RenderDoc targets | MIT |
| **Quake III Arena**, Doom, Wolfenstein 3D (id Software source releases) | Classic engine architecture; read alongside Fabien Sanglard's *Game Engine Black Books* (free PDFs on a pay-what-you-like basis, LaTeX sources public) | GPL-2.0 code; **game data not included** |
| **OpenMW** | A from-scratch engine that runs Morrowind; a model of the legal "reimplement the engine, user brings their own data" pattern | GPL-3.0; you must own Morrowind |
| **Dexed** (Digital Suburban, github.com/asb2m10/dexed, built around Raph Levien's msfa engine) | A DX7 FM synth emulation built by studying real hardware; pair it with Ken Shirriff's DX7 chip teardown | GPL-3.0 (plugin); Apache-2.0 (msfa core) |
| **The house shader corpus** (`state/arsenal/shaders/corpus/`) | 335 shaders already gathered for shader school; recreating one effect from its rendered output, before reading its code, is a perfect drill | Mostly CC BY-NC-SA 3.0: **study only, never copied into tracked files** |

### 2.5 Recreating a known effect as an exercise

This is the graphics and game-feel version of a crackme, and it is legal because we observe and then write
our own version. The protocol:

1. **Pick a reference we may watch.** Our own recording of a game we own, a public trailer, a GDC talk's demo, or
   a shader from the corpus rendered in the browser.
2. **Observe before you build.** Step through it frame by frame (`py -m arsenal.media frames`, `sheet` for a contact
   sheet, `shots` for cut points). Write down timings in frames, shapes, colours, the layering order, and what
   reacts to what.
3. **Write the behaviour spec** (section 4.5) with every MUST tied to a frame number. Separate "this is what it
   does" from "I bet it's a sprite sheet" (an inference).
4. **Build ours from the spec.**
5. **A/B it** at the same frame rate, side by side, and log every difference as a finding.
6. **Only then** read how the original did it (a talk, a breakdown, the corpus source), and score your inferences.

Good references for what experts look for: Martin Jonasson and Petri Purho's *Juice It or Lose It* (GDC Europe
2012) takes a dull Breakout clone and adds screen shake, particles, squash and sound live on stage, with source
provided. Simon Trümpler's *Game Art Tricks* has 90+ breakdowns of how shipped games fake water, mirrors and
explosions. Adrian Courrèges' frame studies (GTA V, 2015, and others) walk a single frame pass by pass. Read those
studies as finished teardowns by others. Our own captures stay on our builds and open-source projects (section 10.6).

### 2.6 Hints, not solutions

Yurichev publishes no solutions, on purpose. His reasoning is that a published answer kills the motivation the
exercise exists to build. Crackmes.one wants write-ups that explain the method and not just the password.
Both match the house's own "second press is a question" principle: a stuck learner gets an escalating ladder of
hints, not the answer. A five-rung ladder for any drill:

1. "Which question are you answering right now?"
2. "Which evidence would settle it, and what is the cheapest tool that produces that evidence?"
3. "Look at offset/function/frame X."
4. "The mechanism is in this family (a checksum, a lookup table, an exponential curve)."
5. The answer, with the reasoning, followed straight away by a similar exercise with one variable changed.

---

## 3. The method, step by step

This is the loop for any teardown in any domain. Steps marked (REA) are habits adapted from morluto/rea.

1. **Get permission straight first.** Is the target ours, open source, built for practice, or something
   we are licensed to use and allowed to examine? Read the EULA or terms. If the answer is unclear, stop and ask Daniel.
   Never choose an example on someone else's behalf: if the request says "my app", ask which (REA).
2. **Write the question checklist.** Turn the request into concrete questions, and list next to each one the evidence
   that would answer it (REA).
3. **Fingerprint the target.** Record the SHA-256, size, version, where it came from, and the tool versions you will
   use. Without this nothing is reproducible.
4. **Route the target to its first tool** (REA). Choose from the artifact type, not from habit: a file → a hex view
   and format identifier; a native binary → identify it (Detect It Easy), then Ghidra; a .NET assembly → ILSpy; a WebGL page
   → Spector.js; a video → frame stepping; an audio box → test signals. The routing table is in section 12.
5. **Start summary-first.** Take the overview or inventory before drilling in (REA). Strings, imports, resource
   lists, chunk lists, render-pass lists, the main menu of a game.
6. **Inspect resources and configuration alongside code** (REA). Behaviour often lives in data: a table of upgrade
   costs, a shader parameter file, a preset. **Never infer behaviour from a name**: a function called `Encrypt`
   may only copy bytes, and a file called `config.json` may be ignored.
7. **Register a prediction, then look.** Write what you expect before every check. Score it afterwards.
8. **Follow one question from entry to result.** Trace the data from where it enters to where it shows its effect.
   Batch related checks around one hypothesis, and widen the search only when the evidence leaves a concrete gap (REA).
9. **Corroborate with the right kind of evidence.** A static reading of a branch is not proof it runs. Watch it
   run, or test it as a black box, when the claim is about runtime behaviour.
10. **Ledger every finding** (section 4.3): claim, kind (O/I/U), evidence IDs, confidence, search boundary, what would
    change your mind.
11. **Do not repeat an identical analysis.** If you are about to rerun something, name the input that changed or
    the blocker that was fixed (REA).
12. **Revisit the checklist at the end.** Mark each question answered, partly answered or unresolved. Don't call an
    investigation complete while a required question is open (REA).
13. **When rebuilding, write the spec** (section 4.5) with required behaviour and design choices in separate
    sections. Then build from the spec, not from the target.

---

## 4. Note-taking and reporting formats

These are the house formats I recommend. They are plain Markdown tables so any seat can write them and any
generator can parse them.

### 4.1 The question checklist (top of every teardown)

```
| Q  | Question                                   | Evidence that would answer it          | Status     |
|----|--------------------------------------------|----------------------------------------|------------|
| Q1 | What container format is this file?        | magic bytes + a parse that round-trips | answered   |
| Q2 | How does weapon upgrade cost grow?         | costs at many levels, incl. far ones   | partial    |
| Q3 | Is the saturator before or after the filter?| a test whose result differs by order   | answered   |
```

Status is one of `open`, `answered`, `partial` or `unresolved (bounded: …)`. It is revisited at the end (REA).

### 4.2 The evidence register

```
| E-ID | Artifact (sha256/12)  | Tool + version          | Exact input / command            | Output kept at            | When / who        |
|------|-----------------------|-------------------------|----------------------------------|---------------------------|-------------------|
| E-A2 | 650559119763 (wav)    | Python 3.11.9 struct    | first 48 bytes                   | drills_output.txt:3-6     | 2026-10-13 Vandor |
```

Every claim in the ledger points to E-IDs. Every E-ID is reproducible from this row.

### 4.3 The finding ledger (the heart of it)

```
| F-ID | Claim                                    | Kind | Evidence    | Confidence           | Search boundary                    | Would change my mind if…        |
|------|------------------------------------------|------|-------------|----------------------|------------------------------------|---------------------------------|
| F-B1 | Cost grows ×1.15 per level for L<25      | O    | E-B1, E-B5  | —                    | every level 1-24 tested            | —                               |
| F-B2 | Growth drops to ×1.08 from L=25 on       | I    | E-B6, E-B7  | very likely (80-95%) | 1-60 exhaustive + 200 random ≤10000 | a mismatch outside the sample   |
| F-B3 | Behaviour above L=9145 is an error       | O    | E-B8        | —                    | bisected exactly                   | —                               |
| F-B4 | Why the designer chose 25 for the cap    | U    | —           | —                    | not answerable from outside        | a design doc or the designer    |
```

**Confidence words** come from one fixed scale so readers do not have to guess. ICD 203 gives one, building on Sherman
Kent's 1964 essay: almost no chance (1-5%), very unlikely (5-20%), unlikely (20-45%), roughly even (45-55%),
likely (55-80%), very likely (80-95%), almost certain (95-99%). Observations do not get a likelihood; they get
an evidence ID.

### 4.4 Diagrams, by domain

A diagram earns its place when it shows a relationship a table would hide. ICD 203's standard 9 asks for visuals
for spatial and temporal relationships. The ones that pay off:

| Domain | Diagram | Tool |
|---|---|---|
| Software | Call graph of the path under study (not the whole program); state machine of the thing that changes mode | Ghidra's function graph, then redrawn by hand in Mermaid (MIT) so only the relevant part is there |
| File formats | A byte map (offset, size, type, meaning, evidence) and the executable spec | ImHex patterns or Kaitai Struct `.ksy`, which compiles to a parser and draws its own diagram |
| Graphics | A pass graph (each render pass, what it reads, what it writes) plus a film strip of the frames that matter | Spector.js/RenderDoc pass list; `arsenal.media sheet` for the strip |
| Games | The core loop (play → reward → upgrade → play); a sources-and-sinks economy diagram; the progression curve plotted | Mermaid flowchart; a chart of measured costs and power |
| Audio | A signal-flow block diagram (what feeds what), plus the measured curves: frequency response, harmonics vs level, envelope | numpy/matplotlib or Plugin Doctor screenshots |

### 4.5 The behaviour spec (what crosses the clean-room wall)

Use Scott Bradner's RFC 2119 words so the strength of each line is unambiguous: **MUST** is required, **SHOULD**
means there could be a reason not to, **MAY** is optional. Each requirement carries its evidence and a test vector.

```
## Required behaviour
R1  Cost(level) MUST equal round-half-up(100 × 1.15^(level-1)) for 1 ≤ level ≤ 24.   [E-B1, E-B5; vectors: L=1→100, L=10→352]
R2  Cost(level) MUST grow ×1.08 per level from level 25.                         [E-B6, E-B7; vectors: L=25→2688, L=40→8528]
R3  Level < 1 MUST be rejected as an error.                                      [E-B9]

## Design choices (ours, free to differ from the original)
D1  We MAY cap levels at 200 instead of failing on overflow near 9146.
D2  Names, data layout, code structure: ours.

## Unknowns carried forward
U1  Why 25 and 1.08 (designer intent).  U2  Behaviour outside the tested domain.
```

The strongest form of spec is the one Wine uses: **conformance tests**. Wine's test suite has to pass on real
Windows first, so the tests themselves become the most precise description of the behaviour. Samba's
differential testing is the same idea. A spec written as tests can cross the wall, and the implementer
knows exactly when they are done.

### 4.6 The report (for Daniel or any reader)

Five ICD 203 habits make a teardown report useful. Lead with the main message. Show judgments with their
confidence. Say which alternatives were considered and why they lost. Say how this changes earlier findings.
Keep source quality visible. The house shape:

1. **Bottom line** (three lines).
2. **Answers to the checklist** (answered/partial/unresolved).
3. **Key judgments** with confidence words and the alternatives considered (an ACH grid if there were real
   competing hypotheses: hypotheses across, evidence down, mark each cell consistent/inconsistent, and keep the
   hypothesis with the **fewest inconsistencies**, which is Richards Heuer's point that disconfirming evidence is what discriminates).
4. **The ledger and the evidence register.**
5. **What we did not look at** (search boundary) and **how to reproduce**.

---

## 5. Team roles in a clean room

### 5.1 The classic shape

From the Phoenix BIOS story and the *NEC v. Intel* record, as summarised by Jorge Contreras, Laura Handley and
Terrence Yang in the Harvard Journal of Law & Technology (1990), a defensible clean room needs at least three groups:
a specification team, a design team and a coordination team. NEC's records ran to many thousands of pages. They held every
page the clean engineer saw and every message he sent or received. The authors' own critique is worth keeping in
view: clean rooms are slow, expensive and duplicate work. So use one only when the risk earns it.

| Role | Sees the original? | Produces | Must never |
|---|---|---|---|
| **Analyst** ("dirty" side) | Yes | Observations, the finding ledger | Write any of the new implementation |
| **Spec writer** (often the analyst in a small team) | Yes | The behaviour spec and conformance tests, in neutral words, with no code, names, art or verbatim text from the original | Paste code, decompiler output or assets into the spec |
| **Monitor / gatekeeper** | Reads only what crosses | Approves or strips each document that crosses the wall; keeps the log; answers the clean side's questions in writing | Let anything cross that carries expression rather than behaviour |
| **Implementer** ("clean" side) | **Never** | The new thing, built only from the spec | Look at the original, its decompilation, leaks, or "helpful" snippets |
| **Verifier** | Behaviour only (pass/fail) | Differential and conformance test results | Return anything but pass/fail and the test vector |
| **Record keeper** | Logs only | The taint register (who saw what, when) and the document log | Lose a record |

The US and Europe differ here. ReactOS's 2006 audit noted that the US approach expects this separation between
the person who tears apart and the person who implements, while some other countries let the same person do
both. The house should use the stricter US shape for anything we publish.

### 5.2 Wine and ReactOS as working examples

Wine's developers state, in the project's forums, that contributors must not reverse engineer Microsoft's code,
including by running native DLLs under Wine's debugger to see what they do. The project's approach is black-box
tests that run on Windows. ReactOS stopped development for
an audit in 2006, had every contributor sign an IP agreement, and its guideline forbids bringing in trade
secrets or NDA material. Both projects show the same lesson. **The record of the process is part of the product.**

### 5.3 Staffing it with house seats

A small team of Daniel plus agent seats can run a real clean room, and it is cheaper than one with people.
Separate sessions are separate rooms, and the spec file is the only door:

- **Analyst seat**: works on the target; writes the ledger and spec in its own session.
- **Monitor**: Daniel, with a second seat as a reviewer that checks the spec for anything that is expression
  (code fragments, distinctive names, copied text, art), not behaviour.
- **Implementer seat**: a **fresh** session with no tool access to the target's path, given only the approved spec.
- **Record keeper**: the ledger in the substrate (a log line per crossing: document hash, from, to, approved by).

**The caveat, and it is serious.** A model's training data may already contain the target's source. That is
very likely for any well-known open-source project, and possible for leaked closed source. In March 2026 the chardet
maintainer released an LLM-assisted rewrite under a new licence. The original author, Mark Pilgrim, objected that
long exposure to the old code made it no clean room. Heather Meeker's analysis of the dispute concludes that
exposure can't be scrubbed away. An AI step in the middle helps only as a neutral actor in a properly
separated process. So for us: **claim "clean room" only with the logs to prove it, never rebuild a
well-known open-source project in order to relicense it, and ask for human legal review before shipping anything whose
origin is a rebuild**.

---

## 6. The practice toolkit: what each tool is for, licence, cost

Installed status was checked today with the house `find` verb (Everything index). "Not installed" means not
found on this machine.

| Tool | What it is for | Licence / cost | Here? |
|---|---|---|---|
| **Ghidra** (NSA) | Disassembler + decompiler + scripting for most CPUs; the free default | Apache-2.0, free; needs a JDK; read its security advisories before use | Not installed; no Java on PATH |
| **IDA Free** (Hex-Rays) | Industry-standard disassembler; free edition has a cloud x86/x64 decompiler | Free for **non-commercial use only** | Not installed |
| **Binary Ninja Free / Non-Commercial** (Vector 35) | Modern disassembler; Free covers x86/x64/ARMv7/AArch64, no API or plugins; Non-Commercial dropped to $199 with version 6.0 (2026) | Proprietary; free tier non-commercial | Not installed |
| **x64dbg** | Windows user-mode debugger for watching a program run | GPL-3.0, free | Not installed |
| **ILSpy** | .NET decompiler (C# out of IL) | MIT, free | Not installed |
| **Detect It Easy** | Identifies a file's type, compiler, linker and packer before you open a disassembler | MIT, free | Not installed |
| **ImHex** (WerWolv) | Hex editor with a pattern language that annotates a file's structure as you learn it | GPL-2.0 (library LGPL), free | Not installed |
| **Kaitai Struct** | Write a file format once as a `.ksy` description; it compiles to a parser in a dozen languages and draws a diagram. The spec IS a test | Compiler GPL-3.0+, runtimes MIT; free; web IDE at ide.kaitai.io | Not installed (web IDE needs nothing) |
| **BinDiff** (Google, ex-zynamics) | Compare two versions of a binary: which functions changed | Apache-2.0 since Sept 2023, free | Not installed |
| **Diaphora** (Joxean Koret) | Binary and pseudo-code diffing inside IDA | AGPL-3.0 (commercial licence available) | Not installed |
| **Compiler Explorer** / **Decompiler Explorer** | Practice loops (section 2.3) | Free web; BSD-2 / open source | Browser |
| **RenderDoc** (Baldur Karlsson) | Frame capture for Vulkan, D3D11/12, OpenGL: every pass, texture and shader of one frame | MIT, free. Its own policy: "intended for debugging your own programs only" | Not installed |
| **Spector.js** (Babylon.js team) | WebGL frame capture as a browser extension; the right tool for our own `arsenal/web` pages | MIT, free | Not installed (browser extension) |
| **Wireshark** | Packet capture and dissection (our own traffic, our own machines) | GPL, free | Not installed |
| **Audacity** | Waveform and spectrogram view, test-tone generation | GPL, free | Installed (`C:\Program Files\Audacity`) |
| **Sonic Visualiser** | Detailed spectrogram and annotation layers for audio | GPL, free | Not installed |
| **Plugin Doctor** (DDMF) | Measures any audio plugin as a black box: frequency/phase response, harmonics vs level, dynamics, oscilloscope | Proprietary, about $29 | Not installed |
| **Syntorial** | Ear training for synth sounds: hear a patch, rebuild it by ear on a built-in synth (197 lessons) | Proprietary, $129.99 | Not installed |
| **numpy / scipy** | Our own measurement and fitting (Drill C) | BSD, free | Installed (numpy 2.4.4, scipy 1.17.1) |
| **arsenal.media** | `frames`, `sheet`, `shots`, `probe`, `peaks`: frame-stepping and contact sheets for effect teardowns | House code | Installed |
| **Mermaid** | Text-defined diagrams (flowchart, state, sequence) that live in Markdown | MIT, free | Renders in most viewers |
| **FLARE-VM** (Mandiant) | Script that turns a fresh Windows VM into a reversing workstation | Apache-2.0, free. Its README: **install only in a VM**, snapshot first; it expects Defender and updates disabled **inside the VM** | Needs a VM first |
| **A disposable VM** (Windows Sandbox, Hyper-V, VirtualBox) | The room every untrusted sample lives in | Windows Sandbox and Hyper-V come with Windows 11 Pro; VirtualBox is free | **None enabled** (Sandbox present in the component store, not enabled; Hyper-V off; WSL present but not a sandbox) |

**Book shelf (commercial unless noted):** Dennis Yurichev, *Reverse Engineering for Beginners* (free PDF); Chris
Eagle and Kara Nance, *The Ghidra Book* (No Starch, 2020); Dennis Andriesse, *Practical Binary Analysis* (No Starch,
2018); Fabien Sanglard, *Game Engine Black Book: Wolfenstein 3D* and *DOOM* (free PDFs); Steve Swink, *Game Feel*
(2008); Vadim Zavalishin, *The Art of VA Filter Design* (free PDF from Native Instruments, rev. 2.1.2, 2020); Julius O.
Smith III's four online DSP books at CCRMA (free).

---

## 7. Worked examples (run today, on artifacts we made)

All four drills ran on 2026-10-13 in Python 3.11.9 with numpy 2.4.4, on this machine. No outside code ran.
The "target" side lives in `hidden_blackbox.py`. The "analyst" side (`drills.py`) only calls the target's
functions and never opens that file. **Honesty note:** I wrote both sides, so these show the **method**, not
a blind test. A real blind drill needs a different seat to write the target (gap G7). Code is in Appendix A. Output was
saved beside the scripts in the session scratchpad.

### 7.1 Drill A: a file format, read from bytes alone

Target: a WAV file the drill generates (1 channel, 16-bit, 22,050 Hz, a quarter second of a 440 Hz tone). SHA-256 prefix
`650559119763077a`, 11,068 bytes.

Observation E-A2, the first 48 bytes:

```
0000  52 49 46 46 34 2b 00 00 57 41 56 45 66 6d 74 20  RIFF4+..WAVEfmt
0010  10 00 00 00 01 00 01 00 22 56 00 00 44 ac 00 00  ........"V..D...
0020  02 00 10 00 64 61 74 61 10 2b 00 00 00 00 dc 05  ....data.+......
```

| F-ID | Claim | Kind | Evidence | Note |
|---|---|---|---|---|
| F-A1 | Bytes 0-3 and 8-11 are ASCII tags `RIFF` and `WAVE` | O | E-A2 | Seen directly |
| F-A2 | Bytes 4-7 are a little-endian size of everything after them | I → confirmed | E-A3: value 11,060 = file size − 8 | The hypothesis predicted a number and the number matched; that is what upgrades an inference |
| F-A3 | Bytes 12-35 are a `fmt ` chunk: format 1, 1 channel, 22,050 Hz, byte rate 44,100, block align 2, 16 bits | I → confirmed | E-A4 plus two internal cross-checks (byte rate = rate × channels × bits/8; align = channels × bits/8), both true | Internal consistency checks are the cheapest corroboration a format offers |
| F-A4 | Bytes 36-43 open a `data` chunk of 11,024 bytes = 5,512 frames = 0.25 s × 22,050 | I → confirmed | E-A5 | Matches the known duration |
| U-A1 | Whether other WAV files carry extra chunks (`LIST`, `fact`) between `fmt ` and `data` | U | — | **Bounded:** one file sampled. A parser that assumes `data` sits at byte 36 is a bug waiting for the second file |

The lesson: **each structural guess must predict a number you can check**. U-A1 is the classic trap of a format
teardown done on one sample.

### 7.2 Drill B: a game's upgrade-cost curve, through its interface only

Target: `upgrade_cost(level)`, a function we treat as a sealed box (as if it were a game we play, or a server we
can only query).

- **E-B1** observed costs for levels 1-10: 100, 115, 132, 152, 175, 201, 231, 266, 306, 352.
- **E-B2/E-B3** successive ratios all sit at 1.148-1.152; a log-linear fit gives 99.93 × 1.1501^(L−1).
- **Inference F-B1:** cost = round-half-up(100 × 1.15^(L−1)). The rebuild matches levels 1-10 exactly.
- **E-B4, the registered prediction:** level 40 should cost **23,292**. Actual: **8,528**. A 2.7x overshoot.
- **E-B5** differential test over levels 1-60: the rebuild diverges at 36 levels, the first at **level 25**.
- **E-B6** around the break: 2,164 → 2,489 → **2,688** → 2,903 → 3,136. The ratio drops to **1.08** from level 25.
- **E-B7** the revised two-segment model matches all of levels 1-60 **and** 200 random levels between 61 and 10,000.
  It treats errors as behaviour too: the target raised `OverflowError` on 23 sampled levels, and so does the model.
- **E-B8** bisection: the last level that answers is **9,145**, whose cost is a 309-digit number (about 1.8 × 10^308),
  the edge of a 64-bit float.
  Level 9,146 raises.
- **E-B9** level 0 and level −3 raise `ValueError`.

The finding ledger for this drill is the example in section 4.3, and the spec is the example in section 4.5.
After the ledger was written, the hidden source confirmed every line: ×1.15 up to level 24, ×1.08 from level 25, and
an error for levels below 1. Three lessons:

1. **Ten good points prove nothing outside their range.** The soft cap was invisible in levels 1-10. If this were a
   competitor's economy and we built our balance on F-B1, our level-40 weapon would cost nearly three times too much.
2. **Errors are behaviour.** Wine's conformance tests check error returns for exactly this reason. Recording
   "what fails, and where" (E-B8, E-B9) is part of the spec.
3. **A soft cap is a design choice we can see from outside but cannot explain from outside** (F-B4 is an unknown).
   That is the line between teardown and design. Section 7.5 picks it up for the Archero idea.

### 7.3 Drill C: an audio "plugin", measured from outside

Target: `mystery_effect(signal)`, an audio processor we only feed and listen to. This is the Plugin Doctor method
written in numpy.

| E-ID | Test | Result |
|---|---|---|
| E-C1 | An impulse at a tiny level (0.001, to stay out of any saturator's bend), then FFT | Flat at DC, **−3 dB at 1,234.9 Hz**, falling about 5.4 dB per octave between 5 and 10 kHz |
| E-C2 | A 1 kHz sine at four levels | Gain 0.777 / 0.773 / 0.690 / 0.529; THD 0.001% / 0.128% / 2.94% / 9.41%; even harmonics more than 97 dB below odd at every level |
| E-C3 | Compression (gain at level 1.0 ÷ gain at level 0.01) at 200 Hz, 1 kHz and 4 kHz | 0.582 / 0.681 / **0.931** |

| F-ID | Claim | Kind | Confidence |
|---|---|---|---|
| F-C1 | Contains a first-order low-pass with its corner near 1,235 Hz | I | very likely: a −3 dB point plus a slope near 6 dB/octave is the one-pole signature, and the 1 kHz small-signal gain of 0.777 is what a 1,235 Hz one-pole predicts |
| F-C2 | Contains a level-dependent, **symmetric** saturator | I | almost certain: THD rises with level, gain falls, and no even harmonics means a symmetric curve (tanh-like, not a diode-like one) |
| F-C3 | The filter comes **before** the saturator | I | very likely. Two hypotheses: H1 filter→saturator predicts much weaker compression at 4 kHz, because the filter shrinks the signal before it can clip; H2 saturator→filter predicts the same compression at every frequency. Measured 0.58 → 0.93: H1 fits, H2 doesn't |
| U-C1 | The exact curve of the saturator (tanh, arctan, polynomial) | U | Needs a finer test: the harmonic ratio vs level, compared against each candidate |

The hidden source, read afterwards: a one-pole low-pass at 1,234 Hz, then `tanh(1.6·x)/1.6`. F-C1 to F-C3 hold.
The lessons: **measure linear behaviour at small levels and nonlinear behaviour at large ones**, and **design the test
that tells hypotheses apart** (E-C3), which is Heuer's ACH in one line. The same method works on our own FL Studio
patches and on any plugin we own, without ever opening the plugin's code.

### 7.4 Drill D: compile our own code, then read what the machine sees

Target: a five-line critical-hit function we wrote, lowered to Python bytecode with `dis`:

```
  2 LOAD_FAST            roll
  4 LOAD_FAST            crit_chance
  6 COMPARE_OP           <
 12 POP_JUMP_FORWARD_IF_FALSE to 24
 14 LOAD_FAST            base
 16 LOAD_FAST            crit_mult
 18 BINARY_OP            *
 22 RETURN_VALUE
 24 LOAD_FAST            base
 26 RETURN_VALUE
```

Reading it back without the source: two values are compared, and a jump skips forward if the comparison is false.
One path multiplies two values and returns; the other returns one value unchanged. That is "if roll < chance:
return base × multiplier, else return base". This is the same shape a C compiler gives an `if` in x86 (a `cmp`, a
conditional jump, two `ret`s). Once you have seen it a dozen times you recognise it in any disassembly. In this
drill, the function and argument names survive. In a stripped native binary they won't, which is why REA warns
against trusting names even when they exist.

### 7.5 A paper worked example: the Archero design teardown, from published material

This is the teardown that serves Daniel's future game. Every input is public analysis or legitimate play; we never
open the game's package or touch its servers. These are **secondary sources**: the authors' observations become
our inferences until we check them in our own play.

**What published teardowns report:**

- **Core loop** (Grillova and Kumar, Deconstructor of Fun, Aug 2019): you move to dodge and stop to shoot
  automatically. Each run descends room by room, and at every level-up you draft one of three random abilities.
  Their reading is that the randomness gives three ways to feel good: getting the ability you hoped for, winning
  without it, or blaming the luck.
- **Meta progression** (same source): permanent talents, gear and gear fusion. Their critique is that the speed of
  talent upgrades and their actual contribution drift apart, that gear fusion needs rare matching items and becomes
  a grind, and that the late game feels unrewarding. They estimated the game left a large share of its possible
  long-term revenue unrealised.
- **Structural tension** (Grillova, Naavik, Oct 2022, comparing Archero with Survivor.io): roguelike runs and
  permanent power growth work against each other. Players hit a power wall early. A player needs only one hero and
  one gear set, so later spending buys little visible progress.

**Turning observations into design questions (ours, not theirs):**

| Observed problem (secondary) | Design question for our game | Teardown habit that applies |
|---|---|---|
| Permanent power fights run-based fun | Can new weapons be **sideways** (new play styles at equal power) rather than straight up? | Separate behaviour from design choice: the genre's ability draft is a mechanic we may use; the power curve is a choice we may change |
| Late-game upgrades feel worthless | Is our upgrade curve smooth, with soft caps we can **show** the player? | Drill B: a soft cap is easy to measure and hard to explain; tell the player rather than hide it |
| Grind-gated gear fusion | Can new weapons and effects ship free, with skill-based unlocks? | Write it as a spec with MUSTs we can test, not an impression |
| Monetisation leans on luck | What do we sell, if anything, that does not touch power? | Out of scope for teardown: a values decision for Daniel |

**What we must not take:** the name, characters, art, icons, UI layout, ability names and descriptions, sound,
and any table of numbers copied from the game's files. Section 10.4 explains why: *Tetris v. Xio* found
infringement in a game that copied look and feel even though the rules themselves were free. A legitimate next step
for us is a **play log**: record our own sessions, frame-step them with `arsenal.media`, and log observed numbers
the UI shows (costs, damage numbers) as observations with frame references.

---

## 8. A twelve-week learning path for a small team

**Who:** Daniel plus two to four agent seats. Roles rotate weekly so everyone works both sides of the wall.
**Rhythm:** Monday, the question checklist and a registered prediction. Tuesday to Thursday, the drill. Friday, the ledger,
a one-page report, the prediction score, and a **teach-back** (a Forest Walk: predict before look, then explain it back).
**Rule:** every week produces a ledger and a scored prediction. Hours alone do not count (section 1.6).
**Prerequisite for weeks 4, 9 and 11:** a disposable VM exists (Daniel's decision; section 11).

| Week | Track | Goal | Read | Do (legal target) | Deliverable |
|---|---|---|---|---|---|
| 1 | All | The method and the notebook | This report §1-4; ICD 203 standard 3 (2 pages); REA's staged workflow | Drill A on three of our own files (a WAV, a PNG, one house JSON); fill in the checklist, register and ledger | Three ledgers; one byte map |
| 2 | Software | Read what compilers write | OST2 Arch1001 (first half); Yurichev chapters 1-3 | 30 Compiler Explorer pairs: write, predict the assembly, compile, compare (vary one thing each time) | A "shapes" cheat-sheet in our own words; prediction hit rate |
| 3 | Software / formats | Formats as executable specs | Kaitai docs; ImHex pattern docs | Write a `.ksy` for the WAV (from Drill A), then for a file type we own but don't know yet; round-trip test it | A `.ksy` that parses 10 of our files; a list of unknown fields |
| 4 | Software | First real binaries (VM) | Ghidra Beginner class | crackmes.one difficulty 1-2 (three of them); challenges.re level-1 listings (no VM needed for listings) | Write-ups explaining the method, with no answers published |
| 5 | Graphics | See a frame | Courrèges' GTA V study, part 1; Spector.js README | Capture one of **our own** `arsenal/web` pages with Spector.js; draw its pass graph; predict each pass's output before opening it | Pass graph plus a ledger; prediction score |
| 6 | Graphics / feel | Recreate an effect | *Juice It or Lose It*; three Trümpler breakdowns | Pick one corpus shader or one hit-flash from our own recording; spec from frames first, then build, then A/B (section 2.5) | Spec, our build, a side-by-side strip, the diff ledger |
| 7 | Games (code) | Read game feel in source | Celeste `Player.cs`; Swink's *Game Feel* ch. 1-3 | Draw Celeste's player state machine; list every "forgiveness" timer with its value | State diagram; "feel constants" table with file:line references |
| 8 | Games (design) | The design teardown | DoF and Naavik Archero pieces; Shattered PD's item and upgrade code | A play log of a game we own (frame-stepped); a deconstruction (core loop, meta, economy as sources and sinks, upgrade curve); then the §7.5 questions answered for **our** game | Teardown report plus a one-page design brief that names what we will NOT copy |
| 9 | Audio | Measure a black box | Zavalishin ch. 1-3; Smith's *Introduction to Digital Filters* (selected) | Drill C on one of our own plugins/patches: small-signal response, THD vs level, attack/release; Plugin Doctor optional | Measured curves; a signal-flow diagram with confidence words |
| 10 | Audio | Recreate a sound | Syntorial's first lessons; Shirriff's DX7 chip teardown; skim Dexed's source | Rebuild three reference sounds by ear, then check against spectrograms; register a prediction of the patch before each check | Patches, spectrogram pairs, prediction score |
| 11 | Protocols / behaviour | The Samba method | Tridgell's "How Samba was written" | Differential-test two implementations of something of ours (two parsers, or a house module and its rewrite) with random inputs; Flare-On challenge 1 from the archive (VM) | A mismatch list with the domain stated; a write-up of challenge 1 |
| 12 | Capstone | A clean room, end to end | §5 of this report; Meeker on chardet | Analyst seat specs an effect or mechanic (ours or open source, MIT/Apache only); Daniel plus a reviewer seat act as monitor; a fresh implementer seat builds it; the verifier runs conformance tests | Spec, implementation, conformance tests, crossing log, retro |

**Graduation check (end of week 12):**

- Solve a difficulty-2 crackme in a VM within two hours, with a ledger.
- Produce a frame-referenced spec of an effect that another seat can build to pass an A/B check.
- Place a measured audio box's corner frequency within 5% and say correctly whether it is linear.
- Run one clean room with no contamination entries in the log.
- Show prediction calibration improving across the twelve weeks.

---

## 9. Mistakes that waste time

1. **Opening the disassembler before writing the question.** Hours vanish into "understanding the program". Fix:
   the checklist first, one question per session, the cheapest evidence first (documentation, observation, then code).
2. **Trusting names and strings.** `CheckLicense` might be dead code. A file called `effects.json` might not be read.
   REA's rule: never infer behaviour from names, strings or layout alone. Confirm with a parse or a run.
3. **Extrapolating past the search boundary.** Drill B: perfect on 1-10, 2.7x wrong at 40.
4. **One sample of a format.** Drill A's U-A1: the second file has a chunk the first didn't.
5. **Treating decompiler output as source.** It is an inference from one tool. Decompiler Explorer exists because
   different decompilers disagree.
6. **Repeating the same analysis and hoping.** Name the changed input or stop.
7. **Not recording versions and hashes.** Next week nobody can tell which build the finding was about.
8. **Reading the solution at the first wall.** It cuts off the feedback that makes practice work. Use the hint ladder.
9. **Staying at a comfortable difficulty.** Ericsson's arrested development. Move up once you solve a level without effort.
10. **Measuring a nonlinear system at the wrong level.** Drill C used a 0.001 impulse for the linear response on purpose.
11. **Letting a fragment cross the wall.** A "quick snippet" pasted into the clean seat's chat ends the clean room.
12. **Picking a target that is legally or ethically off-limits.** Anti-tamper, DRM and online clients cost days and
    end in a dead end at best. Choose practice grounds built for it.
13. **Running a sample on the host.** On this machine (no Defender, no updates by choice) it is the one mistake that
    cannot be undone.
14. **Calling a broad investigation complete with questions still open.** Revisit the checklist and mark each
    question honestly (REA).

---

## 10. Legal notes (jurisdiction-aware; not legal advice)

**Scope rule for the whole arsenal.** We reverse engineer to understand, to learn from design, to interoperate,
to analyse what we own or are allowed to analyse, to secure our own systems, and to rebuild in a clean room. We do
**not** crack DRM or licence checks, pirate, cheat in online games, bypass anti-cheat or anti-tamper, write or
deploy malware, or enter systems we do not own. Where a technique is dual-use, this report describes it at the
level of understanding only.

### 10.1 United States

- **Disassembly for access to unprotected ideas can be fair use.** In *Sega v. Accolade* (9th Cir. 1992), Accolade
  disassembled Genesis games to learn the interface requirements and then wrote its own games. The court held that
  disassembly is fair use when it is the only way to reach the unprotected functional elements and there is a
  legitimate reason to reach them.
- **Intermediate copies made while reverse engineering can be fair use.** In *Sony v. Connectix* (9th Cir. 2000),
  Connectix copied the PlayStation BIOS repeatedly while studying it. Its emulator contained no Sony code, and the court
  found the intermediate copying fair.
- **How you obtained the copy matters.** In *Atari Games v. Nintendo* (Fed. Cir. 1992), Atari got a copy of
  Nintendo's lockout program from the Copyright Office under false pretences. That conduct, and copying beyond what was
  needed, defeated its fair-use defence even though reverse engineering itself was recognised.
- **DMCA §1201** makes it unlawful to circumvent a technological measure that controls access to a work,
  separately from copyright infringement. The exemptions are narrow: §1201(f) for interoperability (lawfully
  obtained program, information not otherwise available, analysis limited to interoperability); §1201(g) for
  encryption research (good-faith effort to get authorisation first); §1201(j) for security testing (owner's
  authorisation required). There are also the Librarian of Congress's triennial exemptions in 37 CFR 201.40, which
  renewed good-faith security research on lawfully acquired devices in October 2024. **Our practice plan
  circumvents nothing.** Every ground in section 2.2 is unprotected or built to be solved.
- **Contracts can take away what copyright allows.** *Bowers v. Baystate* (Fed. Cir. 2003) enforced a shrink-wrap
  ban on reverse engineering. *Davidson & Associates v. Jung* (8th Cir. 2005, the bnetd case) held that users of
  Blizzard's games had waived reverse-engineering rights by accepting the EULA and terms of use. **Read the EULA before any
  code-level teardown of a product we bought.** Observing a game by playing it normally is a different act from
  disassembling it, but terms of service can restrict data mining, automation and traffic capture too.
- **Trade secrets.** The Defend Trade Secrets Act excludes reverse engineering and independent derivation from
  "improper means" (18 U.S.C. §1839(6)(B)). But breaching an NDA or a confidentiality duty is improper. ReactOS bars
  NDA material for this reason.
- **Computer Fraud and Abuse Act and wiretap law.** Probing systems we don't own, or capturing traffic between other
  people, is out of bounds whatever the purpose. EFF's Coders' Rights FAQ is a good plain-language map.
- **Patents.** A game mechanic can be patented even though copyright does not cover it. Check before building any
  distinctive, recent mechanic.

### 10.2 European Union (and the UK)

- **Directive 2009/24/EC, article 5(3):** a lawful user may observe, study or test how a program works, to find
  the ideas and principles behind it, while doing what the licence allows (loading, displaying, running). **Article
  8 makes contract terms against this void.** This is the strongest legal footing anywhere for teardown by
  observation.
- **Article 6:** decompilation is allowed only for interoperability with an independently created program. The
  conditions: a lawful user; the information not already readily available; only the parts needed. The information may
  not be used for other purposes, passed on except as interoperability needs, or used to build a substantially similar
  program. **Learning a game's design is not an article-6 purpose**, so EU design teardowns stay at the article-5(3)
  level of observation.
- ***SAS Institute v World Programming*** (CJEU C-406/10, 2012): functionality, programming languages and data file
  formats are not protected; a licence cannot stop observing, studying and testing; but copying a manual's text can
  infringe the manual.
- **UK:** the Copyright, Designs and Patents Act ss.50B and 50BA mirror articles 6 and 5(3), and s.296A voids contrary terms.

### 10.3 Assets versus mechanics

The US Copyright Office's guidance is explicit that copyright does not protect a game's idea, its name or title, or
its method of play. Rule text and artwork can be protected. So the **mechanics** of an auto-shooting room crawler
with an ability draft are free to use. The **art, sound, text, character designs, names and specific
presentation** are not. Names and logos are also trademarks.

### 10.4 Look and feel: the trade-dress caveat

*Tetris Holding v. Xio Interactive* (D.N.J. 2012) found infringement in *Mino*. The court accepted that the
rules of Tetris are free, but held that copying the game's specific visual expression (pieces, board, look) so
closely that the two were nearly indistinguishable was infringement. *Spry Fox v. Lolapps* (W.D. Wash. 2012)
let a claim against a reskinned clone of *Triple Town* go forward, and the case settled. **For our game:** take the
genre, make the look, feel, names and numbers our own, and do not put our screen next to theirs and match it.

### 10.5 Open-source licences are terms too

GPL code we read is fine to learn from. Copying it into a closed product brings GPL obligations. AGPL (Diaphora)
reaches network use. CC BY-NC-SA (most of the shader corpus) forbids commercial use. "Study only" means study only.

### 10.6 Tool-specific terms

RenderDoc's maintainers state the tool is for debugging your own programs. Capturing commercial games you did not make is
against the project's policy and not discussed in its channels; open-source projects and your own work, including games made
with Unreal or Unity, are fine. IDA Free, IDA Home and Binary Ninja's free tiers are licensed for non-commercial
use only. A future commercial game would need commercial licences or Ghidra (Apache-2.0).

---

## 11. Host safety

This machine runs with Windows Defender off and updates blocked by the owner's choice. That is settled and not
argued here. It means:

- **Never run an untrusted binary, script, firmware image, document or capture on the host.** That covers crackmes,
  Flare-On challenges, downloaded samples, and Office or PDF files from strangers.
- **Analyse inside a disposable VM or sandbox, with a snapshot taken before.** Turn networking off unless the drill needs it.
  Revert after. FLARE-VM's own README says to install it only in a VM, and it expects protections disabled
  **inside** the VM.
- **No VM or sandbox is enabled today** (section 0, finding 6). Turning on Windows Sandbox or Hyper-V is a system
  setting. It is Daniel's decision, and I have not touched it.
- **Keep samples out of the repo.** Store them under a scratch folder outside `E:\AI-Setup` (not on the X:\ ramdisk,
  which is for logs and temp files only). Store them zipped with a password, as crackmes.one and Flare-On do, so
  nothing executes by accident. Record their hashes in the evidence register; never commit them.
- **Static-only work on the host is fine** when nothing executes: reading an assembly listing, hex-viewing a file,
  or Ghidra's static analysis of a known-safe binary we built. Browser-hosted grounds (Compiler Explorer, pwn.college,
  Microcorruption, picoCTF's successor) need nothing local.
- **Uploading is publishing.** Decompiler Explorer keeps what you upload. Upload only our own or already-public samples.

---

## 12. Routing table: practice and teardown questions to first tools

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| "How does this effect look, frame by frame?" (our recording, a public trailer) | `py -m arsenal.media frames` / `sheet` / `shots` | Timing in frames, shapes, colours, layering order, what reacts to what | How it is computed (sprite, shader, mesh); anything off-screen |
| Our own WebGL page or shader | Spector.js | Every draw call, shader, texture and state change in one frame | Why the author chose it; performance on other GPUs |
| Our own native or Godot build | RenderDoc | Passes, render targets, shader code, pipeline state | Gameplay logic; CPU-side decisions |
| A game's progression or economy (a game we play legitimately) | A structured play log plus a deconstruction template, then published teardowns | The loops, visible numbers, pacing, offers | Server tables, true drop rates (unless published), designer intent |
| Open-source game or engine code | Read the source with one question, then draw the state machine | Exact rules and constants | Whether a shipped commercial build matches; asset licences (often differ from code) |
| An unknown file format (ours or open) | Hex view (ImHex or Python `struct`), then a Kaitai `.ksy` | Field layout, sizes, internal invariants (Drill A) | The meaning of opaque fields; variants not in the sample |
| A practice binary (crackme, Flare-On, our own compiled program), in a VM | Detect It Easy, then Ghidra | Compiler and packer identity; functions, strings, pseudocode | Runtime values (needs a debugger); intent; names may lie |
| A .NET assembly we own or may examine | ILSpy | Near-source C# | Obfuscated names' meaning; native interop internals |
| "What did the compiler do with my code?" | Compiler Explorer | The exact instructions per source line | Behaviour of other compilers or flags (change one and recompile) |
| An audio plugin or patch we own (as a black box) | Test signals plus measurement (numpy, Plugin Doctor) | Frequency response, THD vs level, even/odd harmonics, attack/release, block order via a discriminating test (Drill C) | Exact internal algorithm; behaviour at signals not tested |
| A sound in a recording | Spectrogram (Audacity, Sonic Visualiser), then rebuild by ear | Partials, envelopes, modulation rates | The original patch (many patches fit one sound) |
| A protocol between our own components | Capture on our own machine (Wireshark, Redis `MONITOR`), then differential testing | Message vocabulary and sequences; mismatches against a second implementation | Rare paths never exercised; intent |
| A circuit board we own | Photographs plus chip markings plus datasheets (Name that Ware habits) | Parts, buses, likely architecture | Firmware behaviour |
| A CPU or GPU microarchitecture question | Microbenchmarks (pointer chasing, Chester Lam's method) | Latency steps, cache sizes, bandwidth | Why it was designed so; undocumented policies |
| "Is our rebuild equivalent?" | Conformance or differential tests (Wine, Samba) | Every mismatch inside the tested domain (Drill B) | Equivalence outside the sampled domain |
| "What changed between two versions?" (our builds) | BinDiff / Diaphora, or a source diff | Which functions changed and how much | Why they changed |

---

## 13. Lessons the house should keep (trigger-phrased)

1. **Use when** starting any teardown, **before** opening a tool: write the question checklist with the evidence each
   answer needs, and fingerprint the target (hash, version, tool versions). **Don't when** the "teardown" is just
   reading a complete source repository. Use ordinary code reading for that.
2. **Use when** about to check any guess about a target, **before** looking: register the prediction (forecast
   registry), then score it. **Don't when** the check is a pure lookup with no guess involved.
3. **Use when** a model of a target fits the observed range, **before** relying on it outside that range: run a
   differential test well beyond the observed range, including errors, and state the tested domain in the claim. **Don't
   when** the claim is explicitly scoped to the observed range.
4. **Use when** writing any finding, **before** saving it: label it Observation, Inference or Unknown, cite evidence
   IDs, use the ICD 203 likelihood words for inferences, and record the search boundary. **Don't when** the note is a
   scratch thought that will not leave the session.
5. **Use when** a name, string or filename suggests what code or data does, **before** writing that down as
   behaviour: confirm with a parse, a run or a test. **Don't when** the name is all the question asks about.
6. **Use when** rebuilding something from a teardown, **before** writing code: write the spec with required
   behaviour and design choices in separate sections, preferably as conformance tests. **Don't when** the target is our own code
   and no outside expression is involved.
7. **Use when** staffing a clean room with agent seats, **before** calling it clean: run the implementer in a fresh
   session with no access to the target, pass only monitor-approved specs, and log every crossing. **Don't when** the
   target is a well-known open-source project the model has likely seen, or the goal is to relicense someone's code. Then it is not a clean room.
8. **Use when** practising, **before** choosing a target: pick a ground built to be reversed (our own code, crackmes.one,
   challenges.re, Flare-On archives, OST2, open-source games). **Don't when** the target is a commercial product's protection,
   an online game, or anything whose terms forbid it.
9. **Use when** a drill involves any untrusted binary, document, firmware or capture, **before** running or opening it:
   move it into a disposable VM with a snapshot and networking off, and keep the sample out of the repo. **Don't when** the
   work is static reading of something we built ourselves.
10. **Use when** a learner is stuck, **before** giving the answer: walk the five-rung hint ladder. **Don't when** the
    clock matters more than the learning (a production incident). Then give the answer.
11. **Use when** measuring an audio box, **before** reading a frequency response: drive it at a small level for the linear
    picture and at large levels for the nonlinear one, and design one test whose result differs between your rival
    hypotheses. **Don't when** the device is known to be linear by specification and you only need a gain.
12. **Use when** doing a design teardown for the Archero-style game, **before** drafting mechanics: work from play and
    published analyses, log numbers with frame references, and list what we will not copy (names, art, text, UI, number
    tables). **Don't when** tempted to open the game's package or capture its traffic. That is outside our scope.

---

## 14. Gaps: where the house needs a new tool or verb

| ID | Gap | Why it matters | Smallest useful version |
|---|---|---|---|
| G1 | **A `teardown` verb** that scaffolds a folder with the question checklist, evidence register, finding ledger (O/I/U) and end-of-run checklist revisit | The discipline is the skill; a template makes it the default | `py agent_cli.py teardown new <name>` writing four Markdown tables under `state/teardowns/<name>/`, with sha256 and tool-version capture helpers |
| G2 | **No disposable VM or sandbox enabled** | Blocks every untrusted-binary drill (weeks 4, 11, part of 12) | Daniel decides: enable Windows Sandbox (simplest, wiped on close) or Hyper-V with a snapshot discipline; then a `.wsb` config with networking off and a read-only mapped samples folder |
| G3 | **A differential-testing harness** | Drill B and the Samba/Wine method need it for every rebuild | A verb that takes two callables or commands plus an input generator, treats errors as outputs, bisects edges, and prints the tested domain with the result |
| G4 | **An audio measurement verb** in `arsenal.media` | Drill C should be one command, with receipts | `media measure` running impulse/sweep, THD vs level, even/odd ratio and block-order discrimination on a render, in the house result shape with its `blind` field |
| G5 | **A/B comparison for effect recreation** | Section 2.5 needs a synced side-by-side with a difference metric | `media ab <ref> <ours>`: time-aligned strips plus per-frame difference, built on `frames`/`sheet` |
| G6 | **A taint register for clean rooms** | We must prove who saw what | A substrate stream: seat, target hash, document hash, direction, approver; plus a "clean session" launcher that denies tool access to target paths |
| G7 | **A drill generator seat** | Today's drills were written by the same seat that solved them; real practice needs blind targets | One seat writes hidden targets (curves, formats, audio boxes, tiny compiled programs) with answer keys sealed until the ledger is filed |
| G8 | **Toolchain not installed** (Ghidra + JDK, ImHex, Detect It Easy, Spector.js, Sonic Visualiser) | Weeks 2-5 and 9 assume them | An install list for Daniel's approval, not done here |
| G9 | **Prediction scoring per drill** | Calibration is the feedback loop of section 2.1 | Tie the teardown ledger's predictions to the existing forecast registry and calibration verb |

---

## 15. Sources

Practice and expertise
- https://pmc.ncbi.nlm.nih.gov/articles/PMC6731745/ : Macnamara and Maitra (2019), preregistered replication of Ericsson et al. (1993); 26% vs 48% variance; best vs good violinists.
- https://eric.ed.gov/?id=EJ471947 : Ericsson, Krampe and Tesch-Römer (1993), *Psychological Review* 100:363-406, the original deliberate-practice paper.
- https://www.ida.liu.se/~nilda08/Anders_Ericsson/Ericsson_delib_pract.pdf : Ericsson (2006), Cambridge Handbook chapter; automaticity and arrested development.
- https://challenges.re/ : Dennis Yurichev's 87 exercises; CC BY-SA 4.0; no solutions by design.
- https://yurichev.com/writings/RE4B-EN.pdf : Yurichev, *Reverse Engineering for Beginners* (free PDF).
- https://crackmes.one/faq and https://crackmes.one/upload/crackmerules : purpose, VM advice, difficulty 1-6, banned content.
- https://flare-on.com/ : Mandiant FLARE's annual challenge; archives and solutions 2014-2025.
- https://p.ost2.fyi/ : OpenSecurityTraining2 catalogue (Arch1001, Arch1005, Arch2001, RE3011, RE3201).
- https://pwn.college/ : Arizona State University's free platform.
- https://picoctf.org/ : CMU picoCTF, moving into CyLab Security Academy.
- https://www.bunniestudios.com/ : bunnie Huang's blog and Name that Ware.

Tools
- https://github.com/NationalSecurityAgency/ghidra : Ghidra, Apache-2.0; `GhidraDocs/GhidraClass` training.
- https://github.com/compiler-explorer/compiler-explorer : Compiler Explorer, Matt Godbolt, BSD-2-Clause.
- https://dogbolt.org/ : Decompiler Explorer; uploads retained; 2 MB limit.
- https://github.com/baldurk/renderdoc : RenderDoc, MIT; own-programs-only policy.
- https://github.com/BabylonJS/Spector.js : Spector.js, MIT, WebGL capture.
- https://kaitai.io/ : Kaitai Struct; compiler GPL-3.0+, runtimes MIT.
- https://github.com/WerWolv/ImHex : ImHex, GPL-2.0 with LGPL library.
- https://github.com/google/bindiff : BinDiff, Apache-2.0 since 2023.
- https://github.com/joxeankoret/diaphora : Diaphora, AGPL-3.0, IDA plugin.
- https://github.com/x64dbg/x64dbg : x64dbg, GPL-3.0.
- https://github.com/icsharpcode/ILSpy : ILSpy, MIT.
- https://github.com/horsicq/Detect-It-Easy : Detect It Easy, MIT.
- https://hex-rays.com/ida-free : IDA Free, non-commercial, cloud x86/x64 decompiler.
- https://binary.ninja/2026/07/28/pricing-changes.html : Binary Ninja 6.0 pricing and free-tier limits.
- https://github.com/mandiant/flare-vm : FLARE-VM, Apache-2.0, VM-only.
- https://github.com/mermaid-js/mermaid : Mermaid, MIT.
- https://github.com/morluto/rea : REA by morluto, MIT; the discipline this report adapts.
- https://github.com/demberto/PyFLP : PyFLP, unofficial FL Studio project parser, GPL-3.0 (example of community format work).

Graphics, games, audio
- https://fabiensanglard.net/gebb/ : Fabien Sanglard's Game Engine Black Books, free PDFs and LaTeX sources.
- https://github.com/id-Software/Quake-III-Arena : id Software source release, GPL-2.0, no game data.
- https://github.com/NoelFB/Celeste : Celeste player code released as a learning resource, MIT.
- https://github.com/00-Evan/shattered-pixel-dungeon : Shattered Pixel Dungeon, GPL-3.0.
- https://github.com/OpenMW/openmw : OpenMW, GPL-3.0, requires owning Morrowind.
- https://github.com/godotengine/godot : Godot, MIT.
- https://www.adriancourreges.com/blog/2015/11/02/gta-v-graphics-study/ : Adrian Courrèges' frame study.
- https://simonschreibt.de/game-art-tricks/ : Simon Trümpler's Game Art Tricks.
- https://www.gdcvault.com/play/1016487/juice-it-or-lose : Jonasson and Purho, *Juice It or Lose It*, GDC Europe 2012.
- https://www.deconstructoroffun.com/blog/2019/8/9/why-archero-banked-25m-but-leaves-25m-hanging-hlx9n : Grillova and Kumar on Archero's loop and meta (2019).
- https://naavik.co/deep-dives/survivorio-archeros-footsteps/ : Grillova on Survivor.io vs Archero progression (2022).
- https://www.righto.com/2021/11/reverse-engineering-yamaha-dx7.html : Ken Shirriff's DX7 sound-chip die teardown.
- https://chipsandcheese.com/p/measuring-gpu-memory-latency : Chester Lam's pointer-chasing method.
- https://github.com/asb2m10/dexed : Dexed, GPL-3.0; msfa core Apache-2.0 (Raph Levien).
- https://archive.org/details/the-art-of-va-filter-design-rev.-2.1.2 : Zavalishin, *The Art of VA Filter Design* rev. 2.1.2.
- https://ccrma.stanford.edu/~jos/RO/Online_Books_Signal_Processing.html : Julius O. Smith III's free DSP books.
- https://www.syntorial.com/learn-more/ : Syntorial ear-training method and lesson count.
- https://gearspace.com/board/reviews/1327941-ddmf-plugindoctor.html : Plugin Doctor review (analysis modes).

Analysis and reporting
- https://archive.dni.gov/files/documents/ICD/ICD-203.pdf : ODNI ICD 203 Analytic Standards (2015, amended 2022).
- https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf : US Government Tradecraft Primer (2009): key assumptions check, ACH, red team.
- https://www.ialeia.org/docs/Psychology_of_Intelligence_Analysis.pdf : Richards Heuer, *Psychology of Intelligence Analysis*, ch. 8 on ACH.
- https://en.wikipedia.org/wiki/Words_of_estimative_probability : overview of Sherman Kent's 1964 essay (secondary).
- https://www.rfc-editor.org/rfc/rfc2119 : Scott Bradner, RFC 2119 (1997), MUST/SHOULD/MAY.

Clean rooms
- https://jolt.law.harvard.edu/articles/pdf/v03/03HarvJLTech209.pdf : Contreras, Handley and Yang (1990) on *NEC v. Intel*; three-team clean room; Davidian's records.
- https://www.samba.org/ftp/tridge/misc/french_cafe.txt : Andrew Tridgell, "How Samba was written" (2003).
- https://reactos.org/intellectual-property-guideline/ : ReactOS IP guideline.
- https://www.linux.com/news/reactos-suspends-development-source-code-review/ : ReactOS 2006 audit (secondary).
- https://reactos.org/project-news/reset-reboot-restart-legal-issues-and-long-road-03/ : ReactOS's own account of the audit and of US vs other countries' clean-room expectations.
- https://forum.winehq.org/viewtopic.php?t=7138&start=25 : Wine's no-reverse-engineering-of-Microsoft-code stance (forum, secondary).
- https://www.winehq.org/docs/en/winedev-guide.html : Wine Developer's Guide, conformance tests (not fetched today; from search).
- https://en.wikipedia.org/wiki/Clean-room_design : Phoenix BIOS history (secondary).
- https://heathermeeker.com/2026/04/09/the-chardet-controversy-open-source-and-the-ai-clean-room/ : Heather Meeker on chardet and AI clean rooms.

Law
- https://www.law.cornell.edu/uscode/text/17/1201 : 17 U.S.C. §1201, with (f), (g), (j).
- https://www.ecfr.gov/current/title-37/chapter-II/subchapter-A/part-201/section-201.40 : 37 CFR 201.40 exemptions (2024 rulemaking).
- https://law.resource.org/pub/us/case/reporter/F2/977/977.F2d.1510.92-15655.html : *Sega v. Accolade*, 977 F.2d 1510 (9th Cir. 1992).
- https://law.justia.com/cases/federal/appellate-courts/F3/203/596/474793/ : *Sony v. Connectix*, 203 F.3d 596 (9th Cir. 2000).
- https://law.resource.org/pub/us/case/reporter/F3/320/320.F3d.1317.01-1109.01-1108.html : *Bowers v. Baystate*, 320 F.3d 1317 (Fed. Cir. 2003).
- https://www.law.berkeley.edu/archive/files/Davidson_v_Jung.pdf : *Davidson & Associates v. Jung*, 422 F.3d 630 (8th Cir. 2005).
- https://www.loeb.com/en/insights/publications/2012/06/tetris-holding-llc-v-xio-interactive-inc : *Tetris Holding v. Xio*, 863 F. Supp. 2d 394 (D.N.J. 2012), summary and opinion.
- https://en.wikipedia.org/wiki/Spry_Fox,_LLC_v._Lolapps,_Inc. : *Spry Fox v. Lolapps* (W.D. Wash. 2012), secondary.
- https://www.copyright.gov/register/tx-games.html : US Copyright Office on games: ideas, names and methods of play are not protected.
- https://uscode.house.gov/view.xhtml?req=granuleid%3AUSC-prelim-title18-section1839&num=0&edition=prelim : 18 U.S.C. §1839 (DTSA definitions).
- https://www.legislation.gov.uk/eudr/2009/24/article/5 , /article/6 , /article/8 : Directive 2009/24/EC arts 5, 6, 8.
- https://curia.europa.eu/juris/document/document.jsf?docid=122362&doclang=EN : *SAS Institute v World Programming*, C-406/10 (2012).
- https://www.eff.org/issues/coders/reverse-engineering-faq : EFF Coders' Rights reverse-engineering FAQ.
- *Atari Games Corp. v. Nintendo of America*, 975 F.2d 832 (Fed. Cir. 1992), and UK CDPA ss.50B, 50BA, 296A: cited from standing knowledge, not fetched today.

---

## Appendix A: the drill code (ours, run 2026-10-13)

`hidden_blackbox.py` (the target side; the analyst never opens it):

```python
import math
import numpy as np

def upgrade_cost(level: int) -> int:
    if level < 1:
        raise ValueError("level starts at 1")
    if level < 25:
        return int(math.floor(100 * 1.15 ** (level - 1) + 0.5))
    base = 100 * 1.15 ** 23
    return int(math.floor(base * 1.08 ** (level - 24) + 0.5))

_FS, _FC, _DRIVE = 48000, 1234.0, 1.6

def mystery_effect(x: np.ndarray) -> np.ndarray:
    a = math.exp(-2 * math.pi * _FC / _FS)
    y = np.empty_like(x, dtype=np.float64)
    s = 0.0
    for i, v in enumerate(x):
        s = (1 - a) * v + a * s
        y[i] = s
    return np.tanh(_DRIVE * y) / _DRIVE
```

`drills.py` (the analyst side), the core of each drill:

```python
# Drill A: build a WAV we own, then read it as bytes only
riff, riff_size, form = struct.unpack_from("<4sI4s", blob, 0)            # E-A3
cid, csz, fmt_tag, ch, rate, byterate, align, bits = struct.unpack_from("<4sIHHIIHH", blob, 12)  # E-A4
did, dsz = struct.unpack_from("<4sI", blob, 36)                            # E-A5

# Drill B: observe 1-10, fit, PREDICT level 40, then differential-test with errors as outputs
obs = {L: target.upgrade_cost(L) for L in range(1, 11)}
slope, icept = np.polyfit(np.arange(0, 10), np.log([obs[L] for L in range(1, 11)]), 1)
def outcome(fn, L):
    try: return fn(L)
    except Exception as e: return type(e).__name__
bad = [L for L in list(range(1, 61)) + sample if outcome(rebuilt2, L) != outcome(target.upgrade_cost, L)]
# ...then bisect the first level where the target raises

# Drill C: tiny impulse for the linear picture; sines at 4 levels for THD and even/odd;
# compression at 200 Hz / 1 kHz / 4 kHz to tell "filter then saturator" from the reverse
h = target.mystery_effect(imp) / 1e-3
db = 20 * np.log10(np.abs(np.fft.rfft(h)) / np.abs(np.fft.rfft(h))[0])

# Drill D: read our own function's lowered form
for i in dis.get_instructions(crit_damage): print(i.offset, i.opname, i.argrepr)
```

The full scripts and their output (`drills_output.txt`) were kept in the session scratchpad
(`...\scratchpad\re_practice\`). They are not in the repo. Turning them into a house drill pack is gap G7.
