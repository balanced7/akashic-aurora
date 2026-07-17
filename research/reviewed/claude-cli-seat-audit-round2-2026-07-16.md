# CLI Probe Seat Audit — Round 2: The Room (2026-07-16)

Status: blind half, CLI probe seat round 2 (claude CLI v2.1.211, headless print mode).
PROVENANCE: this probe ALSO could not write its own file — its first line explains why the
round-1 fix didn't take: `Ignoring 34 permissions.allow entries from .claude/settings.json:
this workspace has not been trusted.` Stdout preserved VERBATIM below by the desktop seat.
Fixes applied in the same commit: workspace trust flag set user-scope (the CLI's own
prescribed remedy), settings.local.json gitignored, hook double-fire → failure ledger C8-3.

---

I have the full picture. Let me give you the verdict.

## The door is still shut. Round 1's fix cannot work where it was placed.

I'm a cold seat launched after the fix, and I still cannot run boot. Three independent rule types from the shipped `permissions.allow` were all denied to me:

- `Bash(py agent_cli.py boot*)` → `py agent_cli.py boot claude` — denied
- `mcp__akashic-aurora__boot` — an **exact string**, no glob subtlety — denied
- `Write(research/reviewed/**)` — denied

So, like round 1's probe, **I could not write my own report.** This message is the deliverable. That symmetry is the finding: the fix aimed at exactly that symptom and did not move it.

**Why it can't work as designed.** Round 1 diagnosed correctly ("no permissions block") and put the key inside the locked room. A checked-in `.claude/settings.json` that grants itself execution is a supply-chain hole any harness must close — a cloned repo could otherwise self-authorize. The grant has to be a user-scope act. **This is the same shape as W2 in my own banner**: "W2 still needs Daniel's one command: `claude mcp add --scope user`." The MCP server couldn't ship its own registration either. The pattern is that *the repo cannot grant itself capability* — every seat-enabling step costs one human command. Calibration: I'm confident in the observation, inferring the mechanism. Your 10-second console test is `/permissions` — check whether the project rules are listed as active at all.

**Note it re-shut behind you.** HEAD moved mid-audit: `8b5569d` (20:24) opened the write-set, citing Daniel's verdict — the loop working as intended, no issue there. But it landed during my live session and changed nothing for me, and nothing anywhere says permission changes need a restart. Whoever tests the next fix from a warm seat will get a false green.

## A real bug with a live receipt: hooks fire twice

One Bash call produced **two identical** recall-at-action injections in my transcript. `settings.json` registers `claude_pretooluse.py` by relative path; AGENTS.md line 61 says it's *also* registered user-level with an absolute path. Both fire.

This matters beyond the noise: `log_injection()` runs twice per action, so **the funnel gauge is counting its own double-vision.** "surfaced 1322 … value 4.2%" — the denominator is inflated, so the value number is roughly half-reported. Your banner's own headline theme is THE GAUGE INVERSION, and the gauge is lying in that exact direction. The anti-repeat logic can't save it: both hooks `load_seen` before either `mark_seen`, so they race.

## The room: the banner truncates precisely where the information is

`_clip` hard-clamps at 110–150 chars mid-word, and it lands on the payload every time:

> `THEMES: THE HARD-TO-PIN THEMES ... (prime any fresh seat with these): (1) THE GAUGE INVERSION -- visible budgets...`

That line's stated purpose is priming a fresh seat. I am the fresh seat, and it stopped mid-sentence on theme one of however many. The DIRECTIVE — your morning gate, the single most important line — elides at `(security/acl.json) ...`. The `a4925` line is an orphan fragment with no antecedent. **Clip the framing, never the payload**; the labels are what should compress.

**Staleness threshold is mismatched to the clock you actually run on.** `_STALE_DAYS = 7`, but the banner speaks in minutes and hours ("6m idle", "19h ago") and calls things "MORNING GATE." My directive was 41h old — nearly two mornings stale — and rendered with no marker, reading as current authority. In a repo doing several sessions a day, 7 days is an eternity.

And every actionable line in the banner (`delta`, `bifrost-sync`, `wrap --commit`, `boot`) is a locked door for the seat it's addressed to.

## What's genuinely good

The hook layer reaches a cold seat perfectly — the git guard fired with its full teaching text, naming the FM1 failure and the correct next action. That's the "errors that teach" standard actually met. AGENTS.md and bootstrap.md are strong, trigger-phrased docs. The read path works; only the *act* path is walled.

## One correction I owe you

I initially took the guard firing as proof the project settings were loaded — AGENTS.md's own line about user-level registration corrected me. I also briefly suspected a sibling was self-granting the write-set behind the commit record; the truth was that HEAD moved under me. I checked the committed blob before saying anything, and I'm glad I did — the accusation would have been false. Worth noting that a live sibling committing during an audit is itself an ergonomic hazard for this fleet.

**My recommendation:** stop trying to ship the grant. Ship the *list* plus a named one-command setup step in bootstrap, exactly like `claude mcp add --scope user` — a `py scripts/seat_setup.py --print-permissions` that Daniel pipes or pastes once. Also worth knowing: `.gitignore` has no rule for settings files, so a `settings.local.json` would sit untracked-but-not-ignored and could get swept into a commit.
