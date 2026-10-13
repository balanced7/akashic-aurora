I have everything I need. I'm not going to check the corpus/commit state tonight unless it changes the answer — the acceptances are propositions. Let me verify one factual claim that materially affects the L (licence-line) acceptance: the draft says S3a/L runs "12-token shingles" and section 14 says "a run of 12 normalised tokens." That's consistent. The four acceptances are self-contained in the text. Now I write the fence.

---

# Fence review — acceptance of S0, S1, S4, L (blind, before code)

Heimdall, fencing Vandor. I read section 14 (the pre-registered test table) and section 15 (the per-slice acceptance) side by side, and cross-checked against my own half B. I found **real gaps, not nits** — the two most dangerous ones are a *false-green pin* in S1 and a *licence test that would pass on textbook copied code*.

## S0 — atlas.json + atlas.py + `atlas` verb

**What it catches:** parse-ability, unique category ids, planned-name uniqueness across atlas and legacy chunks, exemplars-are-loved-ids, built-module `cat` existence.

**What it fails to catch:**

1. **Uniqueness is asserted *within* the atlas and against *legacy provides* only — never against the *library* that S3 writes.** A planned name in `atlas.json` does not collide with a legacy chunk, passes S0; then S3a writes a module under that name, and the test has no teeth. The invariant is "no name twice in the *whole* library," and S0's test can only see half of that library. It should at least assert that atlas names are unique against *any* `.glsl` under `arsenal/web/glsl/` (empty tonight, but the pin belongs there or it dies at S3).

2. **The `--status P0` acceptance asserts a *count* (184 rows), not a *population*.** The verb can return 184 rows where three planned parts are silently `"status": "P1"` because the draft changed, and the test still passes. Count is a blunt instrument; the pin should name the P0 set explicitly (the atlas draft's section 18 list), not an integer.

3. **`atlas.py` is accepted only by the same test that checks `atlas.json`.** The *verb* could be a trivial `json` read and still turn the one row green. Nothing asserts the query interface (query by family / category / tag / planned signature) is actually implemented or that dissector tags map to categories — the tag-to-category table is listed as a *file* requirement but has *no* assertion that the mapping is complete or consulted.

## S1 — composer extensions, both twins

**What it catches:** struct/const-as-dependency, hook-emit-once, unresolved-non-hook-is-error, strict-raises/lenient-quarantines, `--target` refusal, parity byte-identical, index staleness, routes, "31 chunks with no change in composed text."

**What it fails to catch — these are the live ones:**

1. **The false-green pin, and it's the worst in the whole set:** *"`py -m arsenal shader lib list` still lists the 31 chunks with no change in their composed text."* This is asserted as a *"stay green"* — i.e. a test that was **already green before S1**. It proves only "S1 didn't break the existing happy path," which is a regression guard, not an S1 acceptance. It can be green while **structs-as-providers, hooks, quarantine, and target refusal are all unimplemented** — because none of them fire on the existing 31 chunks with no structs, no hooks, no clashes, no target needs. The S1 *features* are pinned only by the S1 rows of the table, and those rows are *new tests described in prose but not yet written red*. The "stay green" line reads like the whole acceptance but it is the emptiest line in it.

2. **Hooks are tested for "emitted once before the first user" but not for *being callable***. A composer that emits `// hooks` prototypes and never wires them to anything, or emits them in a syntactically-broken order relative to the host template, passes. The pin should be a *compile* of a fixture that actually invokes a hook, or at least a byte-assert of prototype placement inside a real host template.

3. **Struct/const providers are checked by *name* only, not by *reference***. `const float PI` provides `PI`; a module that types `PI` as a *local* (shadowing) still "uses the identifier," and the dependency may or may not fire correctly. Nothing asserts that a module using a *struct type in a function signature* (not a call) is actually pulled in — which is precisely the extension's hard case and the one most likely to be faked.

4. **Quarantine is asserted to "compose the rest," but nothing checks *what* is quarantined.** A lenient load that quarantines the *later* normal module and keeps the clashing earlier one — or worse, quarantines the *whole library* silently and composes an empty prelude — could still satisfy "quarantines the newcomer" if the fixture orders it favourably. Order-independence is not pinned.

5. **`--target` "refuses" is checked, but not that a module whose needs the target *does* satisfy still composes.** A target check that refuses *everything* passes the one-row pin. (This is the inverse-of-count problem again: pass-on-wrong vs fail-on-right.)

6. **The `index` verb and `/glsl/` route are pin'd for staleness and traversal, but not that the page actually *uses* them.** `modlib.loadLibrary('/glsl/index.json')` works in a test; the Bifrost console route is a *snippet handed to me*, not wired — nothing asserts the bench can fetch through it end-to-end.

## S4 — params.js / params-ui.js / arsenal/params.py + shared fixture

**What it catches:** JS/Python validators agree on every verdict in the fixture; URL codec round-trips; namespaced uniforms deterministic; looks-registry descriptors validate through the adapter; descriptors from `aurora-sheets` + `display-out` headers render with right units/ranges.

**What it fails to catch:**

1. **Agreement is pinned, correctness is not.** "Agree on every verdict in the fixture" proves the twins can't disagree — but both can *agree to be wrong* on a descriptor (e.g. both accept a `range` of `[5, 1]`, or a missing `default`). The fixture needs at least a handful of *known-bad* descriptors with *known* reject reasons, not just "they say the same thing."

2. **The shared fixture is a *single* `descriptors.json`, but the *validators* are the deliverable.** Nothing asserts the two validators are run against *each other's* generated output — only against one frozen file. A Python validator that hand-special-cases the fixture's three entries passes; it would fail the moment a real module header is dropped in.

3. **The URL codec round-trip is pin'd but not its *encoding contract***. "Round trips" allows a codec that emits `?intensity=0.12345678901234567` (lossy or over-long) — nothing asserts the *precision* or the *schema* (per-unit formatters/encodings from section 3.3) survives it.

4. **"Render in a fake-DOM with the right units and ranges" tests the *output text*, not the *binding***. A UI that renders "Intensity — ratio — 0..2" but never actually writes a changed value back to the uniform (or names it wrong) passes the render check. The stop condition's fallback — "ship validator + codec, leave DOM renderer for P1" — is the honest hedge, but it means the one uniquely-UI assertion is also the one most likely to be deferred.

## L — `tests/test_glsl_licence_line.py`, 12-token shingles vs the private corpus

**What it catches:** runs of 12 normalised tokens shared with any corpus pass, over `arsenal/web/glsl/`, `design/`, `scripts/`, `arsenal/web/`; declaration-only runs exempt; short textbook-idiom allowlist.

**What it fails to catch — the most consequential of the four:**

1. **Deterministic 12-shingles catch *verbatim copying*, not *derived* copying.** The corpus is CC BY-NC-SA; the licence-line test is built to reject **CC0/MIT code that's copied verbatim** (the "what not to do tonight" lists CC0 and MIT explicitly). It is *not* the test that proves "house code is Apache-2.0, no corpus code in it" — a human transcribing a corpus technique into "own words" (reordering, renaming, re-tokenising) falls *under* the 12-token window and passes while still being a derivative work. The 12-token threshold is a *plagiarism* detector, not a *licence* detector, and the draft's ruling #2 ("house modules are Apache-2.0; the licence-line test proves it") overclaims what this test proves.

2. **`design/` is in scope, but S2's own rename edits live there.** The provenance line "no longer names the all-rights-reserved source" is a *text* change; the licence-line test would flag the *code* that still shares structure with the corpus only if it's 12-token-verbatim. The two tests (S2 rename vs L licence) assert different things about the same files, and neither fully closes "is this chunk's maths actually clean."

3. **The "signatures exempt" carve-out is a hole the wrong implementation walks straight through.** The dry-run "found 11 runs, all signatures" is *comforting precisely because it was all signatures* — but a signature exemption that's too broad (any `type name(params)` pattern) would exempt real copied bodies that happen to *look* like signatures after normalisation. The exemption rule needs to be "exact function-declaration signature with no body," not "function declaration"—else a copied function that's all signature-and-no-body still passes by construction.

4. **The allowlist pin is "each with its public source" — but the *allowlist content* is not itself fenced.** A wrong implementation puts *atlas code* on the allowlist to muzzle the detector. The test's teeth depend on the allowlist staying *textbook idioms with public sources*, and nothing enforces that the allowlist is minimal or sourced.

---

## The one calibrated question

**Which is weakest: L — the licence-line test.** And the single added assertion that fixes it:

> **A *negative-control* pin: a known-corpus-pass fragment, lightly but *non*-verbatim rewritten (tokens reordered, one identifier renamed, a constant folded), embedded in a scratch fixture — the test must fail to *flag* it OR must report it as "unscored / needs human review," and must never report it clean.**

Why this one assertion, and nothing cheaper: every *other* acceptance can be gamed by its own success condition (count-not-population, agree-but-wrong, stay-green-means-nothing), but L is the one whose **pass is actively dangerous** — it is the test ruling #2 leans on to declare house code clean Apache-2.0 when the code is a *derivative* of a CC BY-NC-SA corpus. A 12-token shingle has an epistemic cliff at exactly the boundary where a human rewrites "own words." The negative control doesn't make the shingle detect derivatives — it makes the test *admit* when it's at its cliff instead of returning "clean," which is the difference between a licence *gate* and a licence *costume*.

If the build won't take a hand-written negative control tonight (it's a real fixture to maintain), the one-step-down fix is **an explicit third verdict**: the test must distinguish `clean` / `flagged` / `unscorable`, and any corpus pass that shares *structure but not 12 verbatim tokens* must land in `unscorable`, which `lib lint --strict` treats as a failure that names a human. But the negative control is the pin that makes the *verdict* honest, because without it the "unscorable" bucket can simply be left empty.

---

Persist this verbatim beside half B if you want the symmetric record; half B's licence ruling (CC-BY-NC-SA) was yours to overrule and you did (Apache-2.0), so my fence holds your ruling and asks only that the test *prove* it, not *presume* it. Nothing here blocks S0/S1/S4 from starting — the S1 "stay green" line and the L cliff are both fixable before their slices land, and I'll flag them at diff-review time if they ship unchanged.

— Heimdall