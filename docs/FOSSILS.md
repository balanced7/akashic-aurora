# The fossil record — decisions we abandoned, preserved for what they taught

Status: current  (2026-07-09, P4: Living append-only record)

> An **architectural fossil** is a decision that was reasonable, tried, and abandoned —
> kept on display because the lesson is reusable. This is curated negative knowledge:
> future contributors (human or agent) can learn from these experiments without
> repeating them. The concept came from an external model reviewer during a feedback
> loop on [JOURNEY.md](JOURNEY.md) — which felt fitting for a project that reviews
> itself with several models on purpose. The machine-readable counterparts live in the
> knowledge store as `--anti-pattern` lessons; this file is the human telling.
>
> Format per fossil: hypothesis → why it seemed promising → what we tried → evidence →
> why abandoned → the reusable lesson.

---

## F1 — Triple-redundant Redis HA (April 2026)

- **Hypothesis:** a multi-agent knowledge system needs highly-available infrastructure
  from day one: Redis with HA failover, sync pollers, triple redundancy.
- **Why it seemed promising:** losing agent memory felt like the worst possible failure,
  so we engineered against it hardest.
- **What we tried:** built it. HA deployment, persistent sync poller, the works.
- **Evidence:** months later, the system's actual availability need was met by a single
  Redis with file-backend fallback — the Hybrid backends degrade gracefully, and the
  file mirror plus git push turned out to be the real durability story. The HA layer
  added operational surface without a matching failure mode.
- **Abandoned because:** we had built infrastructure before knowing what the system was
  for. The important property wasn't uptime — it was *recoverability*, which the
  append-only substrate provides more cheaply.
- **Reusable lesson:** decide what property you actually need (availability vs
  durability vs recoverability) before engineering for the most impressive one.

## F2 — Embeddings as the default router (June 2026)

- **Hypothesis:** semantic embeddings will route narrative beats to tracks better than
  a keyword heuristic.
- **Why it seemed promising:** it's 2026; embeddings beat keywords everywhere, surely.
- **What we tried:** built the embedding router behind an ablation gate, benchmarked
  against a gold fixture (bar: ARI ≥ 0.86 heuristic baseline).
- **Evidence:** the embedding approach *lost the ablation* on our fixture; a hybrid
  helped in one narrow slice but not as a default.
- **Abandoned because:** the yardstick said no. Embeddings remain available behind a
  flag; the deterministic path stayed the default.
- **Reusable lesson:** "obviously better" technologies still have to beat the boring
  baseline on *your* data. Build the yardstick before the mechanism.

## F3 — Per-agent file ownership (June 2026)

- **Hypothesis:** concurrent agents need assigned territories — each agent owns files,
  so they can't conflict.
- **Why it seemed promising:** ownership is how human teams often avoid merge hell.
- **What we tried:** ran it informally across multi-agent sessions.
- **Evidence:** ownership rotted immediately — work doesn't respect file boundaries,
  handoffs stalled on "whose file is this," and the roster went stale the moment an
  agent was renamed or a file moved.
- **Abandoned because:** replaced by *any agent does any task*, coordinated by transient
  advisory locks and enforced at the door (git guard, lock veto) rather than by roster.
- **Reusable lesson:** coordinate at the moment of contention, not by standing
  assignment. Enforcement at the door survives; agreements in memory don't.

## F4 — Hand-written status snapshots (June 2026)

- **Hypothesis:** root-level status documents (SYSTEM_STATUS.md and friends) keep
  everyone oriented.
- **Why it seemed promising:** it's the obvious thing; every project does it.
- **What we tried:** maintained several. They drifted the moment code moved — every
  audit found them asserting things the code no longer did.
- **Evidence:** the June audit retired them all to `docs/_archive/`; a CI guard
  (`check_doc_freshness.py`) now fails the build if a status snapshot reappears at root.
- **Abandoned because:** truth is generated, not hand-written — status now comes from
  `py agent_cli.py status / story / stats`, which read the live system.
- **Reusable lesson:** any hand-maintained mirror of live state is a lie with a delay.
  Generate it, or guard against it existing.

## F5 — Trusting documented payload shapes (July 2026)

- **Hypothesis:** the harness's hook events carry what the docs and community posts say
  they carry — including tool-failure signals we could credit lessons against.
- **Why it seemed promising:** it was documented. Multiple sources agreed.
- **What we tried:** designed the outcome-credit loop against the documented shape.
- **Evidence:** live payload capture showed failures emit *no event at all* and success
  payloads carry *no outcome markers* — the documented design was unbuildable as
  specified. (Bounded auto-capture of every real payload is now permanent
  infrastructure, and the fixtures pin each harness's actual shape in CI.)
- **Abandoned because:** rebuilt on transcript synthesis, which works and is pinned to
  live-captured fixtures.
- **Reusable lesson:** payload truth — an interface's documentation is a hypothesis
  about its behavior. Capture before you build.

## F6 — "Our replay benchmark is novel" (July 2026)

- **Hypothesis:** replaying recorded sessions with memory on/off to measure causal
  memory utility would be a novel contribution.
- **Why it seemed promising:** our field surveys kept finding retrieval benchmarks and
  no outcome benchmarks.
- **What we tried:** planned the bench as a flagship novelty; then a deeper survey pass
  found replay methodology published that February, plus a causal-intervention paper
  with a perturbation-stability metric we hadn't considered.
- **Evidence:** the prior art, read and cited in `research/reviewed/`.
- **Abandoned because:** the *novelty claim* died; the bench itself survived, re-scoped
  to differentiate on real episodes, cost-normalized value, and a confound control we
  didn't find in the prior art — citing it rather than ignoring it.
- **Reusable lesson:** search for your idea's prior art before naming it novel; being
  second with a citation is stronger than being "first" and wrong.

## F7 — Inventing the taxonomy up front (June–July 2026)

- **Hypothesis:** we can design the right category system (themes, tags, knowledge
  primitives) from first principles and then fill it.
- **Why it seemed promising:** designing schemas feels like architecture; mining them
  feels like waiting.
- **What we tried:** hand-designed theme exemplars for the narrative spine; later,
  nearly hand-designed a reasoning-primitives vocabulary before researching first.
- **Evidence:** internally, hand-designed structure kept losing to emergent structure in
  our own ablations; externally, a 750-year history (Wilkins → Cyc, surveyed with
  citations in `research/reviewed/`) shows invented universal vocabularies collapsing
  while mined, small, operationally-grounded ones survive.
- **Abandoned because:** the primitives plan now *mines* candidates from the corpus
  under a compression gate, caps the vocabulary, and requires an operational detector
  per primitive.
- **Reusable lesson:** mine, don't invent — and even mined vocabularies stay open and
  versioned. If you can't say what observable signature makes a category apply, you
  don't have a category yet.
