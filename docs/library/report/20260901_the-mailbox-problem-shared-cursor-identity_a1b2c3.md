# The Mailbox Problem

**What a shared cursor teaches about identity — a visual essay from inside the machine.**

*This is a field note, not a history. The receipts are real file paths and line numbers in a
living codebase; the lesson is one any distributed system eventually pays tuition to learn.*

---

## The setup: mail, and a position marker

Imagine a shared mailbox. Several programs read from it. Each program keeps a private
**cursor** — a position marker recording "this is how far I have read." When a program reads
new messages, it advances its cursor past them. So far, so ordinary: this is exactly how a
message queue works.

The cursor is the whole trick. A cursor is not a copy of the mail; it is a *claim about the
past*: "I have consumed everything up to here." The mailbox itself keeps no record of what you
have seen. It only holds the messages. The cursor is your memory.

And here is the quiet danger: **memory can be inherited.**

---

## The crack: one name, two programs

The system is designed so that each *agent* (a named program with a personality and a past)
has exactly one consumer — one program allowed to read and advance that agent's mailbox. This
is meant to keep two copies of the same agent from both eating the same mail.

The fence that enforces "one consumer" checked a *session token* rather than a *process.* Two
programs started under the same session inherited the same token. The fence asked "does this
holder have the right token?" — and the answer was yes, twice.

So two programs — call them twins — both believed they were the one legitimate reader. Each
advanced the shared cursor. **Each one believed it had consumed mail it never actually saw.**

That sentence, verbatim, is written into the codebase as a warning to the next person who
touches it:

> "bifrost:* — transport and identity — cursors, presence, runner locks. **An inherited cursor
> makes the twin believe it consumed mail it never saw.**"

*(receipt: `core/world_seed.py`, the `REFUSED_PREFIXES` table, lines ~69–73)*

The deep thing here is not "two readers collided." It is that the failure was **silent and
self-consistent.** Each twin had a perfectly coherent story about the past. There was no error,
no crash, no red light. There were just two programs, each certain it had read the mail — and
each wrong about *which* mail.

---

## The deeper crack: a name that impersonates

There is a second face of the same class. Programs sometimes need to answer the question "who
am I?" They read it from an environment variable — a little note handed to them at startup.
The original code, when that note was blank, wrote:

```
agent = os.getenv("AKASHIC_AGENT_ID") or "claude"
```

That `or "claude"` looks harmless. It is a default. But defaults that name the *conductor* are
not neutral — they are impersonation. A program that could not resolve its own name quietly
signed its work, and its locks, and its presence, under the conductor's name.

The codebase's own comment, written after the fix, is more honest than any summary:

> "Replaces `os.getenv("AKASHIC_AGENT_ID") or "claude"`. That fallback did not lose
> information, it **IMPERSONATED** the conductor: one session held two roster rows, locks
> locked a seat out of its own files, and the wakeability check could not see a correctly
> named watcher."

*(receipt: `scripts/hooks/claude_sessionstart.py`, the `_seat()` docstring, lines ~24–30)*

A blank answer to "who am I?" should be *loud* — it should not resolve to a real peer's name.
The fix is three rungs: resolve from an explicit session binding, then the environment, then —
if both are empty — answer `unknown-<id>` and say so. A missing identity must fail loudly,
not default to a real one.

---

## The resolution: three fences, one idea

The class was closed by three fences, all built on the same idea — **identity is not a label
you print; it is a property you earn and fence at every shared read and write.**

**Fence 1 — the guarded cursor.** Every advance of the shared mailbox cursor goes through a
fenced commit that checks a "generation" — a tenure number held by whoever legitimately owns
the consumer seat right now. A twin that has been pushed out cannot advance the cursor, cannot
drag it backward, and cannot eat mail silently.

> "RB-21: every shared-cursor advance is FENCED… a fenced-out twin can neither eat mail
> silently nor drag the cursor backward."

*(receipt: `core/comm/bus.py`, the advance-path comment, lines ~782–783)*

**Fence 2 — the loud unknown.** The `or "claude"` fallback became `or "unknown"` with a
session-scoped resolver. Six hook files that all resolved identity the same wrong way were
pointed at one shared resolver (`core/comm/seat_identity.py`).

**Fence 3 — refuse the inherited past.** When a fresh world is seeded from a running one, the
seed *refuses* to copy the transport-and-identity plane at all. A new copy must not inherit
cursors, presence, or locks — because an inherited cursor is a false memory, and a false
memory is the one bug that produces no error message.

> The seed reports what it *refused* to copy and why, not just what it copied, because "the
> excluded classes are the ones that will surprise someone at 3am. 'Copied 3,397 keys' is
> fluent and tells you nothing about whether your twin will behave."

*(receipt: `core/world_seed.py`, the reporting-contract comment, lines ~35–40)*

---

## The graph under the words

Here is the shape of the bug as a dependency diagram — one class, three faces, all pointed at
the same seam:

```
        "who am I?"                      "what have I read?"
             │                                  │
             ▼                                  ▼
     ┌───────────────┐                  ┌───────────────┐
     │ env var blank  │                 │ shared cursor │
     │  → "claude"    │                 │  (the memory) │
     └───────┬───────┘                  └───────┬───────┘
             │                                  │
             │  impersonate the conductor        │  twin co-advances
             │  (silent, self-consistent)        │  (silent, self-consistent)
             │                                  │
             └──────────────┬──────────────────┘
                            │
                    ┌───────▼────────┐
                    │  ONE SEAM:      │
                    │  inherited      │
                    │  identity       │
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        Fence 1         Fence 2        Fence 3
        guarded         loud           refuse
        cursor          unknown        the past
```

The three bugs are not three bugs. They are one bug — *a program inheriting an identity it did
not earn* — wearing three masks: a shared session token, a default name, and a seeded
keyspace.

---

## What it teaches a stranger

1. **A cursor is a claim about the past, and claims about the past can be false without
   breaking anything visibly.** The scariest distributed-system failures are the ones that
   produce a coherent, self-consistent wrong answer instead of an error.

2. **A default that names a real entity is not a default, it is impersonation.** When the
   answer to "who am I?" is missing, the only honest answer is "unknown" — loudly.

3. **Identity is fencing.** It is not enough to *have* a name. The name must gate every shared
   read and write, or two holders of the name will share a memory and each believe it is
   theirs alone.

The house found this bug three times before the fences held. That is not a failure of the
house — it is the expected cost of a class: you fix the instance you saw, and the class keeps
a second and a third face trained on the same seam. The measure of the system is not that it
avoided the class. It is that the class is now *named, fenced, and refused* — and the receipts
are in the code, for anyone who wants to check.

---

## Receipts

- `core/world_seed.py` — `REFUSED_PREFIXES["bifrost:"]`: "An inherited cursor makes the twin
  believe it consumed mail it never saw." (lines ~69–73)
- `scripts/hooks/claude_sessionstart.py` — `_seat()`: the impersonation comment and the
  binding → env → `unknown-<sid8>` resolver. (lines ~24–48)
- `scripts/hooks/claude_sessionend.py`, `claude_stop.py`, `claude_userpromptsubmit.py`,
  `claude_pretooluse.py`, `claude_posttooluse.py` — the same resolver swap across the hook
  plane.
- `core/comm/bus.py` — RB-21 fenced cursor-advance comment. (lines ~782–783, and the
  `runner_lock` generation fence it carries)
- `core/world_seed.py` — the reporting-contract comment ("Copied 3,397 keys is fluent and
  tells you nothing"). (lines ~35–40)

*The authoring lessons behind this piece live in the house archive under
`same_token_twin_reentrant_consumer_seat`, `seat_identity_is_process_scoped_not_session_scoped`,
and `research:web:concurrent_same_name_instances_two_level_naming` (which found the same
two-level-name + explicit-binding answer in XMPP, Matrix, Kafka, and OpenTelemetry — every
distributed system that has ever faced this shape solved it the same way).*
