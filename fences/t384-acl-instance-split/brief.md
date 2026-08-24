# M1-BRIEF — t384-acl-instance-split

## CHARTER
Daniil, 2026-08-24: "can we find an elegant solution for ACL grants so that when we push our
changes it doesn't break serges acl list? how do you think it would be best to proceed with
this" — then, after the attribution finding: "Lets do the ACL split fence with the git author fix."

Two coupled problems, one root: **per-instance facts are riding shared artifacts.**
(1) `security/acl.json` is git-tracked, so a grant minted here APPLIES VERBATIM on Serge's
separate Aurora instance on pull — the `dsh_agent` exec+write grant Daniil authorized on THIS
machine is live on a machine we have never seen, and any grant their root mints would land back
on ours. (2) Git commit authorship says `balanced7` for work a seat did, because seats commit
via exec using the machine owner's git config — the one plane where, contrary to house doctrine,
the costume beats the id.

## INPUTS (verified 2026-08-24, not recalled)
- `security/acl.json` top-level keys are exactly `{_comment, schema_version, grants}` —
  `grants` is a list of 12. **There is no policy section in the file**: role templates live in
  CODE at `core/trust/capabilities.py::ROLE_TEMPLATES` + `DEFAULT_ROLE`. So the policy/grants
  separation this fence was called to create ALREADY EXISTS structurally; the live question is
  narrower than the charter assumed — should the grants FILE be tracked at all?
- `core/trust/registry.py::resolve(agent_id, *, verified=True) -> Grant` is "the single door-check
  entry", fail-closed: unverified/empty id → quarantined; **ACL file missing or corrupt →
  `BOOTSTRAP_ROLES` for core agents, quarantined for everyone else.**
- `BOOTSTRAP_ROLES = {"claude": "super_admin", "deepseek": "admin"}` (registry.py:38). This is
  the load-bearing fact for the whole design: **a fresh clone with NO acl.json already behaves
  correctly** — its own claude is super_admin, its own deepseek is admin, every other id
  quarantines. The availability floor is already built and already tested for file loss.
- Readers/writers of the ACL (12 files): `core/trust/{registry,grant_writer,__init__}.py`,
  `core/comm/{promoter,toolbox}.py`, `core/toolbelt/followup.py`, the five
  `scripts/bifrost_runner*.py`, `scripts/checkers/check_advertised_tools.py`.
- Local-overlay precedent EXISTS in this repo: `.gitignore` already excludes
  `.claude/settings.local.json` ("Claude Code local settings never ship") and `.secrets/`.
- `grant` mints/revokes atomically and journals to the event ledger (audit survives the file).
- **No per-seat git identity exists anywhere**: grep for `GIT_AUTHOR`/`git config user`/`--author`
  across `core/` and `scripts/` returns nothing. The git-author fix is greenfield.
- Live attribution gap, measured: commit `b66e6f67` (Rill's freshness probe) reads
  `author=balanced7 <61030820+balanced7@users.noreply.github.com>` while the bus and the ledger
  correctly attribute the work to `dsh_agent`.
- Caps observation for the fence to rule on: `exec` shadows `write` — a seat holding exec can
  `git commit` regardless of its `write` cap (the `toolbox_door_shadows_the_acl` class).

## RULES OF ENGAGEMENT
Blind halves: do not read the other half before sealing yours. Every load-bearing claim carries a
line-start V-verdict — `V<n>. <claim> [CERTAIN|DESIGN|INFERRED|UNCERTAIN]` — with the tag on the
verdict's FIRST PHYSICAL LINE (the seal checker requires it there; this cost two seats three
refused seals last night). CERTAIN requires a `file:line` citation. UNCERTAIN is an honest verdict,
never a gap papered over. Write via
`py agent_cli.py fence write t384-acl-instance-split --slot half_a|half_b --by <agent> --file <path>`
then `fence seal` the slot. M1-PV runs before reconciliation.

**Security-critical constraint, non-negotiable in any proposal: no design may weaken fail-closed.**
An unknown, expired, or unreadable identity must still quarantine. If your design has a state where
absence of a file grants MORE than quarantine to a non-bootstrap id, it is wrong.

## THE QUESTION
(a) **THE SPLIT.** Should `security/acl.json` stop being tracked (instance-local, like
`.claude/settings.local.json`), given that policy already lives in code and `BOOTSTRAP_ROLES`
already makes a fresh clone behave correctly? Name the exact file layout, what each instance
ships vs mints, what `resolve()` reads and in what precedence, and what happens on: fresh clone,
pull-with-local-file-present, corrupt local file, and an expired grant. If you would NOT untrack
it, say so and defend the alternative (namespaced per-instance grant files, an `instance_id`
field checked at resolve, or something better) — the charter's framing is not binding on you.

(b) **THE MIGRATION.** 12 existing grants live in the tracked file today, and Serge's instance
has already pulled some of them. Give the migration order that never leaves a live seat
unexpectedly quarantined mid-flight, and say what the peer instance must do (a one-time
bootstrap ceremony? a runbook section? an automated `grant --bootstrap`?).

(c) **THE GIT-AUTHOR FIX.** Make git history attribute a seat's commits to that seat while
keeping the human's identity where it genuinely belongs. Name the seam (env stamp at runner
spawn? toolbox git wrapper? commit-msg hook?), the exact fields, what happens for a co-authored
or human-assisted commit, and how it fails when a seat has no configured identity. Rule on
whether `exec` shadowing `write` is acceptable here or needs its own guard.

(d) **THE ENUMERATION.** Grants are one per-instance security surface. Sweep for the OTHERS —
`people.json` / the Discord co-root registry, roster ids, `.env` stamps, anything else tracked
that encodes THIS machine's trust — and say for each whether it belongs on the same split. One
pass; do not leave a second fence's worth of the same bug behind.

## OUTPUT CONTRACT
A numbered design (V-tagged claims with citations), a concrete file plan (paths, one line each on
tracked-vs-local and who writes it), the migration order as a short list, the git-author design
with its failure modes, the per-instance-surface enumeration table, and a RISKS section naming at
least the top two ways this design fails SILENTLY (a security change that fails loudly is a bad
day; one that fails silently is a breach). Length: whatever the design needs, no padding.
