# Software and binaries: the house reverse-engineering field manual

Status: current
Class: research
Arc: reverse-engineering-2026-10-13 (one of eight researcher lanes; this lane is SOFTWARE AND BINARIES)
Written: 2026-10-13, Vandor (claude seat), for Daniel's "I want us to know how to reverse engineer anything" ask

Everything below is in my own words. Tool docs, articles, statutes and court opinions are cited by URL in the Sources
list; people are credited by name. Direct quotes are under 15 words and attributed. The REA skill that triggered this
(`morluto/rea`, MIT) is credited where its discipline is adopted; its text is not copied beyond short quotes.

**This file teaches understanding, interoperability work, analysis of software we own or are permitted to analyse,
security research on our own systems, and clean-room rebuilding.** It deliberately does not give step-by-step for
cracking DRM or licence checks, piracy, online-game cheating, anti-cheat or anti-tamper bypass, or intrusion. Where a
technique is dual-use I describe it at the level of understanding and name the legal line. **None of this is legal
advice.** See section 11 before you point any tool at anything you did not write.

---

## 0. What you get from this report, in one screen

**The outcome.** A complete workflow for reading compiled software when you do not have the source: native binaries
(Ghidra, rizin/Cutter, IDA Free, Binary Ninja), live behaviour of software we own (x64dbg, WinDbg + Time Travel
Debugging, Frida, Process Monitor, API Monitor), managed code that decompiles almost back to source (ILSpy/dnSpyEx for
.NET, JADX for Android), Electron and JavaScript apps (asar, source maps, un-minifiers, un-bundlers), WebAssembly (WABT,
`wasm-decompile`), and file/save formats (Kaitai Struct, ImHex and 010 Editor templates, binwalk, entropy). Then a
routing table, a set of trigger-phrased lessons, and the gaps where the house needs a new tool or verb.

**The hardware analogy that holds the whole thing together.** Reverse engineering a binary is *die-shot analysis for
software*. The source code is the RTL/Verilog the designer wrote; the compiler is the fab. What ships is the
"die" — optimised, layout-scrambled, labels gone. A disassembler is the microscope that turns the die back into gates
(assembly). A decompiler is the analyst who looks at the gates and writes plausible RTL back (C-like pseudocode) — never
the *original* RTL, just one that behaves the same. And exactly like silicon, **how much you can recover depends on how
much metadata survived the fab.** That one fact decides your whole approach, so it leads section 1.

**Five findings that matter to the house tonight:**

1. **The managed/native split decides everything, and it is a one-command check.** Code compiled to a *managed*
   intermediate form — .NET CIL, Java/Android bytecode, Python `.pyc`, unstripped WebAssembly — keeps its symbol names
   and structure, so it decompiles to near-original source. Code compiled to *native* machine code (C/C++/Rust/Go, Unity
   IL2CPP) has thrown that away, so you get pseudocode and a lot of inference. I verified the split live: `python311.dll`
   (native) has no CLI header and exposes only 1,630 flat C exports; `System.Text.Json.dll` (.NET) still carries a
   `#Strings` heap with 3,751 readable identifiers like `JsonTypeInfo`1`. **Check which world you are in first** — it is
   the single highest-leverage move in this manual (section 1, section 4).

2. **Our own machine already proves the Electron supply-chain story.** I statically read the fuse wire out of a shipping
   Electron app on this box (Mullvad VPN, GPL-3.0, so fair game): `EnableEmbeddedAsarIntegrityValidation` is **off** and
   `OnlyLoadAppFromAsar` is **off**. That is the default for the overwhelming majority of Electron apps, and it is why an
   `app.asar` is a zip you can read in seconds: Electron apps are the one "compiled" format that usually isn't compiled
   at all (section 5). 219 source-map files even ship inside Mullvad's asar — that is the original authored TypeScript,
   handed to you.

3. **Entropy is a free X-ray and it reads our own files correctly.** A 4 KiB sliding-window entropy scan told the truth
   about five files on this disk with no parser at all: `app.asar` sits at ~4.5–5 bits/byte (text and code, readable),
   while our own `Enemy.flp` FL Studio project sits at **7.9+ bits/byte across its body** — and when I walked its chunk
   format the high-entropy mass turned out to be six `event id 213` blobs (plugin state, native + VST preset data) at a
   near-maximal 8.0 bits/byte. Entropy told me *where the opaque payloads were* before I understood the format
   (section 8). This is the firmware/save-file triage move.

4. **"Never infer behaviour from a name" is not pedantry — it is the method, and it is Daniel's own rule.** The REA
   discipline (observations vs inferences vs unknowns, inspect resources alongside code, bounded negative searches stay
   bounded) is the same spine as our method-baseline and the `root-cause-before-fixes` skill. A function called
   `validateLicense` might do nothing; a format field called `size` might be a count. In my worked examples every claim
   is tagged OBSERVED (I read the bytes) or INFERRED (I reasoned), and the FLP walk only earned "OBSERVED" because the
   parser *re-derived the declared chunk length exactly* — a falsifiable check, not a guess from field names.

5. **The host posture makes the safety rule non-negotiable, and it changes which tools we reach for.** This machine runs
   Defender off and updates blocked by Daniel's choice (not re-litigated). So: **unknown binaries, firmware, documents
   and captures are analysed inside a disposable VM or sandbox, never executed on the host, and samples never enter the
   repo.** A live example of why: binwalk had a path-traversal flaw (CVE-2022-4510) where merely *extracting* a crafted
   firmware image could run code — the extractor is attack surface, not just the sample (section 11). On a hardened box
   you might shrug; on ours it is a reboot-and-pray. Static-first, VM-for-anything-live is the house default.

---

## 1. The one question that routes everything: what survived the compiler?

Before you open any tool, answer one question about the target: **how much of the original program's structure and names
survived compilation?** Everything downstream — which tool, how good the output, how much you must infer — falls out of
the answer. There are three tiers.

**Tier 1 — Managed / bytecode (names and types survive; you get near-source back).**
.NET (CIL in a PE with a CLI header), Java and Android (`.class`, `.dex`), Python (`.pyc`), and WebAssembly with its
name section intact. These formats were designed to be *portable* and often *reflectable*, so the compiled file still
carries method names, type names, field names and a structured instruction set. A decompiler can reconstruct source that
is often 90–100% faithful. Analogy: the chip shipped *with its data sheet and pin labels still printed on the package.*

I proved names survive with a three-line Python example: compiling `def damage(base, crit_mult, is_crit): ...` and
reading the code object back shows `co_varnames = ('base','crit_mult','is_crit','bonus')` right there in the bytecode.
That is why a `.pyc` decompiles to readable code and a C `.exe` does not.

**Tier 2 — Native with metadata (structure gone, but hints remain).**
C/C++/Rust/Go/Swift compiled straight to machine code. The compiler has inlined, reordered, register-allocated and
discarded local names. But often *some* metadata survives: exported function names in a DLL, import tables naming which
OS APIs are called, RTTI/vtables in C++, Go's embedded module and function tables, debug symbols (PDB) if shipped, or
strings. You get assembly plus decent pseudocode, and the surviving hints are your handholds. Analogy: *the die with the
top metal layer labels sanded off, but the bond-pad names still legible.*

`python311.dll` is a clean Tier-2 example: native (no CLI header), but 1,630 named exports and 19 named imported DLLs
(`bcrypt.dll`, `WS2_32.dll`, …) told me its capability surface — crypto and sockets — before I read a single instruction.

**Tier 3 — Native, stripped and/or obfuscated (you infer almost everything).**
Symbols stripped, maybe packed or obfuscated, maybe Unity IL2CPP (C# turned into C++ then native, with a
`global-metadata.dat` sidecar that you must parse to get names back). You work from control flow, constants, syscalls and
behaviour. Analogy: *a decapped die with no labels at all — you trace traces.*

**How to tell the tier in under a minute (all static, all read-only):**
- `Detect It Easy` (`diec`) or a PE parser: is there a CLI header (byte-check data-directory index 14)? → .NET, Tier 1.
- File magic: `PK` zip that is really a `.jar`/`.apk`/`.aar` → Java/Android, Tier 1. `\0asm` → WebAssembly. `dex\n` → Dalvik.
- Entropy (section 8): whole-file > ~7.2 and flat usually means packed or compressed → you may need to unpack before any
  tier call is meaningful.
- Strings and imports: lots of readable identifiers → metadata survived; almost none → stripped, Tier 3.

This is exactly how the REA skill "routes the target first" before choosing a tool, and it is the same instinct as our
`plan-with-the-corpus` skill: identify the thing before you act on it.

---

## 2. The method (the discipline, lifted from REA and our own method-baseline)

Tools are the easy part. The discipline is what keeps a reverse-engineering session from turning into confident nonsense.
This is REA's spine restated in house terms, and it maps one-to-one onto our method-baseline and `root-cause-before-fixes`.

1. **Turn the request into a checklist of questions, each with the evidence that would answer it.** "How does the upgrade
   path work?" is not a task; "which function reads the save file's `level` field, and what writes it?" is. Write the
   checklist down; revisit it at the end and mark each item answered / partial / unresolved. Do not call a broad
   investigation complete while required questions are open.

2. **Route the target, then start with the smallest overview.** Pick the first tool from *what the target is* (section 1),
   not from habit. Open with an inventory or summary (sections, imports, exports, archive listing) before drilling. A
   summary-first pass is cheap and stops you decompiling 30,000 functions to answer a question the export table already
   answered.

3. **Separate OBSERVED from INFERRED from UNKNOWN, every single claim.** OBSERVED = you read the bytes / watched the call.
   INFERRED = you reasoned from observations. UNKNOWN = you have not established it. Never let static analysis masquerade
   as having watched execution — "the string `admin` appears near this branch" is not "this branch grants admin." Keep a
   finding ledger: each conclusion linked to its evidence, its confidence, the boundary you searched, and what is still
   open. (This is also our attribution discipline: evidence IDs, not vibes.)

4. **Inspect resources and configuration alongside code; never infer behaviour from a name.** A function name, a filename,
   a string constant are *leads*, not findings. Parse the actual resource (the manifest, the config blob, the asset) with
   a format-aware tool. My FLP example only became OBSERVED when the parser re-derived the declared chunk length — a name
   would never have earned that.

5. **Corroborate with the evidence type the claim requires.** A claim about *what the code can do* is answerable
   statically. A claim about *what it actually did at runtime* needs runtime evidence — and runtime evidence means running
   the thing, which means the VM rule (section 11) and the legal rule (section 10) both apply. Prefer static; escalate to
   dynamic only when static genuinely cannot answer the question.

6. **Do not repeat an identical analysis without a changed input.** If a decompile or a search returned nothing useful,
   changing nothing and running it again is wasted tokens and wasted time. Change the input, resolve the blocker, or
   record it as a bounded negative ("searched all exports for `license`, 0 hits, boundary = export table only").

7. **Work summary-first and page into detail.** Large graphs and huge functions overwhelm both you and the tool. Get the
   summary, select the one node/function/section that answers the question, then expand. REA calls this "work
   summary-first"; it is the same reason our `boot` distills to ~9k tokens — more context makes the work worse, not
   better.

8. **When you rebuild, separate observed behaviour from design choice.** If the goal is a clean-room reimplementation
   (section 9 and 12), write down "the original *does* X" (observed) distinctly from "we *choose* to do Y" (design). The
   clean-room wall lives exactly on that line.

---

## 3. Native binaries — the disassembler/decompiler tools

These turn machine code back into assembly (disassembly) and then into C-like pseudocode (decompilation). Pick one as
your primary and learn it deeply; they all read the same binaries.

### The four you should know

**Ghidra** — the house default. Free, open source (Apache-2.0), from the NSA. Full interactive disassembler *and*
decompiler, hundreds of processor families, runs on Windows/macOS/Linux, needs a JDK (recent releases want JDK 21+; check
the release you download). Scriptable in Java and Python (PyGhidra). Crucially it has a **headless analyzer**
(`support/analyzeHeadless`) so you can script analysis with no GUI — and a `-readOnly` flag that disables commits, which
is the right default when you are only reading. Ships with a full teaching course (Beginner → Advanced → Debugger → BSim)
in `GhidraDocs/GhidraClass`. Self-description: "a software reverse engineering (SRE) framework." If we standardise on one
native tool, this is it: free, scriptable, and the course means Daniel can learn it himself.

**rizin + Cutter** — the open CLI + GUI pair. rizin is a reverse-engineering framework (LGPL-3.0/GPL-3.0), a cleaned-up
fork of radare2 "with a focus on usability, features and cleanliness"; Cutter (GPL-3.0) is its official GUI. Add the
`rz-ghidra` plugin and you get Ghidra's decompiler inside Cutter. Scriptable from Python via `rzpipe`. Reach for this
when you want a scriptable pipeline or live on the command line; FLIRT-style signatures help on stripped binaries.

**IDA Free** — the industry-standard disassembler, free tier. Free but **non-commercial only**, x86/x86-64 only, with a
cloud-based decompiler for those two architectures, local x86/x64 debugging, no IDAPython or SDK. Paid tiers climb fast:
IDA Home ($365/yr, one architecture, adds IDAPython), IDA Pro Essential/Expert/Ultimate (€1,099 to €8,599/yr). Use IDA
Free when a tutorial or a sample is written for IDA; otherwise Ghidra does the same job with scripting and no licence
wall. Its on-disk databases are `.idb`/`.i64`.

**Binary Ninja** — the ergonomic commercial one. Free tier ($0, evaluation/education, non-commercial, 5 architectures,
GUI-only plugins); Personal $199; Commercial $1,799; Ultimate $3,499. Its multi-level intermediate language (lifting
assembly up through several readable tiers) is the nicest to read and its API is pleasant. A "buy if we fall in love
with RE" option, not a starting cost.

### Supporting cast (all free unless noted)

- **Detect It Easy (`die`/`diec`, MIT)** — first contact. Identifies file type, compiler, packer, protector. Run `diec`
  on anything before you open a heavy tool; it tells you the tier and whether the thing is packed.
- **capa (Apache-2.0, Mandiant/FLARE)** — rule-based capability detection for PE/ELF/.NET/shellcode, mapped to MITRE
  ATT&CK, with Ghidra/IDA plugins. Answers "what can this program *do*?" without you reading every function. (FLOSS, same
  team, pulls obfuscated strings out of malware.)
- **BinDiff (Apache-2.0, Google)** — diff two binaries' disassembly to find what changed between versions. This is the
  "make releases of new weapons" workflow in reverse: diff v1.0 vs v1.1 of anything to see exactly which functions a
  patch touched. Ships plugins for IDA/Binary Ninja/Ghidra.
- **PDB symbols** — if the vendor shipped or published a `.pdb`, load it; names come back for free. Microsoft's public
  symbol server covers Windows system DLLs.

### The native workflow (static, on something we own or are permitted to analyse)

1. `diec target.exe` → tier, compiler, packed? Entropy check if unsure.
2. Ghidra: import, auto-analyse. Read the **Symbol Tree** (imports/exports) and **Strings** first — these are your map.
3. From the checklist question, find an entry point: an exported function, an imported API you care about
   (`CreateFileW`, `RegOpenKeyEx`, a socket call), or a distinctive string, and follow references *to* it.
4. Read the decompiler output for those functions. Rename variables as you understand them — your renames are your notes.
5. Log each finding as OBSERVED/INFERRED with the address as the evidence ID. Close the loop on the checklist.

What native analysis *cannot* tell you: actual runtime values, which branch really executes on real input, timing, or
anything data-dependent. For that you need section 6 — and the VM rule.

---

## 4. Managed code — where you get the source back

This is the happy path, and it is where an "archero-style upgrade path" investigation most often lives, because mobile
and indie games are frequently Tier 1.

### .NET (C#, F#, VB.NET → CIL in a PE)

A .NET assembly is a PE file with a **CLI header** (optional-header data directory index 14) pointing at a metadata root
whose signature is `BSJB` (0x424A5342). Inside are five streams: `#~` (compressed metadata tables), `#Strings`
(identifier names — *they survive*), `#US` (user strings), `#GUID`, `#Blob` (signatures/constants). I read all five out
of `System.Text.Json.dll` live; the `#Strings` heap alone held 3,751 readable names. That is why .NET decompiles so well.

- **ILSpy (MIT)** — the open .NET decompiler. GUI on Windows/Linux/macOS, plus **`ilspycmd`** (a `dotnet` CLI tool) for
  scripted whole-project decompilation, plus the `ICSharpCode.Decompiler` library if we want to call it from our own
  code. Does BAML→XAML, can generate PDBs, handles ReadyToRun. This is the house default for .NET.
- **dnSpyEx (GPLv3)** — the maintained continuation of dnSpy (original archived). Decompiler (built on ILSpy) *plus* a
  live debugger and assembly editor for .NET and Unity. The debugger is the draw: set breakpoints in decompiled C# of an
  app you own and watch it run — the single most instructive thing you can do to learn how a game's systems fit together.

Note the R2R/mixed-mode wrinkle: `System.Text.Json.dll` reported *not ILONLY* with a ReadyToRun native header present —
modern .NET sometimes AOT-compiles a native copy alongside the CIL. The CIL is still there and still decompiles; just
know the file is both.

### Java and Android (`.class`, `.jar`, `.dex`, `.apk`)

- **JADX (Apache-2.0)** — the one to use for Android. Decompiles Dalvik `.dex` from APK/AAB/APKS straight to Java, decodes
  `AndroidManifest.xml` and resources, has deobfuscation and a smali view, CLI and GUI, needs JDK 11+. The developers are
  honest: "in most cases jadx can't decompile 100% of the code." Start here for any `.apk`.
- **Vineflower (Apache-2.0)** — the best current plain-Java decompiler, a continuation of Fernflower/ForgeFlower/
  Quiltflower; understands modern Java (records, sealed classes, pattern matching). Use it on `.jar`/`.class` and as a
  drop-in decompiler engine in other tools.
- **JD-GUI (GPLv3)** — the old standby for quickly eyeballing `.class` files; fine for a glance, less capable than
  Vineflower on modern bytecode.

### Python (`.pyc`, PyInstaller executables)

- **pyinstxtractor (extremecoders)** — unpacks a PyInstaller `.exe` into its `.pyc` files and PYZ archive; run it with the
  same Python version the exe was built with. Then decompile the `.pyc`.
- **Decompilers** — for Python ≤ 3.9, `uncompyle6`/`decompyle3` give the cleanest source; for 3.10+, `pycdc`
  (Decompyle++, C++) is the one that keeps up, though complex control flow on 3.11+ can still come out subtly wrong.
  Treat 3.11+ decompiles as INFERRED until you confirm against behaviour.

### Unity games — the common game case

Unity ships either as **Mono** (managed `Assembly-CSharp.dll` → decompiles beautifully in ILSpy/dnSpyEx, Tier 1) or as
**IL2CPP** (C# → C++ → native `GameAssembly.dll`, Tier 3, plus a `global-metadata.dat` sidecar you parse with community
tooling to recover names). Check which before you despair: if you see `Assembly-CSharp.dll` you have the source back;
if you see `GameAssembly.dll` + `global-metadata.dat` you are doing native work with a name-recovery step.
- **AssetRipper (GPLv3)** extracts Unity assets and serialized objects back into a Unity-openable project. Its own README
  says it is "not sponsored by or affiliated with Unity Technologies" — a reminder that asset copyright (section 10) is
  separate from the tool being legal.
- **Godot** games: **GDRE Tools / gdsdecomp (MIT)** recovers the project and decompiles GDScript from a `.pck`/exe.

---

## 5. Electron and JavaScript — usually not compiled at all

Electron apps are a desktop shell (Chromium + Node) around a web app. The app code lives in an **`app.asar`** archive,
and ASAR is **not encryption and not compilation** — it is a tar-like concatenation with a JSON header. If the developer
did not turn on integrity fuses, reading it is trivial, which is why this is the easiest "compiled app" category.

### The ASAR format (I parsed it live on Mullvad VPN, GPL-3.0)

Layout: a Chromium **Pickle** holds a little-endian `uint32` = size of the next pickle; the second pickle holds the JSON
header (a `uint32` length then the UTF-8 JSON); file contents are concatenated after the header. Each file entry in the
JSON gives an `offset` (string, relative to content base = 8 + header-pickle size), a `size`, optional `unpacked:true`
(the file actually lives beside the asar in `app.asar.unpacked/`, common for native `.node` modules), and optional
`integrity` (SHA-256 of the whole file plus per-block hashes). Deduplicated files share one offset.

On Mullvad's asar I read: 2,714 files, content base at offset 713,524, top-level `node_modules` (2,391) / `build` (321),
**78 unpacked** entries, every entry carrying an integrity block, `package.json` → name `mullvad-vpn`, version `2026.4`,
main `build/main.js`, licence GPL-3.0-or-later. **219 `.map` source-map files ship inside** — the original TypeScript,
handed over. The `build/` bundles themselves are minified (one line of 123,436 characters) with no `sourceMappingURL`
link, so those maps are for the libraries, not the app's own bundle — a nice illustration that "ships source maps" and
"ships *its own* source map" are different claims (OBSERVED, by reading the last 400 bytes of each bundle).

**Tooling:**
- **`@electron/asar` (MIT, npm)** — `asar list app.asar`, `asar extract app.asar out/`, `asar extract-file`. Node 22+.
- **`npx @electron/fuses read --app <path>`** — reads the security fuses. Or do it statically as I did: find the sentinel
  `dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX` in the binary, then `version` byte, `length` byte, then one byte per fuse
  (`0x30`=off, `0x31`=on, `0x72`=removed). Order: RunAsNode, EnableCookieEncryption, EnableNodeOptionsEnvironmentVariable,
  EnableNodeCliInspectArguments, EnableEmbeddedAsarIntegrityValidation, OnlyLoadAppFromAsar,
  LoadBrowserProcessSpecificV8Snapshot, GrantFileProtocolExtraPrivileges, WasmTrapHandlers. Mullvad: integrity validation
  **off**, only-load-from-asar **off** — the usual defaults, and why ASAR reads as an open archive.
- **Electronegativity (Apache-2.0, Doyensec)** — scans an Electron app (directory or asar) for insecure config
  (`nodeIntegration`, missing `contextIsolation`, disabled `sandbox`). Use it to *audit our own* Electron apps.

### Minified and bundled JavaScript

Web and Electron code ships minified (whitespace/names crushed) and bundled (webpack/esbuild/Browserify concatenate
hundreds of modules into one file). To read it:

- **Source maps first.** If a `.map` is present (or linked via a `//# sourceMappingURL=` comment or `SourceMap:` HTTP
  header), it maps generated positions back to original files and *often embeds the original source* in `sourcesContent`.
  The format is now an ECMA standard — **ECMA-426, 1st edition, December 2024** — fields `version`(3), `sources`,
  `sourcesContent`, `names`, `mappings` (base64-VLQ segments), `ignoreList`. A present source map with `sourcesContent`
  *is the original source*; you are done.
- **No map?** **webcrack (MIT)** deobfuscates obfuscator.io output, un-minifies, and unpacks webpack/browserify bundles
  into separate module files. **wakaru (Apache-2.0)** un-minifies and un-bundles (webpack/esbuild/Browserify/Metro) and
  reverses Babel/TypeScript/SWC transforms back toward modern syntax. Neither recovers original *names* a minifier
  destroyed — they recover *structure and readability*. wakaru's own README is blunt that using it on targets without
  consent is illegal; heed that.

---

## 6. Dynamic analysis — watching software we own run

Static tells you what code *can* do; dynamic tells you what it *does* with real input. Every tool here executes the
target, so **everything in this section is gated by the VM rule (section 11) and the legal rule (section 10): do it on
software we wrote, own, or are permitted to analyse, inside a disposable VM for anything untrusted.** I am describing
these at the level of understanding and for legitimate debugging/interoperability/our-own-security use — not for bypassing
protections.

- **x64dbg (open source, Windows, x86/x64)** — the user-mode debugger for native Windows software. Disassembly, graph,
  conditional breakpoints, tracing, plugins; built on Zydis (disasm), TitanEngine, Scylla (import reconstruction). Use it
  to step through our own native code, or a tutorial crackme you wrote, and watch how a routine computes.
- **WinDbg + Time Travel Debugging (free, Microsoft)** — the superpower. TTD *records* a process's execution to a `.run`
  trace (plus a `.idx` index) and lets you replay it **forwards and backwards**, query it with LINQ-style `dx`, and share
  the trace so someone else sees the identical execution. Caveats from Microsoft's own docs: 10–20× slowdown while
  recording, traces get large, **user-mode only** (no kernel), **read-only playback** (you can rewind but not alter
  history), can't trace Protected Process Light, and it can deadlock Electron apps. For understanding a complex bug or a
  stateful system you own, nothing beats being able to run execution backward to the cause. TTD also conflicts with AV
  that shadows memory — not an issue on this host, but it is in a VM with Defender on.
- **Frida (wxWindows licence; Windows/macOS/Linux/Android/iOS/…)** — "a dynamic instrumentation toolkit," self-described
  as "Greasemonkey for native apps." It injects a JS engine (QuickJS) into a process; its **Interceptor** hooks functions
  and its **Stalker** traces execution, with a two-way channel back to your Python/Node controller. For *our* software it
  is the fastest way to log "what arguments does this function actually get," trace a call, or prototype an interop shim.
  Dual-use caution: hooking is also how cheats and anti-cheat bypasses work — we use it for observation and interop on
  software we own, and we do not use it against online-game protections (section 10, MDY v. Blizzard).
- **Process Monitor (free, Sysinternals, Mark Russinovich)** — real-time file-system, registry, process/thread and
  network-setup activity with full call stacks and non-destructive filtering. The fastest way to answer "where does this
  app store its save / its config / its settings?" without touching the binary. I did the static equivalent in
  section 4 (Unity PlayerPrefs live in `HKCU\Software\<company>\<product>`, unencrypted) — Procmon shows it happening.
- **API Monitor (freeware, rohitab)** — logs Windows API and COM calls with decoded parameters and return values,
  15,000+ APIs and 1,800+ COM interfaces defined. Complements Procmon: Procmon shows the syscalls that hit the OS, API
  Monitor shows the higher-level API calls and their arguments. Note it is freeware, not open source, and old (v2 is from
  the Windows 8 era) — run it in the VM.

What dynamic analysis cannot do: prove a *negative* ("it never sends telemetry" — you only saw the paths you exercised),
and it does not give you clean source. Pair it with static; the two corroborate each other, which is REA method step 5.

---

## 7. WebAssembly — a clean, well-specified target

WebAssembly is the readable end of "compiled for the web." A `.wasm` is a tight binary: 4-byte magic `\0asm`, 4-byte
version, then a sequence of **sections** (id byte + LEB128 size + body): 1 type, 2 import, 3 function, 5 memory, 7 export,
10 code, 11 data, and id 0 *custom* — where the optional **name section** lives. If the name section survived, function
and local names come back (Tier 1-ish); if it was stripped, you get numbered functions (`f123`) and must infer.

I walked `xxhash-wasm`'s module (MIT) live: magic/version confirmed, a 9-entry export section naming `xxh32`, `init32`,
`update32`, `digest32`, `xxh64`, … and a code section with 10 function bodies. The export names alone described the whole
API — a textbook "inspect the interface before the implementation."

**Tooling — WABT (Apache-2.0):** `wasm2wat` (binary → the official text format, WAT), `wasm-objdump` (sections/symbols
like objdump), `wasm-validate`, `wasm-strip`, `wasm2c` (to C), and **`wasm-decompile`** — Wouter van Oortmerssen's tool
that produces readable C-like pseudocode, inferring struct shapes from load/store patterns and pulling names from the
name section or exports. His V8 blog post (2020) is candid about the limit: LLVM optimises `.wasm` heavily, so "the output
code is very unlike what a programmer would write." WAT and `wasm-decompile` output are a *disassembly/decompilation*, not
the original source. Good for understanding; not a source dump.

Workflow: `wasm-objdump -h` for the section map → `wasm2wat` for the full text → `wasm-decompile` for a readable pass →
read the import section to see what the host (JS) must provide, which is where the interesting behaviour usually lives.

---

## 8. File and save formats — the part that matters most for a game

If Daniel wants an upgrade path, releasable weapons and effects, the fights are mostly in **data**: the save file, the
item/weapon tables, the config. Reverse engineering a file format is the most durable skill here because formats outlive
tools. The method is a loop.

### Entropy first — the free X-ray

Shannon entropy over a sliding window (Aldo Cortesi's 2012 technique) tells you *what kind of bytes* live where, before
you understand anything: ~0 = padding/zeros; ~4–5 bits/byte = text, code, structured records (readable); ~7.5+ and flat =
compressed, encrypted, or already-packed media (opaque). I ran it on five of our files (4 KiB windows):
`app.asar` ~4.5–5 (readable), `System.Text.Json.dll` mixed with a 7.56 spike (an embedded compressed/R2R blob),
`Enemy.flp` **7.9+ across the body**. Entropy pointed me straight at the FLP's opaque mass, which the chunk walk then
identified. On an unknown firmware image, the entropy graph is the first thing you generate — it shows you the
filesystem boundary, the compressed kernel, the padding, all before extraction.

### Then the format loop (OBSERVED vs INFERRED, every field)

1. **Header and magic.** First bytes usually declare the format. FLP starts `FLhd`; WASM `\0asm`; PNG `\x89PNG`; a zip
   (so an asar/jar/apk/docx/pck) `PK`.
2. **Carve the top-level structure.** Many formats are chunked: a 4-byte tag + a length + a body, repeated. The *length
   field is your falsifiable test*: if walking tag→length→skip lands you exactly on the next tag and on the file end, your
   structure hypothesis is OBSERVED-correct; if it drifts, it is wrong — no guessing.
3. **Classify records; find the variable payloads with entropy; diff to find meaning.**
4. **Document it** (see below).

### Worked example: our own `Enemy.flp` (FL Studio project, we own it)

FL Studio uses a RIFF-ish container: an `FLhd` header chunk (format, channel count, PPQ) then one big `FLdt` data chunk
of **events**. The event ID's range encodes its own size — a genuinely elegant, self-describing design: id 0–63 = 1-byte
value, 64–127 = 2-byte, 128–191 = 4-byte, 192+ = variable length with a varint size prefix. (Those boundaries are the
PyFLP constants `BYTE=0, WORD=64, DWORD=128, TEXT=192, DATA=208`, credit demberto/PyFLP.)

My parser walked all 2,874 events and **ended exactly on the declared `FLdt` length (2,410,975 bytes) — the structure is
OBSERVED, not guessed.** It read the FL version string out of event 199 (`20.7.2.1863`), classified events by size
class, and found the 7.9-bit entropy mass was six `event id 213` blobs (PyFLP `PluginID.Data = DATA+5 = 213`, the plugin
preset/state blob — native params or a VST's opaque preset) at 8.0 bits/byte. So: the *project structure* is fully
readable; the *plugin state* inside it is opaque by design. That is a complete, honest format finding, and it is the exact
shape of a game-save investigation: readable envelope, opaque or checksummed payloads to characterise.

### The format tools

- **Kaitai Struct (compiler GPLv3+, runtimes MIT/Apache-2.0)** — the right answer for *documenting* a format. You write a
  declarative `.ksy` in YAML (`meta`, `seq`, `types`, `instances`, `enums`) describing what the bytes *are*, and `ksc`
  compiles it to a parser in Python/C++/Java/JS/Rust/… (12 languages). The Web IDE (`ide.kaitai.io`) visualises your spec
  against a real file as you write it, and there is a gallery of ready-made format specs. **This is how the house should
  capture every format it reverses** — one `.ksy` becomes a parser in every language we use *and* the documentation, in
  one artifact. Latest 0.11 (2025-09-07).
- **ImHex (GPLv2, WerWolv)** — the reverse-engineer's hex editor: a C-like **Pattern Language** to parse/highlight
  structures, a data inspector, **entropy and byte-distribution graphs**, a Capstone-backed disassembler (20+ arches),
  diffing, bookmarks, YARA scanning, and a node-based data processor for decoding/decrypting before display. Free. The
  companion `ImHex-Patterns` repo (GPL-2.0) ships ~300+ ready format patterns. Use it for interactive exploration.
- **010 Editor (commercial: $59.95 home/academic, $149.95 commercial, 30-day trial)** — the same idea with C/C++-like
  **Binary Templates** and a large template repository; polished, paid. ImHex covers most of what we need for free; 010 if
  a specific published template saves a day.
- **binwalk v3 (MIT, Rust rewrite)** — firmware/blob triage: signature-scans a file for embedded files and filesystems
  (`binwalk fw.bin`), graphs entropy (`-E`), and extracts (`-e`, recursively with `-M`/matryoshka). **Run extraction only
  in the VM** — see the CVE in section 11.
- **Reference registries when documenting** — the Library of Congress "Sustainability of Digital Formats" FDDs (magic
  numbers, spec links, seven sustainability factors) and the UK National Archives **PRONOM** registry + **DROID**
  identifier (signature-based ID, PUIDs) are how preservation professionals record formats. Ange Albertini's **Corkami**
  dissections and posters are the best visual format references going, and a sharp reminder (polyglots) that a file's
  extension is a claim, not a fact.

---

## 9. Clean-room rebuilding — the legal way to build on what you learn

This is the method that lets the house build "an archero-style game with a real upgrade path" and release weapons and
effects without stepping on anyone's copyright. It is a discipline, not a tool.

The principle: **copyright protects the expression (the actual code, art, music, text, the specific look-and-feel), not
the idea, the rules, or the functional behaviour.** You may freely learn *what* a system does; you must not copy *how it
was written*. The clean-room wall enforces that separation so a rebuild is provably independent.

How it is done (the Phoenix-BIOS pattern, used for decades):
1. **The dirty team** studies the original (statically/dynamically, legally — section 10) and writes a **specification of
   observed behaviour** in plain language: "on crit, damage = base × crit_mult, rounded." No code, no copyrighted
   expression — just functional facts. This is REA method step 8: observed behaviour, not design choice.
2. **A wall.** The spec is reviewed to ensure it contains only unprotected functional facts, no expression.
3. **The clean team** — people who never saw the original code — implement from the spec alone. Their code is
   independently authored; it happens to interoperate or behave similarly, which is exactly what Sega v. Accolade and
   Sony v. Connectix protect (section 10).

For a *game*, the wall sits in a specific place: **mechanics, rules and systems are free to reimplement** (Tetris's
"falling blocks" idea was never the issue); **the specific expression is not** — do not copy art, audio, text, level
layouts, or the distinctive audiovisual look-and-feel. Build your own art and your own code; borrow the *idea* of a
dash-and-shoot roguelite with an upgrade tree. Watch two extra traps: **trade dress / look-and-feel** (Tetris Holding v.
Xio, Spry Fox v. LOLApps — clones that copied the *visual feel* lost) and **game-mechanic patents** (Warner's Nemesis
System patent; Nintendo's Palworld suit — rare, usually weak, but they exist). Document your independent authorship as you
go; the paper trail is the defence.

---

## 10. The legal boundary (jurisdiction-aware; NOT legal advice)

I am not a lawyer and this is not legal advice; for anything we ship or that touches a third party's product, we get a
real opinion. But the house should know the shape of the law so it does not blunder. Reverse engineering for
understanding, interoperability, and analysing what you own is broadly lawful in the US and EU; the traps are DRM
circumvention, contract terms, and copying expression.

**United States**

- **Reverse engineering for interoperability is lawful (copyright).** *Sega v. Accolade* (9th Cir. 1992): disassembly is
  fair use where it is "the only means of access" to unprotected functional elements and the copier has a legitimate
  reason. *Sony v. Connectix* (9th Cir. 2000) extended this — intermediate copying of the PlayStation BIOS to build an
  emulator was fair use and "modestly transformative," and the *number* of intermediate copies did not matter.
- **DMCA §1201 is the real wall.** 17 U.S.C. §1201(a)(1) bans *circumventing* a technological measure that controls
  access to a work; (a)(2)/(b) ban trafficking in circumvention tools. There are statutory exemptions: **§1201(f)
  reverse engineering for interoperability** (lawfully obtained program, sole purpose of identifying elements needed for
  interoperability of an independently created program, info not already readily available, not otherwise infringing);
  **§1201(g) encryption research**; **§1201(j) good-faith security testing** with authorization. The Librarian of
  Congress adds temporary exemptions every three years (37 CFR 201.40; the 2024 rulemaking covers good-faith security
  research, repair, and preservation of abandoned/offline video games by eligible libraries). **This is the line we do
  not teach across: we do not describe how to defeat DRM, licence checks, anti-cheat or anti-tamper.** Understanding that
  they exist is fine; circumvention steps are out of scope.
- **Contracts can take away fair use.** *Bowers v. Baystate* (Fed. Cir. 2003) and *Davidson v. Jung* (8th Cir. 2005, the
  bnetd case): a EULA/TOS term forbidding reverse engineering can be enforceable, and parties "are free to contractually
  forego" the reverse-engineering privilege. So **read the EULA** of anything before analysing it; a no-RE clause is a
  real constraint even where copyright would have allowed it.
- **Online games and the CFAA.** *MDY v. Blizzard* (9th Cir. 2010): a bot that evaded Warden violated §1201 by
  circumventing control over the game's dynamic non-literal elements. *Van Buren v. United States* (2021) narrowed the
  CFAA's "exceeds authorized access" to a "gates-up-or-down" test — you violate it by reaching areas off-limits to you,
  not by having a bad motive for data you may access. Net: **we do not touch live online-game protections.**
  [Corrected 2026-10-13 after review: whether a §1201 violation needs a link to infringement is split between
  circuits. The Ninth Circuit declined to require one (*MDY v. Blizzard*); the Federal Circuit requires one
  (*Chamberlain v. Skylink*, 381 F.3d 1178, Fed. Cir. 2004). *Van Buren*'s footnote 8 left open whether the "gates"
  must be technological or can also be contract or policy limits, so whether breaking a game's terms of service counts
  as unauthorised access is unsettled. The corrected text is in the skill's `method-legal-cleanroom.md`.]
- **Trade secrets.** 18 U.S.C. §1839(6)(B) expressly excludes "reverse engineering, independent derivation, or any other
  lawful means" from "improper means" — reverse engineering a lawfully obtained product does not misappropriate a trade
  secret (though a contract can still forbid it).

**European Union** (often *more* permissive than the US for software, and crucially **not waivable by contract**)

- **Software Directive 2009/24/EC Art. 5(3):** a lawful user may "observe, study or test the functioning of the program"
  to determine its underlying ideas/principles. **Art. 6:** decompilation is allowed, without permission, where
  indispensable to achieve interoperability of an independently created program, by a lawful user, where the interop
  information "has not previously been readily available," confined to the parts necessary — and the results may not be
  used to make a substantially similar program. **Art. 8:** contract terms contrary to Art. 6 or Art. 5(2)/(3) are "null
  and void." So in the EU a no-RE EULA clause cannot defeat the interoperability and study rights (the opposite of Bowers).
- **CJEU *SAS v. World Programming* (C-406/10, 2012):** a program's functionality, its programming language, and its data
  file formats are **not** protected by copyright — you may reimplement behaviour and read formats. **CJEU *Top System*
  (C-13/20, 2021):** a lawful acquirer may decompile to **correct errors**, under Art. 5(1), without meeting Art. 6's
  conditions.
  [Corrected 2026-10-13 after review: not every right in this list is beyond contract, so the heading's "not waivable
  by contract" is too broad. Art. 8 voids terms contrary to Art. 6 or Art. 5(2)–(3) only. Art. 5(1), the basis of
  *Top System*'s error-correction ruling, applies "in the absence of specific contractual provisions" and is not on
  Art. 8's list, so a contract can shape it. The corrected text is in the skill's `method-legal-cleanroom.md`.]
- **Trade Secrets Directive 2016/943, Art. 3(1)(b):** acquiring information by observation, study, disassembly or testing
  of a lawfully obtained product is lawful (recital 16: reverse engineering is lawful "except when otherwise contractually
  agreed").
- **UK (post-Brexit, mirrors the directive):** CDPA s.50B (decompilation), s.50BA (observing/studying/testing); s.50B
  explicitly says a contract term purporting to prohibit it is ineffective.

**Copyright in game assets vs unprotected mechanics (US).** 17 U.S.C. 102(b) excludes any idea, procedure, process,
system or method of operation from copyright. The Copyright Office applies this to games on its games registration page
(https://www.copyright.gov/register/tx-games.html): the idea for a game, its name or title and its method of play are not
protected, but the text of the rules and the artwork can be registered. That is the legal basis for clean-room
game-building in section 9: the method of play is free; rule text, art, audio, audiovisual expression and code are not.
[Corrected 2026-10-13 after review: an earlier draft attributed a quoted sentence about games to Circular 33. Circular 33
does not contain that sentence and does not discuss games; the games statement is on the page above.]

**Bottom line for the house:** analysing software we own or wrote — green. Reverse engineering for interoperability or to
read a format — broadly green (US fair use / EU Art. 5–6), but **check the EULA** (US) and never circumvent a DRM/access
control. Clean-room reimplement mechanics, never copy expression or trade dress. Never touch live online-game
anti-cheat. When in doubt, or before shipping anything that leans on a third party's product, get a real legal opinion.

---

## 11. Host safety — the non-negotiable rule on this machine

This box runs with Windows Defender disabled and updates blocked, by Daniel's deliberate choice (machine-security-posture
memory; not re-litigated here). That choice removes the two safety nets — signature AV and patches — that would normally
catch a malicious sample or a vulnerable tool. So the rule is firm and it is *because* of the posture, not in spite of it:

- **Never execute an untrusted binary, firmware image, document or installer on the host.** Dynamic analysis (section 6),
  firmware extraction, and opening unknown documents happen inside a **disposable VM or sandbox** that gets reverted to a
  clean snapshot afterward.
- **Keep samples out of the repo.** Malware and untrusted binaries never land in `E:\AI-Setup` or any synced/backed-up
  location; they live in the VM or a scratch folder that is not indexed, not committed, not mirrored.
- **The extractor is attack surface, not just the sample.** binwalk had **CVE-2022-4510** (Q. Kaiser, ONEKEY, 2023): a
  path-traversal in its PFS extractor meant that merely *extracting* a crafted firmware image with `-e` could get code
  running, by writing outside the target directory into a location binwalk then loaded. The lesson is general — parsers
  and unpackers are complex C/Rust/Python that eat hostile input, so run them where a compromise is contained. Keep tools
  updated (the irony: the one place we *do* patch is the analysis VM).
- **Isolation options on this machine, cheapest first:** Windows Sandbox is *not available* (Windows 11 **Pro** supports
  it, but it was not present when I checked — enable "Windows Sandbox" via Optional Features if virtualization is on; it
  gives a disposable desktop discarded on close, with networking off and read-only folder mapping via a `.wsb` config).
  **Docker Desktop and WSL are installed** — a throwaway Linux container is a fine place to run binwalk, Ghidra headless,
  the WABT tools and Kaitai. Note WSL interop runs Windows `.exe`s from Linux and mounts `C:` at `/mnt/c` by default; for
  a real airgap use a full VM (VirtualBox/Hyper-V) with host-only networking, or disable interop
  (`/proc/sys/fs/binfmt_misc/WSLInterop`) and do not mount host drives. For a dedicated malware lab, **FLARE-VM**
  (Apache-2.0, Mandiant: Windows RE toolset, "should ONLY be installed on a virtual machine") and **REMnux**
  (Lenny Zeltser: Linux malware-analysis toolkit, VM/appliance/Docker) are the standard builds — snapshot first.
- **Static-first is a safety feature, not just a method.** Reading bytes (every worked example in this report) never
  executes the target. Prefer it; escalate to dynamic only when a question truly needs runtime evidence, and only in the
  VM.

---

## 12. Worked examples, all on our own or permitted files (reproducible)

Every example below was run read-only against a file we own or an open-source file on this disk. The scripts are in the
session scratchpad (`re_examples.py`, `re_examples2.py`); they use only `pefile` (already installed) and the standard
library. Nothing was executed, injected, loaded or modified — pure byte reading.

1. **PE triage** (`python311.dll`, native): machine x64, 19 named imports, 1,630 exports, no CLI header, 7 sections with
   per-section entropy. Established Tier 2 and the capability surface from imports alone.
2. **Managed vs native in one check** (`System.Text.Json.dll`): CLI header present, metadata signature `BSJB`, ReadyToRun
   header present, `#Strings` heap with 3,751 identifiers. Established Tier 1 and showed names survive.
3. **ASAR inventory** (Mullvad VPN, GPL-3.0): parsed both Pickles and the JSON header; 2,714 files, 78 unpacked, 219
   source maps, read `package.json` from inside the archive. Showed an Electron app is an open archive.
4. **Electron fuse wire** (same): found the sentinel, decoded 9 fuses — integrity validation and only-load-from-asar both
   off. Explained *why* the asar is readable.
5. **WASM section walk** (`xxhash-wasm`, MIT): magic/version, 9 named exports, 10 code bodies. Read the API from the
   export section before the implementation.
6. **Entropy profiles** of five files: distinguished readable (asar ~4.5–5) from opaque (FLP body 7.9+) with no parser.
7. **FLP format walk** (our `Enemy.flp`): parsed `FLhd`/`FLdt`, walked 2,874 events, **landed exactly on the declared
   chunk length** (structure OBSERVED), read FL version `20.7.2.1863`, identified the high-entropy mass as six `id 213`
   plugin-state blobs. A complete, honest game-save-shaped format finding.
8. **Bytecode keeps names** (`compile()` + `dis`): showed `co_varnames`/`co_names` present in Python bytecode — the
   mechanism behind "managed decompiles to source."

---

## (a) ROUTING TABLE — artifact/question → first tool → evidence it yields → what it cannot tell you

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| Unknown file, any kind | `diec` (Detect It Easy) + entropy scan | File type, compiler, packer, tier; where opaque regions are | Behaviour; names if stripped/packed |
| "Is this .NET or native?" | PE parse: CLI header (dir index 14) / `BSJB` | Managed→Tier 1 (ILSpy), native→Tier 2/3 (Ghidra) | How good the decompile will be until you run it |
| Windows `.exe`/`.dll`, native | Ghidra (headless `-readOnly` or GUI) | Disassembly, pseudocode, imports/exports, strings | Runtime values; which branch real input takes |
| .NET assembly (C#/Unity Mono) | ILSpy / `ilspycmd`; dnSpyEx to debug | Near-original C#, type/method names | Values that depend on runtime config/DRM |
| Android `.apk` / `.dex` | JADX | Java source, manifest, resources, strings | Native `.so` logic (→ Ghidra); server behaviour |
| `.jar` / `.class` | Vineflower (JD-GUI to glance) | Java source (records/sealed classes handled) | Reflection/dynamically generated behaviour |
| PyInstaller `.exe` | pyinstxtractor → pycdc/uncompyle6 | `.pyc` then Python source | 3.11+ complex control flow (treat as INFERRED) |
| Electron desktop app | `asar list/extract`; `@electron/fuses read` | App JS/TS, package.json, source maps, fuse state | Minified names a minifier destroyed; native modules |
| Minified/bundled JS, has `.map` | read the source map (`sourcesContent`) | The original source, directly | Nothing — you have the source |
| Minified/bundled JS, no map | webcrack / wakaru | Un-minified, un-bundled modules; readable structure | Original identifier names (gone at minify) |
| `.wasm` module | `wasm-objdump -h` → `wasm2wat` → `wasm-decompile` | Sections, imports/exports, WAT, C-like pseudocode | Original source (optimised away); stripped names |
| Unknown binary file/save format | ImHex (entropy + Pattern Language); binwalk for blobs | Structure, chunk boundaries, opaque payload locations | Meaning of a field without diffing/behaviour |
| "Where does this app store data?" | Process Monitor (software we own) | Exact file/registry paths, access patterns | Why; the on-disk format (→ ImHex/Kaitai) |
| "What APIs does our app call, with what args?" | API Monitor / Frida Interceptor (ours) | Live API/COM calls, parameters, return values | Paths you didn't exercise (no negative proof) |
| "Walk this bug backward to its cause" (ours) | WinDbg + Time Travel Debugging | Reversible execution trace, queryable | Kernel mode; PPL processes; altering history |
| "What changed between v1 and v2?" | BinDiff | Per-function matched/changed/new | Why it changed; intent |
| "Document a format for the house" | Kaitai Struct `.ksy` | A parser in 12 languages + the spec, one artifact | Semantics you haven't yet reverse engineered |
| "What can this binary do?" (capabilities) | capa | Capabilities mapped to MITRE ATT&CK | Whether it actually did them at runtime |
| Firmware image | binwalk `-E` then `-e` **in a VM** | Embedded filesystems/kernels/blobs, entropy map | Logic inside extracted binaries (→ Ghidra) |

---

## (b) Trigger-phrased lessons the house should keep

- **Use when** you receive any compiled artifact, **before** choosing a tool: identify the tier first (managed/bytecode →
  near-source decompile; native-with-metadata → pseudocode + hints; stripped/packed → infer). One `diec`/PE-header/magic
  check decides the whole workflow. **Don't when** you already have source — then it is ordinary code reading, not RE.
- **Use when** you meet an Electron or web app, **before** reaching for a disassembler: it is almost never compiled —
  `asar extract` it and look for `.map` source maps (that's the original source). **Don't when** the fuses show
  `EnableEmbeddedAsarIntegrityValidation`/`OnlyLoadAppFromAsar` on *and* you'd have to defeat them — that's circumvention,
  out of scope.
- **Use when** you face an unknown binary or save format, **before** writing a parser: run a sliding-window entropy scan
  to locate text/code vs compressed/encrypted regions. **Don't when** the file is tiny or you already have a spec.
- **Use when** you state any RE finding, **before** you write it down: tag it OBSERVED (read the bytes / watched the call)
  vs INFERRED (reasoned) vs UNKNOWN, with an evidence ID (address/offset). Validate structure with a falsifiable check
  (does the declared length land you on the next record?). **Don't when** tempted to trust a function or field *name* —
  names are leads, never findings.
- **Use when** anything untrusted must actually *run* (dynamic analysis, firmware extraction, opening unknown documents),
  **before** executing: do it in a disposable VM/sandbox (Docker/WSL for Linux tools, a full VM for an airgap), revert
  after, keep the sample out of the repo. On THIS host (Defender off, no updates) there is no safety net — static-first
  always. **Don't when** you can answer the question by reading bytes — then never execute at all.
- **Use when** scoping any RE task that touches a third party's product, **before** starting: check the EULA (a no-RE
  clause can bind in the US per Bowers/Davidson; in the EU/UK it is void against interop/study rights). Stay inside
  interoperability/understanding/our-own-security. **Don't when** the only way forward is defeating DRM, a licence check,
  or online-game anti-cheat — stop and escalate; that line is not ours to cross.
- **Use when** building on what we learned (an archero-style game, a format reimplementation), **before** writing code:
  run it clean-room — write a plain-language spec of OBSERVED behaviour (idea/rules/function, no expression), then
  implement from the spec. Reimplement mechanics freely; never copy art, audio, text, or the distinctive look-and-feel
  (Tetris/Spry Fox). **Don't when** you'd be copying expression or trade dress to save time — that's the one thing
  copyright actually protects.
- **Use when** documenting a reversed format, **before** it evaporates into a one-off script: write a Kaitai `.ksy` — one
  artifact becomes a parser in every language we use *and* the documentation. **Don't when** a throwaway byte-dump
  answers a one-time question.

---

## (c) Gaps — where the house needs a new tool or verb

1. **No RE toolchain is installed.** Confirmed on this box: no Ghidra, rizin, Cutter, x64dbg, IDA, JADX, ImHex, binwalk,
   WABT, Frida, `asar`, 7-Zip, `strings`, no JRE/JDK, no C/Rust/Go compilers. Only `pefile`+`python-magic` (Python),
   Node 24, `dotnet`, Docker and WSL exist. **Proposed verb `arsenal/re` (or extend `arsenal/tools`):** a one-command
   installer/launcher that provisions a pinned RE set — Ghidra (needs a JDK), WABT, Kaitai `ksc`, `@electron/asar`+fuses,
   JADX, ImHex, binwalk, Detect It Easy, capa — preferably into a container so the host stays clean. Until then every
   session re-discovers nothing is installed.
2. **No disposable-analysis sandbox is wired up.** Windows Sandbox isn't enabled; there's no FLARE-VM/REMnux and no
   project convention for "run this untrusted thing safely." **Proposed verb `arsenal/sandbox run <tool> <sample>`** that
   drops the tool+sample into a throwaway Docker container (or a reverted VM) with no host mounts and no repo access, and
   tears it down after. This operationalises section 11 so the safe path is the easy path.
3. **No format registry.** We have no house home for reversed formats. **Proposed:** a `formats/` tree of Kaitai `.ksy`
   specs (FLP started here tonight — structure OBSERVED), each with its evidence ledger, so a format reversed once is a
   parser-in-12-languages forever. Pairs with the Library-of-Congress/PRONOM documentation discipline.
4. **No evidence-ledger primitive for RE.** REA's strength is the ledger (claim → evidence ID → confidence → boundary →
   unknowns). Our `learn`/`note` store lessons, not per-artifact finding ledgers. **Proposed:** a lightweight
   `re_finding` record (target SHA-256, offset/address, OBSERVED/INFERRED, confidence, search boundary) so multi-session
   RE work accumulates instead of restarting — the software analogue of the chronicle.
5. **No managed/native classifier verb.** The single highest-leverage check (section 1) is currently a hand-written
   script. **Proposed:** `arsenal/tools classify <file>` → tier + format + entropy summary + suggested first tool, i.e.
   the routing table as a command. (Tonight's `re_examples.py` is a working prototype of its guts.)
6. **WebSearch budget is a real constraint on legal research.** This session hit the 200-search cap; several court
   opinions were only reachable via summaries, not primary text. **Proposed:** a cached `research/legal/` of the key
   statutes/opinions (DMCA §1201, Software Directive arts. 5–6, Sega, Sony, SAS, Top System, Circular 33) so the legal
   notes don't re-fetch every time.

---

## Sources (URL + one line each)

- https://github.com/NationalSecurityAgency/ghidra — Ghidra: NSA's free Apache-2.0 SRE framework (decompiler, headless, PyGhidra).
- https://ghidra.re/ghidra_docs/api/ghidra/app/util/headless/AnalyzeHeadless.html and https://www.ghidradocs.com/11.4.2_PUBLIC/support/analyzeHeadlessREADME.html — the headless analyzer, `-readOnly`/`-postScript`/`-scriptPath`.
- https://github.com/NationalSecurityAgency/ghidra/tree/master/GhidraDocs/GhidraClass — the bundled Ghidra course (Beginner→Advanced→Debugger→BSim).
- https://rizin.re/ and https://github.com/rizinorg/rizin — rizin framework (LGPL/GPL-3.0), radare2 fork focused on usability.
- https://github.com/rizinorg/cutter and https://github.com/rizinorg/rz-ghidra — Cutter GUI (GPL-3.0) and the Ghidra-decompiler plugin for it.
- https://hex-rays.com/ida-free and https://hex-rays.com/pricing — IDA Free (non-commercial, x86 only, cloud decompiler) and the paid tiers.
- https://binary.ninja/purchase/ — Binary Ninja editions and prices (Free/Personal/Commercial/Ultimate).
- https://github.com/horsicq/Detect-It-Easy — Detect It Easy (MIT): file type/compiler/packer identification, `diec` CLI.
- https://github.com/mandiant/capa — capa (Apache-2.0): rule-based capability detection, MITRE ATT&CK mapping, Ghidra/IDA plugins.
- https://github.com/google/bindiff — BinDiff (Apache-2.0, Google): binary diffing with IDA/BinaryNinja/Ghidra plugins.
- https://github.com/x64dbg/x64dbg — x64dbg (GPLv3): open-source Windows user-mode debugger (Zydis/TitanEngine/Scylla).
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/time-travel-debugging-overview — WinDbg Time Travel Debugging: `.run`/`.idx`, reversible replay, 10–20× overhead, user-mode-only, read-only playback.
- https://frida.re/docs/home/ and https://github.com/frida/frida — Frida (wxWindows licence): dynamic instrumentation, Interceptor/Stalker, QuickJS injection.
- https://learn.microsoft.com/en-us/sysinternals/downloads/procmon — Process Monitor (free, Russinovich): file/registry/process activity with stacks and filters.
- http://www.rohitab.com/apimonitor — API Monitor (freeware, rohitab): logs Windows API/COM calls with decoded parameters (15,000+ APIs, 1,800+ COM interfaces).
- https://github.com/icsharpcode/ILSpy — ILSpy (MIT): .NET decompiler, `ilspycmd` CLI, `ICSharpCode.Decompiler` library.
- https://github.com/dnSpyEx/dnSpy — dnSpyEx (GPLv3): maintained dnSpy continuation; .NET/Unity debugger + assembly editor.
- https://github.com/skylot/jadx — JADX (Apache-2.0): Dex/APK→Java decompiler with manifest/resource decode; "can't decompile 100% of the code."
- https://github.com/Vineflower/vineflower — Vineflower (Apache-2.0): modern Java decompiler, Fernflower/Quiltflower lineage.
- https://github.com/java-decompiler/jd-gui — JD-GUI (GPLv3): standalone `.class` source viewer.
- https://deepwiki.com/extremecoders-re/pyinstxtractor and https://github.com/0xSHAK1B/pycdc — pyinstxtractor (PyInstaller unpacker) and pycdc/Decompyle++ (Python ≤3.9 best with uncompyle6; 3.10+ pycdc, 3.11+ imperfect).
- https://docs.unity3d.com/Manual/il2cpp-introduction.html and https://docs.unity3d.com/ScriptReference/PlayerPrefs.html — Unity IL2CPP (C#→C++→native, `global-metadata.dat`); PlayerPrefs stored unencrypted at `HKCU\Software\<company>\<product>`.
- https://github.com/AssetRipper/AssetRipper — AssetRipper (GPLv3): Unity asset extraction; "not sponsored by or affiliated with Unity Technologies."
- https://github.com/GDRETools/gdsdecomp — GDRE Tools / gdsdecomp (MIT): Godot project recovery and GDScript decompilation.
- https://github.com/electron/asar — ASAR format (MIT): Pickle header + JSON file table, offset/size/unpacked/integrity; `asar` CLI.
- https://www.electronjs.org/docs/latest/tutorial/asar-integrity and https://raw.githubusercontent.com/electron/electron/main/docs/tutorial/fuses.md — ASAR integrity + Electron fuses: sentinel `dL7pKGdnNz…`, version/length/state bytes (`0`/`1`/`r`), fuse order.
- https://github.com/doyensec/electronegativity — Electronegativity (Apache-2.0, Doyensec): Electron misconfig scanner (nodeIntegration/contextIsolation/sandbox).
- https://ecma-international.org/wp-content/uploads/ECMA-426_1st_edition_december_2024.pdf and https://tc39.es/ecma426/ — Source map format, ECMA-426 1st ed. (Dec 2024): version/sources/sourcesContent/names/mappings (base64-VLQ)/ignoreList.
- https://github.com/j4k0xb/webcrack — webcrack (MIT): deobfuscate obfuscator.io, un-minify, unpack webpack/browserify.
- https://github.com/pionxzh/wakaru — wakaru (Apache-2.0): un-minify + un-bundle + reverse Babel/TS/SWC; consent disclaimer.
- https://github.com/WebAssembly/wabt — WABT (Apache-2.0): wat2wasm/wasm2wat/wasm-objdump/wasm-decompile/wasm2c/wasm-strip/wasm-validate.
- https://v8.dev/blog/wasm-decompile — Wouter van Oortmerssen (V8, 2020): wasm-decompile goals and limits; "output code is very unlike what a programmer would write."
- https://webassembly.github.io/spec/core/binary/modules.html — WASM binary layout: magic `\0asm`, version, section ids 0–13, LEB128 sizes, custom name section.
- https://doc.kaitai.io/user_guide.html and https://kaitai.io/ — Kaitai Struct: declarative `.ksy` → parsers in 12 languages; compiler GPLv3+, runtimes MIT/Apache-2.0; Web IDE and gallery.
- https://github.com/WerWolv/ImHex and https://github.com/WerWolv/ImHex-Patterns — ImHex (GPLv2): Pattern Language, entropy graphs, Capstone disasm, YARA; ~300+ ready patterns (GPL-2.0).
- https://www.sweetscape.com/010editor/ — 010 Editor: Binary Templates; $59.95 home/academic, $149.95 commercial, 30-day trial.
- https://github.com/ReFirmLabs/binwalk — binwalk v3 (MIT, Rust): signature scan, entropy `-E`, extract `-e`, matryoshka `-M`.
- https://onekey.com/blog/security-advisory-remote-command-execution-in-binwalk/ — CVE-2022-4510 (Q. Kaiser, ONEKEY, 2023): path traversal in binwalk's PFS extractor; code execution on extraction.
- https://corte.si/posts/visualisation/entropy/index.html — Aldo Cortesi (2012): visualising binary entropy; high=compressed/encrypted, low=padding/code.
- https://protobuf.dev/programming-guides/encoding/ — protobuf wire format: tag=(field<<3)|wiretype, varints, ZigZag; field names are not on the wire.
- https://www.loc.gov/preservation/digital/formats/ and https://en.wikipedia.org/wiki/PRONOM — LoC format descriptions (magic, 7 sustainability factors) and PRONOM/DROID (PUIDs, signature ID).
- https://github.com/corkami — Ange Albertini's Corkami: file-format dissections, posters, polyglots.
- https://github.com/demberto/PyFLP — PyFLP (demberto): FLP event model (BYTE=0/WORD=64/DWORD=128/TEXT=192/DATA=208; PluginID.Data=213).
- https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/ — Windows Sandbox: disposable desktop, Pro/Enterprise/Education, networking off via `.wsb`.
- https://github.com/mandiant/flare-vm — FLARE-VM (Apache-2.0, Mandiant): Windows RE toolset; "should ONLY be installed on a virtual machine."
- https://docs.remnux.org/ — REMnux (Lenny Zeltser): Linux malware-analysis toolkit (appliance/Docker/install).
- https://learn.microsoft.com/en-us/windows/wsl/filesystems — WSL interop: runs Windows `.exe` from Linux, mounts `C:` at `/mnt/c`, disable via `/proc/sys/fs/binfmt_misc/WSLInterop`.
- https://www.law.cornell.edu/uscode/text/17/1201 — DMCA §1201: (a)(1) circumvention ban, (a)(2)/(b) trafficking, (f) interoperability, (g) encryption research, (j) security testing.
- https://www.law.cornell.edu/cfr/text/37/201.40 — 37 CFR 201.40: 2024 triennial §1201 exemptions (security research, repair, abandoned/offline game preservation).
- https://copyright.gov/fair-use/summaries/segaenters-accolade-9thcir1992.pdf and https://www.courtlistener.com/opinion/593285/ — Sega v. Accolade (9th Cir. 1992): disassembly is fair use when the only means to unprotected functional elements.
- https://www.bitlaw.com/source/cases/copyright/Sony-Connectix.html — Sony v. Connectix (9th Cir. 2000): intermediate BIOS copying for an emulator was fair use and "modestly transformative."
- https://en.wikipedia.org/wiki/SAS_Institute_Inc_v_World_Programming_Ltd — CJEU C-406/10 (2012): functionality, language and data-file formats not protected by copyright.
- https://ipcuria.eu/case?reference=C-13/20 — CJEU Top System C-13/20 (2021): lawful acquirer may decompile to correct errors under Art. 5(1).
- https://www.legislation.gov.uk/eudr/2009/24/article/5 , /article/6 , /article/8 — Software Directive 2009/24/EC: Art.5(3) observe/study/test, Art.6 decompilation for interoperability, Art.8 anti-RE terms null and void.
- https://www.legislation.gov.uk/ukpga/1988/48/section/50B — UK CDPA s.50B: decompilation for interoperability; contrary contract terms ineffective.
- https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32016L0943 — EU Trade Secrets Directive 2016/943 Art.3(1)(b): observation/study/disassembly/testing of a lawful product is lawful acquisition.
- https://www.law.cornell.edu/uscode/text/18/1839 — 18 U.S.C. §1839(6)(B): reverse engineering/independent derivation excluded from "improper means."
- https://en.wikipedia.org/wiki/Bowers_v._Baystate_Technologies and https://scholar.google.com/scholar_case?case=5463280175310353497 — Bowers (Fed. Cir. 2003) and Davidson v. Jung (8th Cir. 2005): EULA no-RE clauses can be enforceable in the US.
- https://en.wikipedia.org/wiki/MDY_Industries_v._Blizzard_Entertainment and https://en.wikipedia.org/wiki/Van_Buren_v._United_States — MDY v. Blizzard (§1201 over dynamic game elements) and Van Buren (2021, CFAA "gates-up-or-down").
- https://www.copyright.gov/register/tx-games.html — US Copyright Office games page: the idea, name or title and method of play of a game are not protected; the rule text and artwork can be registered.
- https://www.copyright.gov/circs/circ33.pdf — US Copyright Office Circular 33 (rev. 3/2021), "Works Not Protected by Copyright": restates the 102(b) exclusions in general terms; it does not discuss games (corrected 2026-10-13).
- https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc. and https://en.wikipedia.org/wiki/Spry_Fox,_LLC_v._Lolapps,_Inc. — Tetris v. Xio and Spry Fox v. LOLApps: a game's look-and-feel/expression can be protected even when mechanics are not.
- https://www.techdirt.com/2026/07/02/the-nintendo-palworld-patent-suit-appears-to-be-heading-for-a-muted-conclusion/ and https://mcvuk.com/business-news/warner-bros-secures-patent-for-the-nemesis-system-from-shadow-of-mordor/ — game-mechanic patents exist (Nintendo/Palworld; WB Nemesis System) but are narrow/contested.
- https://github.com/morluto/rea — REA (MIT, morluto): the MCP reverse-engineering skill whose discipline (route-first, observations vs inferences, evidence ledger, resources-alongside-code) this report adopts.
