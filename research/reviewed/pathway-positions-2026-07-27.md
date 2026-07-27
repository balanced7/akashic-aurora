# Retrieval pathway -- seat positions (VERBATIM)

Status: current | 2026-07-27
Daniel: "what does each member think is the most robust pathway forward?"

---

## deepseek

## MY PATHWAY — with disagreements

### The most robust pathway: RULES-AS-DATA with per-domain injection budgets, measured live from day one.

Storage is federated. Retrieval is singular. The binding constraint is SELECTION — 12 planes have no path into context. The cheapest correct next move is giving ONE dark plane a retrieval path under declarative rules, measuring whether it helps, and letting the evidence decide whether to build more.

---

### Where I disagree with A-D

**A: ranking IS a measured failure — we just haven't measured it formally.** Live receipt tonight: after index repair, "3 of 12 relevant" with the three only loosely on point. That's 9 candidates the ranker rejected (correctly) and 3 it admitted that were weak (ranking failure). Selection was the 50× larger problem, but ranking is the NEXT problem, and they compound. Fixing selection without measuring ranking is correct sequencing — but claiming ranking isn't broken because we haven't measured it is survivorship bias.

**D (the order): instrument → give one dark plane a path under rules → read data → split where rules fight. Correct sequence. But the measurement must run BEFORE the dark plane gets a path, not after.** Otherwise you cannot separate "this plane helped" from "any new source would have helped because the agent pays attention to novelty." Run the skim test on the CURRENT single-plane system first. Establish baseline ACTION-RATE. THEN add the second plane. Then measure the delta. Without the baseline, the second plane's effect is uninterpretable — it could be a cell win, or it could be the agent paying attention to anything new.

---

### Q1: SELECTION. Prove me wrong with a skim test.

The discriminating measurement: run a session where the agent can explicitly query EACH dark plane (notes, atoms, tasks) alongside lessons. After each query, record which plane's results the agent ACTED ON. If the agent consistently acts on non-lesson results when they're available, the binding constraint is selection — the knowledge exists but never reaches context. If the agent acts on lessons at the same rate regardless of what else is available, ranking or injection is the constraint — the knowledge is there but not surfaced at the right moment or in the right form.

I predict the agent will act on atom and task results MORE than lesson results when they're available, because those planes answer questions the lesson plane structurally cannot (design intent, current state). If I'm wrong — the agent ignores atoms and tasks and sticks with lessons — then selection is not the constraint. The dark planes are dark because they're not useful, not because they're invisible.

---

### Q2: One pipeline works if rules are DECLARATIVE. It breaks if rules must COMPOSE.

The specific mechanism that breaks a single pipeline: when relevance rules for different domains INTERACT. A note's relevance is recency + supersession. A lesson's relevance is trigger match + outcome credit. If you rank notes and lessons together in one list, you need a CROSS-DOMAIN comparison function. "Is this 2-day-old note more relevant than this lesson with 3 credits?" The rules for each domain are well-defined; the rule for comparing ACROSS domains is arbitrary. That's where the pipeline fractures — not at the per-domain rule, but at the sort.

The fix is not nine cells. It's SEPARATE INJECTION BUDGETS. Notes get N tokens. Lessons get M tokens. Atoms get K tokens. Each domain ranks its own items by its own rules. The injection stage blends them — interleaved, not merged-and-sorted. The cross-domain comparison is avoided by giving each domain its own budget rather than forcing them to compete on one scale.

This is the bus-lane pattern: each lane delivers its own items; the receiver interleaves. Lanes don't compete on a universal priority. They each get their own delivery guarantee.

---

### Q3: Task-type inference is a distraction until selection is solved.

The cheapest honest version: tool call → file path → grep the path against atom citations → surface the atom that governs this file. No inference. No classification. A mechanical join that already has the inverted index built (`atoms.py` `cited-by` sets). This doesn't know what PROBLEM the agent has. It knows what FILE the agent is touching, and what DESIGN governs that file. That's enough for a first pass — and it answers questions nothing currently answers.

Problem-type inference (is this debugging? design? refactoring?) is a harder problem that gets easier AFTER you have per-domain retrieval working. You can infer problem type from which domain's results the agent actually USED. But you need the retrieval paths to exist before the inference can learn.

---

### Q4: Measure-first costs us if it delays giving ANY dark plane a path.

The failure mode: we spend two weeks instrumenting the skim test, running baselines, analyzing data — and during those two weeks, agents keep making decisions without access to atoms, notes, or tasks that exist and would have helped. The cost of delay is real. Every session without atom retrieval is a session where an agent can violate a design constraint because it didn't know the constraint existed.

The mitigation: instrument AND build in parallel. The skim test is ~50 lines of logging in the PreToolUse hook. Building a one-dark-plane retrieval path (atoms, keyed to file path, with a 200-token injection budget) is ~100 lines. Both can ship in the same session. The measurement runs on the current system while the new path is live. The baseline is session N; the treatment is session N+1. You don't need weeks of baseline — you need ONE session of "does the agent use atoms when they're available?" That's answerable in a single sitting.

---

### The one measurement I would run first

**Atom retrieval, file-keyed, with a skim test that records which plane each acted-on item came from.** One session. One new retrieval path. A log that says: "agent opened `core/comm/bus.py`, surfaced atom `art_20260711_bus-lane-split`, agent read it, next action aligned with the atom's design." Or: "agent opened the file, atom surfaced, agent ignored it." Either outcome is informative. The measurement is cheap, the build is cheap, and it answers selection vs ranking in one session.
