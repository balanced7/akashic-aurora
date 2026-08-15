# chronicles/transcripts/ — NOT a commit plane

**Session transcripts are never committed to this repo (Daniel's call, 2026-08-15).**
`.gitignore` enforces it: `chronicles/transcripts/*.jsonl`. Local copies may sit here; git
does not carry them.

## Where transcripts actually live

| Plane | Path | State |
|---|---|---|
| Harness original | `~/.claude/projects/<project>/<session>.jsonl` | runtime, rotates off disk silently |
| Durable archive | `E:\Akashic Aurora\transcripts\rolling` + `F:\...` | UNREDACTED, off-repo, two physical disks |

`scripts/ops/archive_transcripts.py` owns the archive. It is additive-only, refuses a
shrinking source, and is loud on failure — read its docstring before touching it. Durability
is fully covered there. This directory never added durability; it only added exposure.

## Why the redaction approach was retired

The previous policy was: commit a redacted copy. It was executed carefully — a purpose-built
`persist_session.py`, fragment-built needles so the script's own text could not re-plant what
it hunted, per-substitution audit logs, line-count and JSON-reparse integrity checks, and a
forbidden-pattern scan. The 2026-08-11 entry ran **137 substitutions and reported zero leaks.**

A third party's surname survived it anyway, and was live on public `origin/master` until
2026-08-15. Two later redaction commits (`d866532a`, `736900cf`) visited the same file and the
occurrence still survived.

**Mechanism, established 2026-08-15.** The redaction ran as an inline script inside a Bash tool
call, so the harness recorded the script's own source into the transcript. The script built its
needles by concatenation on purpose — `'Sur'+'name'` — so its own text could not re-plant
what it hunted. A second needle in the same line spelled the target out as a complete uppercase
literal, and the concatenation split the name phrase. The captured text had the shape
`FIRST '+'SURNAME`, which **no search for the intact phrase can match**, case-insensitive or
not, because the `+` operator sits inside the name. The anti-self-planting defense manufactured the one variant the
denylist was structurally blind to, and every later pass looked straight through it.

The house already adopted the correct fix without knowing it closed this: needles now live in
`.secrets/redaction-manifest.json`, a gitignored file, so a target never appears in a command
line the transcript can capture. Lesson:
`fragment_built_needles_plant_a_variant_no_later_search_can_match`.

The lesson is not "redact harder". A retroactive denylist can only find what it was told to
look for, and the string is public before the manifest learns it exists. That is a race the
leak wins by default. Deleting the plane removes the race.

See lessons `token_redaction_cannot_clean_a_dossier` and
`redaction_scoped_to_the_tracked_tree_leaves_the_store_reloading_it`.

## Reading a transcript (still true, still useful)

Entries are JSONL. Operator speech lives in `type=="user"` **and** `type=="queue-operation"`
records — lesson `operator_speech_hides_in_queue_operation_records`. Assistant thinking and
tool calls ride `type=="assistant"` messages. An archived copy captures through its run
timestamp; turns after capture live only in the harness original until the next archive run.

## Historical index (files no longer tracked here)

- `20260811_priorish-connectome_af0ca6b8.jsonl` — the priori.sh arc, 2026-08-10/11 night:
  live API+MCP audit, terms clearance, success-vocabulary sweep, hybrid-retrieval fence r1,
  the idea-connectome stance. Re-entry doc: atom `idea-connectome-stance`. Session af0ca6b8,
  Vandor seat, Daniil present throughout. Still on public origin **in git history** — removing
  it from the tree does not remove it from history, and no rewrite has been performed.
