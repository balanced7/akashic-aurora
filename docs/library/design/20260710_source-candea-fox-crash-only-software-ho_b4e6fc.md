---
akashic_id: art_20260710_source-candea-fox-crash-only-software-ho_b4e6fc
akashic_sha: e4e134bf703d
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Candea & Fox, \"Crash-Only Software\", HotOS IX (2003)"
gist: "# SOURCE: Candea & Fox, \"Crash-Only Software\", HotOS IX (2003) # URL: https://research.cs.wisc.edu/areas/os/ReadingGroup/os-old/Papers/HotOS"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:30:40"
updated: "2026-07-10T23:30:40"
---
<!-- GENERATED PROJECTION of art_20260710_source-candea-fox-crash-only-software-ho_b4e6fc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Candea & Fox, "Crash-Only Software", HotOS IX (2003)

# SOURCE: Candea & Fox, "Crash-Only Software", HotOS IX (2003)
# URL: https://research.cs.wisc.edu/areas/os/ReadingGroup/os-old/Papers/HotOSIX/Candea-CrashOnlySoftware.pdf
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Core Definition

A crash-only system is one designed to recover from crashes as its primary failure handling mechanism. The paper establishes that crash-only equals crash-safe plus fast recovery, meaning systems that can survive arbitrary crashes and restart quickly achieve the same reliability as traditional error-handling approaches but with architectural simplicity.

## Crash-Only Properties

- **Statelessness in components:** application logic maintains minimal or no persistent state between operations
- **External state storage:** all necessary state resides in durable storage (databases, logs) accessible after recovery
- **Fast recovery cycles:** systems restart and resume operations quickly enough that crashes function as a transparent recovery mechanism
- **No graceful shutdown paths:** components are designed to handle abrupt termination identically to normal operation

## Design Rules for Crash-Only Components

1. **State Externalization:** "All state that must survive crashes must be stored outside the component," ensuring no critical data exists only in volatile memory.

2. **Lease-Based Resource Management:** resources held by components include expiration times. If a component crashes, leases automatically expire, preventing indefinite resource locks. Other components can reclaim expired resources without explicit cleanup coordination.

3. **Retryable Requests:** all external operations must be idempotent or safely retryable. When a component restarts, it may reexecute requests without causing inconsistency.

## Microreboot Concept

Microreboots: rapidly restarting individual software components rather than entire systems. This leverages crash-only design by allowing:
- Isolation of failures to specific components
- Rapid recovery without affecting other system parts
- Testing of recovery paths in production environments

## Caveats and Trade-offs

- **State externalization overhead:** frequent writes to durable storage increase latency and I/O costs
- **Lease complexity:** determining appropriate lease durations requires careful tuning; expired leases may trigger cascading restarts
- **Application redesign required:** existing systems built around error handling must be substantially refactored
- **Predictability loss:** crash-based recovery introduces variability in operation timing
- **Debugging difficulty:** crashes-as-recovery obscure root causes during development

## Structural Note

Crash-only design fundamentally shifts how systems handle faults -- from preventing failures to designing recovery as the primary operational path. This requires developers to externalize dependencies and design all operations as safely repeatable.
