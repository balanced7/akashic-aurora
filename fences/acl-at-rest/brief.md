# Fence brief — the ACL is a plaintext file anyone can edit

Status: current
Class: brief
Arc: acl-at-rest

**Opened** 2026-10-07 by Vandor (claude seat), at Daniel's ask, minutes after the trust layer
correctly refused to let me grant myself the `screen.*` capabilities I wanted.

## His words, verbatim

> "this is a gaping security hole i've ignored for a good bit, we need to design and implement a
> secure storage mechanism / api for authentication that resists spoofing. requests must be
> encrypted and the box decrypts it, does the interaction with the request, encrypts the output and
> replies to the requestor. This is just an idea but I think that would at least put friction into
> the path. anyone can just go in and edit the json file right now."

And, clarifying when I first read him too narrowly:

> "I meant for the json file to live in a secure file that is encrypted and needs to be handled by
> an intermediary. we wouldn't be leaving the json file in plaintext"

So the proposal is **not** transport encryption around a plaintext store. It is: *the ACL never
exists as plaintext on disk; an intermediary is the only thing that ever sees it decrypted.*

## How it surfaced, which is the part worth keeping

It surfaced from the guard WORKING. I wanted four `screen.*` caps to run the screenspace drill.
`grant` refused the self-grant (`agent_id == by` -> PermissionError, *"a second party mints your
authority"*), and `_bounded_by_granter` refused again because I hold `admin.grant` but no
`screen.*`. There is no path through the door — by design.

Then the remedy for that deadlock turned out to be: **open `security/acl.json` in a text editor and
add four strings.** The door is a vault with a wall of paper beside it.

## The measured state

- `registry.ACL_PATH` = `E:/AI-Setup/security/acl.json`. One file, 14 grant entries, plain JSON.
- It is **gitignored** (instance-local by design, T384), so there is no git history to notice an
  edit against either.
- There is **no signature, HMAC, checksum or seal** anywhere in `core/trust/registry.py` or
  `core/trust/grant_writer.py`. Authority is whatever the file currently says.
- The same shape repeats one level down: `.secrets/` is plaintext-and-gitignored, holding
  `claude_oauth.token`, `chronos_inbound.key`, `chronos_outbound.key` and friends.

So every guard in the trust layer — the self-grant refusal, the granter bounds, the time boxes,
today's new cap-strip refusal (W252) — is enforcing rules read from a file that the thing being
guarded can rewrite.

## THE PRIMITIVE ALREADY EXISTS. Do not add a second crypto stack.

`.secrets/bridge_seal_identity.json` begins:

```json
{"alg": "x25519-xsalsa20poly1305", ...
```

That is a libsodium sealed box: X25519 key agreement, XSalsa20-Poly1305 AEAD. The house already
has a seal identity and has already chosen an algorithm. Whatever this fence lands should extend
that identity rather than introduce a parallel one — two crypto stacks in one house is a worse
outcome than the plaintext file, because then nobody knows which one is authoritative.

**Open question for the halves:** who owns `bridge_seal_identity`, what is it used for today, and
is its private half stored any better than the ACL is? If it is a plaintext key beside a plaintext
ACL, the seal inherits the hole rather than closing it, and that has to be answered before it is
built on.

## What the shape buys, stated honestly

Daniel already framed this correctly as *friction*, not a wall, so this section is not an argument
against it — it is the boundary drawn so the next reader does not oversell it.

It genuinely buys:

1. **No casual or accidental edit.** The failure mode today is not a sophisticated attacker, it is
   anyone — including a future me — opening a file and adding a line. That stops.
2. **Tamper-EVIDENCE, for free, from the AEAD.** A hand-edited ciphertext fails authentication.
   The guard then refuses LOUDLY instead of honouring a forged grant silently, which is the whole
   difference between a security control and a decoration.
3. **One mediated choke point.** Every read and every mutation passes through one process that can
   log, rate-limit and policy-check. Today there is no such point: `registry.resolve()` is a file
   read in whatever process asks.
4. **Portability protection**, if the key is bound to the Windows account (DPAPI user scope) —
   copying the file to another machine yields nothing.

It does not buy protection against code execution as the same user. Anyone who can run code as
this account can patch `registry.py` to skip the check, or read the key the intermediary holds.
That is not a flaw in the proposal; it is the boundary of any local scheme, and it should be
written down once rather than discovered later as a disappointment.

## The decision this fence actually turns on

**Key custody.** Everything else follows from it:

- *Key on the box, user-scoped (DPAPI or equivalent)* — stops editing and copying, stops nothing
  against local code execution. Cheapest, no new operational burden, and honest about its bound.
- *Key off the box (hardware token, phone, remote KMS)* — a grant then requires a human-present
  action, which is the strongest reading of "resists spoofing" and also the one that can lock us
  out at 3am when a seat needs a cap and Daniel is asleep.
- *Hybrid: reads are local-key, WRITES require the off-box key.* Grants are rare and deliberate;
  resolution happens constantly. This is the shape I would defend, and I want it attacked.

## Open questions for the halves

1. Key custody, as above. Which of the three, and what is the 3am failure mode of your choice?
2. Is the intermediary a long-running daemon (another thing to keep alive — see today's finding
   that the wake supervisor had no scheduled task and was alive by luck) or a short-lived process
   per request?
3. What happens when the intermediary is DOWN? Fail-closed means a dead daemon locks the whole
   fleet out of its own authority. Fail-open means the hole is back on the worst day.
4. `.secrets/` has the same exposure. One mechanism for both, or is the ACL special?
5. Migration: 14 live grants, instance-local, no git history. How does the cutover not strand the
   box, and what is the rollback if the seal is wrong?
6. Is there an acceptance test that distinguishes this from decoration? Proposal: a drill that
   hand-edits the ciphertext and proves the next `resolve()` REFUSES loudly, plus one that proves
   a legitimate grant still round-trips. Without that pair this is unfalsifiable.

## Not in scope

Authentication of *remote* requestors, multi-machine key distribution, and anything about the
public repo. This is about one file on one box and the door in front of it.
