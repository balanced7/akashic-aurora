# Handoff — next Vandor, 2026-10-07

Written 2026-10-07 by Vandor#428ba6c4, at Daniel's ask, as he launches the next seat. This
supersedes `handoff-vandor-2026-10-06-screenspace.md`, which is a day stale and predates everything
below.

**One sentence:** 20 commits landed and pushed, the publish door was unblocked after seven days,
the wishlist went 234 -> 182 open, and the single most important thing I found is that **the
Discord ear does not run from this repo**.

---

## READ THIS FIRST — the thing you must not re-derive

**Production Discord runs from `C:\Users\L5\AppData\Local\AkashicAurora\worktrees\
sunshine-discord-split`, branch `codex/sunshine-discord-split`, which is 547 commits BEHIND master
and 1043 ahead.** It is a git worktree of this same repo.

Everything landing on master — today's T418 door-probe fix, the eye's journal plane, 4 seconds off
every turn, the cap-strip guard — **is not in the thing that talks to Daniel.** Master grew
`core/comm/wake_seat.reachable()` (at :1019) for a complaint he filed weeks ago; that branch has no
such function and still conflates presence with reachability.

Daniel cancelled his GPT subscription today, so the codex seat that owned that branch is gone and
he said, verbatim: *"This is your lane now."* Merging production onto master is the open slice. It
is a real migration with a rollback question, not a patch — fence it.

Three scheduled tasks are now orphaned by the cancellation and still Running, doing nothing:
`AkashicAurora-GptNewDiscord`, `SunshineDiscord`, `SunshineFleet`. He has not said to retire them.

---

## What is UNBLOCKED, and what is still blocked

**Unblocked today:** the publish door. `mirror.py --push` had been refusing since 2026-09-30 —
the day *before* T418's identity-grounded boot landed. Three health checks boot as synthetic
residents (`door-probe`, `mcp-boot-regression-<hash>`, `agent_x`), T418 correctly refuses to hand
any session another resident's packet, and both the door probe AND a red door pin block the push.
177 commits were dammed. Fixed with T418's own documented hatch
(`AKASHIC_BOOT_AS_OTHER=1`) in children that are already isolated. Recalibrated the probe's latency
budget 5.0 -> 8.0s from measured bounds on both sides (healthy 4.88-5.94s, mutation-tested degraded
11.38s) and P6's timeout 5 -> 30s, because P6 asserts FRAMING and latency belongs to the probe.

**Still blocked: the screenspace drill**, and this is the live thread he was on when the seat
handed over.

- `screen status` now reports `locked=False` (he is home) and `uia=True`. The window is reachable.
- `verbs permitted: NONE`. The four `screen.*` caps cannot be granted by anyone: no role template
  contains them, nobody in the ACL holds them, `_bounded_by_granter` refuses a cap the granter
  lacks, and self-grant raises PermissionError. **It is a closed loop.**
- The command `screen status` prints as the remedy would fail twice over — `--by daniil` lacks
  `admin.grant`, and it is written in the dangerous `--caps` REPLACE form that W252 fixed today.
  **That text needs updating to the `--add-caps` form. I did not get to it.**
- The unblock is a hand edit to `E:\AI-Setup\security\acl.json`, the `claude` entry, appending
  `"screen.observe", "screen.focus", "screen.type", "screen.act"` to its 14-cap list. Deliberately
  NOT `screen.launch` or `screen.privileged` — no verb maps to them.
- `py agent_cli.py screen prompt --text-file <this file> --show` works today: 10,120 chars, receipt
  nonce printed, nothing sent. Use `--show`, then stage, then `--submit`. Only the last one sends,
  and it is verified by a causal receipt — a new transcript containing the nonce. If no transcript
  carries it, the status is `unverified`, never `ok`. **Re-running sends twice.**

**And `!spawn` has been dead for 21 days** — expired credential, surfaced by the gateway restart:
*"!spawn cannot build a seat until `claude auth login` runs."* The false cold-seat notice had been
offering him that lever the whole time.

---

## The security hole he named, and the fence I opened for it

`fences/acl-at-rest/brief.md`, opened today. His words: *"anyone can just go in and edit the json
file right now."*

Every guard in the trust layer reads its rules from a plaintext, gitignored file that the thing
being guarded can rewrite. His proposal: the ACL lives encrypted at rest and an intermediary is the
only thing that ever sees it decrypted.

**The primitive already exists — do not add a second crypto stack.**
`.secrets/bridge_seal_identity.json` declares `{"alg": "x25519-xsalsa20poly1305"}`, a libsodium
sealed box. Extend that identity. The brief's first open question is who owns it and whether its
private half is stored any better than the ACL is — if it is a plaintext key beside a plaintext
ACL, the seal inherits the hole instead of closing it.

The decision the fence turns on is **key custody**, and the brief lays out three options with their
3am failure modes. It has NOT been fenced yet: no halves, no reconciliation. That is the next move
on it.

---

## The pattern that ran through the entire day

Seven defects, one family: **instruments that report green by comparing a thing to itself, or by
counting only what they managed to keep.**

- `find --sort` re-sorted in Python after asking es.exe for an order — every sort key inert.
- `--verify` compared two RECORDED shas and hashed nothing (now rehashes 1,020 bodies).
- A corpus report counted survivors and called it coverage — 1,997 found, 1,604 taken, and the
  difference was invisible.
- A private-plane leak guard reported clean because its import failed and `except` returned the
  entries unfiltered.
- The TOKENS TODAY gauge read two keys nothing writes: 5,031,502 tokens rendered as `0`.
- `_unread_count` spent 4.1s of every single turn scanning a 66,700-key keyspace to discover there
  are ZERO locks.
- The cold-seat notice fired *because* the message arrived — the send wakes the seat, waking
  consumes the listener, and the probe ran after the send.

**And I wrote four vacuous pins of my own by the same move** — matching a token the broken code
already contained, including twice inside a file about that exact mistake. Three pins SKIPPED while
reading as `sFss`, which I nearly reported as passing ratchets. If you take one thing from this
handoff: **assert structure, not vocabulary, and check that a pin RAN.**

---

## Peers

**Navi (kimi)** took W231 + W229, verified both against live code rather than trusting my receipts,
and **corrected my fix shape on W229**: the render a human actually reads is
`render_collapsed._line` (:607), and `format_digest_line` (:676) prints HH:MM with no date, so an
eight-day-old message reads as today's 04:32. Three call sites, not two. She also answered a
calibrated question better than either option I offered — W235 is *"one concept, two policies, one
word"*: the ranker excludes `engaged` (a curiosity pull is not evidence of help) and the curator
includes it (a full-record pull is evidence it is not dead weight), and **both are right**. Name
them `RANKING_CREDIT` and `RETENTION_CREDIT` and print the exemption counts: measure the
disagreement, do not resolve it. She soft-declined W233/W234 as outside her genus; that stands.

**Rill (dsh_agent)** was briefed with W238 / W173 / W206 and **has not answered**. The brief is on
the bus. Two of his DSH sessions also parse to ZERO events in the eye.

**Heimdall (deepseek)** relayed Daniel's invariant question and was reading `docs/THE-FILING-
SCHEMA.md` lines 110-118 as live — A1 and A2 were WITHDRAWN by
`fences/filing-schema/reconciliation.md` §8 on 2026-10-06. I stamped the doc today. He could not
have known: until this morning `fences/` was in no searchable corpus.

---

## Open, and not mine to close

- **Daniel's calls:** merge production onto master; retire the three orphaned codex tasks; lift the
  lounge carve-out or leave it; Redis `appendonly=no` with ~5,400 unsaved changes (a power pull
  loses up to an hour of bus traffic, and he has had power pulls).
- **The wishlist id collision** — W00, W57-W69, W211 each name two wishes. It blocked 12 of today's
  49 closures. ~250 live citations, and the LATER duplicate is the one most likely cited, so
  renumbering breaks exactly the references most likely to mean it. His call.
- **A weekly wishlist triage task**, proposed and not built: re-check open wishes against live code,
  close the already-built, post him a ranked shortlist. He said he needs "a more regular cadence";
  I argued the cadence should arrive rather than be remembered. Awaiting his go.
- **A stop-hook gate for Discord replies.** I answered him in the terminal pane once today when he
  had asked on Discord. The `.woke` marker already records what woke the turn, so the hook could
  refuse to let a Discord-woken turn end with no Discord send. Load-bearing — pin it carefully.
- `tests/test_world_snapshot_surfaces.py::test_stdio_mcp_advertises_and_calls_glance_end_to_end`
  **hangs** and ate both full-suite attempts today. There is still no clean full-suite run and I
  did not claim one.

---

## House rules that cost me time today, so they do not cost you any

- **Commit by name, never a sweep.** The working tree holds other seats' lanes and a sensitive set
  held back on purpose (the seed-sanitize before/after sample, two employer-plane halves, an 11.8MB
  binary). Each is named with its reason in the commits from `907338e6` onward.
- **The pre-commit hook measures guardrails BEFORE its own regeneration step**, and the printed
  order is reversed from the execution order. Stage your new `.py` files FIRST, then regenerate
  `docs/PRIOR_ART.md`, then commit — otherwise the test-module count moves under you and the
  ratchet blocks.
- **Committing in the worktree needs the seat identity:**
  `GIT_AUTHOR_NAME=claude GIT_AUTHOR_EMAIL=claude@akashic-aurora.local git commit ...`
- **The shell resets cwd to `E:\`** when it rebuilds. Anchor every command with `cd /e/AI-Setup &&`.
- **Heredocs eat `\n`.** Three times today a `\\n` in a bash heredoc became a real newline and broke
  a string literal. Use the Edit tool for anything containing escapes.
- **Re-arm the wake listener via `Bash run_in_background`, never inline `&`** — a detached listener
  notifies nobody. The stop hook enforces it, but it is faster not to be told.
