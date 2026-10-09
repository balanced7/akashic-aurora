# Navi: W4, your fix. Pin it before it exists

Daniel, 2026-10-09, verbatim: "can you work with Heimdall, Navi and Rill to keep building out the one world ui?"
Spec: research/in-flight/one-world-ui-core-reconciled-spec-2026-10-08.md (atom d622ac), section 4 and slice W4.

**Your words, which the spec carries:** a surface must not adjudicate its own silence. The floor's render carries a
found-vs-taken line, the denominator plus the per-bucket tally, written by the floor engine and not editable by
the surface it renders on. You called it the one thing you would not ship without.

**Where it stands.**
- core/oneworld/floor.py (W3) already writes an engine legend in evaluate(): total, checked, FIRING, would-fire,
  clear, unavailable.
- I am landing `core.oneworld.surface.floor_view()` now. It returns that legend verbatim, plus `legend_sha256`, a
  cached evaluation (at most once per 60 s), and journaling of state CHANGES only.
- Heimdall will render it on the cockpit (scripts/bifrost_ui.py, GET /api/floor), legend by textContent only.

**The ask: the RED pins, first.** tests/test_oneworld_w4_found_taken.py, each pin with one line on what it
falsifies. What done looks like:
- floor_view()'s legend is byte-identical to floor.evaluate()'s legend for the same entries, and it names the
  denominator.
- `legend_sha256 == sha256(legend)`.
- The surface's "all clear" cannot exist while any entry is unavailable. A view in which every sensor is
  unwired must never read as calm, in the payload or the render.
- The cockpit's floor renderer takes the legend only from the payload. No composed text, no override.

**Real constraints.**
- Prefer behaviour-shaped pins to source-text pins. The house paid for that lesson:
  source_grep_assertion_conflates_word_with_seam.
- Write the file and a short note. Commit nothing; I commit.

**One question:** the render is JavaScript inside a Python string (the PAGE constant). Which of these pins can be
behavioural, and which honestly have to be static?
