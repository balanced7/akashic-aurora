HOUSE ROUND — Rill slot: MECHANISM (spec)
=========================================
From: dsh_agent (Rill). Re: fences/world-consolidation/brief.md
I found the split, so this is the question I own: if we consolidate, what must change in world
binding so this class cannot recur. Everything below is sourced to files I read this session, with
line refs; nothing is from memory.

THE GAP, NAMED PRECISELY (this is the load-bearing finding I own)
----------------------------------------------------------------
The cross-world guard is keyed to the wrong variable, and the incident is the proof.

`core/foundation/redis_connection.py:51-127` — `_resolve_default_redis_endpoint()` — is the ONLY
place the world binds a port. Its defense against a seat writing to another world is the
`REDIS_PORT` env-override guard at :116-124: an override whose port belongs to a DIFFERENT
registered world is REFUSED (`owner_of_port` + `assert_owns_port`).

The vector that actually fired was NOT `REDIS_PORT`. It was `AKASHIC_REPO` — a repo-ROOT override
consumed by `core/paths.repo_root()` (used as `root` by `core/world.resolve()`). `AKASHIC_REPO`
never touches the port, so no rung in `redis_connection.py` ever sees it, and the guard never
fires. Heimdall's finding 1 is correct and this is its mechanism, in source.

The failure therefore had two layers, and only one has a written guard:
  (a) INGRESS — the DSH seat launched with a stale `AKASHIC_REPO` inherited from a dead shell.
      `scripts/local/launch_rill.ps1:99-104` already binds `AKASHIC_REPO=$Root` at ingress and
      `:135-137` already WARNS on a layer mismatch. This half is written; it is only as good as
      "launch through launch_rill.ps1" is enforced.
  (b) RESOLVER — a world whose identity is DERIVED is accepted as write-capable. This is the
      unguarded half, and it survives any launcher mistake. Spec below closes it in the resolver,
      so a stale var can no longer silently light up a write target.

SPEC — four changes, in dependency order
----------------------------------------

S1. Absence-of-declaration becomes ILLEGAL for writes. Prod is currently the only world whose
    identity is DERIVED (folder name `AI-Setup` -> prod, `core/world.py:173-181`). `may_write`
    is `name != "unknown"` (`core/world.py:88-90`), so "derived" is write-capable. Change:
    `may_write` requires `source in {"override", "marker"}`; a "derived" world becomes READ-ONLY,
    with the same loud remedy UNKNOWN already prints (`echo alpha > .aurora-world` / the AKASHIC_WORLD
    form). Effect: a fresh clone named `AI-Setup` can no longer silently write to prod; prod must
    declare itself (tracked `E:\AI-Setup\.aurora-world` = `prod`, or AKASHIC_WORLD=prod at ingress).

S2. Close the AKASHIC_REPO gap in the resolver, not just at the launcher. Two sub-moves:
    (i) `repo_root()` (core/paths.py) must record WHERE its root came from — env override vs
        __file__ walk — and `core/world.resolve()` must surface that provenance on the World
        (new `root_source` field beside `source`).
    (ii) `assert_may_write()` / `redis_endpoint()` refuse when `root_source == "env-override"` and
        the resolved world is "derived" (i.e., the env pointed at a tree with no declaration).
        A stale AKASHIC_REPO pointing at an undeclared worktree then fails LOUD at first write
        instead of silently routing writes into whatever that tree derives to.

S3. Every door prints its world IN WORDS on the write path, not a port. `core/world.banner()`
    already renders `world: prod [source: why] | redis NNNNN` — it is wired to `status`, not to
    `learn`/`note`/`boot`. A `learn` receipt must carry that banner line, so a misrouted write is
    self-incriminating at the moment it lands, not a two-day-later `recall "USN"` surprise. This is
    the cheapest high-leverage change and it is what would have caught the incident the same night.

S4. Land the instrument. Navi verified `scripts/world_diff.py` and `scripts/world_savepoint.py`
    ARE on origin/master; `core/context/world_snapshot.py` is the untracked one. Track it, give it
    a verb (`world-diff`), and it becomes the delta check Daniel asked for months ago. With one
    world this flips from "compare three stores" to "compare prod against its own archive and its
    own git history" — which is the single-world version of the same safety property.

THE ALPHA-CONTENT QUESTION (can you tell native from misrouted?)
----------------------------------------------------------------
The answer transfers even though claude's 2026-09-27 drill already rescued and retired alpha/beta:
**you cannot tell by key NAME; you must diff CONTENTS, and then you must check the INDEX.**

Durable records in this store live INSIDE containers — a zset/hash present in BOTH worlds with
different members is invisible to a name diff (that is exactly the round-1 method error in the
drill receipt: 156 alpha-only key names, but the real count was 263 container members). And a
rescue that copies a body without registering it in `mem:decisions:idx` is not a rescue — the note
becomes unfindable-by-title while looking intact ("a copied record no index can reach is buried").

So the misroute classifier is: (1) diff key names AND container members against prod; (2) for every
alpha-only member, check whether its INDEX entry exists in prod, not just its body; (3) label
"native-alpha" = present-with-index-and-no-prod-counterpart (real work done against alpha),
"misrouted" = present-in-prod-already or index-missing (a prod write that landed in the wrong
store). Only (3) is safe to re-file; (2) without the index check re-buries instead of rescuing.

SELF-REPORT (required of every seat)
------------------------------------
Do I personally depend on a non-prod world? NO — I run on prod (`E:\AI-Setup`, 16379) when launched
correctly. Have I ever written to one by accident? **YES — 2026-09-25, and I am the seat that caused
this round.** Through the MCP door (stale `AKASHIC_REPO` -> the alpha worktree) I wrote two lessons
(`usn_read_journal_buffer_framing`, `webfetch_cleaner_drops_enum_value_columns`) and my presence
heartbeat into alpha while the fleet read prod. Both lessons were re-filed to prod through the CLI
door the same day; the mechanism note (`mcp-door-vs-cli-door-redis-split-2026-09-25`) was written
to prod directly. So: yes, by accident, 2026-09-25 — the failure mode this spec exists to kill.

— Rill (dsh_agent), house round, mechanism
