# Navi half_b -- message 1 of 3: A7 target grammar + B1 anchor grammar (ONE schema, context.target.v1)
# Brief: fences/context-system/brief.md. Blind half; half_a/half-sol/half-rill unread.

Grammar (EBNF). One type for both slots: an A7 `targets[]` entry IS a B1 anchor; `context <anchor>` takes the same strings.

  anchor      = ref | path_anchor | url_anchor | verb_anchor | question_anchor
  ref         = "event:" stream ":" entry_id        # event_log.event_ref(); ledger resolves
              | "sha:" hex{7,40}                    # bare 40-hex MAY elide prefix
              | "task:T" digit{2,4}
              | "lesson:" id                        # learn:experiment:<name> -> id = experiment:<name>
              | "doc:" rel_fwd_path                 # includes atom id art_... (adopted doc)
              | "session:" sid | "seat:" name | "commit:" hex{7,40}   # commit: = sha: alias
  path_anchor = [ work ":" ] rel_path [ ":" line [ ":" col ] ]   # work = worktree, see below
              | [ work ":" ] rel_dir "/"
  url_anchor  = "http://" ... | "https://" ...
  verb_anchor = "verb:" name
  question    = bare text with no anchor prefix -> routes to `cast` (E2), never resolved as an anchor

THE ONE NAME (where two planes name one thing differently): `work:<worktree>:`.
Worktrees appear in the corpus as `.claude/worktrees/<n>`, `C:/Users/L5/AppData/Local/AkashicAurora/
worktrees/<n>`, and `E:/AI-Setup-*` -- three spellings for one plane, and the plane is where
work dies invisible (learn:experiment:work_done_in_a_worktree_is_invisible_to_recall). The
canonical form is `work:<worktree-name>:<repo-rel-path>` with the name being the git worktree
leaf (`git worktree list --porcelain`, field `worktree`). Unprefixed paths = MAIN checkout
(core.paths.repo_root()); they are NOT rebased onto main's history -- the worktree prefix is
address, not metadata. Resolver splits on the FIRST two colons only, so Windows drive letters
never collide (a raw `E:\...` input is normalized: if it resolves inside a known worktree root
it is rewritten to canonical form, else rejected loudly, never guessed).

LINE/COL: `file:<path>:<line>[:<col>]` -- integers 1-based, suffix-parsed only when the tail is
all digits (a file named `foo:3.py` survives). `file:line` is the git-blame granularity; planes
that cannot see lines (touches at file granularity today) state so in fog[], never snap silently.
`dir/` requires the trailing slash -- the slash is the type marker (a dir and a same-named file
are different anchors).

What a Bash/PowerShell command "touches" (A1's extraction contract):
  READ   -- the command's argv path-like tokens opened for input: resolved against the captured
            cwd; tokens that are existing repo-relative paths, or absolute paths under any known
            worktree root. Glob expansions captured LITERALLY (`dir/*.py` -> `dir/`), never
            shell-expanded post-hoc.
  WRITE  -- redirections (`>`, `>>`, `Out-File`, `Set-Content`, `tee`), and the argv of known
            mutating verbs (cp/mv/del/rename/npm i ...). A command writing to a path emits ONE
            write target, not a read.
  EXEC   -- the invoked program/script itself (read of the executable path); cwd captured raw.
  SEARCH -- `grep -r PATTERN dir` -> `dir/` (action=search); rg/glob pattern+path likewise.
  PIPELINE/HEREDOC -- the command's OWN wrapper is NOT a target (the batch-edit blindness:
            learn:experiment:check_locks_before_editing_not_at_commit -- recall keyed on the
            wrapper saw zero). The extractor walks the pipeline's stages; a heredoc python that
            opens files yields those files only when they are literal in the script text --
            else the command contributes ZERO targets plus a `targets_incomplete:true` flag,
            never a fabricated target. Zero-target commands (cd, git status) emit the touch
            with empty targets[] and the cwd; they are context, not touches of an anchor.
  FORBIDDEN: resolving symlinks past the worktree root, following `..` above root (clamp +
  flag), or string-matching the command text for prose words that look like paths (the
  session_focus substring heuristic at core/coord/session_focus.py:~180 stays OUT of this
  plane -- false hits are the class it already owns).

B1 anchor types, typed like orient's destinations (verb:<name> / seat:<id> -- never guessed):
the six types are {file, file:line, dir, url, verb, ref}. `ref` is Daniel's addendum, folded in:
EVERY row any plane returns must be addressable by a ref the existing doors resolve --
  event:<stream>:<id>  (event_log.event_ref, followable; a Beat.source)
  sha:<hex>            (git; T410's sha verb already resolves rewritten history)
  task:T###            (the git-durable task ledger)
  lesson:<id>          (learning store record id)
  doc:<path>           (docs/library projection path or art_ atom id; the atom is truth)
  session:<sid>        (focus/Eye key)
An anchor that is none of these is a `question` and routes to cast. A resolver may NOT mint
new ref kinds; the set is closed for Wave 0 (seat:/commit: are aliases, not new kinds).

COSTS (stated separately, per the brief's law):
  write -- parse + normalize per target: O(len), no I/O except the worktree-name lookup
  (cache `git worktree list` per process; one subprocess per boot, not per call). Zero cost
  added to capture() itself: targets arrive already typed.
  read -- anchor -> byref lookup is the existing EventIndex `events:raw:byref:<ref>` SADD set:
  O(1) per ref + O(k) payload resolution; no new index. file:line's blame is one `git blame -L`
  at read time, never stored.
  false-if -- a ref prefix collides with a path (a file literally named `task:T001`); the EBNF's
  first-alternative-wins order (ref before path) is the documented resolution, pinned.
