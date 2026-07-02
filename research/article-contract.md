# Article contract — every provisional draft follows this shape

Write to `research/drafts/<slug>.md` (the slug comes from your task file's name).
Keep the whole article under ~150 lines. Structure:

```markdown
# <the task question>
provisional-by: <your agent id>, <date>
task: research/queue/<task file>

## TL;DR
- 3 bullets max, each one finding

## Findings
Numbered. EVERY claim carries its source inline like [1]. If you could not fetch a
source this session, the claim gets **UNVERIFIED** in bold instead of a number --
never a bare assertion.

## Sources
[1] <url> -- <what it is, fetched yes/no>

## Open questions
What the next task should chase. Be specific -- these become tomorrow's queue.

## Confidence
low / medium / high, one sentence why (e.g. "high -- three independent fetched
sources agree" or "low -- single vendor blog").
```

Rules:
- FETCH what you cite (WebFetch, or `curl -sL <url>` via Bash if WebFetch is
  unavailable). Quote sparingly, synthesize mostly.
- Contradictions between sources are FINDINGS, not noise -- report them.
- If a seed URL is dead or off-topic, say so in Findings; do not substitute
  imagined content.
- When done: re-read your draft file to verify it wrote correctly, then stop.
