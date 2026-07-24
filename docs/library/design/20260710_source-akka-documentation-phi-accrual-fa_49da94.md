---
akashic_id: art_20260710_source-akka-documentation-phi-accrual-fa_49da94
akashic_sha: b94063364a4b
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Akka documentation, \"Phi Accrual Failure Detector\""
gist: "# SOURCE: Akka documentation, \"Phi Accrual Failure Detector\" # URL: https://doc.akka.io/libraries/akka-core/current/typed/failure-detector.h"
tenant: solo
visibility: fleet
seats: []
category: [testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:31:12"
updated: "2026-07-10T23:31:12"
---
<!-- GENERATED PROJECTION of art_20260710_source-akka-documentation-phi-accrual-fa_49da94 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Akka documentation, "Phi Accrual Failure Detector"

# SOURCE: Akka documentation, "Phi Accrual Failure Detector"
# URL: https://doc.akka.io/libraries/akka-core/current/typed/failure-detector.html
# Implements: Hayashibara, Defago, Yared, Katayama, "The phi accrual failure detector"
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Core Mechanism

Remote DeathWatch employs heartbeat messages and failure detection to identify network failures and JVM crashes, implementing "The Phi Accrual Failure Detector" algorithm by Hayashibara et al.

## Phi Calculation

phi = -log10(1 - F(timeSinceLastHeartbeat))

where F is the cumulative distribution function of a normal distribution, calculated from mean and standard deviation of historical heartbeat inter-arrival times.

Rather than binary yes/no failure determination, the accrual approach returns a phi value indicating the likelihood a node is down, decoupling monitoring from interpretation.

## Heartbeat Behavior

- Default frequency: one heartbeat per second (configurable)
- Transmission pattern: request/reply handshake
- Replies feed the failure detector algorithm
- Phi scales dynamically based on current network conditions

## Threshold Configuration

The configurable threshold parameter (default 8) determines failure sensitivity:
- Low threshold: faster crash detection but higher false positive rate
- High threshold: fewer false positives but slower detection
- Cloud environments: recommend 12 (e.g., Amazon EC2) to account for transient network issues

## Acceptable Heartbeat Pause

The acceptable-heartbeat-pause parameter manages abnormalities (garbage collection pauses, transient network failures). It adjusts the phi curve upward, providing protective margin. Tunable per environment.

## Logging Indicators

- "Marking node(s) as UNREACHABLE" when failure detected; "REACHABLE" upon recovery
- Warning when heartbeat interval exceeds 2/3 of acceptable pause
- "Scheduled sending of heartbeat was delayed" indicates the SENDER side is delayed (root cause investigation needed)
- Frequent UNREACHABLE/REACHABLE cycling suggests acceptable-heartbeat-pause needs increasing
