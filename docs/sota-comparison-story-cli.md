# SOTA Comparison: `story` CLI (Slice 4)

Status: historical  (2026-07-09, P4: Research snapshot; story CLI built)

## Comparable Tools

| Tool | What it does | Overlap with `story` | Gaps vs `story` |
|---|---|---|---|
| **git CLI** (`git log`, `git show`, `git blame`) | Temporal exploration of commits | `story` = `git log --oneline` (atlas), `story --chapter` = `git show`, `story --track` = `git log --grep` | `git` has search/filter (`--grep`, `--author`, `--since/--until`), blame, diff, format variants |
| **git-lex** | Extends git with RDF/SPARQL knowledge graphs | Much more powerful query model (SPARQL) but more complex | `story` has no query language |
| **git-narrate** | AI narrative generator from git history | Human-readable story output (one-shot, not interactive) | `story` is interactive explorer; `git-narrate` is generate-then-done |
| **agent-memory-tools** | `mem init/add/today/search/analytics` | Very similar model (daily logs + tags → explore) | `mem analytics` (streaks, stats), `mem search`; `story` has no search or analytics |
| **Hermes Agent CLI** | `hermes memory/status/dump` | Agent memory diagnostics | Focused on agent config/state, not narrative |
| **The Narrative Graph** | Web-based narrative consistency engine (fiction) | Knowledge graph for character/plot | Not CLI, web UI only; fiction vs real agent logs |
| **Git Historian** | Web UI for radial timeline from git history | Visual timeline | Not CLI, visual only |
| **Redis CLI** | Direct key-value querying | Flexible, any query | No schema awareness; `story` is opinionated |

## Gaps in `story` CLI vs Prior Art

| Gap | Example in prior art | Priority | Notes |
|---|---|---|---|
| **No search/filter** | `git log --grep`, `mem search` | Medium | `--search`, `--since`, `--until`, `--author`, `--kind`, `--min-weight` |
| **No query language** | git-lex SPARQL | Low | Overkill for CLI; `--where` would suffice |
| **No diff/comparison** | `git diff`, `git log -p` | Low | "What changed between two chronicle runs?" |
| **No export variants** | `git-narrate` exports Markdown/HTML/plain text | Low | Currently JSON + terminal only |
| **No watch mode** | `hermes status --watch` | Low | Live-updating timeline |
| **No analytics/stats** | `mem analytics`, `git shortlog` | Medium | Streaks, word counts, per-track stats |
| **No compact view** | `git log --oneline` | Low | `--brief` or `--count` flag |
| **No shell completions** | git bash/zsh completions | Low | Tab completion for track/chapter/beat IDs |
| **No blame/timeline for individual beats** | `git blame` | Low | "When was this beat last updated?" |

## Differentiators (what `story` has that prior art lacks)

1. **Persistent narrative store** — not just git history, but any tracked agent activity (learning, commits, notes, decisions)
2. **Multi-track chronicle** — parallel narrative threads (ai-setup, research, vision, voice, stemroller) with chapter segmentation
3. **Deterministic chapter IDs** — idempotent re-runs produce same chapter IDs, enabling stable cross-references
4. **Faithfulness gate** — Distiller critic gate ensures summaries don't hallucinate (measurable metric)
5. **Coverage metric** — what % of beats are included in the narrative (unique to `story`)
6. **Back-links** — beats reference their chapter, chapters reference their track, enabling upward/downward navigation (`--beat` → `--chapter` → `--track`)
7. **Unified CLI** — single verb with sub-flags (atlas/track/chapter/beat/at/json) vs multiple separate commands

## Conclusion

`story` CLI fills a real gap: **interactive narrative exploration for persistent agent memory logs**. No prior art combines (a) multi-track chronicling, (b) deterministic idempotent chapter IDs, (c) faithfulness-gated summaries, (d) coverage metrics, and (e) a single unified CLI — all in one tool.

The main actionable gap is **search/filter** (medium priority), which would bring `story` on par with `git log --grep` and `mem search`. Other gaps are lower priority or better left to specialized tools.
