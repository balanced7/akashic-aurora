---
akashic_id: art_20260710_source-john-regehr-independence-in-n-ver_ed7891
akashic_sha: e6c4bd83a8b5
status: draft
type: design
date: 2026-07-10
title: "SOURCE: John Regehr, \"Independence in N-Version Programming\" (blog.regehr.org/archives/303)"
gist: "# SOURCE: John Regehr, \"Independence in N-Version Programming\" (blog.regehr.org/archives/303) # Context for: Knight & Leveson (1986), \"An Ex"
tenant: solo
visibility: fleet
seats: []
category: []
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-10T23:31:28"
updated: "2026-07-10T23:31:28"
---
<!-- GENERATED PROJECTION of art_20260710_source-john-regehr-independence-in-n-ver_ed7891 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: John Regehr, "Independence in N-Version Programming" (blog.regehr.org/archives/303)

# SOURCE: John Regehr, "Independence in N-Version Programming" (blog.regehr.org/archives/303)
# Context for: Knight & Leveson (1986), "An Experimental Evaluation of the Assumption of
# Independence in Multiversion Programming"
# Neutral extraction (claude, 2026-07-10). LOCAL READING COPY -- gitignored, never committed.

## Knight-Leveson Study (1986)

The referenced work demonstrated that a core assumption underlying N-version programming -- that faults occur independently across implementations -- "can easily be unjustified." (The Knight-Leveson experiment: 27 versions written independently from one specification at two universities, subjected to one million tests; the number of tests in which more than one program failed was substantially more than expected under independence. Correlation arises because translating a specification into code creates correlated difficulty: the hard parts of the SPEC are hard for everyone.)

## N-Version Programming Concept

N-version programming: create N independent implementations of the same specification, run them in parallel, vote on the output. Aims to reduce software bug impact through redundancy.

## The Author's Compiler-Testing Counter-Evidence

Three years of randomized differential testing on C compilers (generating random programs, comparing outputs across compilers) identified approximately 300 compiler bugs, and: "we have never seen a case where even two independent compilers have produced the same wrong result for a test case."

## Independence Analysis

The author attributes compiler fault independence to implementation differences at the optimizer level: GCC operates on Gimple/RTL while LLVM uses LLVM IR. The bugs discovered are "typically deep inside the optimizer" rather than in specification interpretation.

Implication as stated: correlation tracks SHARED STRUCTURE. Implementations sharing a spec correlate at spec-interpretation faults; implementations diverging deeply in internal structure (different IRs, different algorithms) can exhibit effectively independent faults in those internals.

## Acknowledged Limitations

Untested areas where correlated failures might exist: variadic functions, floating-point rounding modes, and the volatile qualifier (where previous testing found consistent bugs across all compilers). For C++, the EDG frontend's widespread use presents potential non-independence risk, though sufficient non-EDG implementations may provide adequate cross-checking.
