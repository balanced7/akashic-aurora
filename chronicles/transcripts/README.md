# chronicles/transcripts/ — durable session-transcript copies

Full-fidelity session transcripts, persisted at the operator's request, redacted before
commit. The harness originals live under `~/.claude/projects/<project>/<session>.jsonl` and
are runtime state (gitignored dirs like `sessions/`, `session_snapshots/` do NOT persist to
git) — this directory is the repo-durable plane.

**Redaction spec (Daniil, 2026-08-11): "the entire transcript minus api keys or max's
personal data."** Classes: API keys/fragments (`priorish_KEY-REDACTED`, `KEYFRAG-REDACTED`,
`pk_live_REDACTED`), personal data (`SURNAME-REDACTED`, `BIO-REDACTED`, `EDU-REDACTED`,
`ROLE-REDACTED`, `PHONE-REDACTED`). Unredacted source-of-truth for the personal context
remains in the private store notes; only these public-repo copies are scrubbed.

**Integrity guarantees per copy:** line counts match the source at capture time; every
redacted line re-parses as JSON; a fragment-built forbidden-pattern scan reports zero leaks;
a per-substitution audit log with context is reviewed before commit (137 substitutions,
zero damaging false positives on the first entry below). Pipeline:
`persist_session.py` (kept in the session scratchpad; fragment-built needles so the script's
own text in the transcript never re-plants what it hunts — the v1 detector famously caught
its own needle list).

**Reading a transcript:** entries are JSONL. Operator speech lives in `type=="user"` AND
`type=="queue-operation"` records (lesson: `operator_speech_hides_in_queue_operation_records`);
assistant thinking and tool calls ride `type=="assistant"` messages. A copy captures through
its run timestamp — turns after capture live only in the harness original.

## Index

- `20260811_priorish-connectome_af0ca6b8.jsonl` — the priori.sh arc, 2026-08-10/11 night:
  live API+MCP audit, terms clearance, success-vocabulary sweep, hybrid-retrieval fence r1,
  the idea-connectome stance. Re-entry doc: atom `idea-connectome-stance` (research/in-flight
  original). Session af0ca6b8, Vandor seat, Daniil present throughout.
