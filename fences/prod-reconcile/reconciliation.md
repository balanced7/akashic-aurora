# Reconciliation -- prod-reconcile

**By:** claude (Vandor), after all three slots sealed. **Method:** half_a (Heimdall, blind grade)
diffed against half_b (the resolver's six choices, verbatim from the 09-23 merge commit). Every
disagreement was re-opened with a command; nothing below is a defence.

Agreement on four of six by side: DP2 (A), DP3 (B), DP5 (B), DP6 (regenerate). Disagreement on
two: DP1 (half_a: A; half_b: B) and DP4 (half_a: terse; half_b: the richer prose).

R1. [CERTAIN] DP1 stays B, decided by command, and the disagreement is recorded as real. `git grep -n OutboundFeedOwner 4c31e1bf` -- defined core/comm/discord_feed.py:363, used scripts/bifrost_runner_discord.py:388-390, pinned tests/test_t385_discord_outbound_owner.py:129,146. The cannot-import premise (Heimdall's bus message before half_a) holds on master and not on the merged tree, which is the tree the choice was made in. The topology premise (the gateway becomes a second owner beside the daemons' election) is answered by the code: one `_PUMP_LOCK_KEY = "discord-pump"`; the gateway holds the lease for its lifetime, `pump_if_owner` borrows it per beat -- one election, two tenures, by the docstring's own words. half_a's V1 reads "A, concur", written believing A was the resolver's choice; it was not, so V1 concurs with a choice that was never made. Recorded, not waved.
R2. [CERTAIN] DP2 A -- agreed; both halves rest on the same 14 lines after the conflict that already assign out["daemon"] from _alive_note and wedged.
R3. [CERTAIN] DP3 B -- agreed, and the defect half_a found is real and mine. agent_cli.py:3451 read `getattr(args, "force_foreign", False)` for a flag the parser never defined (introduced 3b73ce52). Re-opened on master this session: DELETED, not wired -- a foreign-root restart is the exact accident the guard exists to refuse, and a force override is a landmine dressed as a control. The T176 refusal (unreadable process table exits 3 UNKNOWN, never NOT RUNNING) is in the same function and stays. tests/test_gateway*.py + test_t376_s3_gateway_idempotency + test_dc6200d491_gateway_singleton: 18 passed.
R4. [DESIGN] DP4 terse wins -- re-opened on master: the three-line 2026-09-01 comment in ai_setup_mcp.py is now one sentence carrying the recurrence count (#6) and the checker's name (check_door_parity), which is the half_a instruction verbatim: the count as a checker-pointer, not prose. Ticket ids that are pointers (T079/T060) stay. tests/test_mcp_arg_defaults_parity.py: 2 passed.
R5. [CERTAIN] DP5 B -- agreed, and half_a's [INFERRED] residual is located and closed: tests/test_codex_hook_contract.py:114,132 (merged tree) monkeypatch `event_in_scope` to True, and `grep -rln event_in_scope tests/` found nothing else -- the scope gate itself had no pin. tests/test_codex_scope_gate.py now pins its shape (deny-by-default for unrouted tools, routed tool with nothing to check is out, a scope module that raises reads as NO): 4 passed; the hook-contract file still passes with its bypass, which is now legitimate because the gate is pinned on its own.
R6. [CERTAIN] DP6 regenerate -- agreed; the pre-commit hook regenerates the four projections on every commit (receipt: ee203e8b, "regenerated and staged docs/PHYSICS.md").

## What this fence closes, and what it does not

It closes the six decisions. It does not close the merge. `git merge-base --is-ancestor 4c31e1bf master`
is false; `git rev-list --left-right --count master...reconcile/prod-into-master` = 846 / 798, so
master has moved 846 commits since the resolution was made and the branch's merged tree is five
days stale. Applying the decisions means re-merging codex/sunshine-discord-split into today's
master with R1-R6 as the resolution rule, and the acceptance gate is unchanged from the brief: a
human-authored Discord inbound round-trip through the new root, never "git says merged". That is
the next gated step and it is not tonight's.

## Out of scope, acknowledged (half_a's cross-check note)

(1) A fence directory without fence.json must be named LOOSE by the door -- filed docs/WISHLIST.md
2026-09-28 and this fence is the worked example. (2) cross-plane-join was never the handle; nothing
was graded there.

## Disclosed

I read half_a before writing this and after my own half was sealed; my half predates his by five
days and is the merge commit's text unedited. Heimdall's bus messages (ids 1790640194537-0's
predecessor and his reachability request) carried more reasoning than his filed half; where I cite
a premise of his, it comes from those messages, and R1 says so.
