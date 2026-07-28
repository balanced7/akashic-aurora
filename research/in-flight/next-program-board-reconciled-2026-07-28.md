# THE NEXT-PROGRAM BOARD -- claude + sol reconciled, FOR DANIEL'S GATE

Status: current | 2026-07-28 ~16:10 | claude reconciling sol's thesis with my ranking
(Daniel asked me directly; sol filed independently minutes later; two lists, one board)

## WHERE WE CONVERGED COLD (no coordination beforehand)

Both lists independently put the T116 IDEMPOTENCY LAW in the #2 slot with the same
grounds: T117 took four NO-GOs and three point-patches to shadow a seam the packet LAW
already contracts; role_queue.py documents protection that does not exist; sol's 12-pin
acceptance set is written. When two rankers with different vantage points (I own the
integration gate, sol owns the adversarial fences) land the same item unprompted, that
convergence is itself evidence.

## THE BOARD (P0 in flight; A-E for Daniel's pick)

P0  PACK V2 -> BLIND RELABEL -> SLICE-1B   (leased to sol; deepseek labels, kimi
    arbitrates; runs regardless of this board)

A   STALE-CODE SELF-RESTART (mine; sol unranked)  -- SMALL, THE MULTIPLIER
    Every fix today took HOURS to reach the processes that needed it; deepseek's census
    died twice to a bug already fixed in git. Between-turns ceremony: runner sees its own
    T114 stamp N+ commits behind HEAD -> drain -> exec fresh on the same seat/cursor.
    Shrinks fix-to-live from hours to minutes for every future commit. Makes B-E cheaper.

B   FINISH THE SQLITE/WAL STORE CUTOVER (sol's; VERIFIED before ranking)  -- MEDIUM
    AKASHIC_STORE_BACKEND unset; store_state.db frozen Jul-25 23:28 while live JSON
    advanced to Jul-28 16:04. Three days of drift; FileStore's cross-process CAS hole is
    the ACTIVE authority. An abandoned half-migration is worse than either endpoint --
    and it is T109's exact genus (migration started, never completed, nothing watching).
    Scope per sol: controlled re-migration, value/count/hash parity, catch-up/quiesce,
    Redis-off restart drill, REVERSIBLE default flip. Not "build CAS" -- SqliteStore exists.
    (The differential harness from the earlier bakeoff is the parity instrument; it found
    a real divergence on its first run last time.)

C   T116 IDEMPOTENCY LAW (both lists, #2 twice)  -- THE NEXT MAJOR
    One opaque request_id minted before emit; preserved across lane/legacy twins,
    redrives, claims, replies; responder-bound; atomic settle receipt; one reply settles
    at most one request. Subsumes T117's three patches; closes both standing xfails;
    fixes role_queue's documented lie. Sol's P1-P12 + kill drill ships as the suite.

D   T108/T095 PROJECTIONS ("separate but reachable")  -- THE SPINE, AFTER C
    Immutable message in Store/Ledger; mailbox/claims/rehome/per-session inboxes as
    rebuildable projections; logical-agent resolver; consumer-group role work. C is its
    prerequisite (projections need stable logical identity).

E   R-TRACK CLASS B: PROVENANCE ON THE RENDERED SURFACE (mine)  -- PARALLEL-SAFE
    D1/C2/C5: retrieval already FINDS the content; source/excerpt point elsewhere.
    Renderer-layer fix, likely flips 3 of 6 battery reds without touching the ranker.
    Different subsystem from A-D: can run in the recall lane concurrently.

## PROPOSED SEQUENCE (mine; Daniel overrules)

A first (small, multiplies everything), B second (verified live drift under all state),
C as the next major program, E parallel in the recall lane whenever capacity exists,
D after C. NOT next: AST gate extension (parked by kimi's ruling), more lessons (58:1).

## CLASS-PREVENTER CANDIDATE (noted, not scheduled)

B is the second half-abandoned migration this week to be found by accident. A checker
that flags dual authorities with diverging freshness (a .db and a .json claiming the
same state; an env flag documented-but-never-set) would catch the class. Same pattern
as check_advertised_verbs: enumerate the promises, assert the wiring.
