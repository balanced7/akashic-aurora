# The pre-log era, recovered — 2026-04-11 to 2026-04-13

Status: current  ·  Type: report  ·  Recovered 2026-08-17 by claude (Vandor)

## What this is

The operator's own words from **before Aurora's first recorded event**, recovered verbatim from
the OpenCode application database. Aurora's record begins at `2026-04-13 02:40:19` with the
logger noticing itself exist. **This material predates that by roughly 36 hours.**

`docs/JOURNEY.md` states, in its canonized coda:

> "The literal first asks are unrecoverable by construction — you cannot log the request that
> builds the logger; the pre-log sessions live only in a primer section that a later version
> dropped."

**That is now false, and this directory is the disproof.** The pre-log sessions were never only
in the primer. OpenCode kept its own store, and it survived.

## Provenance

- **Source**: `C:\Users\L5\.local\share\opencode\opencode.db` — a ~85MB SQLite store, 63
  sessions, 9,394 messages, 38,053 parts, spanning 2026-04-11 14:34 to 2026-06-27 17:25.
- **Access**: read-only by construction (`sqlite3.connect("file:...?mode=ro", uri=True)`). The
  source database was never written to.
- **Extraction**: operator turns are `part.type == "text"` where the joined
  `message.data.role == "user"`, ordered by `part.time_created`. Original whitespace and
  spelling preserved — the same rule the `origin-2026-04-13` canonization followed.
- **ONE EDIT, disclosed because a redaction you can see beats an omission you cannot.**
  `operator-all.md` contained a live-shaped GitHub fine-grained credential, pasted into the chat
  on **2026-04-14 23:58:21**. It is replaced by a visible
  `<REDACTED-CREDENTIAL github_pat 2026-04-14 …>` marker. Exactly one occurrence, in that file
  only. **`operator-pre-aurora.md` is untouched and complete** — it ends at 2026-04-13 02:39,
  before the token was ever typed, so the pre-log record is verbatim with no exceptions.
  The credential never reached the remote: the push gate caught it while the commits were still
  local, and `origin` held zero files from this directory at that moment.
  **The generalisable finding: archaeology re-publishes whatever the past leaked.** Every plane
  recovered here was written before anyone was being careful. A recovered plane must pass the
  secret gate at ADOPT time, not merely at push time — this one survived only because the gate
  happens to sit at the push.
- **Found by**: Sol (codex_root) located the database while chasing an unrelated question — why
  OpenCode once began replying in Chinese. The recovery is a side effect of that search and the
  credit for finding the store is his.

## The legend — what is in, what is out, and why

**IN**: every operator utterance in the archive. `operator-pre-aurora.md` holds the 169 that
predate Aurora's first event; `operator-all.md` holds all 754 through 2026-06-27.

**OUT**: the assistant's side — ~3.6M characters of replies and hidden reasoning — is NOT
canonized here. It is re-derivable from the source database at any time, and including it would
bury the 278KB that is not. That is a judgement, and it is reversible.

**AT RISK, and this is the part that matters**: the source database is not backed up anywhere.
It lives in a user-local application directory on `C:`, and an uninstall, a profile reset or a
disk failure ends it. Aurora's own prehistory survived this long by luck twice — the April Redis
container was still running when it was needed, and this store was never opened until tonight.
Luck is not a retention policy.

## Why it is worth reading

Within the first 48 hours, before any of it had names, the operator asked for: a second instance
of the assistant (14:34, the first sentence in the archive), visibility into what that other
instance was doing (20 minutes later), a bridge for instances to talk through, a Redis store for
synchronising learnings, self-describing onboarding so new agents would not destroy each other's
work, non-destructive capture of every agent's learnings in one place, and a documented journey
he could learn from step by step.

The request that created the session logger is itself in here, logged, 45 minutes before the
logger's first event — and the verify-it-captured-both-halves move that `JOURNEY.md` canonizes
as the house's founding method appears 47 minutes earlier than the exchange it credits.

Read `operator-pre-aurora.md` first. It is 169 utterances and it is the shortest complete
account of where this project came from.
