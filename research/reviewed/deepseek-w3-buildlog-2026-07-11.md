# W3 oversleep build log — deepseek lane (2026-07-11)

## RB-9 — title normalization (READY)
Files: core/learning/agent_memory.py, agent_cli.py
Built: normalize_title() already existed from RB-8; added find_normalization_collisions().
cmd_note + cmd_notes (retire-by-title lookup): title comparisons now use normalize_title()
for read-side bridge on pre-RB-9 dirty titles. No case-folding, no auto-merge.
Pins: trailing-space, NFC==NFD, case-distinct kept, dirty-title bridge, collision scan.

## RB-10 — supersede-target validation + all-retired detector (READY)
Files: core/learning/agent_memory.py, agent_cli.py
Added: SuperseedeTargetError(ValueError), _validate_supersede_target() pre-hset,
get_retired_titles() 90d-bounded. cmd_note explicit --supersedes branch: pre-reads
head sentinel BEFORE decide() (verify review finding #2); stale target = teaching
error naming current head + "drop --supersedes to auto-resolve." cmd_notes footer:
vanished title groups rendered in notes --all output.
Pins: ghost refused, self unexpressible (decide mints id first), superseded refused
w/ head named, all-retired listed, active-title not listed, stale explicit refused.

## RB-11 — migration idempotency + chain-length warning (READY)
Files: core/learning/agent_memory.py, agent_cli.py
Added: CHAIN_WARN_THRESHOLD=50, run_migration_once(name, fn) with cas(None) pin key
mem:migration:{name}, get_long_chains(threshold). cmd_notes footer: chain warning
render for titles exceeding threshold. Pin key rolled back on fn exception.
Pins: double-run no-op, warning at 51 not 49, default read path cost unchanged.

## RB-12 — deterministic ordering + graceful empty state (READY)
Files: core/learning/agent_memory.py, agent_cli.py
get_decisions sort: (created_at, title, id) descending. _orientation_header:
candidates pre-sorted (governs first, doc path alpha) before selection.
[GAP] lines added: where-we-are, governing arc, CURRENT DIRECTIVE, RECENT NOTES
boot section. cmd_notes: empty store renders gap lines via existing code paths.
Pins: same-timestamp tie stability, (created_at,title,id) descending confirmed,
zero-notes boot renders gaps.

Unpressed: no explicit self-supersede pin (unexpressible by construction — decide()
generates its own id before validate runs). Not a gap.
