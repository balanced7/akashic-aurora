---
akashic_id: art_20260714_t060-m1-fence-machine-records-fence-json_4e2038
akashic_sha: fbd3b2b1eeb6
status: fossil
type: report
arc: T060
date: 2026-07-14
title: T060-M1 fence machine records (fence.json + pv_report.json)
gist: "Machine records of the T060-M1 fence round, verbatim (fence workspace v1, T053). ## fence.json ```json { \"id\": \"t060-m1-design\", \"question\":"
tenant: solo
visibility: fleet
seats: [claude, deepseek]
category: [method, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_t060-m1-reconciliation-continuous-presen_55da7b
    rel: supports
created: "2026-07-15T03:18:17"
updated: "2026-07-15T03:18:17"
---
<!-- GENERATED PROJECTION of art_20260714_t060-m1-fence-machine-records-fence-json_4e2038 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T060-M1 fence machine records (fence.json + pv_report.json)

Machine records of the T060-M1 fence round, verbatim (fence workspace v1, T053).

## fence.json
```json
{
  "id": "t060-m1-design",
  "question": "M1 Continuous Presence: formalize the runner+listener architecture as daemon peers -- what is the design for agents that are ALWAYS reachable and resumable, rather than session-bound?",
  "tier": "full",
  "opened_by": "claude",
  "opened_at": "2026-07-15T06:24:43.153187+00:00",
  "seals": {
    "half_a": {
      "by": "deepseek",
      "at": "2026-07-15T07:18:17.148556+00:00"
    },
    "half_b": {
      "by": "claude",
      "at": "2026-07-15T07:18:17.224696+00:00"
    },
    "reconciliation": {
      "by": "claude",
      "at": "2026-07-15T07:18:42.863864+00:00"
    }
  },
  "pv": {
    "ran_at": "2026-07-15T07:18:17.322445+00:00",
    "missing_count": 2
  },
  "authors": {
    "brief": "claude",
    "half_a": "deepseek",
    "half_b": "claude",
    "reconciliation": "claude"
  }
}
```

## pv_report.json
```json
{
  "ran_at": "2026-07-15T07:18:17.322445+00:00",
  "verified": [
    "half_a: core/comm/bus.py",
    "half_a: core/comm/dispatcher.py",
    "half_a: core/comm/runner_lock.py",
    "half_a: scripts/bifrost_runner_deepseek.py",
    "half_a: scripts/bifrost_wake.py",
    "half_a: scripts/hooks/claude_stop.py",
    "half_b: core/comm/incarnation.py",
    "half_b: core/comm/runner_lock.py:39",
    "half_b: core/comm/wake_seat.py:219",
    "half_b: scripts/bifrost_runner_deepseek.py",
    "half_b: scripts/bifrost_wake.py",
    "half_b: scripts/hooks/claude_stop.py:220"
  ],
  "missing": [
    "half_a: docs/runbooks/m1-daemon.md",
    "half_a: scripts/bifrost_daemon.py"
  ]
}
```
