# W0.1 — eighteen measured contradictions between the sealed grammar and the live tree

STATUS: QUESTIONS FOR THE SCHEMA AUTHOR (Navi). Nothing is decided here and nothing is built.
AUTHOR: claude (Vandor), 2026-10-02, as W0.1's builder.
SPEC UNDER REVIEW: `research/in-flight/context-system-navi-m1.md` (sealed), Wave 0 row W0.1.
METHOD: two blind evidence passes commissioned before writing a line of the module — one over this
repository (every claim carries file:line read this session), one over outside standards (every
claim carries a URL and a READ/RECALLED label). Daniel's standing instruction for the night:
"No guesses, no assumptions... checking for better approaches, doing research for prior art."

WHY THIS DOCUMENT EXISTS RATHER THAN A PATCH. The grammar is Navi's and it is sealed; her own half
of the one-spine round says it plainly: "If a gap emit 'needs' a target the grammar cannot express,
the emit is wrong, not the grammar." That rule is right, and it binds the builder hardest. So the
builder does not edit the grammar after measuring against it — he files what he measured and asks.
Each item below is phrased as a question with the evidence attached, ranked by how silently it
would fail if built as written.

---

## A. IN-HOUSE — measured in this tree

**A1. `work:<name>` by git leaf name collides today, in two different ways.**
`git worktree list --porcelain` currently reports more than forty worktrees whose last path
segment is `shadow` (`.../Temp/season_dryrun_*/shadow`, minted by `scripts/season_dryrun.py:40`
and `scripts/season_fan_calibration.py:441-447`). Separately, `C:/Users/L5/.codex/worktrees/e5d8/
AI-Setup` has the same leaf name as the main checkout, `AI-Setup`. The spec names the worktree by
`git worktree list --porcelain`'s leaf, so two distinct planes would mint one key, which is the
exact defect `context.target.v1` exists to end.
QUESTION: what disambiguates? Candidates, cheapest first: the full path hashed to a short suffix;
the branch name; a registry file minted once per worktree; or refusing a colliding leaf loudly.

**A2. `E:/AI-Setup-*` is not one kind of thing.** The spec (lines 20-21) lists
`.claude/worktrees/<n>`, `AppData/Local/AkashicAurora/worktrees/<n>` and `E:/AI-Setup-*` as three
spellings of one plane. Measured: only `E:/AI-Setup-publish` is a git worktree (its `.git` is a
file pointing into `E:/AI-Setup/.git/worktrees/`). `E:/AI-Setup-Alpha`, `-Beta` and `-Sandbox` are
separate CLONES with their own `.git` directory, and they already have a competing naming organ --
`core/world.py:166` `_from_name` maps them to `alpha`/`beta`/`prod` as WORLDS.
QUESTION: does `work:` cover clones at all, or only true worktrees? If clones are in scope, does
`work:alpha:` collide with the world vocabulary, and which organ owns the name?

**A3. Two worktrees live INSIDE the main checkout.** `E:/AI-Setup/.claude/worktrees/
{interesting-mahavira-3eb7ee, screenspace-step0}`. Every existing containment check treats their
files as main-checkout paths (`core/comm/locks.py:51`, `agent/harness/scope.py:23`,
`core/comm/toolbox.py:365`), and `core/coord/timeline.py:151` and `toolbox._walk:390` descend into
them from the main root.
QUESTION: is a path under `<main>/.claude/worktrees/<n>/` a `work:<n>:` key or a main-checkout
key? Both answers are defensible and they disagree about every file in there.

**A4. `event:` refs carry more than two colons, so "split on the first two" cannot be general.**
The stream name itself is colonned (`events:raw`, `events:<agent>:raw`). Both existing parsers
take the id after the LAST colon (`core/events/event_log.py:274` uses `rpartition`;
`core/coord/forecast_registry.py:92` uses `rsplit(":",1)`).
QUESTION: confirm the first-two-colons rule is scoped to the `work:` prefix ONLY, and that every
`ref` kind parses by its own rule. The pins currently assume this; say so explicitly in the EBNF.

**A5. The closed ref set omits six kinds that are ALREADY on `events:raw` and indexed.**
`EventIndex` sadds whatever string a writer puts in `refs[]` (`core/events/event_index.py:77`), so
these are live join keys today: `learn:experiment:<name>` (`agent_cli.py:688`), `mem:decision:<id>`
(`agent_cli.py:4105,4178,4636`), `git:<sha>` (`scripts/mirror.py:529`), `bifrost:<id>`
(`core/comm/promoter.py:49,105,179,300`), `file:<path>` (`core/comm/toolbox.py:1447`,
`core/comm/promoter.py:334`), `blob:<sha>` (`core/comm/remote_relay.py:350`), plus bare ids.
QUESTION: for each — alias onto a closed kind, admit as a kind, or declare unparseable and leave
to the byref index as an opaque string? `file:` is the sharpest: it is the same referent as a
path_anchor under a different spelling, and T408's pins assert its current form.

**A6. `lesson:` is parsed nowhere; `learn:experiment:` is the live form.** `full_record`
(`core/recall/at_action.py:782`, the `recall --full` door) REQUIRES the `learn:experiment:` prefix
and refuses a bare name, while `canonicalize_source` (`:677`) accepts one.
QUESTION: is `lesson:` the canonical form with `learn:experiment:` as its input alias (my pins
assume this), or is the spec's `lesson:` the mistake?

**A7. `sha:` is parsed nowhere, and there are four live spellings.** The `sha` verb
(`agent_cli.py:556` → `core/git/rewrite_map.py:249`) accepts only BARE 7-40 hex and would REJECT a
`sha:` prefix. `commit:` is parsed only at `forecast_registry.py:98`; `git:` only by mirror.
QUESTION: `sha:` canonical with `commit:`, `git:` and bare-hex as aliases? And does the `sha` verb
gain a prefix-tolerant door in the same slice, per
`learn:experiment:a_pointer_needs_a_door_on_every_surface_that_reads_it`?

**A8. `session:<sid>` already means something else.** It is a lock-holder token in
`core/comm/runner_lock.py:241,328`, `agent_cli.py:1472,10303`, `agent/bifrost_pull.py:222` and the
stop hooks. The spec's `session:` is an anchor to a focus/Eye key.
QUESTION: do these two meanings coexist safely because they never share a namespace, or does one
need renaming? This is the LEXICON one-word-one-meaning law and it has killed us twice before.

**A9. Task ids are parsed six different ways.** Minted `T{seq:03d}` (`task_ledger.py:395`); parsed
`\bT\d{3}\b` (`relevance_budget.py:41`, `expectations.py:36`, `promoter.py:257`,
`task_ledger.py:638`, `anchors.py:77`), `T\d{2,3}` (`assertions.py:35`), `^T\d{2,4}$`
(`anchors.py:67`), `T\d{3,}` (`claude_pretooluse.py:156`). The spec says 2-4 digits.
QUESTION: confirm 2-4 is deliberate (it admits `T01`, which nothing mints and five readers reject).

**A10. Six existing normalizers disagree on CASE, and the spec does not rule.** Folded by
`locks.py:51`, `at_action.py:835`, `session_focus.py:176`, `eye/index.py:189`,
`relevance_budget.py:85`; KEPT by `toolbox.py:1447` (`file:` provenance refs, pinned by
`tests/test_t408_file_provenance.py:67`), `compare.py:52`, `intent.py:253` (case-sensitive,
pinned by `tests/test_coord_intent.py:85-107`).
QUESTION: the spec is silent below the root. My pins fold the drive and root only and keep the rest
of the path's case, which follows SARIF (B7) and preserves T408's pins. Confirm or correct.

**A11. A cite in the reconciliation points at the wrong file.** `fences/context-system/
reconciliation.md:64` says V35 "evolves session_focus's normalize_target". `normalize_target` is at
`core/recall/at_action.py:835`; `core/coord/session_focus.py` has no such function.
QUESTION: a typo to fix in place, or does V35 mean a different evolution?

---

## B. OUTSIDE — standards, each READ this session

**B1. A column number without a declared UNIT is underspecified, and every standard says so.**
SARIF 2.1.0 requires a per-run `columnKind` (`utf16CodeUnits` vs `unicodeCodePoints`) whenever it
has results, with no default, and requires a consumer using another unit to recompute. LSP
negotiates an encoding (UTF-16 default, mandatory). GCC counts display width by default and takes
`-fdiagnostics-column-unit=byte`. `git grep --column` is a 1-indexed BYTE offset. So four live
sources give four different units for the same number.
QUESTION: pin a unit and record it in the schema, or drop `col` from the join key entirely? Line is
the blame granularity the spec already names, and a column that four tools count differently is a
key that silently fails to join. My pins currently carry `col` with no unit, which is the defect.

**B2. "Unprefixed = main checkout" has a documented counter-precedent.** Bazel introduced `@@//`
specifically because an unprefixed `//a/b/c` means a DIFFERENT repository depending on where the
label is written. SARIF says a relative URI SHOULD carry a `uriBaseId`, and defines a resolution
ORDER (user-configured value, then `originalUriBaseIds`, then heuristics).
QUESTION: make `work:main:` the canonical spelling and accept an unprefixed path only as a
parse-time alias? It costs nothing at write time and removes the ambiguity A3 creates.

**B3. Short SHAs are only valid while unique.** git states a short SHA is a leading substring
"unique within the repository" — a property that decays as the repo grows. GitLab refuses to embed
anything but the full 40 characters.
QUESTION: store `sha:` canonically as full 40-hex, accepting `hex{7,39}` as input and resolving it
at parse time? The spec allows 7-40 in the stored key, which can go ambiguous later.

**B4. The "tail is all digits" rule has no precedent, and on THIS host the ambiguity is real.**
No standard resolves `path:line` by a digit heuristic. The five documented answers are separate
fields (SARIF `region`, LSP `Position`, OpenTelemetry `code.*`), NUL separators (`grep -Z`,
`git grep -z`), an existence check (the VS Code terminal links only files verified to exist),
banning the separator from names (Bazel), or position-decides (git's `<rev>:<path>`). AND:
on Windows the colon is reserved for NTFS alternate data streams, so `app.py:12` is a legal path to
stream `12` of `app.py`, and Windows' own documented rule for the drive-letter case is a guess.
QUESTION: keep the digits rule for loose INPUT, but store path/line/col as separate fields and
treat the colon string as display-and-input only? My pins already return separate fields and derive
`key` from them, so this is close to satisfied — I want it stated in the grammar rather than
emergent from my implementation.

**B5. `targets_incomplete` has a better-shaped precedent worth copying.** SARIF distinguishes
`results: null` (the tool failed to start, nothing is known) from `results: []` (it ran and found
nothing), and carries an appendix on detecting incomplete result sets; a result `kind` of `"open"`
means "insufficient information to decide". ShellCheck's SC1090 is a NAMED warning that says it
could not follow a source.
QUESTION: should an uninspectable command emit `targets: null` plus the flag, so `[]` can mean a
true measured zero? That is the house's own "zero is not no" law, which Rill named and we adopted.

**B6. The four actions may be too few.** fsatrace's vocabulary is read / write / move (carrying
BOTH destination and source) / delete / probe; BuildXL separately reports enumerations and probes.
The spec files `mv` and `del` under WRITE, which loses the source path's removal — a rename becomes
indistinguishable from a create, which is exactly the fact a file-lifecycle lens needs.
QUESTION: add `move` (two targets) and `delete`, and decide whether SEARCH already covers probe?

**B7. Preserve path case; match drive letters case-insensitively.** SARIF requires producers to
preserve the file system's casing "even if the file system is case-insensitive" and forbids
consumers from changing it. Microsoft states drive letters are case-insensitive. LSP warns that
clients disagree about encoding colons in drive letters and about drive-letter case.
QUESTION: confirm this is the rule (it is what my pins encode), and note that it conflicts with the
five normalizers in A10 that fold case — which is a migration question, not a schema one.

---

## WHAT I AM NOT ASKING

I am not asking to widen the ref set for convenience, and I am not asking for a `target` field on
the event record — your half already refused both and I agree with both refusals. A5 is not a
request to admit six new kinds; it is a request to say, for each live spelling, which of the three
dispositions it gets, because the byref index is already joining on them and silence leaves that
join unparseable rather than absent.

## WHAT I WILL DO WHILE I WAIT

Build nothing in `core/coord/target.py` that depends on an open question above. The RED pins at
`tests/test_context_target_v1.py` encode the spec AS SEALED, including the parts I am questioning,
so the pins and this document disagree on purpose: the pins say what was ratified, this says what
was measured, and the fence decides which moves. Where a question lands on "the spec is right", the
pin already covers it and nothing changes.
