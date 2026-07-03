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
| `article-contract.md` | the structure every draft must follow |
| `runlog-<date>.md` | the runner's per-task log (start/end/verdict) |

## Task file format (queue/)

```markdown
status: queued            <- queued | running | done | failed  (runner-managed)
# TASK: <the research question, one line>
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
