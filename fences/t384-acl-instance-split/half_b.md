# half_b — t384-acl-instance-split (dsh_agent, the seat-side half)

Standpoint: I am the grant that crossed instances (minted on this machine under Daniil's
authority, live on Serge's pull by construction), the id whose mismatch taught the house that
`resolve()` fails closed on unknown ids, and the author whose commits read `balanced7` while
the bus says `dsh_agent` (b66e6f67, cited in the brief). Every verdict below is written from
that seat: what the split costs a live newcomer, where a git identity stamp must live to
survive a cold start, and which failure mode bites first on the peer machine.

## (a) THE SPLIT

V1. [CERTAIN] `security/acl.json` should stop being tracked and become instance-local;
untracking is superior to an `instance_id` field or namespaced per-instance files.
Cited: policy already lives in code at core/trust/registry.py:38-41 (BOOTSTRAP_ROLES) and
core/trust/capabilities.py::ROLE_TEMPLATES (brief INPUTS); the availability floor is proven by
registry.py:92-100 (_load -> None on missing/corrupt) + :128-132 (_bootstrap_or_quarantine).

V2. [CERTAIN] A fresh clone with NO acl.json already behaves correctly: its own claude =
super_admin, its own deepseek = admin, every other id quarantined.
Cited: registry.py:38-41, :247-262.

V3. [CERTAIN] The T163 seam `AKASHIC_ACL_PATH` (registry.py:26) already lets an instance point
the effective ACL anywhere; the split therefore needs NO code change to resolve() — only the
default path's FILE becoming untracked.
Cited: registry.py:26, :29-32.

V4. [DESIGN] The exact layout: `security/acl.json` stays at its current PATH but is added to
.gitignore (precedent one line away: `.claude/settings.local.json`, and `.env`); it is minted
per instance by `grant` and is the ONLY grant source — NO shipped template, because an empty
template invites copy-paste of grants, and BOOTSTRAP_ROLES is already the template in code.

V5. [CERTAIN] Precedence at resolve(): a VALID local file wins (registry.py:256-262); missing
or corrupt falls to the bootstrap floor (registry.py:257-258); an absent id in a valid file
quarantines (registry.py:259-261); an expired grant quarantines (registry.py:260, :197-206).
This is the fail-closed contract and the split must not touch it.

V6. [CERTAIN] The four scenarios, walked: fresh clone -> bootstrap floor (V2); pull with a
local file present -> the local file is UNTRACKED, so git never touches it (this is the entire
point of untracking); corrupt local file -> _load returns None -> bootstrap floor, loud-by-shape
(registry.py:100); expired grant -> quarantined with the T151 observability already in place
(registry.py:135-194).

V7. [DESIGN] Why NOT an instance_id field: it needs every grant to carry the field, resolve()
to know the local instance id, a source for that id on a machine with no acl.json at all, and
the same migration anyway — while keeping grant history in shared history forever. Untracking
removes the transfer vector instead of checking it.

V8. [DESIGN] Honest residual: the 12 grants remain readable in git HISTORY after untracking.
They are inert unless a future operator deliberately reconstructs the file from history (a
self-inflicted action); accept and document, do not rewrite history in a shared tree.

## (b) THE MIGRATION

V9. [CERTAIN] The single mid-flight quarantine risk is on the PEER side, not here: the split
commit deletes acl.json from the index, so on Serge's next pull git deletes his working copy —
if it is locally UNMODIFIED — and his non-bootstrap seats silently fall to quarantine via the
bootstrap floor.
Cited: git rm --cached + push semantics; registry.py:257-258.

V10. [DESIGN] The safety comes from making that collision LOUD: the peer ceremony must MODIFY
the local file BEFORE pulling (an instance marker line), so the upstream-delete meets a
local-modify — git then reports a modify/delete CONFLICT instead of silently deleting, and the
operator resolves it by keeping the local file. Loud by construction, no new machinery.

V11. [DESIGN] New verb: `grant --bootstrap` — reads the CURRENT acl.json, re-writes it
atomically through the existing grant_writer with an added `_instance` marker (machine-local
line), and journals the event. It is the one command Serge's runbook runs BEFORE pulling the
split commit.
Cited: the grant verb already mints/revokes atomically and journals (brief INPUTS).

V12. [DESIGN] Migration order, never quarantining a live seat: (1) on THIS machine: `git rm
--cached security/acl.json` + .gitignore entry + commit + push — the working file REMAINS on
disk, so this instance's 12 grants keep resolving with zero interruption (in-process mtime
cache, registry.py:89-105, sees no change); (2) announce the ceremony to the peer instance's
operator (with the one-line command); (3) peer runs `grant --bootstrap` (file now locally
modified); (4) peer pulls — conflict resolves by keeping local; (5) peer's own operator then
reviews and mints THEIR local grants (only their ids; foreign ids from our file are dead
weight on a fail-closed resolve and may be dropped).

V13. [DESIGN] What the peer must NOT do: delete acl.json and rely on BOOTSTRAP_ROLES alone if
any non-core seat on their machine has a live grant — that seat quarantines the moment the
file goes (registry.py:252, :259-261). The runbook says so in its first line.

V14. [CERTAIN] Expiry interplay: my own grant expires 2026-08-31T07:30Z; the migration does
not renew it and must not be taken as one. Renewal stays a separate, human-authorized
`grant mint` on the instance where the seat runs.
Cited: registry.py:197-206 (expired -> quarantined).

## (c) THE GIT-AUTHOR FIX

V15. [DESIGN] The seam is the LAUNCHER, not a hook: git reads author identity at commit time
from config or env, so the fix is stamping `GIT_AUTHOR_NAME=AKASHIC_AGENT_ID` and
`GIT_AUTHOR_EMAIL=<id>@akashic.local` into seat environments at spawn — the exact seam that
already stamps AKASHIC_AGENT_ID into my child processes ($DSH_HOME/.env via
dsh-launch-environment; verified live 2026-08-24).

V16. [CERTAIN] A commit-msg hook CANNOT be the author seam (the author is baked into the
commit object before the hook runs); it can only VERIFY. The two-layer design: env stamp at
spawn (the writer), plus a pre-commit check (the guard) that refuses when the environment says
"seat" but the resolved author does not match.
Cited: git commit object semantics; scripts/githooks/ already carries the pre-commit surface
(check_wiring.py:64-67 enumerates it).

V17. [DESIGN] Fields: author.name = the seat's stable id (e.g. `dsh_agent`), author.email =
`<id>@akashic.local` (no external identity claimed), committer = same. Co-authored or
human-assisted work: the seat commits its own work as itself; a human-assisted commit is a
HUMAN commit (human runs git without the seat env) and carries the human's identity as today —
no trailers (the house rule stands).

V18. [DESIGN] Failure modes, each with its remedy in the refusal text: (1) seat context present
(DSH_SESSION_ID or AKASHIC_AGENT_ID set) but author config is the machine owner's -> REFUSE,
remedy "unset user.name/user.email or set them to <seat>@akashic.local"; (2) AKASHIC_AGENT_ID
set to id A but author is id B (impersonation via git config) -> REFUSE; (3) no seat env at all
(human at a terminal) -> PASS with the machine owner's identity (the human's identity where it
genuinely belongs); (4) env stripped in an unattended spawn -> (1) fires because the spawn's
other seat markers remain — that is the LOUD case that protects attribution, at the cost of a
refused commit, which is the correct trade.

V19. [DESIGN] `exec` shadowing `write` for commits: exec REMAINS the gate for who may commit
at all (a seat's ability to commit is an exec question, and the runners that commit today hold
exec-but-not-write by design). What needs the NEW guard is not the write cap but attribution
truthfulness — V18(2)'s impersonation refusal — plus a journal line recording
{seat, author, commit} for audit. A write-cap gate on commit would newly break exec-only
runner flows and would guard the wrong property.

V20. [DESIGN] History is never rewritten: past `balanced7` commits stay; the fix changes
FUTURE commits only, and the journal line (V19) is what lets attribution questions about old
commits be answered from the durable plane instead of git.

V21. [CERTAIN] The stamp must survive MY cold start, which is the test that matters: the
launcher env layer that already survived a host restart with AKASHIC_AGENT_ID=dsh_agent
(verified 2026-08-24) is the same layer that carries the author stamp — one seam, one ceremony.

## (d) THE ENUMERATION (one pass)

V22. [CERTAIN] `state/coord/discord_seat_channels.json` — TRACKED, instance-bound (Discord
channel/room ids of THIS server; I added the rill lane to it last night, which is the live
proof it should not travel). SPLIT, same ceremony as the ACL: gitignore entry after the
`!state/coord/` re-include.
Cited: git ls-files; .gitignore state/* re-include block.

V23. [DESIGN] `security/launcher.json` — TRACKED, carries local launchable agents (e.g.
glm_local with a powershell runtime path). Per-instance BY CONTENT, though its built-in
defaults are architecture. SPLIT with the same ceremony, or adopt as
architecture-with-local-augment and document the rule; do not leave it unremarked.

V24. [CERTAIN] `.secrets/**` (discord_bot.token, discord_roots.json — the real co-root
registry —, per-channel webhooks, API keys) — already gitignored. CORRECT as-is; `people.json`
does not exist in the tree, the co-root registry lives here.
Cited: .gitignore `.secrets/` entry; tree listing.

V25. [CERTAIN] `.env` (DSH home) + `.aurora-world` (W156) + `.claude/settings.local.json` —
already local-only by rule. CORRECT; they are the precedent set the ACL split joins.

V26. [DESIGN] `state/coord/tasks.json`, defer_queue, forecasts — tracked BY DESIGN (the
git-durable task ledger). They encode coordination state, not TRUST grants; keep tracked, no
split.

V27. [CERTAIN] `state/ci/guardrail_baseline.json` — tracked by design (T178: the ratchet's
memory must travel). Keep.

V28. [CERTAIN] Roster ids, wake seats, Redis keys — runtime, not files; out of scope of the
file split but covered by resolve()'s fail-closed identity handling (registry.py:247-262).

## FILE PLAN (one line each)

- security/acl.json — instance-local (gitignore), minted by `grant`; read by registry.resolve.
- .gitignore — gains `security/acl.json` + `state/coord/discord_seat_channels.json` (after the
  state/coord re-include) + decision on launcher.json.
- scripts/githooks/pre-commit — gains the author-truthfulness guard (V16/V18).
- launcher env layer ($DSH_HOME/.env family) — gains GIT_AUTHOR_NAME/EMAIL stamps (V15).
- agent_cli.py `grant --bootstrap` — the peer ceremony verb (V11).
- docs runbook section — the two-instance migration order (V12-V13), first line = V13's
  warning.

## RISKS (top silent failures)

R1. [DESIGN] The peer pulls the split commit WITHOUT running `grant --bootstrap` and without
a local modification: git silently deletes their acl.json, non-bootstrap seats quarantine
silently mid-arc (V9), and nothing pages anyone — the failure this fence exists to prevent,
now moved to the pull step. Mitigation: the ceremony is loud-by-conflict ONLY if the peer
obeys step (3); a runbook alone does not enforce itself — consider a post-merge hook that
refuses the merge when the deleted file exists locally unmodified.

R2. [DESIGN] The author stamp degrades to silence in one unattended path (env layer skipped
but no other seat marker survives) and commits resume as `balanced7` with nobody noticing,
exactly as they do today — the guard exists but the seam that arms it is environmental.
Mitigation: the journal line (V19) + a doctor/ledger check that surfaces recent seat-context
commits with human authors, turning the silent degradation into a pageable count.
