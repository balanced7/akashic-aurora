---
akashic_id: art_20260827_cli-verb-prior-art-what-other-systems-te_a7ef86
akashic_sha: 05e74bfdadf0
schema_version: 1
status: current
type: report
arc: T382
date: 2026-08-27
title: cli-verb-prior-art-what-other-systems-teach-us
gist: "## What this is Prior-art survey on systems resembling our verb registry, done 2026-08-26 at Daniil's ask, mapped onto gaps this house actua"
visibility: fleet
body_type: markdown
seats: [claude]
category: [testing, tooling, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-27T00:44:24"
updated: "2026-08-27T00:44:24"
---
<!-- GENERATED PROJECTION of art_20260827_cli-verb-prior-art-what-other-systems-te_a7ef86 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cli-verb-prior-art-what-other-systems-teach-us

## What this is

Prior-art survey on systems resembling our verb registry, done 2026-08-26 at Daniil's ask, mapped
onto gaps this house actually has rather than onto general CLI advice. Web-sourced; every claim
below is attributed and none of it is tested here.

**The headline, stated first so it is not buried: we are behind on DISCOVERABILITY and appear to be
ahead on WARRANT.** Nothing in the surveyed set attaches an evidence grade to a user-defined command
and ships a verifier that promotes it. `--evidence GUESS|INFER|VERIFIED` plus `kata` looks original.
The discoverability gap is the opposite story and it is the one that cost us: on the night of this
survey a single seat rediscovered ELEVEN organs that already existed -- kata, the forecast
registry's --calibration, ask --geometry/--lens/--preset, eye freq, core/recall/anchors.py,
bi-temporal supersession, the Perspectives & Maps build plan, and more.

---

## 1. fish abbreviations -- sugar that teaches its primitive

fish distinguishes ALIASES from ABBREVIATIONS: an abbreviation expands in place, VISIBLY, before it
runs. Consequences its community cites: shell history records the REAL command rather than the
nickname; you learn the underlying command by using the shorthand; and others can read your commands
without decoding your personal vocabulary. The contrast drawn repeatedly is that traditional aliases
"can feel like black boxes."

OUR GAP. `run <seat> <alias>` is a black box. The trace records `calibrate`; nothing downstream sees
`forecast list ; stats`. We already COMPUTE the expansion -- `--dry` prints it -- but only on
request.

PROPOSAL (unbuilt): make `run` echo the expansion by default. Cheap, already implemented, and it
converts every alias use into a discovery event. It also makes the ledger legible to our own
instruments: `eye freq` and recall currently see a nickname where the real verbs were.

## 2. Inform 7 -- why our refusal message lies, structurally

Inform 7 splits every action into three rulebooks: CHECK (may this proceed), CARRY OUT (change
state), REPORT (narrate it). Authors write parser-error rules per condition.

OUR GAP, exactly. At core/comm/toolbox.py:1154 the check and the report are THE SAME LINE -- it
refuses and narrates in one hardcoded string, so a pure read (`audit`, `alias list`, both absent
from the 27-verb `_AGENT_CLI_READ_VERBS`) is told it is a MUTATION. Navi hit this live while
composing a verb proposal whose answer required those reads.

Fixing the string treats the symptom. Separating check from report lets the report be specific to
the check that fired, permanently -- "errors that teach" as architecture rather than as discipline.

## 3. PowerShell approved verbs -- action-flavoured families, and a synonym rule we already break

PowerShell governs a closed verb vocabulary, discoverable via `Get-Verb`, grouped Common /
Communications / Data / Diagnostic / Lifecycle / Security / Other. Two rules transfer:

- THEIR GROUPS ARE ACTION-FLAVOURED; OURS ARE ROLE-FLAVOURED. ENGINEERS / MONITORS / SENTINELS /
  LIBRARIANS / LIFEWORKERS / RHYTHM answer "who am I being". Lifecycle / Diagnostic / Security
  answer "what does this do". Theirs is far better for FINDING a verb you do not know exists, which
  is our stated gap.
- THE SYNONYM RULE -- "always use Remove, never Delete or Eliminate" -- and we are breaking it now:
  `claude` and `kimi` both carry `drain-decide`, and deepseek's `premise-check` is a homonym with an
  unrelated premise concept from the same night.

Their enforcement model also fits us: unapproved verbs still RUN, but importing a module that uses
one emits a WARNING. Our mint accepts `UNSORTED` in total silence.

And `Get-Verb` makes the vocabulary SELF-DESCRIBING, whereas our `alias list` is refused at the
unattended door -- the seats who most need to discover the vocabulary are the ones who cannot.

## 4. jj (Jujutsu) -- undo as a primitive, and the indictment of our ledger

jj records every operation in an OPERATION LOG and offers `jj undo` to reverse repository state. The
line that indicts us, from its commentary: "Git technically has git reflog, but it's a forensics
tool rather than an undo button."

OUR APPEND-ONLY LEDGER IS A REFLOG. It is forensics. There is no `undo`.

And that is not academic: on the night of this survey this seat proposed purging git history to
solve a PRESENTATION problem, and the operator refused it on the grounds that we must not build
habits of erasing. The proposal happened BECAUSE the reversible option was not cheap. jj's answer is
to make reversibility so cheap that destruction is never the attractive move -- which retires a
category of bad proposal rather than guarding against it one instance at a time. Recorded separately
as lesson a_destructive_option_offered_for_a_presentation_problem.

## 5. Magit / transient -- self-documenting menus, and an independent convergence

Transient exists because when a command grows a large option set with dependencies between options,
simple approaches do not scale; it turns every prefix into a self-documenting popup that shows the
relevant options AND their possible values. It has spread beyond Magit on discoverability grounds.

OUR GAP. ~91 verbs plus ~20 aliases, with per-verb `--help` -- the simple approach that does not
scale. Worth noting: Navi independently proposed `speak` ("which grammar am I speaking through right
now?") from live friction, which is a transient-style orientation primitive arrived at without
knowledge of this survey.

## 6. clig.dev -- the framing

Four principles: human-centered design, composability, discoverability, conversationalism -- and
explicitly that designing for composability need NOT be at odds with designing for humans first.
That is the justification for our sugar-only law: composition that compiles through the primitive
serves both, which is precisely what `mint()` enforces by refusing any step that is not already a
live verb.

---

## Ranked, by leverage over cost

1. **`run` expands visibly** (fish). Nearly free, already computed, attacks the dominant failure.
2. **Split check from report at the refusal site** (Inform 7). Fixes a live defect structurally.
3. **Action-flavoured families + a synonym rule + make `alias list` readable at the door**
   (PowerShell). Addresses UNSORTED and the `drain-decide` collision.
4. **`undo` backed by the op log** (jj). Largest lift; retires a whole class of decision.

## Sources

clig.dev · learn.microsoft.com PowerShell approved-verbs and Get-Verb · fishshell.com docs and
allanmacgregor.com on abbreviations · github.com/magit/transient · catn.decontextualize.com Inform 7
concepts · github.com/jj-vcs/jj and neugierig.org tech notes.

## Honest limits

Web-sourced and UNTESTED here -- no claim in this document was verified by running the tool it
describes, and several are second-hand community characterisations rather than primary docs. The
survey is also selected: it went looking for systems resembling ours, which biases toward finding
resemblance. Treat every mapping as a hypothesis about our gap, not a measurement of it.
