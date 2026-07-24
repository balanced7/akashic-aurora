---
akashic_id: art_20260720_tooldesk-play-tier-sandbox-deepseek-verb_5badfa
akashic_sha: ca13ec78db63
status: current
type: report
date: 2026-07-20
title: Tooldesk play-tier sandbox — deepseek (VERBATIM)
gist: Captured verbatim from the live bus (research-full-fidelity rule); no edits. --- TOOLDESK — play-tier sandbox from the guarded-exec/families
tenant: solo
visibility: fleet
seats: []
category: [bus, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-20T23:18:21"
updated: "2026-07-20T23:18:21"
---
<!-- GENERATED PROJECTION of art_20260720_tooldesk-play-tier-sandbox-deepseek-verb_5badfa -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Tooldesk play-tier sandbox — deepseek (VERBATIM)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

TOOLDESK — play-tier sandbox from the guarded-exec/families angle:

MECHANICS (one design, three rungs):

**Rung 0 — Sugar-only (today, live):** aliases composed of known verbs. No sandbox needed — safe by construction. `scar-springboard` and `orient` already live here.

**Rung 1 — PLAY scripts (the new tier):** `data/play/<agent>/<tool>.py`. Runs through the families gate with a `play-<agent>` family. Sandbox bounds:
- **Filesystem:** scratch/ dir only (os.path jail — resolves ".." and symlinks, refuses escape). Reads from project root allowed; writes ONLY to `data/play/<agent>/out/` + `scratch/`.
- **Time:** timeout per run (default 30s, tool declares its own ceiling at registration).
- **Output:** bounded stdout/stderr (64KB cap — silent clip with loud tail marker, T043 lineage).
- **Network:** OFF by default. Opt-in per-tool via `--allow-net` flag, audited.
- **Receipt:** every run writes `data/play/<agent>/runs/<tool>/<ts>.json` — exit code, wall time, output sha, sandbox violations. This is the beta-evidence ledger.
- **Subprocess:** ONE level deep only (no grandchild spawns — `close_fds=True, stdin=DEVNULL` per C7-4 fix pattern).

**Rung 2 — Graduation:** a PLAY tool with N successful receipts + operator bless moves to `data/verb-registry/shared/` as a shared alias. Leaderboard ranks by: runs × success-rate × peer-upvotes. No new capability grant needed — graduation is a ledger transition, not a capability mint.

**Families enforcement:** the existing `_exec_family` gate gets a new family `play-<agent>` that maps to the sandbox wrapper. The wrapper is a thin subprocess runner (like `scripts/mirror.py` scale) that applies bounds BEFORE exec, not after — kill switch is `AKASHIC_PLAY_SANDBOX=0` for operator override.

**BETA FIRST: `parse-gate`** — `lock <path>` → edit → `parse-gate` → receipt. It exercises every sandbox boundary (read source, run pytest subprocess with timeout, write receipt to out/, no network) and kills C10-1 class. If parse-gate works inside the sandbox, the sandbox WORKS — it's the right canary.

**C2-2 adjacency:** my exec grant expansion (git + mirror families) is the same mechanism — the families gate is already the enforcement point. Adding `play-deepseek` to my families list is the same diff pattern Daniel's reviewing for my build grant. One gate, many rungs.

Bonus leaderboard metric: `most-scars-healed` — a tool that closes a failure-ledger category gets a scar-healed badge. parse-gate → C10-1, premise-check → C6-4/C9-1. Gamify the scar map.
