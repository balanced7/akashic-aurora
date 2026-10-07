# Half — the helper's answer, VERBATIM

Received 2026-10-07 via `py agent_cli.py ask --prompt-file fences/eye-journal-plane/half_claude_brief.md --bg`,
handle `12909347`. Reproduced in full and unedited per the full-fidelity preservation rule
(`research/README.md`): the synthesis below it is disposable, this is not.

---

Use **path position**, not corpus derivation. A primary key must be a pure function of the file, not of what other files exist today or what the database has seen before.

The right rule is:

```python
R = transcript_root

def session_id_for(p):
    rel = p.relative_to(R)
    if len(rel.parts) == 1:
        return transcript_stem(p)          # current stem logic; UUID stays UUID
    return rel.parent.as_posix()           # containing directory path
```

Concretely:

- `root/<uuid>.jsonl` → `<uuid>` — unchanged
- `root/<dsh>/session.jsonl.zstd` → `<dsh>` — unchanged
- `root/<session>/subagents/workflows/<wf>/journal.jsonl` → `<session>/subagents/workflows/<wf>` — unique, structure-only, no denylist

If you want shorter workflow ids, you can use `rel.parts[-2]`, but that reintroduces a uniqueness assumption. Full relative parent is the safe structural rule.

**Migration for the 55,470 rows:**

- Root-level UUID transcripts: no re-key.
- DSH one-level transcripts: no re-key.
- Nested transcripts that the old code keyed by stem because the stem was not in the denylist: those may re-key from `<stem>:<line>` to `<relative_parent>:<line>`.

Dry-run the delta by comparing old `session_id_for(path)` with new `session_id_for(path)` for every file in `ingest_state`. Any differing file needs an `UPDATE` over its event rows. The 90 workflow journals have produced **0** existing rows, so they cost no migration; they simply start ingesting under the new path-derived address.

Do **not** persist derived genericness in `meta`. That would make address resolution depend on database history, which is worse than the bug it fixes.
