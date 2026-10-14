# Inline Python goes to a file first (design notes, not yet approved to build)

Status: in-flight · Type: design notes · Date: 2026-10-13 · Author: claude (Vandor)

Daniel, 2026-10-13, on fix 1 of the shader-school retrospective
(`research/in-flight/retro-shader-school-2026-10-13/SYNTHESIS.md`, "Stop typing Python through the shell"):
"For point 1, can we put in an intelligent parser that creates the file in the ramdisk x and runs it automagically?
What are some clever solutions we can think of for this?"

## The problem, measured

About 2,100 inline snippets (560 heredocs, 1,533 `py -c`) in 161 agents in one night; 29 quoting failures; 2 silent
corruptions (a real newline written into a test file; control bytes written into three dissector regex lines). Known
since July: lessons `bash_heredocs_corrupt_regex_backslash_b_to_backspace`, `process_match_by_argv_not_substring_and_no_backslashes`, open wish W234.

Two layers do the damage, and a file fixes only the first:

1. **The shell layer.** Bash double quotes eat `\\ \" \$ \``; PowerShell 5.1 mangles embedded quotes passed to native
   programs. Moving the source into a file removes this layer entirely.
2. **The Python literal layer.** `"\b"` in an ordinary Python string is a backspace, in a file or not. Only a check of the
   parsed source catches it.

## The layers proposed to Daniel (bus, 2026-10-13 20:31Z)

1. **Auto-file.** A PreToolUse hook on Bash and PowerShell sees the command as the agent wrote it, before any shell
   parses it. A long snippet, or one holding a backslash, is written to `X:\Temp\snips\<agent>\<sha12>.py` (fallback
   `%TEMP%\snips` when X: is absent) and the command is rewritten to run that file. Short clean one-liners pass untouched.
2. **Read before run.** `ast.parse` the extracted source; refuse with the exact line on a syntax error before anything
   executes. Walk string constants: a non-raw string holding control characters (`\x08` and kin) where a regex is built
   gets "did you mean r'\b'?".
3. **Guard after writing.** Snapshot `git status --porcelain` plus hashes before the command and compare after; a tracked
   text file that gained bytes below 0x20 other than tab and newline, or a CR, alerts at once.
4. **The second press** (Daniel's principle, memory `second-press-principle`): the first time, file and run quietly; the
   same shape again from the same agent gets "snippet #3 of this kind, saved here; want it as a verb?".
5. **Automatic census.** Every snippet's hash and shape go to a small index (on E:, since X: forgets at reboot); a daily
   report lists the recurring shapes as verb candidates. This turns the retro's hand count into a standing organ.
6. **Repo edits through Edit.** A snippet that opens a tracked file for writing is nudged to the Edit tool, which keeps
   the advisory-lock check (`scripts/hooks/claude_pretooluse.py` runs it only for Edit and Write) and LF endings.

Recommended order: 1 and 2 (they remove the 29 failures), then 3, then 4 with 5. Fence the design with Heimdall (house
rule: system work ships fenced). Daniel said yes to version 1 on 2026-10-13 ("Yes please").

## Heimdall's fence read (bus, 2026-10-13 20:36Z), adopted

1. Assert the byte path end to end: what the hook sees, what the file holds, what the interpreter receives; refuse if
   any step re-parses. `_win_exec` exists because Windows re-tokenizes at the subprocess boundary.
2. The literal check runs on the extracted snippet and is a REFUSAL with the exact line, never a silent rewrite: a
   silent "normalize" is how the dissector's regex lines got control bytes.

## Version 1 spec (layers 1 and 2 only; un-wired until the live test passes)

- `scripts/hooks/snippet_autofile.py`: a pure `decide(payload) -> dict | None` plus a stdin/stdout entry point that
  prints the hook JSON. No permissionDecision is ever returned except `deny` for a refusal.
- **Shapes handled in v1** (anything else passes through untouched; a bounded scope is better than a wrong rewrite):
  - Bash: `py|python|python3 [flags] -c <arg> [args]`, where `<arg>` is single-quoted (literal) or double-quoted
    (bash rules: `\\ \" \$ \`` and backslash-newline are the only escapes; an unescaped `$` or backquote inside means
    bash would expand it, so refuse with advice rather than guess). The rest of the command (pipes, `&&`, redirects)
    is kept byte for byte around the replaced span.
  - Bash heredoc into Python with a QUOTED delimiter (`py - <<'EOF'`, `python3 <<"PY"`): the body is literal; it is
    extracted exactly. An UNQUOTED delimiter whose body holds `\`, `$` or a backquote is refused with "quote the
    delimiter or write a file".
  - PowerShell: `py -c '<arg>'` (single quotes, `''` is one quote) and `@' ... '@ | py -` here-strings; a double-quoted
    PowerShell argument holding `$` or a backquote is refused with advice.
- **When to file**: the snippet holds a backslash, or is longer than 3 lines or 300 characters. Shorter clean
  snippets pass untouched.
- **Lint before run**: `ast.parse` the extracted source; a SyntaxError is a deny naming line and column. Any string
  constant holding `\x07`, `\x08`, `\x0b` or `\x0c` (what `\a \b \v \f` become outside a raw string) is a deny naming
  the line and suggesting `r'...'`; the marker comment `# autofile: control-chars-ok` opts a snippet out.
- **The file**: `X:\Temp\snips\<agent>\<sha12>.py` (agent from `AKASHIC_AGENT_ID` plus a short hash of the payload's
  session and transcript path, so siblings never share a folder); fallback `%TEMP%\snips\...` when X: is absent; LF,
  UTF-8, a two-line header naming the original command's hash and the time. Keep the newest 2,000 files per agent.
- **The rewrite**: `hookSpecificOutput.updatedInput` = the original `tool_input` with `command` replaced, plus
  `additionalContext` telling the agent where the snippet now lives ("saved as ...; next time, Write a file and run
  it").
- **Pins** (red first): every shape above round-trips (the file's bytes equal the intended source, byte for byte,
  including backslashes, quotes and non-ASCII); refusals for the expansion cases; the backspace trap refused; short
  snippets untouched; unknown shapes untouched; the rewritten command runs the file with the same trailing args and
  pipes; a spawn test that actually runs a rewritten command through bash and through PowerShell on safe snippets and
  compares output with the intended source's output (lesson `an_exec_quoting_fix_must_be_pinned_by_spawning_the_interpreter`).

## Facts checked before building (2026-10-13)

- **Rewriting a command.** The Claude Code hooks guide says: "When multiple `PreToolUse` hooks return `updatedInput` to
  rewrite a tool's arguments, the last one to finish takes effect." So the field exists. Not confirmed from the docs: its
  exact place in the JSON (expected `hookSpecificOutput.updatedInput` beside `permissionDecision`), whether it replaces or
  merges the input, the minimum version, and whether it fires for subagent and workflow tool calls. Settle all four with a
  throwaway hook in the sandbox clone before writing layer 1. Fallback if rewriting is unavailable: deny with the file
  already written and the exact one-line command to run it (the second-press shape, one extra turn).
- **Settled from the installed binary (2.1.280, read-only scan of `bin/claude.exe`, 2026-10-13 20:50Z).** Its built-in
  hook reference says `hookSpecificOutput` may carry "`updatedInput` - Modified tool input (PreToolUse only)", so the
  field sits at `hookSpecificOutput.updatedInput`. The binary validates it against the tool's input schema ("PreToolUse
  hook for ... returned updatedInput that failed schema validation"), so the hook returns the COMPLETE input with only
  `command` changed, which is correct whether the harness replaces or merges. In auto mode, a hook's allow is still
  funneled through the classifier ("auto mode requires classifier adjudication").
- **Hooks fire for subagent and workflow tool calls**: the retro counted about 1,418 recall-at-action injections (the
  house PreToolUse hook) inside subagent transcripts (`subagents-late.md`, `rederivations-vs-store.md`).
- **The live test must include the hint path** (Heimdall's sign-off, 2026-10-13): the byte-path attestation covers
  FILED snippets only. A hint-shape command (bash `$` or a backquote, PowerShell `$` or a backtick) deliberately lets
  the shell expand at run time, so the live test runs one and checks the expansion came out CORRECT, not merely that
  the command ran: that branch is the one seam where what the hook saw and what the interpreter got may differ.
- **The live test is still owed.** A nested `claude -p` run in a scratch folder with a throwaway hook failed before any
  tool call: "OAuth session expired and could not be refreshed" on the npm CLI (Daniel's login; refreshing it is his
  step). The hook ships un-wired until that live test passes.
- **`permissionDecision`.** `allow` skips the user's prompt but never overrides a deny rule; `deny` feeds the reason back
  to the agent; `ask` shows the normal prompt. Layer 1 should not return `allow` (it must not widen permissions); it
  should leave the decision to the existing rules.
- **PostToolUse cannot see changed files**, only the tool's name, input and output; layer 3 needs its own before/after
  snapshot.
- **X: is an ImDisk RAM drive of 1 GB**, present with 1.0 GB free. The house rule keeps source files off X:; these
  snippets are throwaway scratch, which is what X: is for. Rotate: keep the newest 2,000 files or 50 MB.
