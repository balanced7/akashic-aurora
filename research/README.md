# Research day — the local fleet's shift work

The economics: frontier tokens are for **deciding**, local tokens are for **gathering**.
A local agent (glm_local, free, ~25 tok/s) works through a queue of research tasks all
day and writes PROVISIONAL articles; a frontier agent reads them in the evening, keeps
what survives scrutiny, and queues the next day's work. Nobody burns Opus-class tokens
on first-pass reading.

## The loop

```
you (morning)          .\scripts\local\run_research_day.ps1        # start the shift
local agent (all day)  queue/*.md -> drafts/<slug>.md              # one article per task
frontier agent (eve)   "review the research day"                   # grade, promote, requeue
```

## Layout

| Path | What |
|------|------|
| `queue/NNN-slug.md` | one task: a `status:` line, the question, seed URLs |
| `drafts/<slug>.md` | the local agent's provisional article (contract below) |
| `reviewed/` | accepted articles (frontier-graded; promotion to docs/ or a store note happens here) |
| `reviewed/frontier-<topic>-<date>.md` | FULL-fidelity records of frontier agent sweeps (see rule below) |
| `article-contract.md` | the structure every draft must follow |
| `runlog-<date>.md` | the runner's per-task log (start/end/verdict) |

**Full-fidelity rule (2026-07-02):** expensive research NEVER lives only in a chat.
When frontier agents return reports, their complete findings + citations are written to
`reviewed/frontier-<topic>-<date>.md` (with a provenance line) and shipped, before the
synthesis. Store notes are the sharpened projection; these files are the atoms they stay
re-derivable from. Forcing-function upgrade queued: a PostToolUse hook auto-archiving
Agent tool results (in-scope sessions only) — graduate the lesson when it ships.

## Task file format (queue/)

```markdown
status: queued            <- queued | running | done | failed  (runner-managed)
# TASK: <the research question, one line>
feeds: <SQn or roadmap item> <- the DECISION this task serves (watchlist.md lists SQ1-SQ5);
                               a task that can't name one doesn't get queued
seeds:
- https://...             <- starting URLs; the agent must FETCH what it cites
notes: <angle, constraints, what "done" means for this task>
```

## Worker toolset (R2)

Discovery: a self-hosted SearXNG (`docker start akashic-searxng`, loopback :8888) via
`py scripts/local/websearch.py "query"` -- free, key-less, private; the local backend has
no server-side WebSearch. Verification: WebFetch / `curl -sL`. Repo: Grep/Glob/Read and
`py agent_cli.py recall` (the corpus may already know). Search finds; only a FETCH
earns a citation.

## Landscape watch (the frontier-tracking venture)

`watchlist.md` = curated sources, each mapped to a standing question (SQ1-SQ5) and a
maturity stage (paper → reference-impl → framework → commodity; the stage decides
adoption TIMING). Weekly fleet sweeps ask for the DELTA since last-swept, from
`queue/_sweep-template.md`. Discipline that keeps this a venture, not a distraction:

- **Findings become hypotheses or discards** at the evening review — a finding that
  changes no action is noise, and the review says so explicitly.
- **WIP limit**: no new sweep tasks while >5 unadjudicated drafts sit in `drafts/` —
  reading must never outrun acting.
- **Kill criterion**: a month of sweeps with zero adopted changes or roadmap
  corrections kills or re-scopes the venture. Decided 2026-07-02, before starting.
- **First duty = thesis guard (SQ1)**: the most valuable single delta is early warning
  that someone shipped causal memory-utility measurement.

## Ground rules (why drafts are trustworthy enough to review)

- **Provisional by construction**: every draft is stamped `provisional-by: <agent>` and
  is not truth until the evening review promotes it. Trust the gates, not the author.
- **Fetch-before-cite**: the contract requires every claim to carry a URL the agent
  actually fetched this session; anything else is marked UNVERIFIED. A local model's
  unfetched "knowledge" is where hallucinations live.
- **Bounded**: one task = one article = one fresh headless session (no context rot,
  no runaway loops; the runner enforces a per-task timeout).
- The evening review REQUEUES weak drafts with feedback appended to the task file --
  iteration is cheap, it's local tokens.
```

---

## The second organism — fleet co-design rounds (declared 2026-07-21, library law R4)

This directory serves TWO lifecycles, both lawful. The research-day loop above (queue → drafts →
reviewed, with `runlog-*.md`, `watchlist.md`, `article-contract.md` at root by this README's
contract) — and the **fleet round loop**: `briefs/` carry work orders to seats (see LEXICON:
brief), round openings/counters land in `drafts/` (zone canon: `<seat>-<topic>-<kind>-<YYYY-MM-DD>.md`),
verbatim evidence (fence reports, walk reports, frontier sweeps, outside reviews) lands in
`reviewed/`, and reconciliations graduate OUT to `docs/`. `*.session.log*` pairs beside drafts
are runtime receipts (gitignored), not knowledge. The full filing law: `docs/LIBRARY.md`. Both
organisms share `drafts/` and `reviewed/` deliberately — the header's `Type:` line tells them
apart; never sort by guessing.
