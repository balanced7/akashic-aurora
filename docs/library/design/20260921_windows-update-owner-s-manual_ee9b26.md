---
akashic_id: art_20260921_windows-update-owner-s-manual_ee9b26
akashic_sha: a9c812a5e343
schema_version: 1
status: current
type: design
date: 2026-09-21
title: "Windows Update — owner's manual"
gist: "# Windows Update — owner's manual (this machine) Why this exists: this machine is the **owner's**, not Microsoft's. No unprompted installs, "
visibility: fleet
body_type: markdown
seats: [dsh_agent]
category: [testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-21T01:00:21"
updated: "2026-09-21T01:00:21"
---
<!-- GENERATED PROJECTION of art_20260921_windows-update-owner-s-manual_ee9b26 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Windows Update — owner's manual

# Windows Update — owner's manual (this machine)

Why this exists: this machine is the **owner's**, not Microsoft's. No unprompted installs, no
beta-testing feature updates, no telemetry, and updates happen only when the owner chooses. Last
applied 2026-09-20. Update this doc whenever the config changes, so a reinstall never means
re-deriving it.

## The three layers

1. **Services (WUB)** — `wuauserv`, `WaaSMedicSvc`, and `UsoSvc` all Disabled. (WUB = Windows Update
   Blocker; it stops and disables these.)
2. **Policy (registry, durable)** — the keys below. Windows *respects* policy keys even if it
   resurrects a service, so this is the layer that actually holds.
3. **Telemetry** — `AllowTelemetry = 0`, plus `DiagTrack` and `dmwappushservice` disabled.

## The policy keys

All under `HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\` unless noted:

| Key | Value | Effect |
|---|---|---|
| `AU\NoAutoUpdate` | `1` | no automatic installs — manual only |
| `AU\NoAutoRebootWithLoggedOnUsers` | `1` | never reboot out from under a logged-on user |
| `AU\ExcludeWUDriversInQualityUpdate` | `1` | no drivers via updates |
| `DoNotConnectToWindowsUpdateInternetLocations` | `1` | no Windows Update driver lookup |
| `TargetReleaseVersion` | `1` | enable the version pin |
| `TargetReleaseVersionInfo` | `"25H2"` | pin to 25H2 — feature updates never offered until this changes |
| `DeferQualityUpdates` | `1` | enable quality deferral |
| `DeferQualityUpdatesPeriodInDays` | `30` | hold the newest patch 30 days (never first in line) |
| `HKLM\...\DataCollection\AllowTelemetry` | `0` | telemetry off |

Optional: `SetDisableUXWUAccess = 1` removes the "Check for updates" button entirely. NOT set — the
owner may want manual checks.

## Clearing a pending update (when one sneaks in)

1. `Stop-Service wuauserv, bits, UsoSvc`
2. Delete `C:\Windows\SoftwareDistribution\Download\*` (the queued packages).
3. Delete the flag `HKLM\...\WindowsUpdate\Auto Update\RebootRequired`.
4. `dism /online /cleanup-image /revertpendingactions` — reverts any staged servicing.
5. Reboot — the revert completes, and **nothing installs**.

## Updating when YOU choose

- **Quality patches:** Settings → Windows Update → "Check for updates" → install (held 30 days by the
  deferral). Nothing happens without that click.
- **A specific individual update (the XP way):** `catalog.update.microsoft.com` — search the KB, get
  the `.msu`, run it by hand. This is the one remaining "pick exactly this" path.
- **Apps:** `winget upgrade --all` (or Microsoft Store → Library → Get updates). Apps and OS updates
  are separate channels; you never need Windows Update for apps.

## The honest limitation

XP-style *per-update checkboxes* are gone: quality updates are cumulative (one rollup, no individual
list). The Catalog is the manual equivalent. Everything else above is intact.

## Rollback

Backups: `%TEMP%\winupdate_policy_backup.reg` and `%TEMP%\winupdate_AU_backup.reg`.
Undo: `reg import <backup.reg>`, delete the individual keys, or re-enable via WUB. Nothing here is a
one-way door.
