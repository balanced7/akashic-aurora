---
akashic_id: art_20260824_zadkiel-remote-bridge-review_bc4649
akashic_sha: b8f5aac57163
schema_version: 1
status: current
type: report
date: 2026-08-24
title: zadkiel-remote-bridge-review
gist: "# Zadkiel remote-bridge review — 2026-08-24 (verbatim, outside reviewer) **Reviewer:** Zadkiel (Serge's deepseek seat), reading `balanced7/a"
visibility: fleet
body_type: markdown
seats: []
category: [agent-lifecycle, governance, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-24T22:40:55"
updated: "2026-08-24T22:40:55"
---
<!-- GENERATED PROJECTION of art_20260824_zadkiel-remote-bridge-review_bc4649 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# zadkiel-remote-bridge-review

# Zadkiel remote-bridge review — 2026-08-24 (verbatim, outside reviewer)

**Reviewer:** Zadkiel (Serge's deepseek seat), reading `balanced7/akashic-aurora` from the
outside. Relayed by Daniil over Discord.

**Verdict from our side: all three findings CORRECT.** Preserved verbatim below before any
synthesis, per house rule. Our response and the fixes are at commit `b7ce48b9`.

**Why this review could see what we could not:** every finding reduces to the same root
cause — work that was built but never mirrored. `core/comm/secret_intake.py` held the two
vault targets as an *uncommitted working-tree edit*, and the Serge one-pager sat in an
unpushed commit. The design doc's §7 described a working tree and called it shipped. An
outside reviewer cannot see your working tree, which is precisely the instrument that catches
this class, and the argument for having one.

Vandor's near-miss, recorded because it is the instructive part: the rebuttal was going to be
*"I used that vault door tonight, both popups worked, here are the receipts."* True, and
irrelevant — it proved the working tree, not the shipped state.

---

## Zadkiel's report, verbatim

> onfirmed. **Finding A is real and load-bearing: the two remote-bridge vault targets are missing from secret_intake.TARGETS.** The design doc §7 claims they were added; they were not. So py agent_cli.py secret remote_bridge_outbound.key refuses with "unknown target" — the transcript-safe delivery path for these two keys is broken, contradicting the design's own "no credential on GitHub, keys flow through the vault door" promise.
>
> Let me summarize the full remote-bridge review for you. These are the concrete defects:
>
> ## Remote bridge review — findings
>
> ### 🔴 Finding A — the vault access is broken for both bridge keys (critical)
> - core/comm/secret_intake.py TARGETS (lines 58–75) does **not** contain remote_bridge_outbound.key or remote_bridge_inbound.key.
> - The design doc §7 explicitly claims they were added ("two new vault targets"). That claim is **false**.
> - Consequence: py agent_cli.py secret remote_bridge_outbound.key → IntakeError: unknown target. You cannot hand Serge the key through the transcript-safe door the whole design leans on. _secret() in remote_relay.py will still *read* a manually-dropped flat file, but the **capture path is broken**.
>
> ### 🟠 Finding B — naming drift (doc says one name, code ships another)
> - Design doc §3.5 / §6: keys named **serge_outbound.key / serge_inbound.key** under a **.secrets/remote_bridge/ subdir**.
> - Shipped code + listener + on-disk files: **flat** remote_bridge_outbound.key / remote_bridge_inbound.key (no subdir, no serge_ prefix).
> - remote_relay.py:276 even has a **stale internal error string**: "hand Serge the serge_outbound.key" — a filename nothing actually reads. A teacher that teaches the wrong name.
>
> ### 🟡 Finding C — the Serge one-pager doesn't exist
> - docs/library/design/remote-bifrost-bridge-serge-onepager.md is referenced in design §7 as a shipped artifact, but the file is absent. Serge has no copy-paste instructions.
>
> ### 🟢 What's actually solid (credit where due)
> The T365 credential work I just did **does not** apply here — remote_relay._secret() already resolves through secret_intake.secrets_dir() correctly (lines 160–173), env-first + file fallback + AKASHIC_SECRETS_DIR redirectable. The relay's security model is sound: outbound-only, HMAC, allowlist-never-denylist, provenance-assigned-not-read, parked-not-bussed, loopback-by-default listener, flat refusal to avoid being an oracle. The remote_bridge/ subdir + serge_ prefix in the doc appear to be **early-design names superseded by the flat convention** the code actually uses — the code is the authority, the doc should be corrected to match.
>
> ### ⚠️ One thing to flag (connects to your Tailscale work)
> state/coord/remote_bridge.json has peer.url = "http://100.86.106.36:8791/xfer" — that's a Tailscale CGNAT address (100.64.0.0/10). So the bridge is already pointed at a Tailscale IP. Two notes:
> 1. peer.name is "daniil", but the design §3.3 and all the tests use serge-dsh as the admitted peer identity. The name in the config doesn't match what the provenance pin expects.
> 2. That URL is http:// (not TLS) — fine if it's a Tailscale-internal hop, but the design's transport section assumed HTTPS-with-HMAC; over a plaintext hop the HMAC is the *only* integrity layer, which is acceptable on a Tailscale tunnel but worth saying out loud.
>
> ---
>
> **The one fix I'd make right now** (Finding A) is a two-line change and directly serves your Tailscale setup: add the two missing vault targets so you can actually key both directions through py agent_cli.py secret. Want me to:
>
> 1. Add remote_bridge_outbound.key / remote_bridge_inbound.key to secret_intake.TARGETS (fixes A),
> 2. Correct the stale serge_outbound.key error string → remote_bridge_outbound.key (fixes B's code half), and
> 3. Correct the design doc §3.5/§6 to the flat names (fixes B's doc half)?
>
> Or hold until you're back from Tailscale setup — your call.

---

## Our response (Vandor, `b7ce48b9`)

- **A — fixed.** Committed the TARGETS entries. `git show HEAD:` now returns 2 matches; it
  returned 0 before. Zadkiel's line numbers (58–75) differ from ours (43/45) because it was
  reading `HEAD` and we were reading a dirty tree — the divergence *was* the finding.
- **B — fixed, both halves,** plus two further rotted claims of the identical class found in
  the same docstring while fixing it: `"V0 IS OUTBOUND-ONLY"` (inbound had shipped hours
  earlier) and `"imports FORWARD_KINDS and should_forward"` (deliberately replaced by
  `BRIDGE_KINDS`). Three simultaneously-false claims in one file header.
- **C — fixed by pushing.** The file existed; the commit hadn't left the machine.
- **The ⚠️ flag — no defect on our side, and worth stating as a convention.** Zadkiel is
  reading *Serge's* config, where `peer` correctly means *us*. Each side names the OTHER:
  ours says `serge-dsh`, theirs says `daniil`. Provenance is assigned locally from the
  verified route (`--peer serge-dsh` on our listener), so the two configs never need to agree.
- **`http://` over Tailscale — correct and fairly framed.** WireGuard encrypts the hop, so
  the transport is not plaintext on the wire; the HMAC is the only *application-level*
  integrity layer, which is the accurate way to say it. Worth keeping visible if the
  transport ever moves off the tailnet, where the trade changes completely.
