# Rill: W5, the unread line that has to change or go quiet

Daniel, 2026-10-09, verbatim: "can you work with Heimdall, Navi and Rill to keep building out the one world ui?"
Spec: research/in-flight/one-world-ui-core-reconciled-spec-2026-10-08.md (atom d622ac), section 5 and slice W5.

**Your diagnosis, which the spec carries:** the never-changing "58 unread bus msg(s)" is a cursor divergence (W173).
It is also the first real instance of "a repeated whisper must change or go quiet". It printed 58 again on every
turn today, after a reboot.

**The ask: W5's data half.** A pure `unread_view(agent)` in core/oneworld/unread.py that reads the TRUE cursor and
returns:
```
{"ok": bool, "as_of": iso, "total_unread": int,
 "directed": [{"kind", "from", "age_s", "id"}],        # handoffs/requests/questions addressed to `agent`
 "oldest_directed_age_s": float|None,
 "bounds": "<what it could not see>"}                  # e.g. "3 of 58 are handoffs to you, oldest 2 days"
```
What done looks like: the count changes when mail is consumed, or the line goes quiet. It never repaints the same
stale number.

**Real constraints.**
- Pure, with an injectable source, so the tests run without a live Redis. The adapters in
  core/oneworld/surface.py are the pattern.
- Fail soft to ok=false, "cannot read the cursor". Never a stale or guessed count; zero is not no.
- Tests alongside. Commit nothing; I commit.
- If the W173 fix itself (the cursor) is a separate change, name it rather than folding it in. I will route it.

**One question:** is the W173 fix on the reader side (it reads the wrong lane or cursor) or on the writer side
(the cursor never advances)?
