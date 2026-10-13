# Software and binaries — the operator's guide

Reading compiled software when you do not have the source. Distilled from
`research/reviewed/reverse-engineering-2026-10-13/software-binaries.md` (the full field manual, with
worked examples and every URL). **Not legal advice**; the legal note is below, the full map in
`method-legal-cleanroom.md`. None of the tools below is installed here, and installing any of them is
**Daniel's decision**.

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

**The analogy that holds it together.** Reverse engineering a binary is die-shot analysis for
software: source is the RTL the author wrote, the compiler is the fab, the shipped binary is the
optimised die with labels gone. A disassembler is the microscope (assembly back out); a decompiler is
the analyst writing plausible RTL back (C-like pseudocode) — never the original, just one that
behaves the same. How much you recover depends on how much metadata survived the fab. That one fact
routes everything.

## The one question that routes everything: what survived the compiler?

- **Tier 1 — Managed / bytecode (names and types survive; you get near-source back).** .NET (CIL in a
  PE with a CLI header), Java/Android (`.class`, `.dex`), Python (`.pyc`), WASM with its name section.
  Decompiles 90–100% faithful. *The chip shipped with its data sheet and pin labels still printed.*
- **Tier 2 — Native with metadata (structure gone, hints remain).** C/C++/Rust/Go/Swift to machine
  code: inlined, reordered, locals discarded, but exported names, import tables, RTTI/vtables, Go's
  embedded tables, a shipped PDB or strings survive. Assembly plus decent pseudocode. *The die with
  top-layer labels sanded off, bond-pad names legible.*
- **Tier 3 — Native, stripped and/or obfuscated (infer almost everything).** Symbols stripped, maybe
  packed, maybe Unity IL2CPP (C#→C++→native with a `global-metadata.dat`; a third party's IL2CPP build
  is out of scope here, see Unity below). Work from control flow, constants, syscalls, behaviour. *A
  decapped die with no labels — trace traces.*

**Tell the tier in under a minute, all static:** `diec` (Detect It Easy) or a PE parse — is there a
CLI header (data-directory index 14)? → .NET, Tier 1. Magic: `PK` zip really a `.jar`/`.apk` →
Java/Android; `\0asm` → WASM; `dex\n` → Dalvik. Whole-file entropy > ~7.2 and flat → packed/compressed
(unpack only a standard packer, on something we own, before any tier call; a commercial protector is
out of scope — stop). Lots of readable identifiers → metadata survived; almost none →
stripped, Tier 3. (Verified live: `python311.dll` native, 1,630 flat exports, no CLI header;
`System.Text.Json.dll` carries a `#Strings` heap with 3,751 identifiers.)

## Native binaries (Tier 2/3)

**Pick one primary and learn it deeply; they read the same binaries.**
- **Ghidra** (NSA, Apache-2.0) — the house default: free, full disassembler + decompiler, hundreds of
  CPUs, scriptable (Java/PyGhidra), a **headless analyzer** (`support/analyzeHeadless`) with a
  `-readOnly` flag (the right default when only reading), and a full bundled course. Needs a JDK
  (**Daniel's decision:** installing Ghidra and a JDK, in the VM once one exists).
- **rizin + Cutter** (LGPL/GPL-3.0) — scriptable CLI + GUI; `rz-ghidra` plugin puts Ghidra's
  decompiler inside Cutter; FLIRT-style signatures help on stripped binaries.
- **IDA Free** — industry standard, non-commercial, x86/x64 only, cloud decompiler, no scripting. Use
  when a tutorial is written for IDA; else Ghidra.
- **Binary Ninja** — ergonomic, commercial (free non-commercial tier); nicest IL to read.

**Supporting cast:** Detect It Easy (`diec`, MIT) first contact; **capa** (Apache-2.0, FLARE) answers
"what can it do?" mapped to MITRE ATT&CK; **BinDiff** (Apache-2.0, Google) diffs two versions'
disassembly (this is the "what changed in v1.1" workflow); public **PDB** symbols bring names back for
free.

**Workflow (static, on something we own):** `diec` → tier/packer. Ghidra: import, auto-analyse, read
the **Symbol Tree** (imports/exports) and **Strings** first — they are your map. From a checklist
question, find an entry point (an exported function, an imported API you care about — `CreateFileW`,
`RegOpenKeyEx`, a socket call — or a distinctive string) and follow references *to* it. Read the
decompiler output; rename variables as you understand them (your renames are your notes); log each
finding OBSERVED/INFERRED with the address as the evidence ID. What native static analysis cannot
tell you: runtime values, which branch real input takes, timing — that needs dynamic (VM).

## Managed code — where you get the source back

**.NET (C#/F#/VB → CIL).** A PE with a CLI header pointing at a metadata root (`BSJB`), five streams
including `#Strings` (identifier names survive). **ILSpy** (MIT) is the house default — GUI plus
`ilspycmd` for scripted whole-project decompile, plus `ICSharpCode.Decompiler` as a library.
**dnSpyEx** (GPLv3) adds a live debugger: set breakpoints in decompiled C# of an app we built and watch
it run (anything else runs only in the VM) (the single most instructive thing for learning how a game's systems fit). Note R2R/mixed-mode:
modern .NET may ship a native copy alongside the CIL; the CIL still decompiles.

**Java/Android.** **JADX** (Apache-2.0) for `.apk`/`.dex` → Java, decodes the manifest and resources
("can't decompile 100%"). **Vineflower** (Apache-2.0) is the best current plain-Java decompiler
(records, sealed classes). JD-GUI for a quick glance.

**Python.** `pyinstxtractor` unpacks a PyInstaller `.exe` to `.pyc` (run it with the matching Python
version); then `uncompyle6`/`decompyle3` for ≤3.9, `pycdc` for 3.10+. Treat 3.11+ decompiles as
INFERRED until confirmed against behaviour.

**Unity — the common game case, with a scope line.** This is for our own builds, and for games whose
licence or terms permit study; never a live-service or online game, never anything that ships
anti-cheat or anti-tamper. **Mono** → `Assembly-CSharp.dll` decompiles (Tier 1). **IL2CPP** →
`GameAssembly.dll` + `global-metadata.dat`: our own IL2CPP builds have source, so read that; a third
party's IL2CPP or protected build is **out of scope**
(`research/reviewed/reverse-engineering-2026-10-13/house-inventory.md`, gap G6). If a
`global-metadata.dat` is encrypted or obfuscated, that is a protection measure: stop and record
"protected, not analysed". AssetRipper extraction follows the same scope (our builds, or terms that
permit it) — measurements may leave the VM, the assets may not (copyright). Godot: GDRE Tools /
gdsdecomp recovers the project and GDScript from a `.pck`, under the same scope.

## Electron and JavaScript — usually not compiled at all

An Electron app is a web app in an **`app.asar`** archive (a Chromium Pickle header + JSON file table
+ concatenated contents) — not encryption, not compilation. If the developer did not turn on integrity
fuses, reading it is trivial (this is the default; verified on Mullvad VPN, GPL-3.0: integrity
validation off, only-load-from-asar off, and 219 source maps shipped inside). **`@electron/asar`**:
`asar list`, `asar extract`. **`npx @electron/fuses read --app <path>`** reads the security fuses
(`npx` downloads and runs a package: **Daniel's decision**). An app we did not build is an untrusted
sample, so extracting or reading it is VM work.
**Electronegativity** (Apache-2.0) audits our own Electron apps for `nodeIntegration`/missing
`contextIsolation`. **Defeating integrity fuses to load modified code is circumvention — out of
scope.**

**Minified/bundled JS:** **source maps first** — a `.map` (linked by `//# sourceMappingURL=` or an
HTTP header) with `sourcesContent` *is* the original source (format now ECMA-426). **No map?**
**webcrack** (MIT) deobfuscates obfuscator.io and unpacks webpack/browserify; **wakaru** (Apache-2.0)
un-minifies and un-bundles and reverses Babel/TS. Neither recovers original *names* a minifier
destroyed — only structure. (wakaru's README is blunt that use without consent is illegal.)

## WebAssembly

A `.wasm` is magic `\0asm`, a version, then sections; the optional **name section** (custom id 0) holds
names if it survived. **WABT** (Apache-2.0): `wasm-objdump -h` (section map) → `wasm2wat` (text) →
`wasm-decompile` (readable C-like; its author is candid that LLVM optimisation makes the output "very
unlike what a programmer would write"). Read the **import section** to see what the host (JS) must
provide — the interesting behaviour usually lives there. WAT is a decompilation, not the source.

## Dynamic analysis — watching software we own run (VM; legal + host rules apply)

- **x64dbg** (Windows user-mode) — step through our own native code or a crackme we wrote.
- **WinDbg + Time Travel Debugging** (free, Microsoft) — records execution to a `.run` trace and
  replays it **forwards and backwards**, queryable with `dx`. User-mode only, read-only playback,
  10–20× slowdown, can deadlock Electron. Nothing beats running execution backward to a bug's cause.
- **Frida** (dynamic instrumentation) — Interceptor hooks functions, Stalker traces; fastest way to
  log "what arguments does this function actually get" on *our* software. Dual-use (hooking is also
  how cheats work) — observation and interop only, never against online-game protections.
- **Process Monitor** (Sysinternals) — "where does this app store its save/config?" without touching
  the binary. **API Monitor** — decoded Windows API/COM calls and arguments (freeware, old; VM).

Dynamic cannot prove a negative (you only saw the paths you exercised) and gives no clean source.
Pair it with static.

## File and save formats — the part that matters most for a game

If the goal is an upgrade path and releasable weapons/effects, the fights are in **data**: the save,
the item/weapon tables, the config. Formats outlive tools, so this is the most durable skill.

**Entropy first — the free X-ray.** Sliding-window Shannon entropy (Aldo Cortesi's technique): ~0 =
padding; ~4–5 = text/code/records (readable); ~7.5+ and flat = compressed/encrypted/packed (opaque).
It shows *where* the opaque payloads are before you understand the format (verified: `app.asar` ~4.5–5,
`Enemy.flp` body 7.9+). **Entropy alone cannot tell compressed from encrypted — a recognised header
can.**

**The format loop (OBSERVED vs INFERRED per field):** header/magic (`FLhd`, `\0asm`, `PK`, `\x89PNG`);
carve the top-level structure (many formats are tag+length+body chunks) — **the length field is your
falsifiable test**: if walking tag→length→skip lands you exactly on the next tag and the file end, the
structure is OBSERVED-correct; if it drifts, the hypothesis is wrong, no guessing. Then classify
records, find variable payloads by entropy, diff to find meaning, document. (Worked on our own
`Enemy.flp`: the parser walked 2,874 events and ended exactly on the declared `FLdt` length — structure
OBSERVED — and identified the 7.9-bit mass as six `id 213` plugin-state blobs; a readable envelope with
opaque payloads, exactly a game-save shape.)

**Tools:** **Kaitai Struct** (`.ksy` YAML → a parser in 12 languages *and* the documentation, one
artifact; Web IDE + gallery) — how the house should capture every format it reverses. **ImHex**
(GPLv2) — the reverse-engineer's hex editor: Pattern Language, entropy/byte-distribution graphs,
Capstone disassembler, ~300+ ready patterns. **010 Editor** (paid) — Binary Templates. **binwalk v3**
(MIT, Rust) — firmware/blob triage (`-E` entropy, `-e` extract) **in the VM** (CVE-2022-4510).
Documentation registries: Library of Congress FDDs and PRONOM/DROID; Ange Albertini's Corkami (a file
extension is a claim, not a fact).

## Routing table (software/binaries)

Markers as in the master table: **(VM)** is VM-only whatever the file; **(trusted on host; untrusted → VM)**
runs on the host only for files we built or recorded, or that Daniel has ruled trusted.

| Artifact or question | First tool | Evidence | What it cannot tell you |
|---|---|---|---|
| Unknown file, any kind (trusted on host; untrusted → VM) | `diec` + entropy scan | Type, compiler, packer, tier; opaque regions | Behaviour; names if stripped |
| ".NET or native?" (trusted on host; untrusted → VM) | PE CLI header / `BSJB` | Tier 1 (ILSpy) vs Tier 2/3 (Ghidra) | How good the decompile is until you run it |
| Windows native (VM) | Ghidra `-readOnly` | Disassembly, pseudocode, imports/exports, strings | Runtime values; branch taken |
| .NET / Unity Mono (trusted on host; untrusted → VM) | ILSpy; dnSpyEx to debug (VM) | Near-original C#, names | Values behind runtime config; a third party's IL2CPP is out of scope |
| Android apk (VM) | JADX | Java, manifest, resources | Native `.so` (→Ghidra); server |
| PyInstaller exe (VM) | pyinstxtractor → pycdc | `.pyc` then source | 3.11+ control flow (INFERRED) |
| Electron app (trusted on host; untrusted → VM) | asar extract; fuses read | JS/TS, package.json, source maps | Minified names; native modules |
| Minified JS + `.map` | read `sourcesContent` | The original source | — (you have it) |
| Minified JS, no map (trusted on host; untrusted → VM) | webcrack / wakaru | Structure, modules | Original names (gone) |
| `.wasm` (VM) | wasm-objdump→wasm2wat→wasm-decompile | Sections, API, WAT, pseudocode | Original source; stripped names |
| Unknown binary/save format (trusted on host; untrusted → VM) | ImHex entropy + Pattern Language; binwalk, always (VM) | Structure, chunk edges, opaque regions | Field meaning without diff/behaviour |
| "Where does it store data?" (ours) | Process Monitor | File/registry paths | Why; on-disk format |
| "What APIs, what args?" (ours, VM) | API Monitor / Frida | Live calls, params | Unexercised paths |
| "Walk a bug backward" (ours, VM) | WinDbg TTD | Reversible trace | Kernel; PPL |
| "What changed v1→v2?" (VM) | BinDiff | Matched/changed/new functions | Why |
| "Document a format" | Kaitai `.ksy` | Parser in 12 langs + spec | Semantics not yet reversed |
| "What can it do?" (VM) | capa | Capabilities (ATT&CK) | Whether it ran them |
| Firmware image (VM) | binwalk `-E` then `-e` | Filesystems, kernels, entropy map | Logic inside (→Ghidra); encrypted parts |

## Lessons (trigger-phrased)

- Use when you receive any compiled artifact, before choosing a tool: identify the tier (managed→
  near-source; native+metadata→pseudocode+hints; stripped→infer) with one `diec`/PE-header/magic check.
  Don't when you already have source — that is ordinary code reading.
- Use when you meet an Electron or web app, before reaching for a disassembler: `asar extract` and look
  for `.map` source maps. Don't when the only path is defeating integrity/only-load fuses — that is
  circumvention.
- Use when you face an unknown binary or save format, before writing a parser: run a sliding-window
  entropy scan to locate text/code vs compressed/encrypted. Don't when the file is tiny or you have a
  spec.
- Use when you state any finding, before writing it: tag OBSERVED/INFERRED/UNKNOWN with an evidence ID,
  and validate structure with a falsifiable check (does the declared length land on the next record?).
  Don't trust a function or field *name*.
- Use when anything untrusted must be run, parsed or extracted, before touching it: the never-on-host
  rule above applies (disposable VM, reverted after, sample out of the repo); on this host there is no
  safety net. Don't execute at all if reading bytes in the VM answers the question.
- Use when scoping a task touching a third party's product, before starting: check the EULA (a no-RE
  clause can bind in the US; void against interop/study rights in the EU/UK), stay inside
  interoperability/understanding/our-own-security. Don't when the only way is defeating DRM, a licence
  check or anti-cheat — stop and escalate.
- Use when documenting a reversed format, before it evaporates into a one-off script: write a Kaitai
  `.ksy`. Don't when a throwaway byte-dump answers a one-time question.

## Gaps (build proposals)

No RE toolchain is installed (no Ghidra/rizin/x64dbg/IDA/JADX/ImHex/binwalk/WABT/Frida/asar/7-Zip/
strings, no JRE/JDK; only `pefile`+`python-magic` in Python, Node 24, `dotnet`, Docker, WSL; each
install is **Daniel's decision**). Proposals:
an `arsenal/re` installer/launcher provisioning a pinned set into a container; an `arsenal/sandbox run`
(the VM of `method-legal-cleanroom.md`); a `formats/` tree of `.ksy` specs; an `re_finding` ledger
primitive; an `arsenal/tools classify <file>` verb (the routing table as a command — `re_examples.py`
is a working prototype of its guts); a cached `research/legal/` of the key statutes/opinions.

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
the EU, where a database right can apply). **For this domain:** decompiling to interoperate is the
protected case; decompiling to copy is not. Defeating a licence check, packer, DRM or an Electron
integrity fuse is circumvention and out of scope, and a third party's Unity IL2CPP or protected
build is out of scope. GPL/AGPL code read during study brings its duties if copied, and IDA Free and
Binary Ninja's free tier are non-commercial. The full map with its caveats is
`method-legal-cleanroom.md`; anything we ship that leans on someone else's product goes past a
lawyer first.

## Sources

Full report: `research/reviewed/reverse-engineering-2026-10-13/software-binaries.md` (every tool URL,
the five worked examples, the complete routing table). Tool projects: Ghidra
(github.com/NationalSecurityAgency/ghidra), rizin/Cutter, IDA Free (hex-rays.com), Binary Ninja,
Detect It Easy (horsicq), capa + FLOSS (mandiant), BinDiff (google), ILSpy (icsharpcode), dnSpyEx,
JADX (skylot), Vineflower, pyinstxtractor/pycdc, AssetRipper, GDRE Tools, `@electron/asar` + fuses,
Electronegativity (doyensec), webcrack (j4k0xb), wakaru (pionxzh), WABT (WebAssembly), Kaitai Struct,
ImHex (WerWolv), binwalk (ReFirmLabs), x64dbg, WinDbg TTD (Microsoft), Frida, Process Monitor
(Sysinternals), API Monitor (rohitab). Discipline credited to **morluto/rea**.
