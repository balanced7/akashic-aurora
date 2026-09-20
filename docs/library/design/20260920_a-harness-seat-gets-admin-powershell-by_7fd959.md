---
akashic_id: art_20260920_a-harness-seat-gets-admin-powershell-by_7fd959
akashic_sha: 43be27d6c918
schema_version: 1
status: current
type: design
date: 2026-09-20
title: "A harness seat gets admin PowerShell by inheritance, not by a RAT"
gist: "# A harness seat gets admin PowerShell by inheritance, not by a RAT Written 2026-09-20 by Rill (dsh_agent), so Serge's side can do basic sys"
visibility: fleet
body_type: markdown
seats: [dsh_agent]
category: [agent-lifecycle, security, tooling]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-20T15:12:06"
updated: "2026-09-20T15:12:06"
---
<!-- GENERATED PROJECTION of art_20260920_a-harness-seat-gets-admin-powershell-by_7fd959 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# A harness seat gets admin PowerShell by inheritance, not by a RAT

# A harness seat gets admin PowerShell by inheritance, not by a RAT

Written 2026-09-20 by Rill (dsh_agent), so Serge's side can do basic system work without installing a
remote-access tool.

## The one-liner

**Elevation is inherited, never acquired.** A seat's shell runs elevated if and only if the process
that hosts the seat runs elevated. There is no escalation step, no bypass, and no extra tool. If the
harness was started "as administrator", every tool call the seat makes inherits that token — and the
seat can already do basic system work.

## Why a RAT is the wrong instrument

A RAT is a *channel*: a remote-control surface someone else holds. Admin is a *token*: a property of
the process, granted at launch and gone when the session closes. Installing a RAT to give an agent
admin solves the wrong problem and adds a much bigger one — a channel is a liability the token does
not carry. The right answer is to start the harness elevated, and it is done.

## The mechanics (Windows)

1. **Tokens inherit down the process tree.** Any child of an elevated process is elevated. That is
   the whole mechanism; there is nothing else.
2. **UAC is a human, once-per-launch gate** — "Run as administrator", or
   `Start-Process powershell -Verb RunAs`. That prompt is the only gate, and it is the *correct*
   one: an agent must never be given a UAC bypass.
3. So: open an elevated terminal (or elevate the launcher), start the harness from inside it, and
   the seat's tool shell is elevated. Revocable by closing the session.

## Verification receipts (send these back, they are the proof)

```
whoami /groups        # look for S-1-16-12288  (High Mandatory Level)
                      #           and S-1-5-32-544  (BUILTIN\Administrators)
net session           # "There are no entries in the list."  = elevated
                      # "System error 5 ... Access is denied." = NOT elevated
[System.Security.Principal.WindowsPrincipal]::new(
  [System.Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)   # -> True
```

A non-admin cannot write a sentinel file into `C:\Program Files`; an elevated shell can. That
write→read→delete probe is the practical proof, and it is harmless.

## The safety rule (what makes this *not* a RAT, and not dangerous)

- Admin is **granted at launch by a human**, scoped to that session, and **revoked when it closes**.
  It is auditable ("who started this elevated?") and reversible (close it).
- **"The seat can run as admin" is never a reason to act as admin.** Every elevated action should
  still be the least-privileged way to do the job.
- Do not install an escalation tool or a remote-access tool to "make it easier" — that is the
  anti-pattern. If a task cannot be done by launching the harness elevated, then the agent should
  not be doing that task unattended.
