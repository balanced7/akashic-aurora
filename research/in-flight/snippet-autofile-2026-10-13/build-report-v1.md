# Snippet auto-file hook, version 1: build report

Status: in-flight · Type: build report · Date: 2026-10-13 · Author: claude (build agent, for Vandor)

**Result.** Version 1 of the hook is built and all 139 pins pass.
- The build follows the binding sections of `design-notes.md` ("Version 1 spec" and "Heimdall's fence read").
- It also takes in the coordinator's revision of 2026-10-13: shell expansion now gets a gentle hint, and only
  certain bugs get a hard refusal.
- The hook is **un-wired**: nothing is in any settings.json, nothing is committed, nothing is written to Redis.

This report holds no command text from real transcripts, only counts and categories. The examples in it are
synthetic test probes.

## What exists

- **`scripts/hooks/snippet_autofile.py`** (ASCII, LF line endings)
  - `decide(payload, *, snips_root=None, now=None)`: one decision per PreToolUse payload. It writes a file only when
    it files a snippet, and writes the hint counter only when it gives a hint.
  - `main()`: reads stdin as UTF-8 bytes and prints ASCII JSON or nothing. It always exits 0. Internal exceptions go
    to `<snips root>\_errors.log`.
  - Settings: `AKASHIC_SNIPPET_AUTOFILE=0` turns it off, and `AKASHIC_SNIPS_ROOT` overrides where files go.
- **`tests/test_snippet_autofile.py`**: 139 pins. Ten of them spawn real Git bash and real `powershell.exe`.

## The four outcomes

All four outcomes apply only to a snippet the hook would otherwise file: one that holds a backslash, or runs longer
than 3 lines or 300 characters. Shorter snippets run exactly as they do today.

| Outcome | When | What the agent gets |
|---|---|---|
| **File** | a handled shape whose source is known before any shell parses it | `updatedInput` with only `command` changed to run `X:\Temp\snips\<agent>\<sha12>.py` (or `%TEMP%\snips` when X: is absent or unwritable); one line of `additionalContext` naming the file |
| **Hint** | the shell will expand part of the snippet on purpose. That is a bash `"..."` argument with `$` or a backquote, an unquoted heredoc body holding `\`, `$` or a backquote, or a PowerShell `"..."` holding `$` or a backtick | `additionalContext` only, under 200 characters, naming what will be expanded (`$HOME`, `` `date` ``, `$env:USERNAME`). The command runs exactly as written. The third hint for one agent folder inside ten minutes names its count, e.g. "(hint 3 in 10 min)". The count lives in that folder (`_expansion_hints.json`) |
| **Deny** | a certain bug only; see the next section | the exact line and column, what would have happened, and the fix |
| **Untouched** | everything else | nothing |

A command holding both a filed snippet and a hinted one gets the filing, with both lines in `additionalContext`. Any
deny wins over everything else in the command, and on a deny no file is written.

## Hard refusals (certain bugs only)

1. **SyntaxError.** The hook compiles the source but never runs it, and names the line and column in the snippet.
2. **Control character in a non-raw string or bytes literal.** That covers `\a \b \v \f`, `\x07`, `\x08`, `\x0b`,
   `\x0c`, the octal forms, `\u0008`, `\N{BACKSPACE}` and literal control bytes. The deny names the exact escape. For
   `\b` it asks "Did you mean r'\b'?". The comment `# autofile: control-chars-ok` opts a snippet out.
3. **A bash-style `` \` `` inside a PowerShell double-quoted string or here-string.** Measured on Windows PowerShell
   5.1.26100: PowerShell keeps the backslash and treats `` `X `` as its own escape.
   - `` `0 `a `b `f `n `r `t `v `` become NUL, bell, backspace, form feed, newline, carriage return, tab and vertical
     tab.
   - Every other `X` stays itself, so the backtick is simply dropped.

   The reason says which of these would have happened. This check runs before the expansion hint, so a mangled
   string with a `$` in it is still refused.
4. **A double quote inside a PowerShell `-c` argument.** Measured on 5.1: PowerShell hands it to py unescaped, and
   py's command-line parser treats a bare quote as a quoting toggle. Synthetic probe: `'a"b' 'c d'` arrived as
   `ab c` and `d e`. The reason says so.

## Shapes handled

- **Bash:**
  - `py`, `python` or `python3`, after optional `NAME=val` assignments and the words `if`, `then`, `do`, `!` or
    `time`, at any command position;
  - `-c '...'` and `-c "..."`;
  - `py [flags] - [args] <<'EOF'` (also `<<"EOF"` and `<< 'EOF'`), the same with no `-`, and an unquoted `<<EOF`
    whose body bash would not change.
  - The heredoc becomes `</dev/null`, and its body is removed from the command.
- **PowerShell:**
  - `py -c '...'`. `''` and doubled typographic quotes decode as 5.1 decodes them; I measured this.
  - `py -c "..."` and `py -c @'...'@` or `@"..."@`.
  - `@'...'@ | py [flags] [-] [args]`, also with `@"..."@`.
  - A leading `&` call operator.
- **Flags:** `-X v`, `-W v`, `-Xv`, `-Wv`, combined letters from `bBdEIOPqRsSuv`, and the py launcher's `-3.11` as
  the first argument.
- **Left untouched (bounded scope), among others:**
  - script files and `-m`;
  - `py` inside strings or comments;
  - `$'...'`, mixed-quote words, `-uc`;
  - `cat <<EOF | py -`, `<<-`, `<<<`;
  - `timeout` or `env` prefixes, `& 'py'`, `--%`, `py -c $var`;
  - unterminated quotes.

## The file

- **Header line 1** names the snippet hash, the original command's hash, the UTC time, and "the snippet starts on
  line 3".
- **Header line 2 is code.** It restores what the inline run had and a file run lacks:
  - `sys.path[0]`, which is the cwd for `-c`, not the snips folder. Every `py -c "from core..."` run from the repo
    depends on it.
  - `sys.argv[0]`: `-c`, `-` or empty.
  - `__file__`: absent for `-c`, `<stdin>` for a piped program.

  Spawn pins compare all three against real `py -c`, `py -` and `py` runs. A mutation probe that blanked line 2
  turned five spawn pins red.
- **Consequences of line 2:** a snippet with a `__future__` import passes untouched, and traceback line numbers are
  +2. The `additionalContext` line says so.
- **The source** follows the header byte for byte. The file is LF and UTF-8, with no shebang and no coding cookie.
- **Rotation** keeps the newest 2,000 files and at most 50 MB per agent folder.

## Red, then green

| Run | Result |
|---|---|
| Pins before the module existed | 125 collected, 0 passed (117 errors, 8 failures) |
| Pins against a do-nothing stub | 48 passed (the "leave it alone" pins, vacuous against a no-op by design), 77 failed |
| First green | 125 passed |
| Revision pins written first (hints, counter, PowerShell manglings) | 21 failed, 118 passed |
| Final: `py -m pytest tests/test_snippet_autofile.py -q` | **139 passed** |

## Census on real commands

Method:
- `decide` ran over every distinct Bash or PowerShell command mentioning `py` in the 2,000 newest local Claude Code
  transcripts (about 945 MB, read-only).
- Snippet files went to a temporary folder, deleted afterwards.
- The file list is frozen in the build session's scratch folder, so the fence read can rerun the identical sample.
  The only residual drift is the build session's own transcript, which is in the list and still growing.

| | Before the revision (refuse on expansion) | After the revision (hint on expansion) |
|---|---|---|
| Distinct commands | 9,260 | 9,216 (the "newest 2,000" window moved) |
| Filed | 3,244 | 3,214 |
| Filed, with a hint for another snippet in the same command | n/a | 9 |
| Hinted only | n/a | 160 (bash `-c`: 75, bash heredoc: 20, PowerShell: 65) |
| Denied | 177 | **8** |
| Untouched | 5,839 | 5,825 |

Deny categories:
- **Before:** 168 expansion, 7 SyntaxError, 1 PowerShell backtick, 1 unquoted-heredoc backslash.
- **After:** **SyntaxError 7, PowerShell backslash-backtick 1**. There were no control-character or PowerShell
  double-quote denies in this sample.

What the eight remaining denies were:
- The seven SyntaxErrors are all genuine on the house Python 3.11: backslashes inside f-string expressions.
- The PowerShell one is a real catch. A double-quoted string held bash-style backslash-backtick escapes, which 5.1
  would have silently rewritten.

Other results:
- No crashes in any run.
- No idempotence breaks: a rewritten command never files or denies again. A hint on it is expected, because a hinted
  snippet stays in place.
- `decide()` takes 0.06 ms at the median and about 7 ms at p99.

**Differential byte-path check (Heimdall's point 1).** For every snippet the hook files from the frozen sample, I
asked the real shell what the quoted text decodes to and compared that with the file body:
- for bash: `printf %s <word>`, or `cat` on the original heredoc;
- for PowerShell: `[Console]::Out.Write(<token>)`.

Result: **2,932 bash and 375 PowerShell snippets, 0 mismatches.** This was safe to run, because a filed snippet never
holds anything either shell would expand.

**Cost as a process:** median about 144 ms per shell call, against about 109 ms for any Python process on this
machine. Heavy imports load only on the analysis path, which saved about 12 ms.

## Choices the spec left open

1. **Header line 2 is code** (see "The file").
2. **Hints and refusals apply only to snippets that would be filed.** Short ones are untouched, so short one-liners
   that expand `$` keep working silently.
3. **The hint counter counts this hint too.** The third hint inside 600 seconds is the first to name its count. The
   counter is fail-open: if it cannot be written, the hint is given without a count.
4. **I handled more shapes than the spec lists.** All are pinned:
   - PowerShell double-quoted `-c`;
   - `@"..."@`;
   - `py -c @'...'@`;
   - bash `NAME=val` prefixes;
   - `<< 'EOF'`;
   - unquoted heredocs with a literal body.
5. **Lint uses `compile`, never execution.** It catches more than `ast.parse`, and it also checks bytes literals.
6. **The snips folder:**
   - Name: `<AKASHIC_AGENT_ID sanitised to [A-Za-z0-9_-]>-<sha8 of session_id, transcript_path, agent_id>`.
   - A hostile agent id cannot leave the root.
   - Writes go through a temporary file and `os.replace`.
   - The file's mtime is set to the decision time, so rotation is deterministic.

## Open items

- **The live harness test is still owed** before wiring (design notes, "live test owed"). Questions for it:
  - Does the permission check and the auto-mode classifier see the rewritten command?
  - Does `py 'X:/Temp/snips/...'` need an allowlist entry?
  - Is `updatedInput` honoured for subagent and workflow calls?
  - Does `additionalContext` reach the agent without a decision?
- **The lint compiles with the hook's own Python (3.11).** A `py -3.14 -c` snippet using 3.12-only syntax would be
  wrongly refused. None appeared in the sample.
- **The PowerShell double-quote deny would also catch a working edge case.** That case is a `\"`-escaped `-c`
  argument with no spaces. Measured: it reaches py intact. It is refused only when the snippet would be filed. None
  appeared in the sample.
- **Bash-style `\$` inside a PowerShell double-quoted string gets an expansion hint, not a deny.** PowerShell keeps
  the backslash and expands the variable. The hint names the variable.

## Experiments behind the measured claims

All run on this machine, 2026-10-13, with synthetic probes only:
- PowerShell 5.1 quote classes and here-string rules;
- PowerShell 5.1 native argument passing of `"`;
- PowerShell 5.1 `` \`X `` for 18 values of X;
- a no-space `\"` argument (`py -c 'print(\"hi\")'` printed `hi`), and `"a\$x"` (became `a\VALUE`);
- `sys.path[0]`, `argv[0]` and `__file__` for each Python launch mode on 3.11;
- Git bash argument passing to py.exe and `</dev/null`.

The scripts and outputs are in the build session's scratch folder, not in the repo.
