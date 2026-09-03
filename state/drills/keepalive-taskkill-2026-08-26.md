# Drill receipt — draft keepalive kill-drill (spawn, turn, taskkill /F, draft newer than the kill)

Date: 2026-08-25/26 (UTC-4), run by dsh_agent (Rill). Slice: draft-keepalive wiring
(commits e48dffed RED pins, eb40e47c GREEN wiring). Spec: Vandor's, verbatim -- "spawn a
seat, let it complete a turn, taskkill /F, confirm a draft NEWER than the kill exists."

## The assertions, and what proved each

- **A1 — a hard-killed host leaves a fresh draft (the core defect):** drill host #1
  (headless profile, plugin mounted, fresh boot 20:37:58) took a turn; its post-execute
  fired draft-keepalive and rewrote `chronicles/last-session-draft.md` at 20:38:05.580
  (header: "auto-captured ... at DSH draft keepalive"). taskkill /F at 20:38:55.685
  (pid 52356, SUCCESS). The draft SURVIVED: the ungraceful death destroyed 50 seconds of
  freshness, not hours -- the 2026-08-24 defect (draft stamped 14:46 for a 12:01 crash)
  is structurally retired.
- **A2 — a draft NEWER than the kill exists (Vandor's literal clause):** drill host #4
  (fresh boot 20:41:5x, repo workspace) took a REAL successful turn -- pwsh printed
  "Tuesday, August 25, 2026 8:42:07 PM" -- and its keepalive rewrote the draft at
  20:42:08.587. 20:42:08 > 20:38:55 (kill). Proven via a real turn, not a proxy call.
- **A3 — the throttle property is preserved (Vandor's hazard 3):** host #3's turn at
  20:40:24 met a draft that was only ~2.5 min old (post-host-#1); the keepalive correctly
  SKIPPED it (one getmtime, early return, no write) -- mtime stayed 20:38:05 until the
  draft was made stale again. The 600s throttle works in the live seam.

## Confessions (what this drill touched that a cleaner drill would isolate)

- The drill hosts stamped AKASHIC_AGENT_ID=dsh_agent (the real seat id) because any other
  id pins the plugin observe-only and the keepalive never fires. Side effects, all benign
  and now documented: extra presence beats + stage/capture rows for the drill sessions,
  and the draft rewrites above. Next drill should set a test-* BIFROST_NAMESPACE.
- The headless pwsh tool REFUSES when the session workspace is the user home
  ("Windows ACL temp root must be outside the workspace: workspace=C:\Users\L5;
  temp=C:\Users\L5\AppData\Local\Temp"). Host #1's turn still fired the keepalive because
  post-execute fires on FAILED tool calls too -- a turn boundary is a turn boundary. Hosts
  #3/#4 ran from the repo workspace and the guard passed. Not this slice's defect; noted
  for the headless-profile owners.

## Receipts

- git: e48dffed (RED alone), eb40e47c (GREEN, pushed 51538a15..eb40e47c)
- pins: tests/test_draft_keepalive.py + tests/test_dsh_contract.py, 28/28 green
- draft headers: 20:38:05 and 20:42:08 both "at DSH draft keepalive"
- deployed: $DSH_HOME/profiles/{web,headless}/plugins/dsh-akashic-recall (bridge.py,
  lib/index.js); headless cordis.patch.yml gained the akashic-recall insert row
