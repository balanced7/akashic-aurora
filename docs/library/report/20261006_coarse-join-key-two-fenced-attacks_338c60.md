---
akashic_id: art_20261006_coarse-join-key-two-fenced-attacks_338c60
akashic_sha: e5a2b391fa64
schema_version: 1
status: current
type: report
date: 2026-10-06
title: coarse-join-key-two-fenced-attacks
gist: "# The coarse join key, attacked by two fenced peers — 2026-10-06 Transcribed from the two agents' final reports at the end of the overnight "
visibility: fleet
body_type: markdown
seats: []
category: [memory, bus, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-06T09:48:47"
updated: "2026-10-06T09:48:47"
---
<!-- GENERATED PROJECTION of art_20261006_coarse-join-key-two-fenced-attacks_338c60 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coarse-join-key-two-fenced-attacks

# The coarse join key, attacked by two fenced peers — 2026-10-06

Transcribed from the two agents' final reports at the end of the overnight run. Both were
READ-ONLY and fenced from each other and from my synthesis: neither saw my notes, my
commit messages, or the other's findings. The first hand-labelled every coarse-only join
on the live stream; the second replayed the whole stream and **executed** every adversarial
case rather than predicting it.

Faithfully transcribed rather than byte-verbatim: the agent transcripts at
`%TEMP%\claude\...\tasks\*.output` were **0 bytes** when I went to copy them, so this file
is reconstructed from the delivered reports in full substance, including every table.
That 0-byte finding is itself worth filing — the task output path is not a durable archive,
so a peer report that is not transcribed in the turn it arrives is lost.

**Why this file exists.** Both reports materially changed the implementation. Of the eight
coarse-only joins that had a lesson surfaced, **two were false**, and the key that minted
them was still live after my first two fix commits. My commit messages are the projection;
this is the evidence.

Context: `coarse_target()` in `core/recall/at_action.py` is a second join axis for the
recall credit loop, added at `3ac876b5` / `0c51836b` / `9a51f695` and corrected at
`5ed736e8` on the strength of these two reports.

---

## PEER 1 — hand-labelled precision pass over the live stream

### What the instrument counts

`scripts/measure_credit_join.py --json`, re-run 2026-10-06:

```
outcome_rows_replayed 20004   sessions 21   fails 567 (560 command, 7 path)
fails_without_coarse_axis 73
joinable_exact 7    joinable_either 51    joinable_coarse_only 44
joinable_either_surfaced 12    joinable_coarse_only_surfaced 8
```

It is a counterfactual: every row on `recall:outcome` was written before the axis existed,
so the script recomputes `coarse_target()` from each row's recorded `t`. Per session, in
stream order, a FAIL is "coarse-joinable" if any **later** row has the same non-empty
coarse key and `ok=True`. Upper bound on observability, not on credit — credit additionally
needs `surfaced`. An independent scratch extractor mirroring that logic also recovered
**44**, matching the instrument.

### Counts, with denominators

| Population | Denominator | LEGIT | FALSE | UNCLEAR |
|---|---|---|---|---|
| Coarse-only join rows | **44** | 31 | **9** | 4 |
| …of which a lesson was surfaced (credit actually minted) | **8** | 6 | **2** | 0 |

Other denominators for the same 9 FALSE rows: 9 of 51 `joinable_either`; 9 of 567
failures; 9 of 20,004 replayed rows across 21 sessions.

44 rows = 43 distinct failing commands (one `ls -la …research/reviewed` fail appears
twice). They come from 10 sessions, concentrated in three: 11 + 10 + 8 = 29 of 44.
`k:pythonutf8=1 py` alone supplies 6 rows.

**The number that decides the guard: 2 false credits out of the 8 coarse-only joins that
had a lesson up.** Both the same class. The lessons that would have been credited:

- `k:export pythonioencoding=utf-8 py` → `guarded_import_must_probe_symbol_not_module`,
  `bifrost_mesh_comm`. The failure was `b.r if hasattr(b,'r') else b._r` — the first lesson
  is exactly on point for it. The joining success was editing a markdown brief and sealing
  a fence. The lie is not "wrong lesson"; it is "the loop is claimed closed with no
  evidence it was acted on."
- `k:pythonutf8=1 py` → `narrative_test_isolation_gap`. Failure was a mutation harness on
  `core/recall/at_action.py`; joining success was merging Navi's batch-2 moments into the
  eval fixture. Unrelated.

### The FALSE classes

**CLASS A — the heredoc is the program, and a preamble buys the key past the floor.
7 of the 9 FALSE rows.**

`_coarse_command` did `cut = payload.find("<<")` and discarded everything after it, so for
`py - <<'EOF'` the entire program is deleted. What remains is an interpreter invocation.
The `len(set(key.split())) < 2` floor is then satisfied by a token that names nothing: an
env assignment, an `export`, or a `timeout`. Verified against the live function:

```
''                                     <- py -c "import io; io.open(1)"   (floor refuses, as documented)
'k:pythonutf8=1 py'                    <- PYTHONUTF8=1 py - <<PY
'k:export pythonioencoding=utf-8 py'   <- export PYTHONIOENCODING=utf-8 && py - <<EOF
'k:timeout 600 py'                     <- timeout 600 py - <<py
```

The floor's own docstring names `py -c "<script>"` → `"py"` as the dogfooding case that
credited six unrelated lessons. The same command with **any** preamble routes around it.
Measured collision breadth on these keys — distinct later successes sharing one key:
**105, 72, 60, 45, 23, 18, 12, 9, 9, 5**. Rows 24, 30–33, 36–41 (11 of 44). Three of those
joined legitimately **by accident** (33, 39, 40) — the key did no work there.

**CLASS B — a flag before the subcommand erases the subcommand. 1 FALSE row (#5), widest
blast radius.**

`seen_flag` latched on the first `-` token, after which only path-like tokens survived. A
version flag therefore deleted the subcommand while the script path survived on its `.py`:

```
'k:py agent_cli.py'        <- py -3.11 agent_cli.py bifrost-send --help
'k:py agent_cli.py'        <- py -3.11 agent_cli.py mailbox claude --as act --note x
'k:py agent_cli.py learn'  <- py agent_cli.py learn --help   (no flag first: subcommand survives)
```

In #5 the key gathered 7 distinct later successes including a mailbox **write**
(`--as act --note "…"`), so a failed `--help` would be credited by a successful write.

**CLASS C — same target, different question. 3 UNCLEAR (25, 26, 35), 1 UNCLEAR by accident
(31), 1 FALSE judgment call (28).** The key names a shared file; the two bodies ask
materially different things of it. This is the guard's *declared* contract, so these are
intended joins. Whether each is a credit or a lie turns on what the failure actually was,
and `recall:outcome` rows carry only `agent/at/credited/flipped/join/ok/s/sid/surfaced/t`:
no error text, no exit code. **That is the evidence gap.**

**Latent (no FALSE in this sample, real hole) — redirection direction is erased.** `>`,
`>>`, `<` were all in `_SHELL_OPS`:

```
'k:cat notes.txt' <- cat > notes.txt <<MSG    (write)
'k:cat notes.txt' <- cat >> notes.txt <<MSG   (append)
'k:cat notes.txt' <- cat notes.txt            (read)
```

A failed write followed by a successful read of the same path mints credit. Rows 12 and 34
ride this class; both happen to be write→write.

**Also latent:** newlines are not statement separators in `_split_statements`, and
`_pipeline_head` cuts at the first unquoted `|`. In the multi-line PowerShell blocks of
rows 17–20 the key sees only the first pipeline; a whole trailing
`py agent_cli.py manual ingest …` is invisible to it.

**Opposite failure mode (over-specific, not false):** `_looks_pathy` fires on any `/`, `\`
or `.ext` tail, so `-c` script text leaks in as pseudo-path tokens, then
`.replace("\\","/")` mangles it — `k:py txt=re.sub(r'<(script|style)[^>]*>.*?<//1>'…`,
`k:py t='/n'.join(p.get_text()`. Rows 1, 10, 23, 35, 44. Brittle rather than promiscuous;
the risk is a lost join, not a false one.

### The labelling rule used

**LEGIT**: same program/subcommand against the same named target, difference confined to
flags, output post-processing, or a heredoc/script body the guard drops by design.
**FALSE**: the programs differ, the named targets differ, or the key names nothing but an
interpreter. **UNCLEAR**: the key names a shared target but the two bodies ask materially
different questions of it.

### The full labelled list

`k:` = shared coarse key. Commands abbreviated where they stop differing.

| # | sid | shared key | fail → success | label |
|---|---|---|---|---|
| 1 | bee0f118 | `$t = get-date py …/test_score_export.py exit=$lastexitcode…` | `… \| foreach { …Substring(0,min(3000,…)) }` → `… \| foreach { $_.ToString() }` | LEGIT — same test, output truncation only |
| 2 | bee0f118 | `py tests/test_arsenal_nashville.py tests/test_arsenal_pianocue.py` | `pytest …-q \| select -last 12` → `pytest …-q -p no:cacheprovider \| grep` | LEGIT — same two files |
| 3 | bee0f118 | `py tests/test_arsenal_pianocue.py` | `-k "numbers_are_named_as_the_page or …"` → whole file, no `-k` | LEGIT (judgment call: `-k` narrows the run) |
| 4 | bee0f118 | `py tests/test_arsenal_pianocue.py` | `-k "…_as_the_page_names_them or …"` → whole file | LEGIT (same call) |
| 5 | bee0f118 | `py agent_cli.py` | `py agent_cli.py --help` → `py -3.11 agent_cli.py bifrost-send --help` | **FALSE** — Class B; 7 colliding incl. a mailbox write |
| 6 | bee0f118 | `node tests/piano_looks_store.test.mjs` | `\| select -last 40` → `\| select -last 20` | LEGIT — tail length only |
| 7 | bee0f118 | `$t = measure-command { py tests/test_arsenal_tiktok.py…` | `-q -p no:cacheprovider` → `… --durations=5` | LEGIT |
| 8 | bee0f118 | `$t=get-date py tests/test_arsenal_tiktok.py wall:…` | `--durations=12 \| last 60` → no `--durations`, `\| last 15` | LEGIT |
| 9 | bee0f118 | `timeout 300 node …/gpu_lock.mjs run probe4.mjs` | `\| grep "^{" \| node -e "…"` → `\| tail -6` | LEGIT — identical up to the pipe |
| 10 | bee0f118 | `py txt=re.sub(…) c=re.sub(r'/s+',` | html→text on `emobox_html1.html` → same, `sys.stdout` wrapped utf-8 | LEGIT — same file, encoding fix |
| 11 | 010c3922 | `py tests/test_legacy_net_exact_and_bounded.py` | `-rn \| select-string …` → no `-rn`, `\| last 25` | LEGIT (surfaced — earned) |
| 12 | c097980f | `scratch="…/scratchpad cat $scratch/fencemsg.txt` | `cat > fencemsg.txt <<msg …` → same `cat >`, edited body | LEGIT (rides Class D) |
| 13 | 4ebe0d10 | `ls e:/ai-setup/research/reviewed/` | `ls -la "e:\…\reviewed\" \| grep duckdb` → `ls -la "e:/…/reviewed/" …` | LEGIT (surfaced) — backslash→slash, the textbook case |
| 14 | 4ebe0d10 | `ls e:/ai-setup/research/reviewed/` | duplicate stream row of #13 | LEGIT (surfaced) |
| 15 | 4ebe0d10 | `ls e:/ai-setup/research/reviewed/` | `ls "e:\…\" \| grep duckdb` → `ls "e:/…/" \| grep duckdb` | LEGIT |
| 16 | 4ebe0d10 | `$env:pythonutf8='1 … duckvenv/…/python.exe duck3.py` | `… duck3.py` → `… duck3.py 2>&1 \| select -last 9` | LEGIT — same script |
| 17 | 4ebe0d10 | `set-location e:/ai-setup … py scripts/mirror.py` | `--push --yes --include-others` → `--push --yes` | LEGIT (surfaced; judgment call — `--include-others` widens the commit set) |
| 18 | 4ebe0d10 | `… $out = py tests/test_ledger_cross_process.py tests/test_ledger.py` | identical pytest, different select-string report | LEGIT |
| 19 | 4ebe0d10 | `… $out = py tests/test_manuals_shelf.py` | identical pytest, `first 16` → `first 10` | LEGIT |
| 20 | 4ebe0d10 | `… $out = py tests/test_manuals_shelf.py` | pytest + `re-ingest with the new pipeline version` → pytest + `re-cut + re-embed` | LEGIT (judgment call: the differing tail is invisible to the key) |
| 21 | f9fdc9b8 | `py tests/test_t406_eye_sees_the_dsh_plane.py` | `\| last 30` → `\| last 25` | LEGIT |
| 22 | f9fdc9b8 | `py tests/test_t408_durability_sweep.py` | `\| last 12` → `\| last 15` | LEGIT |
| 23 | a90a987a | `py d=json.load(open('state/coord/tasks.json'));` | print 15 task statuses (crashed on `r` = None) → same, with `if r is None: continue` | LEGIT — same script, guarded |
| 24 | a90a987a | `timeout 600 py` | unpack one take + mock one 9:16 frame → render frames for six takes | **FALSE** — Class A; 5 colliding |
| 25 | a90a987a | `d="…/wf_ece5ec17-fbf py $d/journal.jsonl` | find `judge:accuracy` result, print ranking → count starts/results since last launch | UNCLEAR — Class C |
| 26 | a90a987a | `d=state/arsenal/score/…/full … py $d/score.json` | shape-probe of top-level keys → duration/tpq census | UNCLEAR — Class C |
| 27 | a90a987a | `d=state/arsenal/score/…/full … py $d/score.json` | tpq+meter print **and** duration census → the duration census alone | LEGIT — same analysis, trimmed |
| 28 | a90a987a | `pythonioencoding=utf-8 py agent_cli.py mailbox claude` | `--open 0f73a82ded \| sed \| py -c` → `--open discord:15545 \| head -60` | **FALSE** (judgment call) — different message, nothing fixed |
| 29 | 2dc61419 | `py agent_cli.py bifrost-sync claude` | `--consume --digest --limit 50` → `--limit 5 \| head -20` | LEGIT — `--limit` only |
| 30 | bb86400e | `export pythonioencoding=utf-8 py` | read `bifrost:*:inbox:claude` via xrevrange → edit a markdown brief, `fence write`, `fence seal` | **FALSE (surfaced)** — credited `guarded_import_must_probe_symbol_not_module`, `bifrost_mesh_comm` |
| 31 | bb86400e | `export pythonioencoding=utf-8 py` | xrevrange inbox filtering `frm=daniil`, died on `b.r`/`b._r` → xrevrange via `b._client`, filtering deepseek replies, then `bifrost-fetch` | UNCLEAR — the AttributeError fix is real but the follow-on differs; Class A key, so any match is accidental |
| 32 | bb86400e | `export pythonioencoding=utf-8 py` | multi-hunk patch to `core/comm/resume_on_deaf.py` → write a T418 receipt note | **FALSE** — Class A |
| 33 | 428ba6c4 | `pythonutf8=1 py` | `events:raw` dup census count=4000, died decoding a non-bytes key → same census count=6000 with an `s()` decode helper | LEGIT **by accident** — 105 colliding |
| 34 | 428ba6c4 | `cat research/in-flight/recall-the-anti-popularity-prior-2026-10-02.md` | `cat > <file> <<md` (author) → `cat >> <file> <<md` (append held-out result) | LEGIT (surfaced) — rides Class D |
| 35 | 428ba6c4 | `$d="…/tool-results py t='/n'.join(p.get_text() $d/webfetch-…pdf` | pymupdf: regex `ece`, ±1400 chars → pymupdf: find `4.2`, 9000 chars | UNCLEAR — Class C |
| 36 | 428ba6c4 | `pythonutf8=1 py` | mutation harness on `core/recall/at_action.py` → merge Navi batch-2 into `tests/fixtures/recall_eval/moments.json` | **FALSE (surfaced)** — credited `narrative_test_isolation_gap`; 72 colliding |
| 37 | 428ba6c4 | `export pythonioencoding=utf-8 d="…/zq py` | patch `oa2.py` to add retries then run it → regex-scrape `shah.html` for pdf hrefs | **FALSE** — Class A |
| 38 | 428ba6c4 | `pythonutf8=1 py` | in-process probe of `core.tools.everything.search` with a faked subprocess → edit the test file renaming `format_search`→`format_result` | **FALSE** (judgment call) — causal chain real, actions differ; 60 colliding |
| 39 | 428ba6c4 | `pythonutf8=1 py` | regex-extract `{"candidate_count"…}` from `w5ejv8gx9.output` → `json.load` the same file and walk it | LEGIT **by accident** |
| 40 | 428ba6c4 | `pythonutf8=1 py` | chord-naming census over `…dca2a2df/events.jsonl` with a dict `pc()` → same census, rewritten `pc()` | LEGIT **by accident** |
| 41 | 428ba6c4 | `pythonutf8=1 py` | scan core/scripts for unlocked read-modify-write → mask `sk-ant` literals in `tests/test_touch_v1.py` | **FALSE** — Class A |
| 42 | 428ba6c4 | `py agent_cli.py injections` | `injections \| first 30` → `injections --hours 24 \| head -40` | LEGIT — `--hours` only |
| 43 | 428ba6c4 | `git add scripts/bifrost_wake.py tests/test_t073_wake_longlived.py git commit` | `git add … && git commit -f - <<msg` → same, edited message body | LEGIT |
| 44 | 81efa6f6 | `py p='tests/fixtures/claude_payloads/transcript_fail_then_success.jsonl` | iterate the jsonl printing tool_use/tool_result → same, with blank-line and parse-error guards | LEGIT (surfaced) — same script, guarded |

### Caveats on reading these numbers

- **Small and clustered.** 9 FALSE of 44, from 10 sessions, 29 of 44 from three sessions.
  Realised credit is 2 of 8. No percentage belongs on either.
- **Counterfactual, not observed.** No coarse key was ever stored; these joins never
  happened. The `surfaced` flag was recorded live, so the 8-row credit population is real.
- **The stream is live.** `xlen` was 20,009 against a 20,004 replay, including rows from
  the measuring session itself. The counts move.
- **What would settle the 4 UNCLEAR rows:** the failure's error text. One line of stderr
  answers "was the thing that broke the thing the second command fixed?"; the command
  strings alone cannot.
- **The three LEGIT-by-accident rows (33, 39, 40) are not the guard working.** Their key
  was `k:pythonutf8=1 py`, which admits any heredoc; those joins landed correctly because
  the agent happened to re-run the same analysis next.

---

## PEER 2 — adversarial replay, every verdict executed

### Headline, from the live data

Replayed every recorded `recall:outcome` stage row on this machine — **23,636 distinct real
`c:` command keys** — in session order through the live coarse logic:

- **9 exact flips. 48 *additional* coarse flips.** The axis is doing ~84% of the crediting,
  not a trickle at the margin.
- **865 collision groups** (one coarse key, ≥2 genuinely distinct commands) covering
  **3,373 real commands** — 14% of everything the sensor has ever keyed.
- **~25 of the 48** new flips are one family: the identity was inside a `-c`/heredoc body
  and a prefix token bypassed the `test_j9` floor. The guard written to block exactly this
  blocks almost nothing in practice.
- One coarse flip already in the live flip log (09:14:33, session `81efa6f6`) **credited 6
  lessons** on a `py -c` throwaway. Recomputed against then-HEAD: **still non-empty**
  (`k:py p='tests/fixtures/claude_payloads/transcript_fail_then_success.jsonl`). The 09:25
  fix did not cover it.
- No time window and no adjacency requirement: a FAIL joined a same-coarse SUCCESS **40
  unrelated actions later** (`flipped=True, credited=1`). Every class below is session-wide.

### Ranked findings

**1. FALSE-JOIN — any prefix token defeats the bare-interpreter floor.** The floor counts
distinct tokens, and a prefix contributes one, so `py` becomes `<prefix> py`.

| prefix | `py -c "<A>"` vs `py -c "<B>"` | key |
|---|---|---|
| none | blocked | `''` |
| `cd /e/AI-Setup &&` | blocked | `''` |
| `PYTHONUTF8=1` | **FALSE-JOIN** | `k:pythonutf8=1 py` |
| `PYTHONIOENCODING=utf-8` | **FALSE-JOIN** | `k:pythonioencoding=utf-8 py` |
| `export PYTHONIOENCODING=utf-8 &&` | **FALSE-JOIN** | `k:export pythonioencoding=utf-8 py` |
| `Set-Location e:\ai-setup;` | **FALSE-JOIN** | `k:set-location e:/ai-setup py` |
| `$env:PYTHONUTF8='1';` | **FALSE-JOIN** | `k:$env:pythonutf8='1 py` |
| `timeout 600` / `time` / `sudo` / `winpty` | **FALSE-JOIN** | `k:timeout 600 py` etc. |
| `d="state/x";` / `$t = Get-Date;` | **FALSE-JOIN** | `k:d="state/x py` |

Identical for `py - <<'EOF'`. End-to-end: `PYTHONUTF8=1 py -c "import json; print(...)"`
(FAIL) → `PYTHONUTF8=1 py -c "import shutil; shutil.rmtree('build')"` (SUCCESS) =
`flipped=True, credited=1, join=coarse`. **Severity: highest.** The UTF-8 prefix is the
house's own idiom — live groups `k:pythonutf8=1 py` (119 distinct commands, 6 real flips),
`k:pythonioencoding=utf-8 py` (76), `k:export pythonioencoding=utf-8 py` (36, 3 real
flips). One real pair: "read the bifrost inbox" FAIL credited by "rewrite a research
markdown file" SUCCESS. Also live: `Set-Location e:\ai-setup; py -m arsenal.practice
history --days 30` (FAIL) → `...practice list` (SUCCESS), confirmed `flipped=True` — `cd`
is dropped but `Set-Location` is not, so PowerShell's own nav verb *creates* the bypass.

**2. FALSE-JOIN — dropping `cd` drops which tree.** `cd /e/AI-Setup && py agent_cli.py boot
claude --json` vs `cd /e/AI-Setup-Sandbox && …` → both `k:py agent_cli.py boot claude`,
`flipped=True`. Same for `cd /e/AI-Setup && npm run build` vs `cd /e/akashiclabs-site && npm
run build`, and `cd A && pytest tests/test_x.py -q` vs `cd B && …`. **Severity: very high,
already live** — `k:py agent_cli.py bifrost-sync claude` mixes
`worktrees\sunshine-discord-split` with `/e/ai-setup`; `k:sed arsenal/web/piano.js` mixes
`/e/ai-setup` with `/e/aurora-strings`; a real flip fired on `k:cat patch3.mjs` across two
different scratchpad directories.

**3. FALSE-JOIN — `py -m pytest FILE -k "<selector>"` keys to `py FILE`.** `-k "player"`
(FAIL) → `-k "one_tab"` (SUCCESS) = `flipped=True`, key
`k:py tests/test_arsenal_pianocue.py`. **Severity: very high frequency** — live groups of
41 (`test_arsenal_pianocue.py`) and 26 (`test_arsenal_practice.py`) distinct commands, with
a real flip across different `-k` selectors and `--tb` modes. This is the TDD loop: narrow
a selector, fail, narrow differently, pass. The `-k` expression **is** the action's scope.

**4. FALSE-JOIN — a pathy token from inside the script body supplies the floor.** The
already-minted 6-lesson credit is this. Live group
`k:py d=json.load(open('state/coord/tasks.json'))` holds **23 distinct throwaway scripts**.
Tokens after `-c` are dropped unless `_looks_pathy`, and a quoted path *inside the Python
source* is pathy. **Severity: high** — precisely the class `test_j9` names, surviving by a
different route.

**5. FALSE-JOIN — the subcommand sits after a flag, so it is dropped.** All executed:

| A | B | key |
|---|---|---|
| `git -C /e/AI-Setup status` | `git -C /e/AI-Setup push` | `k:git /e/ai-setup` |
| `py agent_cli.py --help` | `py -3.11 agent_cli.py bifrost-send --help` | `k:py agent_cli.py` *(real live flip)* |
| `pip install -U redis` | `pip install -U duckdb` | `k:pip install` |
| `npm install -g pnpm` | `npm install -g yarn` | `k:npm install` |
| `docker run -d nginx` | `docker run -d redis` | `k:docker run` |
| `curl -X POST .../api/nudge` | `curl -X GET .../api/nudge` | `k:curl http://localhost:8787/api/nudge` |
| `git checkout -b wave0` | `git checkout -b wave1` | `k:git checkout` |
| `git branch -D wave0` | `git branch -D wave1` | `k:git branch` |
| `git reset --hard HEAD~1` | `git reset --hard HEAD~9` | `k:git reset` |
| `py agent_cli.py boot --agent claude` | `--agent deepseek` | `k:py agent_cli.py boot` |
| `git --no-pager log -5 f.py` | `git --no-pager blame f.py` | `k:git core/recall/at_action.py` |
| `node server.js --port 80` | `--port 443` | `k:node server.js` |

Live: `k:py agent_cli.py events` holds 31 commands spanning `--agent claude/daniil/discord`;
`k:py agent_cli.py mailbox claude` holds 19, mixing read `--open <id>` with the
state-changing `--intent X --as act`, and a real flip fired across two different `--open`
ids. Note `git tag -d v1.0`, `rm -rf /a`, `git checkout wave0`, `docker stop X` came back
**OK** — the dot-extension and `/` heuristics rescue those, which is why this class is
uneven rather than uniform.

**6. FALSE-JOIN — the pipeline tail is dropped, but for `xargs`/`tee`/`| py -` the tail IS
the action.** `git diff --name-only | xargs py -m ruff check` vs `| xargs rm -f` → both
`k:git diff`, `flipped=True`. `cat data.json | py -c "<A>"` vs `| py -c "<B>"` → both
`k:cat data.json`. `Get-Content x.log | Select-String "error"` vs `| Measure-Object -Line`
→ both `k:get-content x.log`. `py scripts/a.py | tee out.log` vs `| py scripts/b.py` → both
`k:py scripts/a.py`. Severity: medium-high.

**7. FALSE-JOIN + MISSED-JOIN — `--flag=value` drops a path the space form keeps.**
`--out=exports/a.json` vs `--out=exports/b.json` → both `k:py scripts/export.py`,
`flipped=True`. And `--out=exports/a.json` vs `--out exports/a.json` (the *same* command) →
`k:py scripts/export.py` vs `k:py scripts/export.py exports/a.json` = **MISSED-JOIN**.
Inconsistent with `test_j4`'s guarantee in both directions. Severity: medium-high.

**8. FALSE-JOIN — newlines are not statement separators.** `normalize_target` collapses
whitespace and `_split_statements` only knows `;`/`&&`/`||`, so in a multi-line block the
first line's flag swallows the following lines. `npm run build --silent\nnpm run test
--silent` vs `…\nnpm run lint --silent` → both `k:npm run build`. `py agent_cli.py recall
--limit 5\npy agent_cli.py learn --json` vs `…\npy agent_cli.py promoted --json` → both
`k:py agent_cli.py recall agent_cli.py`, `flipped=True`. Corollary MISSED-JOIN:
`py a.py --x 1\npy b.py` → `k:py a.py b.py` but `py a.py --x 1; py b.py` → `k:py a.py py b.py`.

**9. FALSE-JOIN — the `<<` cut swallows every statement after it.**
`cat > /tmp/a.py <<'EOF'…EOF\npy /tmp/a.py` vs `cat > /tmp/a.py <<'EOF'…EOF\nrm -rf
/e/AI-Setup/build` → both `k:cat /tmp/a.py`, `flipped=True`. The cut happens before
statement splitting, so write-then-run and write-then-destroy are one key. Severity:
medium-high; write-a-scratch-script-then-run-it is the fleet's most common compound command.

**10. FALSE-JOIN — wrapper commands swallow the real program, across interpreters.**
`uv run --with redis py scripts/a.py` vs `uv run --with redis node scripts/a.py` → both
`k:uv run scripts/a.py` — a direct violation of `test_j4`'s "different executable NEVER
join". Same shape: `npx --yes tsx scripts/a.ts` vs `npx --yes esbuild scripts/a.ts` →
`k:npx scripts/a.ts`; `py -m pytest tests/x.py` vs `py -m unittest tests/x.py` →
`k:py tests/test_x.py`. Severity: medium.

**11. FALSE-JOIN — a redirect target or a bash line-continuation manufactures the second
distinct token.** `py -c "<A>" > out.json` vs `py -c "<B>" > out.json` → both
`k:py out.json`. `py -c "<A>" \`<newline>`2>&1` vs same with `<B>` → both `k:py /` —
`_looks_pathy("\\")` is True, so a lone continuation backslash becomes a `/` token. Also
`py -c "A" && node -e "B"` vs `py -c "C" && node -e "D"` → both `k:py node`.

**12. FALSE-JOIN — `find -exec`.** `find . -name "*.py" -exec rm {} \;` vs
`-exec chmod +x {} \;` → both `k:find . *.py /`. `find . -name "*.log" -delete` vs
`-print` → both `k:find . *.log`. Low frequency, high harm if it fires.

### MISSED-JOINs (less harmful, worth knowing)

- **`test_j5`'s own promise fails for single-token commands.** `pytest` → `k:pytest`, but
  `cd /e/AI-Setup && pytest` → `''`, `pytest | tail -40` → `''`, `make` vs
  `cd … && make` likewise. The `key != payload` escape hatch grants an axis only to the
  *literally* minimal spelling, so the dressed sibling can never reach it — the exact
  scenario the docstring says it fixes. `npm test` (two tokens) is fine.
- **Path spelling.** `py E:\AI-Setup\scripts\a.py` vs `py /e/AI-Setup/scripts/a.py`,
  `py ./scripts/a.py` vs `py scripts/a.py`, relative vs absolute. The fleet writes all of
  these for the same script.
- **Rerun with output captured.** `py scripts/a.py` vs `py scripts/a.py > out.log 2>&1` →
  `k:py scripts/a.py` vs `k:py scripts/a.py out.log`. A very common retry shape.
- **`test_j1`'s "a flag VALUE is not identity" leaks for decimals and version strings**,
  because `_EXT_RE` matches `.5`: `--threshold 0.5` vs `0.9`; `uv venv --python 3.11` vs
  `3.12`. Integer values (`--limit 5` vs `7`) correctly agree.
- **Preambles and wrappers block the join they should allow.**
  `$env:PYTHONPATH="."; py scripts/a.py`, `env FOO=1 py scripts/a.py`,
  `AKASHIC_AGENT_ID=claude py scripts/a.py`, `time py scripts/a.py`, `npx vitest run x`,
  `timeout 30|60 py a.py` all miss the bare spelling. In the bash inline-env case the key's
  *first* token is the assignment, not the executable.
- **PowerShell idioms outside the ops/nav tables:** `2>$null` is kept (not in
  `_SHELL_OPS`), `Set-Location` is not dropped, `( cd scripts && py a.py )` keeps the
  subshell's `cd`, and PS here-string bodies are not dropped the way bash heredocs are.
- **A stray unmatched apostrophe hides a pipe**, since `_iter_unquoted` has no escape
  handling: `py scripts/a.py --msg wasn't | tee out.log` → `k:py scripts/a.py out.log`. An
  apostrophe inside double quotes is handled correctly.

### The peer's own fix suggestions

1. `_CD_RE = re.compile(r"^(cd|set-location|sl|pushd|popd)(\s|$)")` — kills the
   `Set-Location` bypass (2 live flips) and makes the PowerShell and bash idioms agree.
2. Add `"\\"` (and PowerShell's backtick) to `_SHELL_OPS` — kills the phantom `/` token and
   cleans `find -exec` keys.
3. Rank 1 is two lines: skip assignment-only statements, and drop leading `VAR=value`
   tokens inside a statement before the floor is computed. It does **not** break
   `test_j10`. But it is **not free** — it newly collapses
   `AKASHIC_AGENT_ID=claude py a.py --j` with `AKASHIC_AGENT_ID=deepseek py a.py --j`,
   which currently separate correctly. Worth a pin either way.

---

## What I did with this, 2026-10-06

Landed at `5ed736e8`: the inline-program refusal (rank 4 / the still-live false credit),
tree identity for a non-repo-root `cd` (rank 2), PowerShell nav verbs (rank 1 residual),
assignment-only statements (rank 1 residual), line continuations (rank 11), and the
missed-join repair for dressed minimal commands. Pinned as `test_j11`–`test_j17` in
`tests/test_credit_join_coarse_key.py`. Refusals rose 101 → 163 of 562 failures; the
creditable subset fell 8 → 5, and per the hand labels the three that left include both
false credits.

**Accepted cost, named:** dropping inline env assignments means
`AKASHIC_AGENT_ID=claude py a.py` and `AKASHIC_AGENT_ID=deepseek py a.py` now share a key.
The peer flagged this and it is a real loss of separation; I took it because an env prefix
is not the action, and because the alternative leaves the highest-severity bypass open.

**Not fixed, carried forward:** the pytest `-k` selector as action scope (rank 3, live
groups of 41 and 26); `| xargs` / `| tee` / `| py -c` tails (rank 6); `--flag=value`
inconsistency (rank 7); newlines as statement separators (rank 8); the `<<` cut swallowing
later statements (rank 9); wrapper commands `uv run` / `npx` / `-m pytest` vs `-m unittest`
(rank 10); `find -exec` (rank 12); path-spelling missed joins; `_EXT_RE` matching `.5`.

**The structural gap both peers independently named:** `recall:outcome` rows carry no error
text and no exit code, so four of the 44 rows are unlabelable in principle and Class C can
never be adjudicated from the stream alone. One line of stderr per failure row would settle
them. That is the next instrument, and it is a schema change rather than a tuning change.
