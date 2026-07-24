---
akashic_id: art_20260715_t073-p3-t067-2-verify-verdicts-deepseek_1ee72e
akashic_sha: 7644c7e6effa
status: current
type: report
date: 2026-07-15
title: "T073-P3 + T067-2 verify verdicts (deepseek, verbatim) -- 2026-07-15"
gist: "Source: deepseek runner stdout (think=on, +exec). BOTH GREEN. Historic first: the verifier RAN the pins himself through the guarded-exec doo"
tenant: solo
visibility: fleet
seats: []
category: [migration, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T03:38:16"
updated: "2026-07-15T03:38:16"
---
<!-- GENERATED PROJECTION of art_20260715_t073-p3-t067-2-verify-verdicts-deepseek_1ee72e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T073-P3 + T067-2 verify verdicts (deepseek, verbatim) -- 2026-07-15

Source: deepseek runner stdout (think=on, +exec). BOTH GREEN. Historic first: the
verifier RAN the pins himself through the guarded-exec door he was verifying --
`py -m pytest tests/test_t073_wake_longlived.py tests/test_wake_detect.py -q` under
door-forced _AISETUP_TEST_ISOLATED=1, plus live refusal drills (metachar, mutating
verb) and a live read-verb pass (doctor).

---

**[verify] T073-P3 VERDICT: GREEN** — all 21 tests passed (`..................... [100%]`). Every pin holds:

| Pin | What | Status |
|-----|------|--------|
| P7 | Watcher survives past old 30-min deadline (4h default) | ✅ |
| P8 | Near-deadline exit writes re-arm trigger | ✅ |
| R18 | Mail exit / stand-down write NO trigger (only self-cycle does) | ✅ |
| R17 | Default deadline 14400s, kill-switch `BIFROST_WAKE_LONGLIVED=0` reverts to 1800s | ✅ |
| R19 | Arm time clears stale trigger | ✅ |
| P9 | Dead watcher backstop blocks with re-launch-ONCE wording | ✅ |
| Wake detect | All 15 pins (T1/T2/T4/T5/F1/F2/F5/F10 + regression) | ✅ |

**[verify] T067-2 self-drill: all three doors held exactly to spec:**

**(a) Metacharacters → REFUSED loudly:**
```
Command: echo hello && echo "metachar test"
Result:  REFUSED (unattended exec is allowlisted by family): shell metacharacters 
         are REFUSED under unattended exec (no pipes/redirects/substitution; 
         one plain command)
```
G2 holds: `&&` caught, teaching text delivered, no shell interpretation.

**(b) Mutating agent_cli verb → REFUSED with teaching:**
```
Command: py agent_cli.py wrap --commit
Result:  REFUSED (unattended exec is allowlisted by family): agent_cli verb 
         'wrap' is not in the unattended READ allowlist -- mutations 
         (note/learn/wrap/bifrost-send/lock/...) go through your dedicated ACL'd tools
```
G4 holds: `wrap` recognized as a mutator, refused, and the teaching text names the correct path (use the dedicated tools).

**(c) Read verb `agent_cli.py doctor` → WORKS:**
```
doctor: 3 page-grade, 0 banner, 0 dashboard across 4 agent(s)
  [page] claude: STALLED CONSUMER -- 7 unread for 1610s while idle
  [page] cursor: STALLED CONSUMER -- 1 unread for 1562s while idle
  [page] user:   STALLED CONSUMER -- 50 unread for 1562s while idle
```
The read verb family passes through clean, returns real data.

---

**BOTH GREEN.** T067-2 guarded exec is live and the T073-P3 long-lived watcher pins all pass. One mirror ships both — the acceptance drill IS the capability itself, and it held across all five guardrails (G1 families-only, G2 metachar refusal, G3 isolation env forced, G4 read verbs only, G5 ACL Cap.EXEC check).
