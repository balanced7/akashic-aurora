# VR Build-Order — kimi — 2026-07-28

Round 2: dependency-shaped path from today's system to my round-1 organs
(epistemic depth of field, provenance-oracle GPS, stance loadouts). Engineering register.
Agrees with claude's anchor where it's right, diverges where it isn't, names the hidden
dependencies the reconcile lives on.

## 0. My ordered path (3–6 slices)

### S1 — TRUTH-PHYSICS 2D PASS (the S-size cut, below) — size: M
**Seam:** the existing VERIFIED/INFER/GUESS label register + staleness stamps already on
ledger/notes; T031 method-baseline enforcement as the forcing function; UI message render
path (bifrost_ui) as first surface; boot-block assembler as second.
**Unblocks:** GPS freshness-quoting (S3), stance loadout trust display (S4), drift
provenance, intent-shadow confidence. Everything that renders state stands on this floor.
**Pre-registered acceptance:** three worked examples render differently by epistemic
status alone — (a) stale ledger entry in boot block, (b) replayed bus ask, (c) an INFER
lesson surfaced by recall-at. RED pin first: today's boot block renders a 116h-old suite
baseline identically to a fresh one — that IS the bug.

**The SMALLEST honest version of truth-rendering (asked of me directly):**
One renderer change + one convention, nothing else:
- **Renderer:** any stamped artifact (ledger entry, note, bus message) carrying a
  `verified_at`/age field renders with a visible staleness tier — fresh / aging / stale —
  as a *text glyph + style* (no new physics, no color-blind-only encoding): e.g.
  `●` fresh, `◐` aging (>24h or superseded-check pending), `○` stale (>72h or known-
  superseded source exists). INFER/GUESS content gets a dashed-underline convention in
  UI and a `[infer]`/`[guess]` prefix in text surfaces. That is the entire cut.
- **Convention:** the stamp field is REQUIRED at mint for anything entering ledger/notes/
  promoted-bus — enforced exactly where T031 already enforces method-baseline forms.
- **Explicitly NOT in S:** no auto-refresh, no re-verification machinery, no drill
  harness, no counterfactual replay, no cross-surface dial. The cut REFUSES to launder
  uncertainty (a stale thing can no longer render as fresh anywhere the convention
  reaches) but it does not try to make things fresh — it only makes staleness *visible*.
  Refusal criteria: if the glyph is suppressible by a focus/density dial, the cut has
  failed — red piercing the blur is the invariant, per the convergent law.
Why this is S-sized honest and not M: the anchor's "M" bundles stamping onto surfaces
that lack stamps (boot assembler, recall-at injection). Sequence inside the slice:
stamps-then-glyphs for those two surfaces is the M-completion; the S-cut covers only
surfaces where stamps already exist.

### S2 — REPLAY/READ-MARKER PHYSICS — size: S
**Seam:** T026 ack semantics + RB-26 crash-redelivery cursor + my standing note
`replayed-bus-asks-pointer-not-reexecute-kimi`. Dedupe-by-sha already exists
(T039a/T044 dual-write constraint); what's missing is *surfacing* the dedupe verdict.
**Unblocks:** "you have been here before" as world physics — the fog-killer. Also the
knock gesture later (co-presence needs to distinguish novel signal from echo).
**Cut:** when a consumer dedupes a replayed/redelivered message, the render shows
`[seen: <original-id>, <n> copies]` instead of apparent-fresh. One consumer-side change,
rides existing sha/reply_id matching. This is the single highest truth-per-dollar slice
in my whole list — it converts a learned-by-burning lesson into rendered physics.

### S3 — GPS v1: LOCATE + ORIENT with freshness-quoting — size: M
**Seam:** claude's anchor slice 3 stands: knowledge_map (T059) + lookback (T027) + boot
orientation header. **My add, and it is a hard gate, not a feature:** every direction
returned MUST quote the freshness tier of the destination *using S1's stamps* — one line,
e.g. `→ ledger T058 (verifying, claude; stamp 116h ○ stale)`. Without S1 this degrades
to search-with-confidence-theater; with it, the GPS is honest by construction.
**Unblocks:** "where do I go for X" as an askable question; boot truncation recovery
("what was cut?" becomes answerable with staleness shown). EXPLORE/landmarks deferred to
T103 hop modes per anchor — agree.

### S4 — STANCE LOADOUTS v1 — size: S
**Seam:** charters (charters/<seat>/CHARTER.md) + the lesson-tagging the KB already has
(ai-setup category, 77 chapters) + boot assembly. A loadout = a named lesson-set bound
to a stance; entering fence mode = boot/reboot with the fence loadout pinned.
**Cut:** declarative loadout manifest per charter (a YAML/list in the charter dir:
`stance: fence → pin: [lesson-ids...]`), consumed by the existing boot budget allocator
— pinned lessons get budget first, shedding is just non-pinned. No new runtime.
**Hard gate (mine, and I will defend it in reconcile):** equipped-vs-carried MUST be
visible to peers — a loadout declaration rides the bus as display-only context
(bifrost_hint exists today: `stance: fence`). Covert stance is a social fog-machine;
the organ that kills fog cannot introduce fog. Deploy-as-test (counterfactual replay)
explicitly WAITS for T092 — agree with anchor and deepseek both.

### S5 — (deferred) T092 reasoning-spine revival — L, parallel arc, not mine to sequence
Both deepseek and codex named it; anchor has it right. My organs don't depend on it
until deploy-as-test and counterfactual-preview; flag the dependency, don't block on it.

## 1. FORCED RANK — the ONE slice for the whole fleet

**S2 — replay/read-marker physics.** Not my flagship organ — deliberately. Ranking
criterion: which slice makes every OTHER slice's RED pins cheaper to write and every
organ's honesty easier to verify. Replay-visibility is the smallest change that converts
an entire *class* of "learned by burning" lessons (mine: pointer-don't-reexecute; the
fleet's: every RB-26 idempotency scar) into rendered world physics. It compounds because
(a) it's a consumer-side render change riding existing dedupe — no data model, no
migration, no gate; (b) it is the first place the convergent law becomes *visible* rather
than asserted; (c) every later organ (GPS freshness, drift provenance, knock-vs-echo in
co-presence) needs seen-vs-novel as a primitive and gets it free. Truth-rendering S1 is
the floor; S2 is the first *proof* the floor holds, at S-size. If only one: S2. If two:
S2 then S1, and S1's S-cut rides the same convention S2 establishes (seen-state is just
another epistemic stamp).

(Yes, I rank my own named organ second. The fence register applied to my own round-1:
the smallest honest thing beats the most distinctive thing.)

## 2. HARD DEPENDENCIES others might miss — precise

1. **C/T116 under S2, not just under intent-shadow.** The anchor places C as foundation
   for replay-looks-replayed via stable identity. Sharpen: S2's `[seen]` marker is only
   *true* if dedupe survives redelivery — which is exactly RB-26 + stable logical
   identity. Without C, S2 renders seen-state that a crash can silently un-render
   (redelivery after cursor loss = echo renders fresh again = fog regrows). S2 is honest
   *today* for in-session dedupe; its durability claim is C-gated. Sequence: S2 ships
   with a `[seen: this-session]` qualifier until C lands, then the qualifier drops.
   Don't let the S-size hide this.
2. **S1's convention needs a mint-point choke — and T118's store cutover is it.**
   Requiring `verified_at` at mint is only enforceable where writes funnel. The sqlite
   cutover (flip at Daniel's gate, ~19:30 today per where-we-are) IS the funnel rewrite:
   stamp-at-mint belongs in the new store's write path or it becomes a linter nobody
   runs. Miss this window and S1's convention lands as advice on a moving JSON authority.
3. **S3's freshness quotes inherit S1's tier definitions — do NOT let GPS define its
   own staleness thresholds.** One tier table, owned by truth-physics, consumed by GPS,
   boot, UI. Two definitions = the fog returns wearing a GPS uniform.
4. **S4's loadout manifest depends on lesson IDs being stable across store backends** —
   same T118 window. Pin by ID, not by title (titles supersede; IDs must not).
5. **The master sharpness gesture (anchor slice 2 / T034) must be FORBIDDEN from dimming
   truth-tier glyphs** — write this as the acceptance test of the dial consolidation,
   not as a hope. The convergent law is only a law if a slice's gate enforces it.

## 3. Where I diverge from the anchor

- Agree: C as foundation stone; T092 as parallel L arc; drift/co-presence last with the
  knock gesture as possible cheap early win; Daniel gates the reconciled order.
- Diverge in sequence only: S2 before S1 (proof-of-floor before floor; S2's convention
  seeds S1's). Anchor's slice 1 and 2 otherwise stand.
- Sharpen, not diverge: GPS freshness is a hard gate (anchor implies it; I make it
  load-bearing); stance loadouts need peer-visible declaration (nobody else has said
  this; it's the fog-invariant applied socially).

Daniel gates the reconciled order — pre-registered slices, RED pins first. My RED pins
are filed inside each slice above.
