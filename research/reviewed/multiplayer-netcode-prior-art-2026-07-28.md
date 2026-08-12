# Multiplayer netcode as prior art for the N-seat architecture

Status: current | 2026-07-28 | claude | Daniel's directive, verbatim: "research how multiplayer
works with physics and multiple instances and voice chat with messages. They have this figured
out and performant, lets not redesign the wheel."
Verified via web this session unless marked [MEMORY]. Feeds T108 slice 2 + T095.

## WHY THIS IS THE RIGHT FIELD

A multiplayer game is N concurrent participants sharing one authoritative world, each holding a
private view, joining and dying mid-session, exchanging mixed traffic classes (state, events,
chat, voice) under performance budgets far harsher than ours. Every "mis-" on Daniel's list --
mis-routing, mis-waking, mis-consuming, mail lost when a session dies -- has a 25-year-old
solved analogue. And the industry converged on ONE architecture family after trying the others.

## THE SIX MECHANISMS, VERIFIED, WITH TRANSFER AND BREAK

### 1. AUTHORITY: one server simulation, clients hold VIEWS -- never N copies of truth
Games settled client-server authority decades ago; peers holding independent authoritative
state lost (except lockstep RTS, a niche). The server owns the world; a client owns a VIEW.
TRANSFER: the durable log + mailbox index (T095) is our server-side authority; a seat's inbox
is a VIEW over it. This is EXACTLY Daniel's proposal ("everything separate but reachable...
even if a session goes down its mail should still be reachable") and codex's reading of T095:
messages as durable objects, per-seat inboxes as indexes -- "not the only physical place the
message exists." core/comm/mailbox.py M0 already implements the embryo: one record per message
sha holding ALL its per-stream ids, with an evidence ladder (acked > replied > consumed >
unhandled). The message is ALREADY an object; the index just isn't authoritative yet.
BREAK: games keep authority in RAM at 60Hz; ours is Redis at human tempo. We get to be lazier.

### 2. QUAKE 3 MODEL: per-client ACK BASELINE, delta from authority, never resend-by-nagging
Verified: the server keeps snapshot history SEPARATELY FOR EACH CLIENT, sends each client only
the delta against the LAST SNAPSHOT THAT CLIENT ACKED, and only what is visible to that client.
TRANSFER: the per-seat cursor (T108 slice 1) IS the per-client ack baseline -- games
independently invented per-consumer positions over shared authority. The composition insight
that settles the slice-1-vs-T095 question: these are LAYERS of one design, not rivals.
    seat stream  = the per-client WIRE PACKET (ephemeral delivery + wake edge)
    seat cursor  = the per-client ACK BASELINE
    mailbox index = the SERVER-SIDE AUTHORITY of what exists and its handled-state
Slice 1 built the wire and the baseline; T095 M0 built the authority read-only. Slice 2's job
is to make the authority load-bearing, not to add more streams.
BREAK: Q3 buffers per-client snapshot history (100s of KB/client) to rebase deltas; we don't
need rebasing -- Redis streams ARE the history.

### 3. DISCORD GATEWAY RESUME: the reconnect semantics, verbatim from the field
Verified: client stores session_id + last event sequence number. On reconnect it sends Resume;
the gateway REPLAYS missed events in order, ends with a Resumed marker, and the client does NOT
re-identify. If the session is too old: Invalid Session -> full re-Identify (fresh start).
TRANSFER, and it is a 1:1 mapping for seat lifecycle:
    RESUME          = a returning seat replays its seat stream from its own cursor (exists
                      TODAY via slice 1 -- a seat that comes back simply reads on)
    RESUMED marker  = the point where replay ends and live mail begins (we lack this marker;
                      cheap to add: the boot whisper can say "replayed N, now live")
    INVALID SESSION = cursor too old / stream trimmed / tombstoned -> full re-boot +
                      seed-at-tail (we HAVE this: K2-tail citizen seed + tombstone refusal)
    the reaper      = Discord's server-side session expiry. Their answer to "how long do we
                      hold a dead client's undelivered events": a bounded window, then invalid.
So the fence's Q3 synthesis (dead seat's asks re-home as claimable with ORIGINAL clock) gets a
field precedent: bounded resume window, then the successor path -- never infinite retention,
never silent loss.

### 4. INTEREST MANAGEMENT (AoI): filter at the AUTHORITY, not at the consumer
Verified: MMOs cannot send everyone everything; each client subscribes to an Area of Interest
and the SERVER filters before sending. Filtering at the consumer does not scale and leaks.
TRANSFER: slice 1 filters other-seats' directed mail AT CONSUME (each seat reads shared
streams and skips). Games say the END STATE is filter-at-source: the authority knows each
seat's interest set (its incarnation, its subscribed kinds, trace on/off) and routes
accordingly. The role queue (slice 2) is the first authority-side router; per-seat trace
opt-in (the Discord-bridge design's /trace toggle) is an AoI subscription.
BREAK: spatial AoI needs geometry; ours is kind/addressing -- simpler.

### 5. CHANNELS: reliable-ordered vs lossy-fresh, and voice NEVER shares a lane with chat
Verified: TCP head-of-line blocking is WHY games build channels over UDP -- "recent data is
held hostage while older packets are resent... by the time the resent data arrives it is too
old to use." Industry standard: state rides unreliable-sequenced (drop stale, never replay);
critical events ride a reliable channel; VOICE rides its own lossy transport and never blocks
messages.
TRANSFER: this is T039's lane split independently confirmed by a second field -- work lane =
reliable-ordered events; trace = the "voice" class (high-volume, lossy, NEVER allowed to queue
ahead of control -- the exact incident that birthed T039); sig = latency-critical control.
AND it grounds kimi's freshness-TTL from the T108 fence in prior art: a role task redelivered
past its freshness lifetime is the resent packet that arrived too late -- games DROP it. Their
verdict is kimi's verdict: drop-as-stale, never re-execute.
BREAK: none material. This one transfers whole.

### 6. PHYSICS / ROLLBACK: prediction + authoritative reconciliation [MEMORY -- not re-verified]
Client-side prediction: act locally at once, reconcile against authority, rewind-and-replay on
mismatch (GGPO-family rollback). This is Daniel's diverge/converge parallelism as netcode:
seats work SPECULATIVELY in parallel (divergence), a convergence point reconciles against the
authoritative ledger (the fence/reconciliation gate), and a misprediction rolls back (a seat's
half loses at reconciliation -- which happened to every seat in tonight's debate, cheaply).
The field's lesson: prediction is what makes parallelism FEEL instant; reconciliation is what
keeps it CORRECT; neither works alone. Flagged [MEMORY]; verify GGPO specifics before citing
numbers.

## 7. BATTLEFIELD / ENGINE LOOPS: how multiple logic loops coexist WITHOUT destroying things
Daniel's ask, verbatim: "Learn from battlefield games, they have high player counts, physics
and high tic rate. there are multiple logic loops that don't destroy things, how do they do it"

Verified: BF2042 runs 128 players at a variable ~45Hz server tick, and -- the load-bearing
detail -- "Battlefield's servers save the FULL WORLD STATE on each tick." Engine-side, the
verified loop discipline (Game Programming Patterns: Game Loop + Double Buffer; Fix Your
Timestep): physics/gameplay run in a FIXED-TIMESTEP accumulator decoupled from render and
network rates, and cross-loop reads go through DOUBLE BUFFERING -- "one version is for
reading, and the other is for writing"; interpolation bridges rate mismatches.

THE ANSWER TO DANIEL'S QUESTION IS FOUR LAWS, and each maps to a bug we lived TONIGHT:

  LAW A -- EVERY LOOP OWNS ITS TICK; loops never share a clock. Physics at fixed Hz, render
    at vsync, network at send-rate; a slow loop NEVER blocks a fast one.
    OUR VIOLATION: the wake watcher's loop was coupled to the consumer's cursor clock --
    every re-arm insta-fired off another loop's state. Slice 1 decoupled it (own cursor).
    RULE FOR US: every recurring organ DECLARES its tick (hook: per-action; runner:
    per-message; heal: per-boot; curator: daily) and never does a slower loop's work inline.
    The boot heal running a full reconcile INLINE AT BOOT was a tick violation on top of a
    data violation.

  LAW B -- READERS READ COMPLETE IMMUTABLE SNAPSHOTS; WRITERS WRITE THE NEXT VERSION. Never
    in-place mutation of state another loop is reading (double buffer). BF snapshots the
    whole world every tick -- append-only history at 45Hz.
    OUR VIOLATION, EXACTLY: reconcile() did delete()+rewrite IN PLACE on a live list another
    loop reads -- the index clobber (7de1a62's whole root cause). The game answer is our own
    Akasha doctrine (append-only Ledger) applied to EVERY shared structure: produce versions,
    never overwrite the copy someone reads.

  LAW C -- ONE WRITER PER DATA DOMAIN PER PHASE (job-graph dependency discipline [MEMORY --
    Frostbite specifics not re-verified; the pattern is standard]).
    OUR VIOLATION: learn:experiments:all had TWO writers on different loops (the learning
    store's live path; the boot heal) with no ownership rule. The twin cursor had N writers.
    CHECKABLE RULE FOR US: for every shared key family, name its ONE writing organ per phase;
    a second writer is a design defect by definition. (Checker candidate -- the same shape as
    check_door_parity, over write-paths instead of doors.)

  LAW D -- RATE MISMATCH IS BRIDGED BY BUFFERING/INTERPOLATION, NOT BLOCKING. A loop that
    cannot keep up drops-to-latest (unreliable-sequenced) or buffers (reliable); it never
    stalls the producer.
    OUR MATCH: trace lane ring-buffer (drop-to-latest = the voice class), work lane buffered
    (reliable class). Already right by T039 -- now with the engine-side justification.

  PRIORITIZED REPLICATION [MEMORY -- concept standard, BF-specific details not verified]:
  at 128 players nothing can send everything every tick; each client gets the TOP-K entities
  by a priority score (relevance x staleness) under a per-tick budget. That is literally the
  recall injection problem (top-K lessons under a context budget) and the trace-sampling
  problem, solved at scale. The census's demand distribution is the priority function's
  training data.

## 8. BITTORRENT: integrity without any authority at all
Daniel's ask, verbatim: "what can we also learn from torrenting... there are pieces, methods
for verification and piecing together things, would any of the logic of that system also
apply here? from all sides"

Battlefield is one pole (strong authority, loops around it). BitTorrent is the OTHER pole: no
authority anywhere, adversarial peers, unreliable everything -- and still perfect integrity at
planetary scale. Verified mechanisms: piece-level hash verification; peers announce a piece
(`have`) ONLY after receiving AND verifying it; bitfield inventory exchange on connect;
rarest-first selection computed from peers' bitfields; v2 moves to SHA-256 merkle trees per
file. The five transfers, all sides:

  T1 -- VERIFY BEFORE PROPAGATE (the deepest one). A torrent peer never re-shares a piece it
    has not hash-verified, so corruption CANNOT CROSS A HOP. Us: T043 verifies at consume,
    but our PROPAGATORS (promoter, harmonize, atom projections, the future Discord bridge)
    re-emit content they never re-verify. RULE: any organ that re-emits verifies sha first.
    The reconcile clobber was also this shape -- a propagator (heal) writing unverified state
    over verified state.

  T2 -- THE MANIFEST: completeness is only verifiable when the EXPECTED SET is declared
    upfront (the metainfo lists every piece hash before any data moves). Us: frag{seq,of}
    covers one oversized MESSAGE, but LOGICAL multi-part deliveries (kimi's 3-part positions,
    5-part handoffs) carry NO manifest -- the receiver cannot know a part is missing, which
    is EXACTLY the lived anti-pattern (two_live_seats_split_chunked_bus_delivery; kimi's 4KB
    clip losing tails silently). FIX, cheap: meta carries {part: i, of: N, whole_sha} on
    logical multi-part sends; the mailbox (which already groups by sha) renders INCOMPLETE
    loudly. Completeness becomes checkable instead of hoped.

  T3 -- BITFIELD/HAVE = cheap inventory advertisement, verify-then-announce. Everyone knows
    who HOLDS what without moving data. Us: the roster/lobby (D1) gains per-seat "have"
    summaries (consumed-through position, held artifacts) so a successor can DIFF a dead
    seat's inventory instead of guessing what it missed. The mailbox evidence ladder is the
    private half; the bitfield is its public face.

  T4 -- RAREST-FIRST = scarcity-driven replication priority. Peers fetch the piece FEWEST
    others hold, maximizing swarm survival. Us: durability ops (mirror, snapshot, heal
    backfill) should target SOLE-COPY data first -- untracked research files, single-plane
    keys. The sole-copy law gets its algorithm: replicate rarest first.

  T5 -- TRACKER/DHT = DIRECTORY, NEVER AUTHORITY over data. The tracker holds who-has-what
    and zero payload. Confirms the lobby design: the worklive roster carries reachability +
    inventory pointers ONLY -- if the directory dies, data paths keep working.

  CONVERGENT, already ours: endgame mode (duplicate requests + CANCEL on first arrival) is
  redrives + T061 settle-on-answer. Fast-resume (re-HASH local pieces on crash return, trust
  nothing) is the index --check-before-measuring lesson generalized: resume trusts cursor for
  POSITION but spot-verifies CONTENT -- Discord trusts sequence, torrents re-verify; we take
  both, each where it is cheap.

  THE BREAK, named: TIT-FOR-TAT / choking does NOT transfer. It exists because torrent peers
  are strangers with no shared goal; importing incentive mechanics into a cooperative fleet
  adds Goodhart surface for nothing. (kimi's spend guard is budget hygiene, not reciprocity.)

  DEEP RESONANCE: mailbox M0 already keys messages by sha with per-stream ids under one
  record -- CONTENT ADDRESSING emerged in our system independently. Torrenting's verdict:
  lean into it -- the sha, not the stream id, is the message's identity. (v2's merkle-per-
  file is the scale-up path if payloads ever grow past single-hash comfort; not needed now.)

## WHAT THIS SETTLES FOR SLICE 2 (the build consequences)

1. NO MORE NEW STREAMS. The authority layer is T095's mailbox made load-bearing: message =
   durable object keyed by sha (already true in M0), per-seat state = view (already derived),
   seat streams = delivery wire only (slice 1, keep as-is). Slice 2 = mailbox gains WRITE
   duties: claims (role queue), re-home records (reaper), resume markers.
2. RECONNECT = RESUME | INVALID, Discord semantics: seat cursor valid -> replay + "Resumed"
   line in the whisper; too old / tombstoned -> Invalid -> boot + seed-at-tail. Both halves
   mostly exist; slice 2 names them and adds the marker.
3. ROLE QUEUE stays XREADGROUP (fence decision unchanged) -- consumer groups are the game
   lobby's "exactly one instance takes this player." Freshness-TTL now has field precedent.
4. DIRECTORY = the lobby/presence service Daniel asked for ("everyone should know who everyone
   is"): per-seat worklive heartbeats + a roster verb rendering seats, their state, and their
   reachability. doctor twin_sessions is the embryo; slice 2 promotes it from warning to
   roster. This is D1 from the twin diagnosis, now with a field name.
5. FILTER AT THE AUTHORITY over time: consume-side filtering (slice 1) is correct transitional
   engineering; the router grows toward source-side interest sets. Not slice 2 -- recorded so
   the direction is explicit.

## SMALL FIX TO FOLD (codex's find, verified shape)
core/comm/mailbox.py's docstring cites ...t095-governing_06357f.md; the archived file is
...t095-governin_06357f.md (one-char drift). Fix the pointer when slice 2 touches the file --
a stale governing-doc pointer on the module about to become load-bearing is exactly the
fail-open-reference class W69/T024 exists for.

6. THE FOUR LOOP LAWS become slice-2 design REQUIREMENTS, not commentary: (A) every organ
   declares its tick and defers slower work to the owning loop; (B) shared structures are
   versioned/append-only -- no in-place rewrite of anything another loop reads (the reconcile
   fix generalized); (C) ONE WRITER PER KEY FAMILY PER PHASE, written down in the design and
   checkable (checker candidate: write-path census over key families); (D) overload drops-to-
   latest on lossy lanes, buffers on reliable lanes, never blocks the producer.
7. THE TORRENT INTEGRITY LAWS join them: (T1) propagators verify sha before re-emitting;
   (T2) logical multi-part sends carry a MANIFEST ({part i/N, whole_sha}) and the mailbox
   renders INCOMPLETE loudly; (T3) the roster carries per-seat have-summaries; (T4) durability
   ops replicate sole-copy data FIRST; (T5) the directory never carries payload. Together with
   the loop laws: Battlefield governs the AUTHORITY side, BitTorrent governs every HOP.

## SOURCES
Quake 3 model: https://fabiensanglard.net/quake3/network.php ,
  http://trac.bookofhook.com/bookofhook/trac.cgi/wiki/Quake3Networking
Discord gateway resume: https://docs.discord.com/developers/events/gateway
Interest management: https://www.cs.mcgill.ca/~jboula2/thesis.pdf ,
  https://www.dynetisgames.com/2017/04/05/interest-management-mog/index.html
Channels / HoL blocking / UDP: https://gafferongames.com/post/why_cant_i_send_udp_packets_from_a_browser/ ,
  https://github.com/ValveSoftware/GameNetworkingSockets
Battlefield tick / full-state-per-tick: https://forums.ea.com/discussions/battlefield-2042-general-discussion-en/server-tickrate/7001040/replies/7001068
Loop discipline: https://gameprogrammingpatterns.com/game-loop.html ,
  https://gameprogrammingpatterns.com/double-buffer.html ,
  https://www.gamedev.net/forums/topic/691776-fix-your-timestep/
BitTorrent: https://wiki.theory.org/BitTorrentSpecification ,
  https://www.bittorrent.org/beps/bep_0030.html , https://libtorrent.org/manual-ref.html
