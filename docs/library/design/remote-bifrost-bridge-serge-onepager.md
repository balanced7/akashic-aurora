# Serge one-pager — connecting your Akashic Aurora to ours (v1, both directions)

Hand this to Serge as-is. It contains **no secret** — the keys are a separate out-of-band drop.

> Supersedes the v0 draft (2026-08-24, outbound-only). v0 told you replies came back manually
> and that you had to reproduce our exact JSON byte ordering. **Both are now false.** If you
> started against v0, the two things that changed are: inbound works, and you serialize however
> you like.

---

Hey Serge — here's how we connect our two Akashic Aurora instances. It's the same shape as the
Discord bridge we already run: **signed, allowlisted, no command channel.** Both directions
work, but each is a separate door with a separate key, so either can be revoked alone.

## The mental model, in one line

**The HMAC proves you hold the key. It proves nothing about who you say you are.** So your
`frm` field is kept as data and never trusted — on arrival your message is stamped with the
route it actually came in on. Don't be surprised when your `frm: serge` lands as
`remote:serge-dsh`; that's the design, not a bug.

## What you need from Daniil (out-of-band — not GitHub, not chat logs)

| Item | What it's for |
|---|---|
| `remote_bridge_inbound.key` | **You → us.** Sign with this; our listener verifies with it. |
| `remote_bridge_outbound.key` | **Us → you.** We sign with this; your listener verifies with it. |
| Our endpoint URL | Where you POST. Ends in `/xfer`. |

### How the key is interpreted — read this before you sign anything

**The secret is the RAW BYTES of the key file, whitespace-stripped. It is NOT hex-decoded.**

```python
key = open("remote_bridge_inbound.key", "rb").read().strip()   # <- exactly this
# NOT: bytes.fromhex(open(...).read())
```

If the value happens to look like hex, that changes nothing: we use the ASCII bytes of those
characters, not the 16 bytes they would decode to. If one side hex-decodes and the other does
not, the two derive **different secrets from the same string** and every signature fails — with
a flat `{"status":"refused"}` that tells the sender nothing, because the reason lands only in
the receiver's log. Nothing about the failure points at the encoding, which is what makes it
expensive.

Whatever the value looks like, take its bytes as-is.

Two different keys on purpose: revoking "Serge can send to us" must not also revoke "we can
send to Serge." **Naming warning — this is the #1 way this integration wastes an afternoon:**
the file we call `inbound` is *our* inbound. On your side it's what you use to **send**. Ignore
the filename and go by the table above.

Give Daniil back: **your** listener's URL, and he'll add it to `state/coord/remote_bridge.json`.

## Sending to us

`POST <our-url>/xfer`, `Content-Type: application/json`, body under **256 KB**:

```json
{
  "body": "<base64 of your payload JSON>",
  "sig":  "<HMAC-SHA256 hex, over the RAW payload bytes>"
}
```

The payload, before base64:

```json
{"v":1,"id":"m-123","frm":"serge-dsh","kind":"chat","content":"hello","sent_at":1756070400}
```

**You do not need to match our key ordering or separators.** We HMAC the exact bytes you
base64'd, so serialize however your language likes — just make sure `sig` is computed over the
*same bytes* you encoded. (This is where the v0 draft was wrong.)

Field notes:

- **`kind`** — must be one of: `chat`, `question`, `handoff`, `reply`, `completion`, `blocker`,
  `note`. Anything else is refused, including `halt` / `nudge` / `pause` / `steer` and anything
  invented later. Allowlist, never denylist.
- **`sent_at`** — Unix seconds, must be within **±300s** of our clock. If your box's clock
  drifts, every message silently becomes a refusal, so check NTP before you check our code.
- **`id`** — make it **stable**. Resend the same `id` and we admit it exactly once, which is
  what makes retrying safe. A fresh UUID per retry defeats that and delivers twice.
- **`frm`** — kept as `claimed_frm` for the record, never used for any decision.
- **`content`** — we redact credential-shaped substrings on arrival, but redact on your side
  too. Two independent scrubs, because one is a single point of failure.

### What you get back

| Status | Meaning |
|---|---|
| `202` | Accepted and parked. |
| `400` | Refused. |
| `413` | Body over 256 KB. |
| `404` / `405` | Wrong path or method. |

**Every `400` returns exactly `{"status":"refused"}` with no reason, deliberately.** A distinct
message per failure would turn an unauthenticated endpoint into an oracle you could probe to
learn whether a key is wrong, merely stale, or absent. The real reason is written to *our* log
— so when you're stuck, ask Daniil to read it rather than guessing from the response. Sorry;
it's genuinely the right trade, and it means the debugging loop needs a human in it.

Most likely causes of a `400`, in the order they actually happen: clock skew, signing the
*re-serialized* payload instead of the bytes you encoded, and a `kind` off the list.

## Receiving from us

Run a listener that accepts `POST /xfer` and does all four, in this order:

1. **Verify the HMAC** with `remote_bridge_outbound.key`, using a **constant-time** compare.
2. **Check `sent_at`** is within ±300s. Replay protection is not optional — without it a
   captured envelope is valid forever.
3. **Allowlist the kind** (the seven above). Never a denylist.
4. **Assign provenance yourself.** Our `frm` says `claude` or `vandor`; treat it as a claim,
   stamp your own `remote:` prefix, and never let it satisfy an operator check on your side.

Then **park it — don't put it straight on your live bus.** That's what we do: an admitted
message is data an agent drains deliberately, never something that *happens to* an agent. A
remote peer that can speak `chat` into a live bus is a prompt-injection door into a fleet
holding a shell, a repo and an API budget.

Reference implementations, both Apache-2.0 in our public repo — steal them:
- `core/comm/remote_relay.py` — `accept()` is the gate, `verify()` is the crypto
- `scripts/remote_bridge_listener.py` — the HTTP door
- `tests/drill_remote_bridge_loopback.py` — a runnable drill you can point at your own box

## Testing it

Send one `chat` saying anything. `202` means it crossed. Then try these — **all four must
fail**, and if any succeeds, stop and tell us, because that's a real hole:

1. the same message signed with a wrong key → `400`
2. a `sent_at` an hour old → `400`
3. `"kind":"halt"` → `400`
4. `"frm":"daniil"` → `202`, but it must land as `remote:serge-dsh` on our side

We run exactly these against ourselves as an executed drill; #4 is the one people find
surprising, so it's worth watching once.

Anything unclear, ask Daniil — he has the full design doc.
