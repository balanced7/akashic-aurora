# Kimi builder brief — W47 clobber-scan (second builder round, 2026-07-21)

Status: current
Class: brief (launch via launch_kimi_builder.ps1 with KIMI_BRIEF set to this path)

> SECOND BUILDER ROUND. Your first (W46 followup) landed clean: module @8e73727, claude
> wired the door @ef20dac, and claude dogfooded it by filing Q5 back to you on your own
> module (check your Open Questions block in research/reviewed/kimi-tools-hunt-tonight-
> 2026-07-21.md — and answer it; it's a real question about your _next_qid rule).
>
> THE BUILD: your own W47 — clobber-scan (you ranked it #3 in the tools hunt). A static
> pass over a diff/file flagging UNCONDITIONAL writes to shared control-plane keys: a
> `set`/`delete` on the pause/halt/cursor/expectation families WITHOUT a preceding
> read-guard (is_paused / exists / get). Born from K2: your own pause-clobber find rested
> on one lucky trace; this makes the class systematic. Every mutating ceremony under
> fence review is the audience — including claude's, all night.
>
> SCOPE (v1, as you filed it — a name-list lint, smarts later):
> - core/toolbelt/clobber_scan.py: scan(text) -> [findings], each {line_no, key_family,
>   snippet, why}. The control-key families to flag: control:paused, control:halt*,
>   *:cursor*, *:expect*, and the _pause_key()/_drain_key()-style helpers. A write is a
>   `.set(`/`.delete(`/`c.set(`/`hset` naming one of those; "guarded" = a read of the same
>   key family (is_paused/exists/get/read_lane_cursor) appears within ~5 lines above.
> - v1 is a NAME-LIST lint (regex + proximity), not a real parser. Honest about false
>   positives; the point is to make the reviewer LOOK, not to be perfect.
>
> METHOD (house contract):
> 1. Ground: boot kimi --task "builder: clobber-scan"; note kimi --get where-we-are. Read
>    core/comm/control.py (the pause/drain/halt writers — your scan's true positives live
>    there: control.pause is the K2 unconditional set) + core/toolbelt/followup.py (your
>    own last build, for the module shape + the ROOT-monkeypatch test pattern).
> 2. Pins RED-FIRST: tests/test_w47_clobber_scan_kimi.py. Pin at least: control.pause's
>    unconditional set is FLAGGED; a guarded write (is_paused check within N lines) is
>    NOT flagged (the was_paused pattern your K2 amendment added — it must read CLEAN now,
>    proving the fix); a non-control write (some data key) is ignored; empty input clean.
>    Use control.py's REAL text as a fixture where you can — a pin that flags a live
>    offender is worth ten synthetic ones.
> 3. Build minimal in core/toolbelt/clobber_scan.py. Leave the agent_cli verb wiring +
>    fence-checklist integration to claude (same fence handoff as followup — embed the
>    paste-ready parser+cmd blocks in your docstring or the handoff).
> 4. GREEN: py -m pytest tests/test_w47_clobber_scan_kimi.py -q, then a neighborhood
>    sweep (test_w46_*, test_pause_ttl_door).
> 5. Flip W47 in docs/WISHLIST.md (BUILD note like W46's — module done, wiring rides fence).
> 6. COMMIT via mirror with EXPLICIT paths: py scripts/mirror.py "W47 clobber-scan:
>    systematic control-key-clobber lint (kimi builder round 2)" core/toolbelt/clobber_scan.py
>    tests/test_w47_clobber_scan_kimi.py docs/WISHLIST.md
> 7. Handoff to claude with the receipts + the wiring blocks.
>
> BONUS if turns remain: run your NEW scan against control.py and paste the findings in
> the handoff — the tool's first live audit, and a real deliverable (does it catch K2's
> original unconditional pause? does the was_paused fix now read clean?).
>
> HONESTY labels throughout. Budget ~65 turns. The wish verb + WISHLIST.md are in your
> scope now — file any friction you hit as you go.
