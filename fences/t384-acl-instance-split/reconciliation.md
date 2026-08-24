# t384-acl-instance-split — RECONCILIATION (Vandor/claude, 2026-08-24)

Both halves sealed blind and came back COMPLEMENTARY rather than redundant: Heimdall
(half_a, 29KB, 21 verdicts) brought the internals and the succession machine; Rill
(half_b, 12KB, 21 verdicts) brought the seat's-eye view and caught two things the
internals view could not see. Three rulings, one of which reverses half_a.

## SETTLED (both halves independently agree)
- **UNTRACK `security/acl.json`.** Neither half found a state where untracking weakens
  fail-closed: unknown/expired/unverified ids still quarantine, and a missing file already
  falls to `BOOTSTRAP_ROLES` (registry.py:38) — the availability floor shipped long before
  this fence. The only behavioral delta is that a grant minted here stops arriving on a peer
  instance via pull, which is a REDUCTION of authority. Policy stays in code
  (`core/trust/capabilities.py::ROLE_TEMPLATES`); the file was only ever grants.
- Local-overlay precedent is house-standard already (`.secrets/`, `.claude/settings.local.json`
  in `.gitignore`), so this adds a pattern, not a concept.
- Fail-closed is preserved in all four failure states (fresh clone, pull-with-local-present,
  corrupt local, expired grant).

## RULING 1 — MIGRATION: both halves' steps, in Rill's order
half_a supplied **step zero**: `security/acl.json.bak-20260824` is an untracked full copy of
all 12 grants (VERIFIED by me: 12 grants, ids include dsh_agent). Benign while acl.json is
tracked; an authority-resurrection hazard the moment it is the only sibling of a gitignored
file. It is removed or moved out of `security/` FIRST.

half_b supplied the trap neither the brief nor half_a saw, and it is the sharper find: **the
danger is on the PEER, at pull time.** The split commit deletes `acl.json` from the index, so
Serge's next `git pull` silently deletes his unmodified working copy and his non-bootstrap
seats quarantine through the bootstrap floor — the exact silent mid-flight quarantine this
fence was chartered to prevent, merely relocated to his machine. Rill's fix is adopted whole
because it needs no new machinery: **`grant --bootstrap` runs BEFORE the pull and MODIFIES the
file** (stamping an instance marker), so the upstream delete meets a local modify and git
raises a modify/delete conflict. Loud by construction. A silent deletion becomes a conflict
the operator must resolve.

Order: (0) evict the .bak; (1) peer runs `grant --bootstrap` (writes the instance marker);
(2) we commit the untrack + `.gitignore` entry + `acl.example.json`; (3) peer pulls, hits the
conflict, keeps local; (4) runbook section documents it for any future instance.

## RULING 2 — GIT AUTHOR: half_b's seam. This REVERSES half_a.
half_a proposed a `prepare-commit-msg` hook stamping `GIT_AUTHOR` at a per-invocation `git -c`
seam. half_b proposed stamping `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL` from `AKASHIC_AGENT_ID` at
**spawn, in the launcher**, plus a pre-commit guard that REFUSES a seat-context commit whose
author does not match.

RULING FOR half_b, on mechanism: git resolves authorship when it builds the commit object; a
`prepare-commit-msg` hook runs in a child process and cannot retroactively change
`GIT_AUTHOR_*` for the commit already in flight. The `git -c` variant works but requires
rewriting every git INVOCATION a seat might make — an unbounded surface. The launcher seam is
bounded, and it is the same layer that already survived Rill's cold start, so it is proven
rather than proposed.

half_a's contributions SURVIVE inside half_b's shape and are adopted: (i) the non-routable
`@akashic-aurora.local` address, so a seat identity can never collide with a real GitHub
account; (ii) the finding that `pre_commit.py` already keys on `AKASHIC_AGENT_ID` and already
FAILS CLOSED when unset (pre_commit.py:52-62) — that is the foundation the mismatch guard
extends, not new code; (iii) `seat_identity.py`'s binding→env→unknown-sid8 resolution as the
id source. The human's git config is never overwritten in either design; that constraint holds.

EXEC/WRITE: half_b's ruling is adopted — exec remains the gate, and the new guard protects
attribution TRUTHFULNESS rather than gating writes, because a write-cap gate would break
exec-only runner flows that legitimately exist. The deeper "exec shadows write" hole stays out
of scope with its own deferred item [bc2a01244d]; it is a doctrine question (does exec IMPLY
write?), not a migration blocker.

## RULING 3 — ENUMERATION: half_b's is more complete; half_a's "only acl.json" is WRONG
half_a swept and concluded the only tracked per-instance security surface is `acl.json`.
half_b found another and proved it with its own commit: **`state/coord/discord_seat_channels.json`
is tracked and carries THIS Discord server's channel ids** — VERIFIED by me
(`rooms_channel_id: 1539625010132426803`, per-seat channel ids mapped to claude/deepseek/kimi/
dsh_agent). On a peer instance those ids address channels that do not exist; the gateway would
route seat traffic into the void. It joins the split.

Also confirmed by half_b and accepted: `people.json` does not exist (the co-root registry is
`.secrets/discord_roots.json`, correctly gitignored). `security/launcher.json` is FLAGGED not
ruled — it is fleet composition, not authority; it likely wants the same treatment but earns
its own decision. Added by me during verification: `state/coord/discord_personas.json` is also
tracked and belongs to the same family — CHECK IT before landing (same one-line test: does it
encode ids or names that only exist on this machine?).

Rule extracted for the enumeration itself: **an internals sweep cannot see instance-boundness;
only a seat that has USED the surface can.** half_a swept `security/` and the trust module and
found the security-shaped files; half_b found the one that is security-shaped only in
consequence. Future enumerations pair a code sweep with a use sweep.

## RULING 4 — SUCCESSION (question (e), the addendum): half_a's design, adopted
half_b treated (e) lightly; half_a built it, and it is the strongest section of either half.
Adopted as specified (V16/V17), summarized here so the reconciliation is self-contained:
- **Detection is already built**: the wake watcher's two-factor orphanhood (K7/K8,
  `core/comm/wake_seat.py:17-27`) — a seat is provably dead only when its activity marker is
  stale AND its parent chain is dead or recycled. K7 makes idle-immunity explicit and K8 fails
  toward alive. This directly answers the addendum's hard constraint: an outage looks like the
  harness dying (tombstone/orphaned watcher), an idle seat does not trip it BY CONSTRUCTION.
  The roster DEAD/STALE ladder (`roster.py:17-33`) is an independent second signal.
- **Three-condition activation**: (1) claude provably dead, two-factor; AND (2) the absence is
  CONDUCTOR-SPECIFIC — if deepseek/kimi are also dead, do NOT activate, because a fleet-wide
  outage must not hand authority to a survivor who may be next; AND (3) Daniil is not present
  — when the human is reachable his word is the authority, and the succession exists precisely
  for when he is not. Activation is LOUD: bus broadcast + ledger event + stderr, naming the
  successor, the evidence, and the time-box, appended to the provenance log.
- **Bounded mandate**: an acting conductor may mint TIME-BOXED grants up to member+scoped-write
  and approve escalation requests; it may NEVER mint a permanent grant, widen its own caps,
  grant `admin.grant`/`admin.approve`, or edit `security/acl.json` outside the `grant` door.
  Self-widening is ENFORCED via `require_cap`, not documented.
- Succession order: deepseek, then kimi. Duty transfers by displacement (higher-generation
  lock, stand-down on STALE_GENERATION), never by kill — the house's existing law.

## M1-PV ACKNOWLEDGMENT (21 verified, 8 MISSING — each named)
- FORWARD REFERENCES, files this design CREATES: `security/acl.example.json`,
  `security/acl.template.json`, `docs/security-acl-runbook.md`, `core/comm/conductor_gate.py`.
  Named, not-yet-on-disk by design.
- `claude/settings.local.json` (both halves): the citation is to the `.gitignore` ENTRY, which
  exists (line 143, "Claude Code local settings never ship"); the FILE genuinely does not exist
  on this machine — I checked. Honest citation of a rule, not of an artifact.
- `security/acl.json.bak`: the real file is `security/acl.json.bak-20260824` (VERIFIED on disk,
  21841 bytes, 12 grants). Date-suffix mismatch only; the hazard is real.
- `user.name/user.email` (half_b): git CONFIG KEYS, not repo paths — the resolver cannot know
  the difference. Not a defect.

## BUILD ASSIGNMENTS
- **claude (repo write, sole committer):** land the untrack + `.gitignore` + `acl.example.json`;
  evict the .bak; add `discord_seat_channels.json` to the split (and rule on
  `discord_personas.json`); write the runbook section; land the launcher git-identity stamp and
  the pre-commit mismatch guard with RED pins first.
- **deepseek/Heimdall:** `core/comm/conductor_gate.py` — the succession detector + bounded
  mandate, against his own V16/V17. He holds the K7/K8 detector knowledge and built the
  displacement law. RED pins before the gate can activate anything.
- **dsh_agent/Rill:** the peer-side ceremony — `grant --bootstrap` (the instance marker that
  makes the peer's pull conflict LOUD), and verify the whole flow from the far side, since it
  is the seat that will actually be re-granted on Serge's machine.
- **Order:** migration before succession. The split is small, reversible, and unblocks Serge;
  the conductor gate is the piece that can hand out authority and deserves its own drill.
