---
akashic_id: art_20260710_source-hypothesis-documentation-stateful_ea9daa
akashic_sha: 7f240e31dc5a
status: draft
type: design
date: 2026-07-10
title: "SOURCE: Hypothesis documentation, \"Stateful tests\" (RuleBasedStateMachine)"
gist: "# SOURCE: Hypothesis documentation, \"Stateful tests\" (RuleBasedStateMachine) # URL: https://hypothesis.readthedocs.io/en/latest/stateful.htm"
tenant: solo
visibility: fleet
seats: []
category: [testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:32:07"
updated: "2026-07-10T23:32:07"
---
<!-- GENERATED PROJECTION of art_20260710_source-hypothesis-documentation-stateful_ea9daa -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: Hypothesis documentation, "Stateful tests" (RuleBasedStateMachine)

# SOURCE: Hypothesis documentation, "Stateful tests" (RuleBasedStateMachine)
# URL: https://hypothesis.readthedocs.io/en/latest/stateful.html
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Core Concept

Stateful testing generates entire test SEQUENCES rather than individual data points, combining primitive actions into sequences to discover failures through state-machine exploration.

## RuleBasedStateMachine Architecture

Rules are methods decorated with @rule() representing actions the system can perform. Unlike @given tests (independent), rules chain together -- multiple rule invocations within a single test run interact and share state.

Constraints: at least one rule per machine; one rule per function; rules cannot access external fixtures or pytest parametrize -- provide values via strategies (e.g., sampled_from()).

## Bundles

Bundles enable data flow between rules -- a named collection of generated values reusable across operations:
- target=a_bundle: adds a rule's return value to the bundle
- an_argument=a_bundle: draws a value from that bundle
- consumes(a_bundle): draws AND removes a value
Useful for establishing a universe of test values multiple rules operate on, encouraging reuse of keys/values across operations.

## Initialize Rules

@initialize() rules execute exactly once before any normal rules; multiple initializes execute in arbitrary order per run. Commonly populate bundles or set up state.

## Preconditions

@precondition(fn) filters which rules can execute based on current machine state (fn evaluated against the instance). Advantage over assume(): Hypothesis filters inapplicable rules BEFORE execution, generating more useful step sequences. Limitation: preconditions cannot access bundles; use instance variables.

## Invariants

@invariant() methods execute after EVERY step, ensuring properties hold throughout execution. Can carry preconditions; cannot access bundles (store state on the instance).

## Configuration

Settings on the TestCase class: max_examples (number of test cases), stateful_step_count (rule invocations per case).
  MachineName.TestCase.settings = settings(max_examples=50, stateful_step_count=100)

## Failure Output

On failure, Hypothesis produces a MINIMAL reproduction program (shrunk sequence of rule invocations) resembling executable Python:
  state = MyStateMachine()
  var1 = state.rule1(...)
  var2 = state.rule2(var1, ...)
  state.teardown()

## Integration

Extract a unittest TestCase: TestX = MyMachine.TestCase (works with standard runners); or run_state_machine_as_test() for manual invocation.
