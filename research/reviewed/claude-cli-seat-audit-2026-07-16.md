# CLI Probe Seat Audit — Boot Ergonomics (2026-07-16)

Status: blind half, CLI probe seat (claude CLI v2.1.211, headless print mode), 2026-07-16.
PROVENANCE: the probe could not write this file itself — the permission wall it discovered
blocked its own Write. Its stdout is preserved VERBATIM below by the desktop seat
(full-fidelity preservation doctrine). The wall it found is fixed in the same commit
(permissions.allow block in .claude/settings.json); a re-run audits the room behind the door.

---

I have enough for an honest audit. Let me state the result plainly.

## The audit ended at the front door — which is the finding

**A fresh Claude CLI seat cannot boot Akashic Aurora at all.** Not through the CLI, not through MCP. I never got to evaluate the quality of `boot`'s output, because I could not run `boot`. Every path the documentation points at is gated behind a human tapping "approve."

Here is what I observed first-hand, in this session:

- `py agent_cli.py boot claude --task "..."` — the exact command on line 18 of AGENTS.md, and the headline of the SessionStart banner — returned `This command requires approval`.
- `mcp__akashic-aurora__boot` — the second door, freshly registered user-scope in commit 6a8133a — returned the same.
- Reading `~/.claude.json` to check accumulated approvals: blocked. Even `ls ~/.claude/`: blocked.

The cause is verifiable and specific: `.claude/settings.json` has a rich `hooks` block and **no `permissions` block at all**. There is no `settings.local.json` in the project. `bootstrap.py` — the repo's own bootstrap script — never touches permissions; I grepped it. And the word "permissions" appears in eight markdown files, none of which are README, AGENTS.md, or bootstrap.md. The three docs a fresh seat actually reads never mention that the commands they prescribe won't run.

## The asymmetry underneath it

This session is its own proof. **The hooks all fired perfectly and unprompted.** I received the SessionStart context — directive, siblings, delta, mail count, funnel stats — without approving anything. The UserPromptSubmit hook fired and told me about 8 unread messages. Meanwhile every command I tried to type was refused.

So the system's involuntary nervous system is immaculate: five hook types, registered user-level with absolute paths, working from any cwd, as AGENTS.md proudly notes. The voluntary muscles are all gated. **Akashic Aurora observes a fresh seat flawlessly and lets it do nothing.** AGENTS.md closes with "Boot to load context, learn to give back" — a cold seat can do neither.

Veterans don't feel this. Their approvals accumulated in a local file that never ships with the repo, so the door only looks open from inside.

## What the door hands you instead

Since the banner arrived free, I audited it. It gives a fresh seat about ten lines: five are commands that can't run, and three truncate mid-word. Two details worth fixing regardless of permissions:

The THEMES line reads `THE HARD-TO-PIN THEMES of 2026-07-14/15 (prime any fresh seat with these): (1) THE GAUGE INVERSION -- visible budgets...` and stops. I am the fresh seat it addresses, and it truncates precisely where the priming would begin. It's also **double-truncated**: `chronicles/memory.md` already clips that note at "visible budgets/gauges are prosthetics that help...", and SessionStart clips the clipped version even shorter. Neither reaches content.

The WHERE line split a commit SHA across a line wrap — `T081 boot-ergonomics DONE @72...` then `a4925 (all 8 slices...` — so `72a4925` is unusable as written.

And `chronicles/memory.md` is 76 entries of the same shape: a compelling hook, an ellipsis, and a `source: mem:decision:ADR_...` pointer. Every dereference of those pointers requires `recall` — gated. The cold-boot surface is entirely pointers, and every pointer is behind the wall.

## Proposed fix — not applied

Per the assessment carve-out in AGENTS.md, I'm reporting and stopping rather than editing. The fix is a `permissions.allow` block in `.claude/settings.json` covering the read-only door — `boot`, `recall`, `recall-at`, `status`, `bifrost-sync`, `notes`, `promoted`, `delta`, `locks`, plus the matching `mcp__akashic-aurora__*` read tools. That's the safe core: it reads shared memory, mutates nothing.

The judgment call I'd want from Daniel is the write set — `learn`, `note`, `handoff`, `lock`. Allowlisting those lets a fresh seat close the give-back loop unattended, which is the whole point of the system, but it also means an unsupervised seat writes to shared memory on its first turn. My recommendation is to allow them: the ledger and dedup already absorb bad writes, and a seat that can read but not write is exactly the half-citizen this audit found.

One caveat on scope, stated plainly: I could not verify what `boot` actually returns, how good its ranking is, or whether the 9k budget holds — the permission wall stopped the audit before its real subject. Everything above is about the door, not the room. If you grant the allowlist, I'll re-run the cold boot and audit what's actually behind it.
