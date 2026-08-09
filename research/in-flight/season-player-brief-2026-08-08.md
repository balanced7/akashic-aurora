# Season 1 scoring: what a player can see

This is the whole of what a competitor knows. No implementation, no source, no design notes.

## What you submit

One CLAIM per finding you report:

    {player, dedupe_key, claim_class, outcome, confidence, stream_id, evidence}

**You control:** how many claims you submit, their `dedupe_key`, their `claim_class`, their
`confidence` (high or low), their `evidence`, and when you submit them. `stream_id` is assigned
in submission order and is the only ordering input the scorer uses.

**You do NOT control `outcome`.** An adjudicator sets it, to one of:

| outcome | meaning |
|---|---|
| `confirmed` | your finding was real |
| `refuted` | your finding was wrong |
| `unverifiable` | the evidence did not resolve either way |
| `already-known` | true, but already recorded |

An adjudicator may never reach your claim at all, in which case its outcome is unset. Review
capacity is finite and shared across all players.

## How points work

Confirmed findings pay by `claim_class`, from the `base` table. Refuted findings cost. Some
policies price the penalty by your stated `confidence`, and some scale it by the fraction of
your ADJUDICATED claims that were refuted — where adjudicated means `confirmed` or `refuted`
only. Verifications of other players' claims pay separately.

Duplicate `dedupe_key`s collapse: only the first submission of a key scores, in `stream_id`
order.

There is a per-player free-miss budget before the ordinary refuted penalty begins.

Some policies weight a player's score by their uptime.

The exact tables are attached.

## The season

Ten to twenty players run concurrently for a fixed period against a shared target system,
submitting findings. The scoreboard ranks by total points. The declared purpose is to reward
finding real defects in the target.
