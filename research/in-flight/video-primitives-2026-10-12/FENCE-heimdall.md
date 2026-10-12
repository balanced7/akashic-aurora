# FENCE — video primitives v0 (arsenal.media)

Heimdall, 2026-10-12 ~03:00. Fence of Vandor's build spec + the three committed foundation commits.
This REPLACES my earlier bus reply (which fenced without the spec prose). Boundary now closed: I read
`PRIMITIVES-SPEC.md` in full (Parts 0–7), `FENCE-REQUEST.md` (the 9 reconciliation points + the three
questions), `STUDIO-RECONCILED.md` (the studio decisions), and the committed code:
`arsenal/media/{ff,receipt,frames,probe,__init__,__main__}.py`, `tests/test_arsenal_media_ff.py`,
`tests/test_arsenal_media_frames.py`, and the head of `arsenal/tiktok.py`.

**Verdict: PASS with conditions.** No lane's output is *wrong* as specced, and the REUSE/EXTEND sheet is
the most disciplined version of decision 1 I could hope for. But there are two blocking defects — one in
the *spec text* (it still states the un-reconciled search order) and one in the *code* (a caps check that
bypasses the watch-list) — plus a contract hole inherited from the earlier fence, and several should-fixes.

Order below: **Blocking → Should-fix → Nits → The three questions.**

---

## Blocking

### B1 — The spec still states the OLD search order, and a builder reading it will re-implement it
`PRIMITIVES-SPEC.md` P1 "Order of search" block says:
`1. ARSENAL_FFMPEG  2. PATH  3. config.json  4. imageio-ffmpeg`.
The committed `arsenal/media/ff.py` docstring and `locate()` say:
`env → config → PATH → bundled` (config *above* PATH, with a written rationale).

This is reconciliation point #1, and the code is RIGHT (config is written only by `doctor --save` which
ranks every build; PATH is whatever an installer dropped). But the spec's Part 0/P1 prose — the document a
builder reads *to build the remaining lanes* — was never edited to match. That is the exact "two idioms"
failure the reconciliation exists to prevent: the next lane author, doing diligence against the spec's
"Order of search," will wire PATH before config and diverge from `ff.locate()`. The tests don't catch it
because `test_saved_config_beats_path` pins the *code's* order, not the spec's.

**Fix (spec-side, trivial but mandatory):** update the P1 "Order of search" list to `env → config → PATH →
bundled`, and note the rationale in one line (it already sits in the `ff.py` docstring — copy it). Do this
before any lane author's PR references the old block.

### B2 — `ff.has_filter()` / `ff.has_encoder()` bypass the watch-list and re-read the cache they just wrote
`arsenal/media/ff.py`:
```python
def has_encoder(name: str) -> bool:
    binary = ffmpeg()
    caps(binary=binary)                                    # <- builds + caches the view, discards it
    entry = (_read_json(state_dir() / "caps.json") or {}).get(binary) or {}
    return name in set((entry.get("raw") or {}).get("encoders_all", []))   # <- re-parses raw, all encoders
```
Two defects in one:
1. It calls `caps()` (correctly stamp-cached) and then *throws away the returned view* and re-reads
   `caps.json` off disk, re-deriving `encoders_all`/`filters_all` out-of-band. TOCTOU: if `caps()` were ever
   refreshed with `refresh=True` and the file write raced, this second read sees a different cache. More
   important, it's not *wrong* today only because nothing invalidates the cache concurrently.
2. It answers from `encoders_all`/`filters_all` — the FULL list, **not** `WATCH_ENCODERS`/`WATCH_FILTERS`.
   So `has_filter("movie")` returns True (it's a source filter, present in `-filters`), and a caller wiring
   `-vf movie=...` gets `ff.run` to emit an argv that `caps()["filters"]` never watched and never validated.
   The filter whitelist exists precisely so the primitives only *claim* capabilities ffmpeg actually has in
   the house build; has_filter's full-list read undercuts that.

**Fix:** `has_encoder`/`has_filter` should call `caps()` and read the returned `.get("encoders")` /
`.get("filters")` dict keys (the watch-list), not re-open the cache. If a primitive genuinely needs a
non-watched filter, add it to `WATCH_FILTERS` first — that is the house's declared capability surface.

### B3 — `at_times()` past-EOF synthesizes a "last frame" stamped with the requested t, indistinguishable from a real frame
(upgraded from my earlier should-fix to blocking, because two consumers — avsync (P12) and clockmap (P8) — both
read frames and both can feed their output back onto the timeline.)

`arsenal/media/frames.py` `at_times()`: when a requested time lands past EOF, it yields the last decoded
frame as `(t_req, last_pts, last_img)`. The tuple's second element is the *source* pts of the final frame, but
nothing flags that this frame did not exist at `t_req`. The `blind` list carries the prose ("times past the
end of the file return the last frame"), but `blind` is a receipt-level string, not a per-item marker, and a
downstream `at_times` consumer that just iterates `(t_req, t_pts, img)` will hand a frozen final frame to the
next primitive believing it is the frame at `t_req`.

**Fix:** add a 4th element (or a flag on the item) `synthesized: bool` — False for real frames, True for the
EOF freeze — and make the two frame-consumers (`clockmap`, `avsync`, and the editor's scrubber) assert on it
or drop it. One line to produce, one doctrine to state ("a synthesised frame must be distinguishable from a
decoded one"), otherwise the "bit-identical to every earlier script" promise in reconcile #4 silently becomes
"bit-identical *except at EOF, where we invented a frame with the right timestamp*."

---

## Should-fix

### S1 — `frames()`/`keyframes()` have a split null-pts contract; only `at_times()` guards it
`frames.py` `_stream()` yields `(round(t + t_offset, 6) if t is not None else None)` — i.e. a `None` pts is
possible when `showinfo` emits no `pts_time` for a frame. But:
- `frames()` and `keyframes()` signatures annotate `Iterator[Tuple[float, ndarray]]` (no `None`),
- only `at_times()` does `if t is None: continue`.

A direct `frames()` consumer gets `(None, img)` and, if it feeds pts onward (which avsync/words will), a
`None` sneaks into a subtraction. Make `frames()`/`keyframes()` drop None-pts frames themselves (a frame with
no pts_time is a decoder hiccup, not a frame to hand upstream), and keep the annotation honest.

### S2 — `quick_id` collides on same-head/tail files; add a middle-stride
`receipt.py quick_id` = `sha256(size || first 1 MiB || last 1 MiB)[:16]`. Two *different* files sharing the
first+last MiB (same container header + same trailing run of identical content) collide at 64-bit-equivalent.
Low-stakes as a *catalog* id, but it is also the receipt suffix and the `resolve_dropped` → catalog join key,
which makes a collision a *join* failure, not just a cosmetic hash. This is the exact class your own lesson
`dhash_is_blind_on_flat_frames_pair_it_with_a_palette` names: a content signature blind on a degenerate case.
Add a stride read at `size/3` (or `size/2`) to the hash for ~5 ms more — cheap insurance, matches house muscle.

### S3 — P3's interface names `accurate=True`; the code has no such parameter
Spec P3 lists `frames.at_times(..., accurate=True)`. Committed `frames.py at_times` signature is
`(path, times, crop, size, pix_fmt, hw, max_gap=8.0)` — no `accurate`. Either the spec's `accurate` is a
leftover from the OT scratch (and should be dropped) or it names behaviour the promotion dropped (and should
be kept). A lane author writing `media_grab(..., accurate=False)` per the MCP doc will get a `TypeError`.
Reconcile the surface *before* the MCP door and agent_cli verb get built on it (build step 13).

### S4 — `doctor --save`'s ranking weights are undocumented in the spec
`ff.py _score()` weights: AMF ×4, ass ×3, whisper ×2, scdet ×2, ebur128 ×2, libx264 ×2, has_probe ×3. The
spec never mentions that `doctor --save` is a *ranked replacement*, not a last-write-wins. A builder (or
Daniel, running it by hand) will be surprised when `--save` silently swaps the cached build because a
stronger one scored higher. One paragraph in the spec's P1 (or `ff.doctor` docstring) naming the weights is
enough — the weights themselves are reasonable.

### S5 — `receipt.write()` swallows an OSError into `res["receipt"] = None` silently
`receipt.py result()` → `write()` returns `None` on `OSError`. Correct *behavior* (a receipt failure must not
fail the primitive) but silent data-loss — the house's recurring "hollow control" class. Emit a
`warnings.warn` (or append `"receipt not written"` to the `blind` list) so the "one result shape, always
written" promise degrades loudly, not quietly.

### S6 — `_gpu_wrap` warns "GPU lock unavailable" on every call when `node`/`gpu_lock.mjs` is absent
`frames()` streaming would spam that warning per process spawn. Gate it (module-level `once` flag), or downgrade
to a single stderr line at first import. Not a correctness bug, but it will drown real warnings in the exact
narrow-window streams the primitives produce.

---

## Nits

- `__main__.py` maps `sheet`, `filmstrip` → module `"sheet"`, and `grab` → `"frames"` (with `--sheet`). Both
  `sheet` and `filmstrip` will hit the "not built yet" exit-3 path cleanly — confirm no *two built* verbs share
  a module and disagree on `cli()` arity (`grabs`'s `cli(verb, argv)` vs a hypothetical `sheet.cli`).
- `probe.py` re-exports `quick_id` with `# noqa: F401` and "the documented name," but `quick_id`'s real docstring
  lives in `receipt.py`. Split documentation; one line in `probe.py` pointing back saves a hop.
- `_probe_caps` reads `-encoders`/`-filters`/`-hwaccels` with a 30 s timeout each; first-ever `caps()` on a cold
  cache is ~90 s of subprocess + parse. Fine, but worth a line in `ff.py` noting the first-call cost so nobody
  treats it as a hot path.
- The spec's Part 2 P1 test says "`arsenal.tiktok`'s tests still pass *after it imports from `media.ff`*" — but
  reconciliation #3 says tiktok keeps its own finder and the convergence waits for Daniel. These are in tension:
  the spec's P1 test is a *future* assertion while the reconcile defers it. Pick one and state it; build step 1
  shouldn't be green/red depending on which document the lane author read.

---

## The three questions (from FENCE-REQUEST.md)

### (a) Timeline document as the v0 stand-in for "the board is the master project file"?
**Right call for v0, one field short.** The reconciliation's decision 2 says the master is the *board* (the
storyboard schema with the fact-binding doctrine), and decision 3 says v0's timeline "lives in the board (or a
board-projected timeline document)." The build spec lands on a **board-projected timeline document** at
`state/arsenal/media/edits/<pid>.json` with a rev counter → 409 on stale PUT. That is the correct v0: the rev
counter is the CRDT-fence answer to "one writer at a time," and it is *exactly* the right amount of
board-mastery to ship tonight without building the full board projection.

The one thing to add now, not later: a **self-naming authority field** in the document — e.g. `"master":
"timeline-v0"` — so that when v1 flips the timeline into a *true projection of the board*, the flip is a data
migration the editor can detect ("this doc predates board-mastery") rather than a silent re-point that breaks
every `.json` already on disk. Same reason your own earlier fence said "express the studio AS a projection":
the document should name what it is a projection of, so it never quietly pretends to be the real thing.

### (b) Is First Light the right editor home under decision 8?
**Yes — with a hard "separate state object" caveat.** I read `arsenal/web/first-light.html/.js`; it genuinely
already carries library roots (`libSearch`/`libList` DOM cache, `libraryClips` state, the `/api/resolve`
name+size path you cite), so "First Light already has library roots" is *true in the code*, not aspirational.
The risk is entanglement: `first-light.js` is a WebGL2 shader page whose model is *effect-over-a-single-video*
(`state.clip`, `state.epoch`, a rAF `drawFrame` loop, MIDI learn). An Edit mode adds a *timeline* — plural
clips, tracks, gain/mute, trim — a different state machine. If the edit controls are woven into `state` (the
existing object) rather than a sibling `editState`, the shader loop and the timeline scrubber will fight over
`state.epoch`/`state.lastMediaTime`, and you'll get the house bug your own lesson
`piano_topbar_control_dropped_by_workbench_move_list` describes: a control is added to HTML but not to the
page's DOM-cache/id-list path and silently vanishes (or, here, the editor hijacks the shader page's clock).

**Concretely:** editor JS in `arsenal/web/edit/*.js` (as you have it) must mount as a **separate module with a
separate state object**, registered in the page's DOM-cache path alongside (not inside) the existing `state`.
The `serve.py` one-dispatch-line for `editapi.py` and the `Range`/probe reuse are both correct; keep them. Just
don't let the Edit mode *be* `first-light.js`'s `state`.

### (c) Anything in the REUSE/EXTEND sheet I'd call a second idiom?
Two, both mild, both worth naming in the morning report rather than fixing tonight:

1. **`arsenal.tiktok.find_ffmpeg()` keeps its own finder with a *different pinned order* (env → PATH →
   bundled)** — divergent from `media.ff`'s env → config → PATH → bundled. This is reconciliation #3, and it is
   the *right* deferral (its tests pin the order; converging changes pinned behaviour; waits for Daniel). But
   it means the house now has **two ffmpeg finders with different orderings**, which is literally what
   `ff.py`'s own docstring says it exists to eliminate ("find and run ffmpeg once, for every agent"). It is not
   a defect tonight — it is a *named, dated follow-up* that must not become a silent re-discovery. Put it in
   the morning report as "converge tiktok on media.ff after Daniel okays the ordering change," with the one
   test that would have to change (`tiktok`'s order pin).

2. **`words` extends `arsenal.stt.transcribe()` with a `vad` parameter whose intended default change is gated
   on a not-yet-run WER test** — this is *correct* ("ask before deleting functionality," and you named the WER
   gate), but it is a second *idiom risk*: `stt.transcribe()` today defaults `vad=False`, `words.words()` will
   pass `vad=True`, and the two will disagree on the same audio until the WER test lands. That's a latent
   "same input, two different transcripts" seam. Fine as long as the morning report names it ("stt.vad default
   flips only after the clean-voice WER test, and until then `words` and raw `stt.transcribe` differ on game
   audio by design").

Everything else in the sheet reads as a *justified* departure, not a second idiom. The `contact sheets →
 NEW, absorbing six copies` row is the strongest REUSE write-up in the doc — "absorb the copies, then
 storyboard calls the new one" is exactly the "no second port/receipt idiom" discipline decision 1 demands.

---

## Two things I could not verify (so they fold into the morning report, not silently)

1. **The oracle files themselves** (Part 5) — `rec_17-51-11.clockmap.json`, `synthetic2_truth.json`,
   `ttk_video_summary.json`, the match/timeline JSON, the export-preset measurements. They live under
   `C:\Users\L5\AppData\...\Temp\claude\E--\2242a56c...` (or `state/`), some outside my scoped root, and I
   verified only their *names and claimed contents* as the spec states them, not their bytes. A test that
   "skips when they're missing" is only as strong as the skip being *correctly* keyed on absence — worth one
   look by the lane authors (a test that passes-by-skip is the hollow control again).
2. **The `test_arsenal_media_frames.py` pins** were not re-read line-by-line in this pass; I read
   `test_arsenal_media_ff.py` fully. `frames`'s keyframe-count = `probe.keyframes()` equivalence is claimed in
   the spec; I'd want that one pin confirmed live since it's the bridge between P2 and P3.

---

**Fence disposition: PASS with conditions.** Merge the spec-side search-order fix (B1) and the
`has_filter`/`has_encoder` watch-list fix (B2) before any lane references either surface; add the
`synthesized` flag to `at_times` (B3) before avsync/clockmap consume frames. The build order is sound, the
REUSE sheet is the right discipline, and the two editor questions resolve cleanly per (a)/(b). Nothing here
should stop the lanes — but B1, B2 and B3 must land in the fix passes, not the morning report.
