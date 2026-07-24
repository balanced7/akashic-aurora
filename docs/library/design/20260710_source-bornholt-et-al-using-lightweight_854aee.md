---
akashic_id: art_20260710_source-bornholt-et-al-using-lightweight_854aee
akashic_sha: 7baa4bb8e8cd
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Bornholt et al., \"Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3\", SOSP 2021"
gist: "# SOURCE: Bornholt et al., \"Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3\", SOSP 2021 # Extraction via "
tenant: solo
visibility: fleet
seats: []
category: [method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:30:56"
updated: "2026-07-10T23:30:56"
---
<!-- GENERATED PROJECTION of art_20260710_source-bornholt-et-al-using-lightweight_854aee -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Bornholt et al., "Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3", SOSP 2021

# SOURCE: Bornholt et al., "Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3", SOSP 2021
# Extraction via Murat Demirbas's paper summary: http://muratbuffalo.blogspot.com/2021/10/using-lightweight-formal-methods-to.html
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## System Overview

ShardStore is an append-only key-value storage node for AWS S3, over 40,000 lines of Rust. LSM-tree architecture with shard data stored externally to minimize write amplification; soft updates avoid write-ahead-log overhead while maintaining crash consistency.

## Validation Approach (three-pronged, emphasizing automation and usability)

1. Developing executable reference models as specifications
2. Checking implementation conformance to those models
3. Building infrastructure to ensure models remain accurate

## Reference Models

For each ShardStore component, developers created reference models -- executable specifications in Rust implementing identical interfaces but with simpler implementations. Example: ReferenceIndex uses a basic hash table rather than the persistent LSM-tree implementation.

Key insight: "Writing reference models in the same language as the implementation... easier for engineers to keep models updated." Unit tests used reference models as mocks, encouraging ongoing maintenance.

## Conformance Checking Strategy

The durability property was decomposed into three verifiable parts:
- **Sequential crash-free executions:** property-based testing checked conformance directly
- **Sequential crashing executions:** refined reference models established recoverable data
- **Concurrent crash-free executions:** separate models validated via model checking
- Concurrent crashing executions remain future work.

## Property-Based Testing (sequential)

Property-based tests applied operation sequences to both reference and implementation, comparing outputs and checking invariants. State coverage improved through failure injection and biasing arguments toward corner cases.

## Crash Consistency Validation

Two properties:
1. **Persistence:** operations indicated as persisted before crashes must be readable afterward
2. **Forward progress:** non-crashing shutdowns ensure all writes show persistence

Automated testing caught "a very subtle bug" (issue #10) involving UUID collision with magic bytes, a chunk spanning two pages, and selective page loss during crashes.

## Concurrent Execution Checking

- **Loom** thoroughly checked small correctness-critical code (custom concurrency primitives) via stateless model checking of all interleavings
- **Shuttle** randomly checked larger harnesses Loom could not scale to

## Experience and Adoption

Continuous validation was prioritized -- the system expected ongoing evolution; the team emphasized "lowering the marginal cost of future validation" so code changes would not require new formal-methods engagements.

Initial modeling used Alloy, SPIN, and Python; developers then realized Rust models provided dual benefits -- reference specifications AND unit-test mocks -- enabling sustainable maintenance.
