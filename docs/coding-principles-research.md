# Coding principles research: naming/clarity + cleanup-at-scale

Date: 2026-06-19. Two questions: (1) what did our naming/clarity approach get
right, and how do we make it more potent? (2) how do experts clean up massive
complex projects? Short answer to both: **we've been intuitively practicing the
named, canonical disciplines — and the way to compound the strength is to make
the implicit explicit and then enforce it automatically.**

---

## Part 1 — Naming & clarity

### What we got right (it has formal names)

- **Ubiquitous Language (Domain-Driven Design, Eric Evans).** Using *one*
  vocabulary in conversation and in code, so there's no translation layer between
  "what we mean" and "what the code says." Our relationship-types vocabulary (66
  types) + semantic method names (`append_signal`, `derive_full_context_for_agent_repriming`,
  `record_blocker_preventing_task`) is exactly a ubiquitous language. DDD's whole
  premise: friction comes from translating between domain-speak and code-speak;
  remove the translation and ambiguity collapses. That's the "pays exponentially
  as it grows" intuition you had — it's the documented core benefit.
- **Intention-revealing names (Clean Code, Robert Martin).** A name should answer
  why it exists and what it does; choose **precision over brevity**. We do this
  (`AgentSignalLedger.append_signal`, not `bus.add`).
- **Genus-before-species.** Our rule "name a container after the genus, never a
  species" (`AgentSignalLedger`, not `decision_log`) is a consistency principle
  DDD calls keeping the model coherent — same concept, same word, everywhere.

### How to make it more potent (the additions)

1. **Write the lexicon down.** DDD practitioners maintain a *glossary* of the
   ubiquitous language. We have it implicitly (relationship_types.py + the
   Store/Ledger/AgentMemory definitions + the genus/species rule). Promoting it to
   a single `docs/LEXICON.md` means every term has one authoritative definition —
   new code (and future-you) reaches for the right word by default.
2. **Forbid "names that lie" (linguistic anti-patterns).** The research term for a
   name whose behavior contradicts it. We hit two this session: `Bus` (implied
   real-time push; was append-and-replay) and `success: "True"` (a boolean wearing
   a vocabulary's clothes). Make it a review rule: *a name must match what the
   thing does, or one of them changes.*
3. **Consistency as a checkable property, not a vibe.** "Same concept → same word"
   can be partially automated (flag a new module that reintroduces a retired term,
   or a second class with an existing name — the duplicate-`LearningStore` we
   caught). Even a tiny grep-based check in CI keeps drift out.

---

## Part 2 — Cleaning up massive, complex projects

### What we got right (these are the textbook patterns)

This session's migration *was* the canonical large-refactor playbook, by instinct:

- **Branch by Abstraction.** Introduce an abstraction so old and new coexist, then
  swap underneath. Our `Store`/`Ledger` interfaces are exactly this — `HybridStore`
  let the old Redis path and the new File path live together with zero disruption.
- **Strangler Fig (Martin Fowler).** Build the new around the old and replace piece
  by piece until the old can be decommissioned. We migrated consumers one at a time
  (LearningStore → coordinators → sync coordinator), then retired the originals.
- **Parallel Run.** Run old and new side by side and compare. `HybridStore`'s
  dual-write (File always + Redis best-effort) is a parallel run — both backends
  get every write.
- **Characterization tests first.** Capture current behavior before changing it.
  Our "verify the 9 existing learnings round-trip *before* touching anything" was
  precisely this — a golden-master safety net.
- **Narrow, semantics-preserving, verified steps (Google LSC).** Google's insight:
  large-scale changes should be narrow, pure refactors, behind a strong test net,
  split into independent shards. Our phased approach (each phase shippable +
  verified, no behavior change) matches.

### How to make it more potent (the additions)

1. **Automated guardrails are the exponential lever.** Clarity and clean
   boundaries only *stay* clean if enforced — otherwise entropy creeps back (which
   is how the legacy shell drifted from `core/`). Turn the audit's findings into
   cheap CI/pre-commit checks, e.g.:
   - only `redis_connection.py` may `import redis` directly,
   - no bare `except:` in `core/`,
   - no `sys.path.insert` in library modules,
   - no second class reusing an existing core name.
   Each is a few lines of grep/AST. This is the single biggest multiplier — it
   makes the cleaned state *durable*.
2. **Mikado Method for the big refactors.** For a large change (e.g. the Context
   pillar consolidation), build a dependency graph: try the goal, note what breaks,
   recurse on prerequisites, then execute leaf-first. It prevents the "pulled one
   thread, half the system unraveled" trap. Worth using explicitly for Context
   Phase 1.
3. **Codemods (AST-based) for mechanical sweeps.** Hand-editing is fine for a few
   files; for systemic changes across many (the 12 `sys.path.insert` removals, or a
   future namespace rename) an AST codemod (Python `libcst`/`ast`) does it
   uniformly and safely. We did Bus→Ledger by scripted replace — the same idea,
   leveled up.
4. **Dead-code detection by import graph.** Our "0 importers" sweep that found
   `services/` and the orphaned learning files is a repeatable technique — a small
   script that flags modules nothing imports (minus known entry points) keeps the
   surface honest over time.
5. **Boy-Scout Rule, bounded.** Leave each touched file cleaner than found — but
   *bounded* by the change at hand, so cleanups don't sprawl (we used `spawn_task`
   for out-of-scope fixes; same discipline).

---

## The synthesis for us

Both strengths share one meta-principle: **make the implicit explicit, then let a
machine hold the line.** A written lexicon + enforced naming/boundary checks turn
"we try to name things well" into "the codebase cannot drift," which is what makes
the payoff compound instead of decay. The patterns we used for the migration are
the industry-standard ones; the next level is tooling them so they apply
automatically as the codebase grows.

Concrete cheap wins (when supervised): `docs/LEXICON.md`; a `scripts/check_boundaries.py`
(the four guardrails above) wired into a pre-commit/CI step; an import-graph
dead-code report.

## Sources
- [Clean Code — Meaningful / Intention-Revealing Names](https://harshppatel2880.medium.com/importance-of-intention-revealing-names-in-programming-clean-code-concepts-98108e689b3a)
- [What is Ubiquitous Language? (Agile Alliance)](https://agilealliance.org/glossary/ubiquitous-language/)
- [DDD — The Ubiquitous Language](https://medium.com/@johnboldt_53034/domain-driven-design-the-ubiquitous-language-4f516a385ca4)
- [Domain-Driven Design: Systematic Literature Review](https://arxiv.org/pdf/2310.01905)
- [Strangler Fig, Branch by Abstraction, Parallel Run explained](https://simranchawla.com/unlocking-legacy-systems-strangler-fig-branch-by-abstraction-and-parallel-run-explained/)
- [The Mikado Method (Manning)](https://www.manning.com/books/the-mikado-method)
- [Software Engineering at Google — Large-Scale Changes (Ch. 22)](https://abseil.io/resources/swe-book/html/ch22.html)
- [Large-Scale Automated Refactoring Using ClangMR (Google Research)](https://research.google/pubs/large-scale-automated-refactoring-using-clangmr/)
- [Key points of Refactoring at Scale](https://understandlegacycode.com/blog/key-points-of-refactoring-at-scale/)
- [Codemods for code migration (AST refactoring)](https://medium.com/@vasanthancomrads/codemods-for-code-migration-a-beginners-guide-to-smarter-refactoring-be90d3c60e41)
