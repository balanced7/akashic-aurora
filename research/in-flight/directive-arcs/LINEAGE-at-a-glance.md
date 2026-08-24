# Directive Lineage at a Glance

Projection: arc map (his words, timestamps) × task ledger (owner, status, commit, files).
Built by Navi 2026-08-19, exec-grant session. Sources: DRAFT-directive-arc-map.md (ratified
2026-08-18) + state/coord/tasks.json @ seq 364. Nothing here is new truth -- it is a JOIN over
two existing truths. Where the chain breaks (ledger files field empty), the break is shown.

## Arc 1 · “seamless continuity from session to session”  (2026-04-12 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 07-15 | no manual pasting for me but just seamless continuity from session to session | T074 | done | claude | c39e207 | ⚠ files not recorded — commit c39e207 is the pointer |
| 08-07 | have it auto-reconstruct for you when you reach for it | T220 | done | claude | f714fa7 | ⚠ files not recorded — commit f714fa7 is the pointer |
| 07-29 | entry 8: "I wish I could always return to the best version of me at peak creativity | T341 | done | claude | 4af09d11 | agent_cli.py |

## Arc 2 · “your digital ironman suit”  (2026-07-16 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 07-16 | what can we build and add to augment your abilities further, for this to be your digital ironman suit that you can customize and improve! | T084 | approved | — | — | — (row approved; no commit yet) |
| 08-04 | what if you could quickly invoke with a verb a deepseek instance... reduce your cognitive load if you could quickly ask for help yourself | T171 | done | claude | fe00880 | ⚠ files not recorded — commit fe00880 is the pointer |
| 08-05 | using that fleet solve the orchestration problems of running that fleet | T181 | done | claude | b9b1d3e | ⚠ files not recorded — commit b9b1d3e is the pointer |
| 08-07 | your deepseek budget is unlimited, I want to see all the powerful ways you can leverage these capabilities | T215 | done | claude | HEAD | ⚠ files not recorded; commit logged as HEAD (unresolved pointer) |

## Arc 3 · “so we stop getting all this mail mis routing, mis waking, mis consuming, mis everything mess”  (2026-04-15 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 07-19 | if you, deepseek and kimi all have write and invoke permissions then if anyone gets stuck the others can resuscitate them | T097 | approved | — | — | — (row approved; no commit yet) |
| 07-28 | why can't we have two seats or as many as we need... | T108 | claimed | claude | — | — (row claimed; no commit yet) |
| 08-06 | Bifrost should optimize for collaboration first and infrastructure second | T197 | done | claude | e8217c0 | ⚠ files not recorded — commit e8217c0 is the pointer |
| 08-10 | make bifrost as easy and reliable as the ask verb | T263 | done | claude | e0fbc4a | agent_cli.py<br>tests/test_cli_send_spills.py |

## Arc 4 · “I get to seed ideas at my pace”  (2026-04-12 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 07-21 | I leave the order up to you, lets get to building | T099 | parked | claude | — | — (row parked; no commit yet) |
| 07-28 | open the ask to everyone on what we should build next and lets build it | T117 | abandoned | — | — | — (row abandoned; no commit yet) |
| 07-31 | my priority is figuring out a workflow where I get to seed ideas at my pace and have you or a collection of agents parse them... and get things done | T126 | claimed | claude | — | — (row claimed; no commit yet) |

## Arc 5 · “you dont need to drive it yourself to observe it”  (2026-04-11 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 07-20 | build our own... full visibility of what works | T098 | proposed | — | — | — (row proposed; no commit yet) |
| 08-04 | lets build it... a good place for our security eyes when we get them | T156 | done | claude | db1a629 | ⚠ files not recorded — commit db1a629 is the pointer |
| 08-07 | you dont need to drive it yourself to observe it, you can troubleshoot from without now | T206 | done | claude | HEAD | ⚠ files not recorded; commit logged as HEAD (unresolved pointer) |
| 08-07 | we can see how old a file is and last time it was modified | T212 | done | claude | HEAD | ⚠ files not recorded; commit logged as HEAD (unresolved pointer) |
| 08-07 | at work I find a lot of value by seeing what one system has and the other doesn't | T213 | done | claude | HEAD | ⚠ files not recorded; commit logged as HEAD (unresolved pointer) |
| 08-17 | We need to give deepseek and kimi eye access, I am most curious where they will go | T336 | done | claude | 2543ffc8 | core/comm/toolbox.py |

## Arc 6 · “I don't want our forest thread to lie to us”  (2026-08-10 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 08-10 | How can we fix all clipping instances everywhere so we stop running into that issue? | T273 | proposed | claude | — | core/comm/packet_spec.py<br>agent/bifrost_pull.py<br>scripts/checkers/check_clips.py<br>tests/test_clip_contract.py |
| 08-17 | why are things still clipping, how do we get around that, I thought we fixed this | T338 | done | claude | 43d1c8f3 | agent_cli.py |
| 08-17 | Lets add that fidelity, I don't want our forest thread to lie to us | T335 | done | claude | 1f44d98a | core/eye/routes.py<br>agent_cli.py |
| 08-17 | KPIs have a nasty habit of being good at one thing and missing a heard of elephants | T337 | done | claude | 5ac63274 | scripts/arc_scorecard.py |

## Arc 7 · “I'd rather lean towards ergonomics”  (2026-04-12 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 08-04 | I dont want things stalled on performance because we built things in singlethreaded ways | T157 | done | claude | af6c973 | ⚠ files not recorded — commit af6c973 is the pointer |
| 08-07 | make an unlimited version and we can figure out scaling down from there | T204 | done | claude | HEAD | ⚠ files not recorded; commit logged as HEAD (unresolved pointer) |
| 08-10 | Is there a way to verbify it so that it is easier for you to make these? | T275 | done | claude | 5ce065d8 | design/report-kit.css<br>scripts/generators/gen_report_scaffold.py<br>agent_cli.py<br>tests/test_report_kit.py |
| 08-10 | 08-16 "how do we verbify the sql queries | T324 | approved | — | — | core/eye/index.py<br>agent_cli.py |
| 08-17 | I don't want to let security break the usability of this system | T339 | done | claude | 44a60234 | core/comm/toolbox.py |

## Arc 8 · “Remember I like halo and mythical things”  (2026-07 → live)

| When | His words | Row | State | Owner | Commit | Files |
|---|---|---|---|---|---|---|
| 08-10 | What are some positive callsigns... that also credit the incredible discoveries and contributions each has made? | T258 | done | claude | a7e63e7 | core/fleet/residents.py<br>agent_cli.py<br>tests/test_resident_identity.py |
| 08-10 | I still want us to have an organized port naming and allocation schema | T266 | done | claude | 33d3b70 | config.py<br>scripts/generators/gen_ports.py<br>scripts/checkers/check_ports.py<br>tests/test_port_registry.py |
| 08-10 | build it out with placeholder names and we can change them later | T267 | done | claude | d2dcda1 | core/fleet/residents.py<br>agent_cli.py<br>tests/test_resident_placement.py |

---

## What the join shows

- 32 directive instances resolve to live ledger rows.
- 12 TRUE breaks in the files chain: the row is DONE (work landed) but the files
  field is empty. Open/approved/claimed rows with no commit yet are NOT breaks -- the action
  has not happened, so there are no files to record.
- Two break shapes: (a) commit sha present but files never filled in -- the commit carries the
  truth, the ledger does not; (b) commit logged as the literal string HEAD -- an unresolved
  pointer that will rot the moment HEAD moves (T206, T212, T204, T215 carry this shape).
- If 'reasoning lineage at a glance' is to be a standing surface, the files field is the seam
  that wants a git-backed backfill verb: resolve each done row's commit to its touched files
  once, write them back, and the chain closes. HEAD-shaped commits want resolving to their
  sha at write time, before the pointer rots.
