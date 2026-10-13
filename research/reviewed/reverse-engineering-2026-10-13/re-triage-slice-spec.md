# re triage — the read-only front door of the reverse-engineering arsenal (SLICE SPEC)

Status: draft (unreviewed)
Class: research
Arc: reverse-engineering-2026-10-13 (gap G3)
Written: 2026-10-13, Heimdall (deepseek seat), for Daniel's "I want us to have the whole reverse engineering arsenal"

This is a SPEC, not an implementation claim. It defines the first slice: `re triage`, the
read-only "what is this file, and which door do we open next" router. It answers gap G3 in
Vandor's `house-inventory.md` — "No generic 'what is this file' router" — and leans on his
inventory (F5: `python-magic` and `pefile` are already installed) rather than asking for new
tooling.

---

## 0. What it is, in one screen

`re triage <path>` reads a file's first bytes, identifies what kind of thing it is, and routes
to the right per-format door — the way `arsenal.media probe` knows a video, `shader dissect`
knows GLSL, `riot.py` knows match JSON. It runs **read-only**: it opens the file, never
executes it, never trusts it, and every conclusion is an observation, an inference, or an
unknown — the REA discipline Vandor already restated in `teardown-toolkit-and-practice.md`.

The point is NOT to parse every format (that is what the per-format doors do). The point is to
answer, loudly and with a bounded search, the one question a router must answer before any
deeper tool runs: **what did we just get handed, and what may we do with it here?**

## 1. The contract (three rules)

1. **Read-only, always.** Open with `open(path, "rb")`, read a bounded prefix, close. No
   import, no unpack, no execute. Arbitrary unsandboxed binaries are opened only inside a
   disposable VM — Vandor's gap G1, Daniel's call, *not* this slice's. `re triage` therefore
   reads a bounded prefix and stops; it never runs a target.

2. **Observations apart from inferences apart from unknowns.** Every field in the receipt
   carries an evidence tag: `[observed]` (bytes we read), `[inferred]` (what a detector
   guessed, with its confidence), `[unknown]` (questions we know we have not answered). The
   split is the whole point of the discipline.

3. **Bounded negatives stay bounded.** "No match" means "no detector in the registered set
   matched, over the first N bytes, at this hash" — never "this is nothing". The `blind`
   field names exactly what was not searched.

## 2. The receipt (house shape, matching `arsenal/media`)

```json
{
  "api": "arsenal.re/v0",
  "source": {"path": "...", "sha256": "...", "size": 12345, "prefix_bytes": 4096},
  "params": {"max_prefix": 4096},
  "computed_with": {"python_magic": "0.4.27", "pefile": "2024.8.26", "detectors": 7},
  "payload": {
    "kind": "PE executable",
    "matches": [
      {"detector": "pefile", "claim": "PE32+ executable (GUI), x86-64",
       "tag": "observed", "confidence": 0.99, "evidence": "magic MZ at 0x0, PE\\0\\0 at 0x3c->0xf8"}
    ],
    "candidates": ["native binary", "maybe .NET"],
    "route": "arsenal re binary"  // which door we open next
  },
  "blind": {
    "unsearched": ["only first 4096 bytes read"],
    "defenses": ["not executed", "not unpacked"],
    "notes": ["no sandbox enabled on this host; do not run until G1 is Daniel's call"]
  }
}
```

## 3. The detector ladder (cheap first, exact before guessing)

Ordered so the cheapest and most certain claim wins, and a detector never runs after a
higher-confidence claim already routed the file:

1. **`python-magic` (libmagic)** — the byte-signature oracle. Magics a file by its contents,
   not its name. Emits `[observed]` (that is what libmagic does — it reads signatures) but
   tagged `[inferred]` because it guesses a *kind*, not a proof.
2. **`pefile`** — if libmagic says PE: parse the DOS/PE headers, emit machine type, subsystem,
   .NET presence (COM descriptor directory), bitness. `[observed]` fields (real header bytes).
3. **ELF/Mach-O header checks** (struct reads, no import) — for binaries that are not PE.
4. **Archive/container signatures** (zip, tar.gz, 7z, rar) via magic + header bytes.
5. **Script/plaintext heuristics** (shebang, `<?xml`, `<html`, `{`/`}` density) — lowest
   confidence, always `[inferred]`.
6. **Fallback** — `[unknown]` kind, with the byte histogram as the only observation, and a
   loud "nothing matched" that names the denominator.

## 4. Routing (what it says next, not what it does)

`re triage` only *names* the next door; it never runs it. The route map (living, grows as the
arsenal does):

| Detected kind | Route |
|---|---|
| PE / native binary | `arsenal re binary` (gap G5 — NOT built; triage names it and stops) |
| video / audio / image | `arsenal media probe` (exists) |
| GLSL source | `shader dissect` (exists) |
| JSON (Riot match-v5) | `riot.py` (exists) |
| generic JSON / text / unknown | `arsenal re ledger` (gap G2 — NOT built) |

Triage pointing at a not-yet-built door is a feature, not a gap: it makes the map honest. The
router knows the arsenal's *current* extent and says the boundary out loud.

## 5. What this slice deliberately does NOT do

- Does not disassemble, unpack, execute, or sandbox (G5, G1 — later / Daniel's call).
- Does not keep a finding ledger (G2 — the ledger is a separate slice; triage's receipt is a
  snapshot, not a case file).
- Does not guess DRM/anti-tamper/work-alike status — out of scope and out of the legal fence.
- Does not register an MCP door (Daniel's call; `arsenal/media/door.py` shows the precedent).

## 6. Build order (next)

1. `arsenal/re/__init__.py` — the receipt schema + evidence-tag enum.
2. `arsenal/re/triage.py` — the detector ladder + router, pure functions, no processes.
3. `arsenal/re/cli.py` — `cli.VERBS["triage"]` registration, matching `shader dissect`'s shape.
4. Register `external` engine in the manifest (the hook `registry.py` already reserves).
5. Pins: a fixture PE, a fixture zip, a fixture text, a fixture unknown — each asserting the
   `[observed]/[inferred]/[unknown]` split and the `blind` field.

This is the spec. Rebut or reshape before I pour the implementation.
