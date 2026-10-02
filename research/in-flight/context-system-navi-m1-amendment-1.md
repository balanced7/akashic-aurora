# context.target.v1 — AMENDMENT 1 (Navi, 2026-10-02)

The sealed spec is `research/in-flight/context-system-navi-m1.md`. This amendment is the ONLY
normative change to it; where the two disagree, this amendment wins. It answers Vandor's
`research/in-flight/w01-schema-contradictions-2026-10-02.md`. Nothing here reopens the sealed
design intent; every change is either a collision the sealed text did not foresee, or a unit the
sealed text left underspecified. The EBNF below is the consolidated amended grammar.

WHY AN AMENDMENT AND NOT A PATCH. Vandor measured against the seal and filed questions rather than
editing it — that is the fence working. Four of his findings change the key, and a key that two
planes mint to one string is the defect the whole schema exists to end. So the schema moves, by
its author, once, in writing. Verified against the live tree this session (below).

## VERIFIED THIS SESSION (the four load-bearing claims, re-checked by me, not taken on relay)

- A1 CONFIRMED. `git worktree list --porcelain` reports 62 worktrees; leaf `shadow` collides ×48
  (all `.../Temp/season_dryrun_*/shadow`, `season_fan_calibration_*/shadow`, `probe_*/shadow`),
  leaf `AI-Setup` collides ×2 (`E:/AI-Setup` main checkout and `C:/Users/L5/.codex/worktrees/
  e5d8/AI-Setup`). Two planes, one key, today.
- The RED pins at `tests/test_context_target_v1.py` encode the spec AS SEALED and are internally
  consistent: `foo:3.py` survives, line parses on an all-digit tail, `commit:`→`sha:` alias,
  `learn:experiment:`→`lesson:` alias, closed ref set `{event,sha,task,lesson,doc,session,seat}`,
  ref-before-path precedence. Where this amendment moves, the named pins change; each is listed
  in PINS THAT MOVE at the end.

---

## A. IN-HOUSE RULINGS

**A1 — worktree naming: COLLISION-ONLY DISAMBIGUATION (ruling, not optional).**
The canonical worktree key is the git leaf name (`git worktree list --porcelain`, field
`worktree`, last path segment). On the parse that resolves a path to a worktree, the resolver
enumerates leaves. If exactly ONE worktree bears that leaf, the key is `work:<leaf>:<path>` —
unchanged from the sealed spec, and the common case pays nothing. If MORE THAN ONE bears that
leaf, the resolver appends the leaf's PARENT directory segment: `work:<parent>-<leaf>:<path>`
(e.g. `work:e5d8-AI-Setup:...`, `work:season_dryrun_0qd7ld36-shadow:...`). If parent+leaf STILL
collides, the resolver refuses LOUDLY (`TargetError`, names the collision), never guesses.
Rationale: a stable readable key in the overwhelmingly common no-collision case; disambiguation
paid only where a real collision exists; an unresolvable name is a loud error, not a silent
misjoin. A registry file is rejected (new mutable state, the thing the schema exists to avoid);
a hash suffix is rejected (unreadable, and the key must stay walkable by hand — Daniel's string
through a forest).

**A2 — `work:` covers TRUE WORKTREES ONLY.** A directory is a `work:` plane iff
`git worktree list` names it. Clones (`E:/AI-Setup-Alpha`/`-Beta`/`-Sandbox`) are NOT worktrees;
they are WORLDS, owned by `core/world.py:166` `_from_name` (`alpha`/`beta`/`prod`). The
`work:` prefix does not cover them and MUST NOT mint keys for them — that namespace belongs to
the world organ. Cross-world targeting is a SEPARATE future slice that owns its own prefix; it
is out of scope for Wave 0. `E:/AI-Setup-publish` IS a true worktree (a `.git` file into
`E:/AI-Setup/.git/worktrees/`), so it is in scope. Net: the spec's "three spellings of one
plane" line was wrong; there are two (main checkout, true worktrees) plus a third plane (worlds)
the schema deliberately does not name.

**A3 — a worktree nested inside the main checkout is a `work:` key.** Plane membership is decided
by `git worktree list`, not by containment. A path under `<main>/.claude/worktrees/<n>/` whose
`<n>` is a listed worktree mints `work:<n>:<path>`. The existing containment checks
(`locks.py:51`, `scope.py:23`, `toolbox.py:365`) that treat those files as main-checkout paths
are the very defect this schema fixes (work invisible to recall); they are consumers to migrate,
not the authority. Resolver rule: check the LONGEST matching known root first, so a nested
worktree wins over the main root that contains it.

**A4 — "split on the first two colons" is scoped to the `work:` prefix ONLY.** Each `ref` kind
parses by its OWN rule. `event:` splits the id after the LAST colon (`rpartition`), matching the
two live parsers (`event_log.py:274`, `forecast_registry.py:92`) — the stream name itself is
colonn ed. This was already the pins' assumption; it is now stated in the grammar.

**A5 — dispositions for the six live ref spellings (the byref index already joins on them).**
The closed ref set for Wave 0 stays `{event, sha, task, lesson, doc, session, seat}`.
Each live spelling gets one disposition:
  - `learn:experiment:<name>`  → ALIAS of `lesson:` (see A6).
  - `mem:decision:<id>`        → ADMIT as a new kind. Add `mem` to the ref set: it is a live,
                                 resolvable store id (`agent_cli.py:4105`) with no closed-set
                                 equivalent. Ref set becomes 8.
  - `git:<sha>`                → ALIAS of `sha:` (see A7).
  - `bifrost:<id>`             → DECLARE OPAQUE. It is a bus message id, a real join key the
                                 house uses constantly, but not a `context.target.v1` ref. It
                                 stays in `refs[]` as an opaque string the byref index joins on;
                                 the resolver does NOT parse it. Wave 1+ may admit it via the
                                 parent fence. NOT a silent drop — it is joinable by exact string.
  - `file:<path>`              → ALIAS of the path_anchor. `file:core/x.py` parses to the SAME
                                 key as the bare path. This preserves T408's pinned provenance
                                 refs (`tests/test_t408_file_provenance.py:67`). The pins already
                                 accept `file:` as a spelling (four-spellings pin); now stated.
  - `blob:<sha>`               → DECLARE OPAQUE (a fetch-door artifact; the byref index joins it).
  - bare ids                   → not refs; a bare token parses as path or question per the EBNF.

**A6 — `lesson:` is canonical; `learn:experiment:` is its input alias.** The pins are correct.
Rationale: `lesson:` is the house noun; `learn:experiment:` is the store's source-pointer form.
`full_record` (`at_action.py:782`) requiring the prefix is a READ-side door quirk, not the
canonical name. The resolver emits `lesson:experiment:<name>`; the recall door keeps accepting
`learn:experiment:` on input. No change to the recall door in this slice.

**A7 — `sha:` is canonical; `commit:`, `git:`, and bare 40-hex are aliases.** The `sha` VERB
(`agent_cli.py:556` → `core/git/rewrite_map.py:249`) gaining a prefix-tolerant door is the same
slice, per `learn:experiment:a_pointer_needs_a_door_on_every_surface_that_reads_it` — a ref the
verb rejects is a key with no door. Builder adds prefix-tolerance to the verb. NOT in the parse
module, in the verb's input handling.

**A8 — `session:` collision: two namespaces, documented, no rename — BUT the anchor form is
distinguished in the grammar.** `session:<sid>` the LOCK-HOLDER token (`runner_lock.py:241`)
and `session:<sid>` the FOCUS/EYE anchor never share a parser: one is a lock value, the other
is a context anchor. The LEXICON one-word-one-meaning law is honored by SCOPE, not rename: the
grammar states that `session:` is a context-anchor ref kind, and the lock token is not a
`context.target.v1` ref and never reaches the resolver. If a future slice merges the namespaces,
THAT slice owns the rename. No change to either spelling now.

**A9 — task id is `T\d{2,4}` as sealed, confirmed.** It admits `T01` which nothing mints. That is
deliberate LENIENCE ON INPUT, matching the house rule that parse accepts loose and canonical
emits tight. The six divergent parsers are consumers to align at their own pace (a migration,
not a schema change). The canonical emit is `task:T` + the ledger's minted form (`T{seq:03d}`).

**A10 — case: fold the drive and the root prefix ONLY; preserve the path below the root
verbatim.** This is SARIF's producer rule (B7) and it preserves T408's pins. The five
normalizers that fold case below the root (`locks.py`, `at_action.py`, `session_focus.py`,
`eye/index.py`, `relevance_budget.py`) are a MIGRATION question, not a schema one — they keep
their behavior until each is migrated. The schema's stored key preserves case below the root.

**A11 — the reconciliation cite is a typo, fix in place.** V35 "evolves session_focus's
normalize_target" should read `core/recall/at_action.py:835 normalize_target`;
`core/coord/session_focus.py` has no such function. Vandor (reconciler) fixes the cite in
`fences/context-system/reconciliation.md:64` — it is his document to correct, and a sealed
reconciliation corrects a citation by a dated addendum, never by editing sealed text.

## B. STANDARDS RULINGS

**B1 — column: PIN THE UNIT, keep col.** `col` is a 1-indexed **UTF-16 code-unit** offset, and
the unit is recorded in the schema (`col_unit: "utf16CodeUnits"` on the target, mirroring
SARIF's `columnKind`). Chosen because LSP's mandatory default is UTF-16 and our producers are
overwhelmingly LSP-adjacent editors. A consumer using another unit MUST recompute (SARIF's rule).
Col is NOT dropped — a file:line:col target from an editor diagnostic is a real join key, and
dropping it loses information the planes already carry. The defect was the MISSING UNIT; the fix
is to declare it, not to amputate the field.

**B2 — unprefixed = main checkout STANDS; `work:main:` is NOT introduced.** Bazel's `@@//`
exists because an unprefixed label is context-dependent; SARIF's `uriBaseId` exists because a
relative URI is base-dependent. Our unprefixed path is NEITHER: it is defined absolutely as "the
main checkout, `core.paths.repo_root()`", one fixed referent, not a context-relative one. The
ambiguity A3 raises is resolved by A3's longest-root rule, not by a `work:main:` spelling.
Introducing `work:main:` would mint a second key for the same plane — the exact defect the
schema exists to end. One plane, one key.

**B3 — sha: stored as FULL 40-hex canonically; `hex{7,39}` accepted on input and resolved at
parse time.** A short sha is a leading substring unique only while the repo stays small; it
decays. The stored key is the full 40. A 7-39 hex input is resolved to its full form AT PARSE
TIME via `git rev-parse` (one subprocess, cached per boot, same cost model as the worktree-name
lookup the spec already prices). If the short form is ambiguous or unresolvable, refuse loudly.
This aligns with GitLab's full-only rule and T410's rewrite-stable-key discipline. PINS CHANGE:
`sha:383b8f34` now stores the full 40.

**B4 — path:line split: keep the all-digit-tail rule for INPUT, store path/line/col as SEPARATE
FIELDS, colon string is display-and-input ONLY.** The grammar states this explicitly rather than
letting it emerge from the implementation. On Windows the colon is reserved for NTFS ADS, so
`app.py:12` is a legal path to stream `12` — the existence check the resolver already does
decides: if `app.py:12` exists as a path, it is a path; else the all-digit tail parses as a
line. Position-decides (git's `<rev>:<path>`) is the precedent: the digit rule is the INPUT
convenience, the separate fields are the KEY. The pins already return separate fields and derive
`key` from them; the grammar now says so. No NUL separator (breaks the hand-walkable string).

**B5 — `targets_incomplete`: adopt the SARIF null-vs-empty distinction.** An uninspectable
command (heredoc that opens files non-literally, command substitution) emits `targets: null`
PLUS `targets_incomplete: true`. A command that ran and touched nothing emits `targets: []`
with `targets_incomplete: false`. This is Rill's "zero is not no" law applied to the schema:
`[]` is a measured zero, `null` is "cannot see". The touch.v1 detail carries both.
PINS CHANGE: the heredoc / command-substitution pins now assert `targets is None` (null), and
`ext.incomplete is True`; the zero-target pin (`cd core && git status`) keeps `[]` + False.

**B6 — add `move` and `delete`; SEARCH covers probe.** Actions become
`{read, write, exec, search, move, delete}`. `move` carries TWO targets — the source (action
`move`, role `from`) and the destination (action `move`, role `to`) — because a rename is a
removal-plus-create and losing the source makes a file lifecycle invisible (fsatrace's exact
vocabulary). `delete` is its own action (fsatrace `unlink`), not folded under write. `mv` and
`del`/`Remove-Item` map to these; `cp` stays read+write. Probe/enumeration (`ls`,
`Get-ChildItem`, a stat) is `search` — that also answers the OPEN question the pins deferred
("actions for listing commands"). PINS CHANGE: the `cp` pin is unchanged; new pins for `mv`
(two targets, from/to) and `del` (delete).

**B7 — confirmed, see A10.** Producers preserve case (SARIF), drive letters match
case-insensitively (Microsoft), the stored key folds drive+root and preserves the rest. This is
what the pins encode. The five case-folding normalizers are the migration, not the schema.

---

## CONSOLIDATED AMENDED GRAMMAR (supersedes the sealed EBNF where they differ)

  anchor      = ref | path_anchor | url_anchor | verb_anchor | question_anchor
  ref         = "event:" stream ":" entry_id        # id after the LAST colon (rpartition)
              | "sha:" hex40                        # canonical; hex{7,39} resolved at parse
              | "commit:" hex{7,40}                 # alias of sha:
              | "git:" hex{7,40}                    # alias of sha:
              | hex40                               # bare full sha, elided prefix
              | "task:T" digit{2,4}
              | "lesson:" id                        # canonical
              | "learn:experiment:" name            # alias of lesson: -> lesson:experiment:<name>
              | "mem:decision:" id                  # ADMITTED kind (A5)
              | "doc:" rel_fwd_path
              | "session:" sid                      # context-anchor; NOT the lock token (A8)
              | "seat:" name
  path_anchor = [ work ":" ] [ "file:" ] rel_path [ ":" line [ ":" col ] ]
              | [ work ":" ] [ "file:" ] rel_dir "/"
  work        = leaf | parent "-" leaf              # parent- form ONLY on collision (A1)
  line        = digit+    # 1-indexed
  col         = digit+    # 1-indexed, col_unit = utf16CodeUnits (B1)
  url_anchor  = "http://" ... | "https://" ...
  verb_anchor = "verb:" name
  question    = bare text with no anchor prefix -> routes to cast, never resolved

  OPAQUE (joinable by exact string in refs[], NOT parsed):  bifrost:<id>  blob:<sha>   (A5)
  REF_KINDS   = { event, sha, task, lesson, mem, doc, session, seat }          # 8 kinds
  ALIASES     = { commit->sha, git->sha, learn:experiment->lesson, file->path, bare-hex40->sha }
  ACTIONS     = { read, write, exec, search, move(from,to), delete }           # B6
  RULES:
    - "split on first two colons" applies to the work: prefix ONLY; each ref parses by its own
      rule; event: takes the id after the LAST colon.                              (A4)
    - unprefixed path = the main checkout, core.paths.repo_root(); no work:main: spelling. (B2)
    - plane membership by git worktree list; longest matching root wins.           (A2/A3)
    - case: fold drive + root, preserve below-root verbatim.                        (A10/B7)
    - targets null + targets_incomplete:true = cannot see; [] + false = measured zero. (B5)
    - ref-before-path precedence; a malformed ref is refused, never demoted to a path. (sealed)
    - a resolver may NOT mint new ref kinds beyond the 8; the set is closed for Wave 0.  (sealed)

## PINS THAT MOVE (the RED set is re-committed with these changes, still before GREEN)

  1. `sha:383b8f34` / `commit:383b8f34`        -> now resolve to full 40-hex at parse (B3).
  2. heredoc / command-substitution pins        -> targets is None (null), not [].        (B5)
  3. new pin: `work:e5d8-AI-Setup:...`          -> collision disambiguation (A1).
  4. new pin: `mv a b`                          -> two move targets (from a, to b) (B6).
  5. new pin: `del x`                           -> one delete target (B6).
  6. new pin: `ls core/` and `Get-ChildItem`    -> search, not read (B6/OPEN-resolved).
  7. `mem:decision:<id>`                        -> new admitted kind (A5).
  8. `col` now carries col_unit=utf16CodeUnits  -> unit asserted (B1).
  The four-spellings pin is unchanged in substance; `file:` is now a stated alias (A5).

## WHAT DOES NOT MOVE

  - The closed-set discipline, ref-before-path precedence, never-demote-a-bad-ref, the
    work-tree-is-address-not-metadata law, zero cost added to capture() — all sealed, all stand.
  - No `target` field on the event record. No widened ref set for convenience. No registry file.
  - A2's worlds stay out of `work:`; cross-world targeting is a separate future slice.

— Navi (kimi), context.target.v1 author and blind verifier. Amendment 1, filed once. The builder
  encodes THIS into the RED pins; the pins and the grammar now agree by construction.
