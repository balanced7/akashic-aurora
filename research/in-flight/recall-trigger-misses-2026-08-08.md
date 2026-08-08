# Recall-at trigger: measured misses with ground truth, 2026-08-08

Status: current | Type: evidence dossier | Author: claude#f9d12d26

This is an ANSWER KEY, which is what recall evaluation has never had. On 2026-08-08 one seat
made a series of mistakes, and for each one a lesson describing that exact mistake either
already existed in the corpus or was written minutes later. The hook fired throughout. It
surfaced something else almost every time.

Retrieval is NOT the problem, and this was checked before writing this file: querying the store
directly for each lesson below returns it as the FIRST hit. The corpus is good and the search
works. The failure is in WHEN, not in WHAT.

## What the trigger currently keys on

`core/recall/at_action.py::recall_at(path=..., command=...)`, called from
`scripts/hooks/claude_pretooluse.py`:

```
path    = tool_input.file_path      # for file tools
command = tool_input.command        # for shell tools
```

Those two strings are the entire input. The mechanism ranks lessons against the FILE BEING
TOUCHED or the SHELL STRING BEING RUN. It has no access to what the actor is trying to do, what
the actor just did, or what the actor is about to get wrong.

Funnel at the time of writing: **822 lessons, 6751 surfaced, useful=290 noise=45, helped 61,
value 5.2%.**

---

## THE MISSES

Each case: what was about to happen, which lesson would have prevented it, whether that lesson
existed at that moment, and what the hook actually surfaced instead.

### M1 — a coercion at a door destroys a capability

**Moment.** About to edit `agent_cli.py` to parse `--prompts-file`. The existing line was
`prompts = [str(p) for p in loaded]`. I had, forty minutes earlier, shipped `ask_many` support
for dict prompts. The `str()` silently destroyed it.

**Lesson that applied, and EXISTED:** `capability_without_a_door` — *"when adding a capability
to a lower layer, expose it on the SAME door agents already use, in the same slice."*

**What fired instead:** lessons about git staging, TRELLIS setup on an RX 9070 XT, and a gemini
runner pin audit.

**Note, and it is the sharpest datum in this file:** `capability_without_a_door` DID fire — four
hours later, while I was running a `recall` query about recall. Right lesson, wrong moment. The
path-keyed mechanism worked exactly as designed both times.

### M2 — a RED pin that fails for the wrong reason

**Moment.** About to commit `tests/test_t247_...py`. Its fake client had invalid nested-class
scoping, so the file died at collection with a `NameError` rather than on its assertion.

**Lesson that applied, and existed IN MY OWN WORDS FROM THAT HOUR:** two commits earlier I had
written *"a RED pin must fail for its stated reason or it proves nothing"* into a commit message,
and had said it to the operator in prose.

**What fired instead:** nothing about pins. This is the strongest case in the file, because the
knowledge was not merely in the corpus — it was authored by the same actor, the same hour, and
still did not arrive.

### M3 — persist the RAW result before any transform

**Moment.** About to write a harness that ran a paid 5-branch fan, transformed the results, and
persisted the transform. The transform was wrong; five paid answers were unrecoverable.

**Lesson that applied, and existed:** the session handoff, read at boot, states verbatim:
*"Persist an expensive result BEFORE anything that can raise."* Also present as a lesson.

**What fired instead:** nothing about persistence.

### M4 — POSITIVE CONTROL, and it is not a success

**Moment.** Running `grep` over `core/recall/*.py` while investigating this very question.

**What fired:** `recall_at_action_ergonomics` — *"Remaining recall polish (optional): a
SessionStart hook to pre-warm the cache..."* — and `retrieval_benchmark_floor_imports_contested_ground`.

Both are genuinely ABOUT recall. The path-keying selected correctly. And both were useless,
because I was not polishing recall ergonomics; I was diagnosing a trigger. **A correct match on
topic can still be a total miss on moment.**

---

## The shape the misses share

In M1, M2 and M3 the file path was, respectively, `agent_cli.py`, a new test file, and a
scratchpad script. None of those strings carries any signal about *coercion*, *pin validity*, or
*persistence ordering*. The applicable lessons are keyed to an ACT the actor was about to
perform, and the trigger only knows a LOCATION.

In M4 the path did carry the topic, the match was correct, and the result was still noise.

## What this dossier does not establish

- **n=4, one seat, one day, one model.** No claim about base rates.
- These are the misses I NOTICED. Misses I did not notice are invisible here by construction,
  and are probably the larger set.
- No measurement of the opposite error: lessons that fired and *were* used. `helped 61` says
  that set is non-empty.
- Whether any available signal at those moments would actually have selected the right lesson is
  **the open question**, not something this file answers.
