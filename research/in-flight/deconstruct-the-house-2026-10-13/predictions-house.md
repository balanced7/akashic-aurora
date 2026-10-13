<!-- Provenance: a verbatim copy of the house seat's prediction register, moved out of the session scratch folder
     (scratchpad/house/predictions.md, written 2026-10-13 10:02-10:20 EDT) on 2026-10-13 after review defect D9,
     because a scratch folder gets cleared. Nothing below this comment was edited. The report that uses it is
     the-house-deconstructed.md (section 9a). -->

# House-altitude predictions, registered 2026-10-13 10:02 EDT, before any test ran

H1  The teardown's own folder is invisible to the house's finding doors: knowledge-map (counter kill-switch set)
    returns no node under research/in-flight/deconstruct-the-house-2026-10-13 for a query naming it.
H2  Same for lookback --layers research: 0 hits from research/in-flight.
H3  The house's only automatic clock (Task Scheduler) drives capture and archiving, never a drift reader:
    no scheduled task action names doctor, gen_library, recall-curate, snapshot_knowledge,
    check_dual_authority, check_doc_currency or arc_scorecard.
H4  At least three separate hard-coded operator / exempt id sets exist in production Python, and at least one
    of them lacks 'daniil'.
H5  The arsenal is still decoupled: 0 import lines of core / agent / scripts in arsenal/**/*.py.
H6  core/eye imports nothing from core.foundation (the eye keeps its own SQLite, outside the memory core).
H7  AKASHIC_AGENT_ID is NOT set in the User or Machine environment; the 'claude' stamp comes from a Claude Code
    settings env block (so any process started from a Claude session inherits it).
H8  The live deepseek and kimi runners' parent processes are gone (orphaned launch; who launched them stays unknown).
H9  T418 still reads 'proposed' in the task ledger now.
H10 Local master is now MORE than 76 commits ahead of origin/master (work keeps landing, nothing pushes).
H11 The newest knowledge snapshot is still 2026-09-24.
H12 The newest ephemeral-archive receipt reads ok:false.
H13 Redis db 0 holds at least 23 more learn:experiment:* lesson hashes than the SQLite durable tier.
H14 research/reviewed/reverse-engineering-2026-10-13/audio-music.md is still NOT committed.
H15 `py agent_cli.py status` prints no warning about any of: Redis-only records, archive failures, refused boots,
    snapshot age (the self-report cannot see the house's measured defects).
H16 The doc-currency checker still FAILs with at least 17 violations.

## Added 2026-10-13 10:10 EDT, before running
H17 The house already holds lessons that name its own disease; `recall "alarm nobody reads staleness budget"`
    returns at least one of the_house_reports_what_exists_and_never_what_should_exist_and_does_not,
    advisory_prints_evaporate, when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it in its top 5.
H18 No page is standing on bifrost:pages right now (LLEN = 0), despite tonight's fan-out.
(Observation, NOT pre-registered: the boot_refused scan since 10-09 04:00Z was run as exploration.)
H19 (10:14 EDT, before running) The memory core is the foundation in code, not only on paper: each of core/recall,
    core/comm, core/fleet, core/coord, core/library imports core.foundation somewhere; core/trust does not
    (it reads acl.json directly).

## Results (10:05-10:20 EDT)
H1 held (0 in-flight nodes; side observation: library projections titled "---")
H2 held ([] )
H3 held (16 AkashicAurora-* tasks: watchdogs/services, capture/archive, secret scan, wishlist triage; no drift reader)
H4 held (6 tables, 4 distinct contents; both budget-exempt sets lack daniil)
H5 FAILED on the working tree: arsenal/re/ledger.py:35 (untracked, written 10:03 by the RE workflow) imports core.foundation.ledger; tracked tree still 0
H6 held (core/eye imports only core.eye.* and core.comm.bus.sid8)
H7 held (User/Machine unset; both .claude/settings.json set claude at line 3)
H8 held (parents of runners and their daemons dead; WakeDaemon parent svchost started 10-09 08:32:51)
H9 held; H10 held (77); H11 held; H12 held (49 of 69 ok:false since 08-12); H13 held (exactly 23, all no TTL; decisions 1,175 vs 1,111)
H14 held (untracked; re-triage-slice-spec.md from the same folder was committed 09:41)
H15 held; H16 held (17, exit 1); H17 held (rank 1); H18 held (key absent = 0 pages); H19 held
Exploratory: 32 boot_refused rows since 10-09 04:00Z; first 10-09 08:36:21 (kimi) and 08:36:23 (deepseek)
