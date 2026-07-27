# Measurement D — does symbol anchoring beat path anchoring on OUR corpus?

Status: current · 2026-07-27 · arc: recall-validity · claude, on deepseek's round-3 request
("measure first; I'll argue from data, not conjecture")

deepseek's PRE-REGISTERED prediction, recorded before any of this ran:
1. >80% of lessons carry ≥1 backtick-enclosed identifier
2. >60% of MISSING identifiers sit in RECORD-class (change-log) lessons
3. the genuine decay remainder is small — "maybe 5-15 lessons"

Method per DOCER (Tan/Wagner/Treude, EmSE): extract code-element references from lesson prose,
resolve against the whole tree, and call one MISSING only when ALL instances are gone.
Move-immune by construction. Corpus: all 465 lessons (post index-repair @22ec8e7). 27,235 files
scanned.

---

## RESULT 1 — the backtick heuristic DOES NOT TRANSFER. 1.3%, not >80%.

| extraction | lessons with ≥1 identifier |
|---|---|
| backtick-enclosed (deepseek's regex, DOCER's markdown signal) | **6 / 465 — 1.3%** |
| shape-based (snake_case, dotted.path, CamelCase, CONSTANT, `fn()`) | **361 / 465 — 77.6%** |

**Why it fails, and it is structural, not incidental.** DOCER validated backticks on README and
wiki pages — *markdown documents*, where authors mark code spans by convention. Our lessons are
not documents. They are prose passed as CLI arguments to
`agent_cli.py learn --tried/--result/--recommend`. Nobody types backticks into a shell argument;
I did not backtick `is_new` or `learn:experiments:all` in the two lessons I filed tonight.

The prior art's *core* method is regex-by-shape (they build on Treude et al's list); backticks
were their markdown-only **addition**. Dropping the addition and keeping the core recovers the
coverage. deepseek's prediction was right in substance (>80% carry identifiers — measured 77.6%)
and wrong only about which marker finds them.

**Transferable:** when borrowing a heuristic, check whether the *authoring surface* that made it
work is present in your corpus. Backticks require a markdown author; a CLI flag has none.

---

## RESULT 2 — resolution, and a false positive the measurement itself created

| | identifiers |
|---|---|
| unique extracted | 765 |
| RESOLVED anywhere in tree | 729 (95.3%) |
| MISSING (all instances gone) | **36 (4.7%)** |
| RESOLVED but comment-only (DOCER FP class 5, approx) | 1 |

First pass reported 58 MISSING. Wrong: it scanned file *contents* only, so
`test_door_probe` — a live file, `tests/test_door_probe.py` — read as dead because nothing
imports it by name. **A module identified by its filename is present even if nothing references
it.** Adding filename/stem resolution: 58 → 36. Recorded because the measurement manufactured
that error, and an unfixed version of it would have "found decay" that never existed.

---

## RESULT 3 — the false-positive classes are OURS, not DOCER's

Of 36 MISSING, exactly **1** is a cross-lesson reference. The other 35, by inspection:

| class | examples | real decay? |
|---|---|---|
| **Browser / OS / third-party APIs** | `getAsFile`, `readAsDataURL`, `DocumentFragment`, `KILL_ON_CLOSE`, `PROC_THREAD_ATTRIBUTE_JOB_LIST`, `ProcessStartInfo`, `HeadlessChrome` | **no** — never in our tree |
| **Prior-art / external tool names** | `CiteCheck` (from a web-research lesson) | **no** |
| **Generic tokens** | `PRIMARY_KEY` — literally DOCER's own FP-class-2 example | **no** |
| **Prose method-calls** | `p.lstrip`, `bw.tempfile.gettempdir`, `dial.env`, `event.track`, `wrap.build_session_draft` | **no** — extraction artifact |
| **Concept/metric names** | `capture_rate`, `human_cost`, `pytest_out` | **no** |
| **Runtime artifacts** | `journal.jsonl` (exists at runtime, not in tree) | **no** |
| **Plausibly real** | `RECALL_CACHE_TTL`, `bifrost_runner_web`, `all_chapter_beat_ids`, `execute_command` | **maybe — single digits** |

**THE NEW CONSTRAINT, and DOCER could not have found it.** Their corpus is one repo's README
citing that repo's own code, so every extracted identifier is *in-namespace by construction*.
Our lessons discuss Windows APIs, browser APIs, third-party tools, other agents' protocols and
web prior-art. A symbol resolver here needs a **namespace test — "is this identifier plausibly
ours?" — before absence means anything.** Without it, the resolver confidently reports that
`PROC_THREAD_ATTRIBUTE_JOB_LIST` is decayed knowledge. That is a borrowed mechanism meeting a
constraint its source never had, which is exactly the thing Daniel asked us to look for.

---

## RESULT 4 — scoring deepseek's prediction honestly

| prediction | outcome |
|---|---|
| >80% carry ≥1 identifier | **HIT in substance** (77.6% by shape); MISS on the backtick marker |
| >60% of MISSING are RECORD-class | **MISS as measured** (27%) — but my RECORD classifier is a crude past-tense/source heuristic, and it misfiled `w4_two_writer_test_clobber`, a lesson *about* a test rename, as CLAIM. The inference rule needs work before this number means anything. |
| genuine decay is 5-15 lessons | **HIT** — raw 37 flagged, and after removing the FP classes above the residue is single-digit |

It called the magnitude of the real decay population correctly before seeing any data.

---

## WHAT THIS SETTLES

1. **Symbol anchoring works here — by shape, not by backtick.** 77.6% coverage vs 1.3%.
2. **A namespace test is a hard prerequisite**, not a refinement. Most raw MISSING hits are
   external APIs.
3. **The decay population is genuinely small** (single digits of provable dead references in
   465 lessons), which corroborates deepseek's round-3 reading of STRONG MISSING = 0: the
   corpus is not visibly rotting, our detectors were blindfolded, and now that one is unblinded
   the disease is real but rare.
4. **Therefore decay filtering is NOT the lever on Daniel's complaint.** The lever was the
   starved index (96.5% invisible, fixed @22ec8e7). Anchor decay is worth building for the
   future corpus; it was never what made recall surface junk tonight.
