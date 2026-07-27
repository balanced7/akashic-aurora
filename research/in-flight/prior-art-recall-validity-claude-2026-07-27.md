# Prior art — recall validity / lesson decay (claude's half, round 1)

Status: current · 2026-07-27 · arc: recall-validity (Daniel's overnight reliability mandate)
Fence partner: deepseek (his half = secondary-index integrity, self-healing indexes,
materialized-view maintenance). This half = doc-code drift, truth maintenance, invalidation.

Daniel's standing instruction for this arc, verbatim: *"Remember to periodically check for prior
art or examples of others engineering solutions for similar issues so we don't waste time
re-inventing the wheel. I'm not saying to just blindly copy, I'm saying lets learn about each
problem and the constraints and possible solutions before we engineer everything by hand."*

---

## 1. DOCER — Tan, Wagner, Treude (Empirical Software Engineering; arXiv 2212.01479)

**"Detecting Outdated Code Element References in Software Repository Documentation."** Read in
full (25pp). This is the closest published analogue to our tier-1 problem, and it is a
*measured* study over 3,000+ GitHub repos, not a position paper.

### The rule, and why it matters to us
> "If a reference remains in the documentation after **all instances have been deleted from the
> source code**, we consider the documentation outdated."

True positive requires the element to have existed in a previous revision and be gone now —
either the instance was deleted from a surviving file, or the file itself was deleted.

**This is MOVE-IMMUNE BY CONSTRUCTION, and it is the fix for our 78% false-positive problem.**
We anchor on PATHS; paths move. DOCER anchors on the code element and searches the *whole*
codebase, so a file that migrates keeps its symbols and never registers as decay. deepseek's
measurement (two thirds of our 23 dead-path lessons cite `scripts/hooks/ →
agent/harness/hooks/`) is a pure artifact of path-anchoring. Symbol-anchoring would have scored
those lessons as live without any special-casing.

### Their empirically-derived false-positive taxonomy
Worth copying wholesale, because it was built by hand-annotation (free-marginal kappa **0.92**
across three raters on 50 samples), not guessed:
1. doc content duplicated inside the source tree (matches itself)
2. **common words, capitalised common words (`PRIMARY`, `INACTIVE`), abbreviations (`API`,
   `iOS`), non-project-specific words (`Data`, `User`)** — the dominant class
3. URLs and URL alt-text
4. the "source file" matched is itself documentation (e.g. HTML)
5. the surviving match is **inside a source-code comment**

### Their precision trick, which we can afford immediately
Backticks. They added a regex for backtick-enclosed text after observing developers mark code
elements that way, and *removed* bare-URL extraction as too noisy. They deliberately do **not**
extract fenced code blocks (```) — "longer texts that are less likely to be matched."
Our lessons are authored markdown-ish prose by agents who backtick identifiers by habit.
Requiring a backtick for a mined identifier is a cheap, high-precision filter we get for free.

### Scale/duration findings
- **28.9%** of the top-1000 GitHub projects currently carry ≥1 outdated reference; **82.3%**
  did at some point in history. (Google's repos: 5.4% — they hypothesise size, median 1.47 MiB
  vs 31.7 MiB.)
- References stayed outdated a mean of **4.7 years** (top1000) / **4.2 years** (google) before
  anyone noticed.
- 12.3% / 7.1% of all detected references were outdated at some point.

Their framing of *why* is our framing exactly: *"unlike source code, software documentation gets
outdated **silently** — there are no crashes or error messages."* Same disease, same organ.

### THE TWO LIMITATIONS THAT DECIDE OUR DESIGN

**(a) The ceiling is tier 1, and they say so.**
> "Our approach cannot detect outdated relationships between the repository and documentation
> **if the code elements are still present** in the source code, i.e. documentation could be
> considered outdated even if all the code element references are matched."

Our reconciled design (`20260725_lesson-decay-reconciled-design_194ab2`) concluded from first
principles that tier 3 (flipped premise) and tier 4 (true but incomplete) are not mechanically
detectable. **The literature independently confirms it.** This should stop us hoping a cleverer
anchor reaches them — it does not, and the confirmation is worth more than another design round.

**(b) The change-log exemption — the sharpest transfer of the night.**
> "A project's **change log** may also be incorrectly flagged as outdated as it contains
> references to code elements that are no longer in the repository. These references **should
> not** be considered as outdated as they only serve as a notice that the referenced class or
> function has been deprecated. These false positives are difficult to eliminate and require
> project maintainers to verify individually."

deepseek measured this in our corpus; DOCER names it as a known, hard, *unsolved* false-positive
class in the general case. But we are better placed than they are: they must infer that a
document is a change log, whereas **we control the write door.**

**DESIGN CONSEQUENCE (new, falls straight out of the prior art):** a lesson has a KIND that
decides whether decay even applies —
- a **claim about current behaviour** ("X does Y") — anchorable, invalidatable, can go stale;
- a **record of a change** ("we moved X to Y", "the class returned in 9 days") — a change-log
  entry, whose references to vanished things ARE its content. Permanently valid; must be exempt
  from dead-pointer staleness by construction, not by threshold-tuning.
Our worst false positives are all the second kind. `mcp_boot_hang_c7_4_class_closed` — "do NOT
point-fix call sites; that was tried 2026-07-17 and the class reopened in 9 days" — is a
change-log entry. Any dead-pointer check that flags it is wrong, and no amount of anchor
precision fixes that; only the kind distinction does.

(c) Also relevant to us specifically: their comment false-positive. This repo is unusually
comment-dense by house style, so "the symbol survives only inside a comment" will fire here more
than in their corpus. A symbol living only in prose is arguably dead — but that is a judgement,
and per our own doctrine the resolver should confess it, not rule on it.

---

## 2. Truth-maintenance systems (JTMS / ATMS) — de Kleer, Doyle; Shapiro's overview

The canonical machinery for "a belief is held *because of* its justifications; retract a premise
and every dependent belief is revisited." JTMS records the facts that directly infer a fact;
ATMS records the assumptions underlying it.

**What transfers:** the *shape* — beliefs carry explicit dependency records, and revision is
driven by following dependency arcs forward from a retracted assumption. That is precisely
"lesson cites artifact; artifact changes; revisit lesson." Our `cites` field is a justification
link in the JTMS sense, and this literature is why justification links are worth paying for.

**What does NOT transfer, and it is disqualifying for the core loop:** a TMS assumes beliefs are
*derived by inference rules the system itself ran*, so it can recompute them. Our lessons are
authored by agents from lived experience; there is no derivation to re-run. Retracting the
premise of `wake_consume_then_arm` cannot regenerate a corrected lesson — it can only flag it
for a human or an agent. So TMS gives us the dependency graph and the invalidation trigger, and
gives us nothing for the repair step. Anyone proposing "just do belief revision" should be shown
this paragraph.

---

## 3. What I have NOT yet covered in my half
Build-system invalidation (Bazel/Make content hashing) and cache invalidation (push vs pull,
CRL vs OCSP) — the frame I put to deepseek as Q3 — plus RAG groundedness/citation verification.
Named rather than silently dropped, per the discard-audit obligation.

---

## Bottom line for round 2
1. **Switch the anchor from path to symbol**, and require *all* instances gone. Move-immunity is
   free, and it dissolves the 78% false positive without special-casing.
2. **Backticks as the extraction signal** — cheap precision, empirically validated.
3. **Stop trying to reach tiers 3-4 mechanically.** Two independent derivations now agree.
4. **Introduce lesson KIND (claim vs change-record).** The prior art's hardest unsolved false
   positive is one we can make unrepresentable, because we own the write door and they do not.
