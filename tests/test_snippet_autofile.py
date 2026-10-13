"""PINS: scripts/hooks/snippet_autofile.py -- inline Python goes to a file first (version 1).

Spec (binding): research/in-flight/snippet-autofile-2026-10-13/design-notes.md, sections
"Version 1 spec" and "Heimdall's fence read". Daniel, 2026-10-13: "For point 1, can we put in an
intelligent parser that creates the file in the ramdisk x and runs it automagically?" then
"Yes please". The night it answers: about 2,100 inline snippets, 29 quoting failures, 2 silent
corruptions (one where "\\b" in a regex became a backspace byte).

What is pinned, in the spec's order:
  1. ROUND TRIP. Every handled shape files the snippet so that the file's bytes after its two-line
     header equal the intended source byte for byte: backslashes, both quote kinds, non-ASCII,
     tabs, a raw-string regex holding \\d and \\b.
  2. HINTS, not refusals, for the EXPANSION cases (coordinator, 2026-10-13, after the census found
     168 of 9,260 real commands -- 1.8% -- relying on expansion on purpose): a bash double-quoted
     argument with $ or a backquote; an unquoted heredoc body holding \\ $ or a backquote; a
     PowerShell double-quoted argument with $ or a backtick. The command runs exactly as today
     (no updatedInput, no permissionDecision); one additionalContext line under 200 characters
     names what the shell will expand. The third hint inside ten minutes for one agent folder
     names its count ("the second press is a question"), counted in that folder.
  3. HARD REFUSALS only for certain bugs, each naming the exact line and column and the fix: a
     SyntaxError; a control character (the backspace trap) in a non-raw string, with the
     "# autofile: control-chars-ok" opt-out; and the PowerShell manglings measured on 5.1 -- a
     bash-style backslash-backtick in a double-quoted string, and a double quote inside a -c
     argument -- each reason saying what PowerShell would have done.
  4. UNTOUCHED: short clean snippets, and every shape v1 does not handle.
  5. THE REWRITE: trailing args, pipes, &&, redirects kept byte for byte around the replaced
     span; updatedInput is the COMPLETE tool_input with only "command" changed; never "allow"
     or "ask".
  6. FILES: X: absent -> %TEMP%\\snips; one folder per agent seat; rotation keeps the newest N.
  7. SPAWN (lesson an_exec_quoting_fix_must_be_pinned_by_spawning_the_interpreter): the
     rewritten command, run through real Git bash and real powershell.exe, prints exactly what
     the intended source prints. Includes the -c semantics the file must keep (the cwd on
     sys.path, argv[0], __file__), without which every "py -c 'from core...'" would break.
  8. main(): reads stdin as UTF-8, prints the hook JSON or nothing, and fails OPEN.

This file is ASCII on purpose: non-ASCII test text is built from the <E> <U> <K> <RSQ> <TAB>
placeholders by fill(). Every test writes only under pytest's tmp_path; nothing touches X:.

Run: py -m pytest tests/test_snippet_autofile.py -q
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "scripts" / "hooks" / "snippet_autofile.py"
BASH = Path(r"C:\Program Files\Git\bin\bash.exe")
POWERSHELL = shutil.which("powershell.exe")
NOW = 1760389200.0

need_bash = pytest.mark.skipif(not BASH.exists(), reason="Git bash is not installed here")
need_ps = pytest.mark.skipif(not POWERSHELL, reason="powershell.exe is not on PATH")


def fill(text: str) -> str:
    return (text.replace("<TAB>", "\t").replace("<E>", "\u00e9").replace("<U>", "\u00fc")
            .replace("<K>", "\u6f22").replace("<RSQ>", "\u2019"))


# ---------------------------------------------------------------------------------- fixtures

@pytest.fixture(scope="module")
def sa():
    """The hook, loaded by path under a unique module name."""
    spec = importlib.util.spec_from_file_location("snippet_autofile_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _stable_env(monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "pin")
    monkeypatch.delenv("AKASHIC_SNIPS_ROOT", raising=False)
    monkeypatch.delenv("AKASHIC_SNIPPET_AUTOFILE", raising=False)


@pytest.fixture
def snips(tmp_path):
    return tmp_path / "snips"


# ---------------------------------------------------------------------------------- helpers

def payload(command, tool="Bash", transcript="C:/transcripts/one.jsonl", session="sess-1"):
    return {"session_id": session, "transcript_path": transcript, "cwd": "E:\\AI-Setup",
            "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"command": command, "description": "pin call", "timeout": 120000,
                           "run_in_background": False}}


def check_contract(out):
    """The invariant on EVERY output: None, a filing, a hint, or a deny. Never allow, never ask."""
    if out is None:
        return None
    assert set(out) == {"hookSpecificOutput"}, out
    h = out["hookSpecificOutput"]
    assert h["hookEventName"] == "PreToolUse"
    if "permissionDecision" in h:
        assert h["permissionDecision"] == "deny", h
        assert set(h) == {"hookEventName", "permissionDecision", "permissionDecisionReason"}, h
        assert isinstance(h["permissionDecisionReason"], str) and h["permissionDecisionReason"]
    elif "updatedInput" in h:
        assert set(h) == {"hookEventName", "updatedInput", "additionalContext"}, h
    else:
        assert set(h) == {"hookEventName", "additionalContext"}, h
    assert "\n" not in h.get("additionalContext", "")
    json.dumps(out)
    return h


def run_decide(sa, command, tool="Bash", root=None, now=NOW, **kw):
    out = sa.decide(payload(command, tool, **kw), snips_root=str(root) if root else None, now=now)
    check_contract(out)
    return out


def filed(out):
    assert out is not None, "expected a filing, got None (untouched)"
    h = out["hookSpecificOutput"]
    assert "updatedInput" in h, f"expected a filing, got {h}"
    return h


def denied(out):
    assert out is not None, "expected a deny, got None (untouched)"
    h = out["hookSpecificOutput"]
    assert h.get("permissionDecision") == "deny", f"expected a deny, got {h}"
    return h["permissionDecisionReason"]


def hinted(out):
    """A hint only: the command runs exactly as written (no updatedInput, no decision)."""
    assert out is not None, "expected a hint, got None (untouched)"
    h = out["hookSpecificOutput"]
    assert set(h) == {"hookEventName", "additionalContext"}, f"expected a hint only, got {h}"
    return h["additionalContext"]


def snip_files(root):
    root = Path(root)
    return sorted(root.rglob("*.py")) if root.exists() else []


def split_file(path):
    data = Path(path).read_bytes()
    first = data.index(b"\n")
    second = data.index(b"\n", first + 1)
    return data[:second + 1], data[second + 1:]


def bq(path):
    """How the hook names a file to Git bash: single-quoted, forward slashes."""
    return "'" + str(path).replace("\\", "/") + "'"


def pq(path):
    """How the hook names a file to PowerShell: single-quoted, native path."""
    return "'" + str(path) + "'"


def ps_sq(text):
    """Encode text as the inside of a PowerShell single-quoted string."""
    return text.replace("'", "''").replace("\u2019", "\u2019\u2019")


def bash_dq(text):
    """Encode text as the inside of a bash double-quoted string."""
    return (text.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
            .replace("`", "\\`"))


def lc(text, idx):
    line = text.count("\n", 0, idx) + 1
    col = idx - (text.rfind("\n", 0, idx) + 1) + 1
    return f"line {line}, column {col}"


# ---------------------------------------------------------------------------------- sources

SRC_BASH_SQ = fill(r'''import re
pat = re.compile(r"\bcaf<E>\d+\b")
print(pat.findall("x caf<E>12 y"), "tab:<TAB>end", "back\\slash", "<K>")
print(len("\n"))
''')

# Built by hand with bash's double-quote rules: \d stays \d, \\ -> \, \" -> ", \$ -> $,
# \` -> `, and backslash-newline disappears.
CMD_BASH_DQ = fill(r'''py -c "import re
print(re.findall(r'\d+\\b', 'a1 b22'), \"dq\", '\$x', '\`', 'caf<E>', 'it\\'s', \
'joined')"''')
SRC_BASH_DQ = fill(r'''import re
print(re.findall(r'\d+\b', 'a1 b22'), "dq", '$x', '`', 'caf<E>', 'it\'s', 'joined')''')

BODY = fill(r'''import re
s = 'single' + "double"
print(re.findall(r"\bcaf<E>\d+\b", "x caf<E>12 y"), s, "$HOME stays", "`tick`", "tab:<TAB>end")
print("<U>n<K>", len("\\"))
''')

BODY_PLAIN = fill('''import sys
a = 1
b = 2
print(a + b, 'plain', "caf<E>")
''')

SRC_PS_SQ = fill(r'''import re
print(re.findall(r'\bcaf<E>\d+\b', 'x caf<E>12 y'), 'it' + chr(39) + 's', 'tab:<TAB>end', '<U><K>')
# it<RSQ>s a comment with a typographic apostrophe
print(len('\\'))''')

SRC_PS_DQ = fill(r"import re; print(re.findall(r'\d+', 'a1 b22'), 'caf<E>', len('\\'))")

BODY_HS = BODY.rstrip("\n")

BODY_HS_DQ = fill(r'''import re
s = 'single' + "double" + ""
print(re.findall(r"\bcaf<E>\d+\b", "x caf<E>12 y"), s)
print("<U><K>", len("\\"))''')

SRC_PS_C_HS = fill(r'''import re
print(re.findall(r'\bcaf<E>\d+\b', 'x caf<E>12 y'))
print('<U>n<K>')
print('tab:<TAB>end')''')

ROUND_TRIP = [
    ("bash-c-single", "Bash", "py -c '" + SRC_BASH_SQ + "'", SRC_BASH_SQ),
    ("bash-c-double", "Bash", CMD_BASH_DQ, SRC_BASH_DQ),
    ("bash-c-assignment-prefix", "Bash",
     "PYTHONIOENCODING=utf-8 python -c '" + SRC_BASH_SQ + "'", SRC_BASH_SQ),
    ("bash-heredoc-dash", "Bash", "py - <<'EOF'\n" + BODY + "EOF\n", BODY),
    ("bash-heredoc-implicit", "Bash", 'python3 <<"PY"\n' + BODY + "PY", BODY),
    ("bash-heredoc-space", "Bash", "py - << 'EOF'\n" + BODY + "EOF\n", BODY),
    ("bash-heredoc-unquoted-literal", "Bash", "py - <<EOF\n" + BODY_PLAIN + "EOF\n", BODY_PLAIN),
    ("ps-c-single", "PowerShell", "py -c '" + ps_sq(SRC_PS_SQ) + "'", SRC_PS_SQ),
    ("ps-c-double", "PowerShell", 'py -c "' + SRC_PS_DQ + '"', SRC_PS_DQ),
    ("ps-herestring-dash", "PowerShell", "@'\n" + BODY_HS + "\n'@ | py -", BODY_HS),
    ("ps-herestring-implicit", "PowerShell", "@'\n" + BODY_HS + "\n'@ | python", BODY_HS),
    ("ps-herestring-crlf", "PowerShell",
     "@'\r\n" + BODY_HS.replace("\n", "\r\n") + "\r\n'@ | py -", BODY_HS.replace("\n", "\r\n")),
    ("ps-herestring-double", "PowerShell", '@"\n' + BODY_HS_DQ + '\n"@ | py -', BODY_HS_DQ),
    ("ps-c-herestring-arg", "PowerShell", "py -c @'\n" + SRC_PS_C_HS + "\n'@", SRC_PS_C_HS),
]


# ---------------------------------------------------------------------------------- 1. round trip

@pytest.mark.parametrize("tool,command,source", [r[1:] for r in ROUND_TRIP],
                         ids=[r[0] for r in ROUND_TRIP])
def test_round_trip_byte_for_byte(sa, snips, tool, command, source):
    h = filed(run_decide(sa, command, tool, snips))
    files = snip_files(snips)
    assert len(files) == 1, files
    header, body = split_file(files[0])
    assert body == source.encode("utf-8")
    assert header.startswith(b"# snippet-autofile")
    assert b"\r" not in header
    assert re.fullmatch(r"[0-9a-f]{12}\.py", files[0].name)
    quoted = bq(files[0]) if tool == "Bash" else pq(files[0])
    assert quoted in h["updatedInput"]["command"]


def test_header_is_two_lines_naming_the_command_hash_and_the_time(sa, snips):
    command = "py -c '" + SRC_BASH_SQ + "'"
    filed(run_decide(sa, command, "Bash", snips))
    header = split_file(snip_files(snips)[0])[0].decode("utf-8")
    lines = header.split("\n")
    assert len(lines) == 3 and lines[2] == ""
    assert hashlib.sha256(command.encode("utf-8")).hexdigest()[:12] in lines[0]
    assert time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW)) in lines[0]
    assert not lines[0].startswith("#!")                 # the py launcher reads a shebang
    assert "coding" not in header                        # nor a PEP 263 cookie on lines 1-2


def test_ps_typographic_quote_doubling_decodes_like_powershell(sa, snips):
    """PowerShell treats U+2018..U+201B as single quotes; a doubled pair is one character, the
    second (measured on 5.1: 'a<RSQ><RSQ>b' -> a<RSQ>b, 'a'<RSQ>b' -> a<RSQ>b)."""
    filed(run_decide(sa, "py -c '" + ps_sq(SRC_PS_SQ) + "'", "PowerShell", snips))
    body = split_file(snip_files(snips)[0])[1].decode("utf-8")
    assert "it\u2019s a comment" in body and "\u2019\u2019" not in body


# ---------------------------------------------------------------------------------- 2. hints

R_BASH_DQ_DOLLAR = r'''py -c "import os
print(os.sep == '\\\\', '$HOME')"'''
R_BASH_DQ_BACKQUOTE = r'''py -c "import re; print(re.findall(r'\d', '`date`'))"'''
R_HD_UNQUOTED_BS = "py - <<EOF\nimport re\nprint(re.findall(r'\\d', 'a1'))\nEOF\n"
R_HD_UNQUOTED_DOLLAR = "py - <<EOF\nimport os\na = 1\nb = 2\nprint(a, b, '$HOME')\nEOF\n"
R_HD_UNQUOTED_BACKQUOTE = "py - <<EOF\nimport os\na = 1\nb = 2\nprint(a, b, '`whoami`')\nEOF\n"
R_PS_DQ_DOLLAR = r'''py -c "import re; print(re.findall(r'\d', '$env:USERNAME'))"'''
R_PS_DQ_BACKTICK = r'''py -c "import re; print(re.findall(r'\d', 'a`tb'))"'''
R_PS_HS_DQ_DOLLAR = '@"\nimport re\nprint(re.findall(r\'\\d\', \'$env:USERNAME\'))\n"@ | py -'
R_PS_SQ_DQUOTE = r'''py -c 'import re; print(re.findall(r"\d+", "a1 b22"))' '''.strip()
R_PS_BACKSLASH_BACKTICK = r'''py -c "import re; print(re.findall(r'\d', 'a\`<b'))"'''
R_PS_BACKSLASH_BACKTICK_AND_DOLLAR = r'''py -c "import re; print(re.findall(r'\d', '$x a\`<b'))"'''
R_PS_HS_BACKSLASH_BACKTICK_N = '@"\nimport re\nprint(re.findall(r\'\\d\', \'a\\`nb\'))\n"@ | py -'

EXPANSIONS = [
    ("bash-dq-dollar", "Bash", R_BASH_DQ_DOLLAR, "$HOME"),
    ("bash-dq-backquote", "Bash", R_BASH_DQ_BACKQUOTE, "`"),
    ("bash-heredoc-unquoted-backslash", "Bash", R_HD_UNQUOTED_BS, "backslash"),
    ("bash-heredoc-unquoted-dollar", "Bash", R_HD_UNQUOTED_DOLLAR, "$HOME"),
    ("bash-heredoc-unquoted-backquote", "Bash", R_HD_UNQUOTED_BACKQUOTE, "`"),
    ("ps-dq-dollar", "PowerShell", R_PS_DQ_DOLLAR, "$env:USERNAME"),
    ("ps-dq-backtick", "PowerShell", R_PS_DQ_BACKTICK, "`t"),
    ("ps-herestring-dq-dollar", "PowerShell", R_PS_HS_DQ_DOLLAR, "$env:USERNAME"),
]


@pytest.mark.parametrize("tool,command,named", [r[1:] for r in EXPANSIONS],
                         ids=[r[0] for r in EXPANSIONS])
def test_expansion_cases_get_only_a_hint_and_run_as_today(sa, snips, tool, command, named):
    ctx = hinted(run_decide(sa, command, tool, snips))
    assert named in ctx, ctx
    assert "Write a file" in ctx and len(ctx) < 200, ctx
    assert "in 10 min" not in ctx                        # the first press is quiet
    assert snip_files(snips) == []                       # nothing filed


def test_short_expansion_snippets_stay_untouched_without_a_hint(sa, snips):
    """Only a snippet the hook would otherwise file earns a hint; a short one-liner that expands
    a variable on purpose is left exactly as it is today."""
    assert run_decide(sa, "py -c \"print('$HOME')\"", "Bash", snips) is None
    assert run_decide(sa, "py -c \"print('$env:USERNAME')\"", "PowerShell", snips) is None


def test_the_third_hint_in_ten_minutes_names_its_count(sa, snips):
    ctxs = [hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=NOW + 60 * i))
            for i in range(4)]
    assert "in 10 min" not in ctxs[0] and "in 10 min" not in ctxs[1]
    assert "hint 3 in 10 min" in ctxs[2], ctxs[2]
    assert "hint 4 in 10 min" in ctxs[3], ctxs[3]
    assert all(len(c) < 200 for c in ctxs)


def test_hints_older_than_ten_minutes_do_not_count(sa, snips):
    for t in (NOW, NOW + 60):
        hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=t))
    late = hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=NOW + 700))
    assert "in 10 min" not in late                      # the two early hints fell out
    hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=NOW + 710))
    third = hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=NOW + 720))
    assert "hint 3 in 10 min" in third, third


def test_the_hint_counter_lives_in_each_agents_snips_folder(sa, snips):
    for i, transcript in enumerate(["C:/t/a.jsonl", "C:/t/a.jsonl", "C:/t/b.jsonl"]):
        ctx = hinted(run_decide(sa, R_BASH_DQ_DOLLAR, "Bash", snips, now=NOW + i,
                                transcript=transcript))
        assert "in 10 min" not in ctx                    # 2 + 1, never 3 in one folder
    folders = sorted(p for p in snips.iterdir() if p.is_dir())
    assert len(folders) == 2
    assert all((d / "_expansion_hints.json").is_file() for d in folders)
    assert snip_files(snips) == []


LONG_NAME = "$A_VERY_LONG_SHELL_VARIABLE_NAME_THAT_KEEPS_GOING_FOR_A_WHILE_LONGER_STILL"
LONG_HINT_CASES = [
    ("Bash", 'py -c "import os\nprint(os.sep == \'\\\\\\\\\', \'' + LONG_NAME + '\')"'),
    ("Bash", "py - <<A_REALLY_LONG_HEREDOC_DELIMITER_NAME_FOR_SNIPPETS\nimport re\n"
             "print(re.findall(r'\\d', 'a1'))\nA_REALLY_LONG_HEREDOC_DELIMITER_NAME_FOR_SNIPPETS\n"),
    ("Bash", "py - <<A_REALLY_LONG_HEREDOC_DELIMITER_NAME_FOR_SNIPPETS\nimport os\na = 1\nb = 2\n"
             "print('" + LONG_NAME + "')\nA_REALLY_LONG_HEREDOC_DELIMITER_NAME_FOR_SNIPPETS\n"),
    ("PowerShell", 'py -c "import re; print(re.findall(r\'\\d\', \'' + LONG_NAME + '\'))"'),
]


@pytest.mark.parametrize("tool,command", LONG_HINT_CASES)
def test_a_hint_stays_under_200_characters_even_with_a_count(sa, snips, tool, command):
    for i in range(5):
        ctx = hinted(run_decide(sa, command, tool, snips, now=NOW + i))
        assert len(ctx) < 200, (len(ctx), ctx)
    assert "hint 5 in 10 min" in ctx


def test_a_filed_snippet_and_a_hinted_one_share_one_command(sa, snips):
    command = "py -c '" + SRC_BASH_SQ + "' && " + R_BASH_DQ_DOLLAR
    h = filed(run_decide(sa, command, "Bash", snips))
    files = snip_files(snips)
    assert len(files) == 1
    assert h["updatedInput"]["command"] == "py " + bq(files[0]) + " && " + R_BASH_DQ_DOLLAR
    assert "saved as" in h["additionalContext"] and "$HOME" in h["additionalContext"]


# ---------------------------------------------------------------------------------- 3. refusals

PS_MANGLING = [
    ("ps-arg-double-quote", R_PS_SQ_DQUOTE, '"',
     ["Windows PowerShell 5.1 would have", "quote", "here-string"]),
    ("ps-backslash-backtick", R_PS_BACKSLASH_BACKTICK, "\\`",
     ["Windows PowerShell 5.1 would have", "kept the backslash", "dropped the backtick"]),
    ("ps-backslash-backtick-beats-the-dollar-hint", R_PS_BACKSLASH_BACKTICK_AND_DOLLAR, "\\`",
     ["Windows PowerShell 5.1 would have", "dropped the backtick"]),
    ("ps-herestring-backslash-backtick-n", R_PS_HS_BACKSLASH_BACKTICK_N, "\\`",
     ["Windows PowerShell 5.1 would have", "newline"]),
]


@pytest.mark.parametrize("command,culprit,phrases", [r[1:] for r in PS_MANGLING],
                         ids=[r[0] for r in PS_MANGLING])
def test_powershell_mangling_is_refused_saying_what_powershell_would_do(sa, snips, command,
                                                                        culprit, phrases):
    reason = denied(run_decide(sa, command, "PowerShell", snips))
    assert lc(command, command.index(culprit)) + " of the command" in reason, reason
    for phrase in phrases:
        assert phrase in reason, (phrase, reason)
    assert snip_files(snips) == []                       # a refusal files nothing


SYNTAX_CASES = [
    ("heredoc", "Bash", "py - <<'EOF'\n{src}EOF\n",
     "import re\nx = 1\ny = (x +)\nprint(re.findall(r'\\d', 'a1'))\n"),
    ("bash-c", "Bash", "py -c '{src}'",
     'import re\nprint(re.findall(r"\\d", "a1")\nprint(2)\n'),
    ("ps-herestring", "PowerShell", "@'\n{src}\n'@ | py -",
     "import re\nfor x in [1]\nprint(re.findall(r'\\d', 'a1'))\nprint(4)"),
]


@pytest.mark.parametrize("tool,template,src", [c[1:] for c in SYNTAX_CASES],
                         ids=[c[0] for c in SYNTAX_CASES])
def test_syntax_error_is_refused_with_its_line_and_column(sa, snips, tool, template, src):
    try:
        compile(src, "<snippet>", "exec")
    except SyntaxError as exc:
        where = f"line {exc.lineno}, column {exc.offset} of the snippet"
    else:
        pytest.fail("the pin's source must not compile")
    reason = denied(run_decide(sa, template.replace("{src}", src), tool, snips))
    assert where in reason and "SyntaxError" in reason, reason
    assert snip_files(snips) == []


SRC_TRAP = 'import re\nprint(re.findall("\\bword\\b", "a word here"))\n'


def test_backspace_trap_is_refused_at_the_exact_escape(sa, snips):
    reason = denied(run_decide(sa, "py -c '" + SRC_TRAP + "'", "Bash", snips))
    assert "line 2, column 19 of the snippet" in reason, reason
    assert lc(SRC_TRAP, SRC_TRAP.index("\\b")) == "line 2, column 19"
    assert "r'" in reason and "backspace" in reason.lower(), reason
    assert "# autofile: control-chars-ok" in reason
    assert snip_files(snips) == []


CONTROL_LITERALS = [
    ("bell", '"\\a"'), ("vtab", '"\\v"'), ("formfeed", '"\\f"'), ("hex-08", '"\\x08"'),
    ("hex-0C-upper", '"\\x0C"'), ("octal-010", '"\\010"'), ("octal-7", '"\\7"'),
    ("bytes", 'b"\\b"'), ("fstring", 'f"\\b{1}"'), ("named", '"\\N{BACKSPACE}"'),
    ("u-escape", '"\\u0008"'), ("literal-char", '"a\x08b"'), ("docstring-ish", '"""x\n\\b"""'),
]


@pytest.mark.parametrize("literal", [c[1] for c in CONTROL_LITERALS],
                         ids=[c[0] for c in CONTROL_LITERALS])
def test_control_characters_in_non_raw_strings_are_refused(sa, snips, literal):
    src = "import re\nx = 1\ny = " + literal + "\nprint(re.findall(r'\\d', 'a1'))\n"
    reason = denied(run_decide(sa, "py - <<'EOF'\n" + src + "EOF\n", "Bash", snips))
    start = src.index(literal)
    bs = literal.find("\\")
    idx = start + bs if bs >= 0 else start + literal.index("\x08")
    if literal.startswith('"""'):
        idx = start + literal.index("\\")
    assert lc(src, idx) + " of the snippet" in reason, reason


ALLOWED_LITERALS = ['"\\\\b"', 'r"\\b"', 'rb"\\b"', 'Rb"\\f"', '"\\t\\n"', '"\\d"', "'''\\\\a'''"]


@pytest.mark.parametrize("literal", ALLOWED_LITERALS)
def test_raw_and_harmless_escapes_are_filed_not_refused(sa, snips, literal):
    src = "import re\nx = 1\ny = " + literal + "\nprint(re.findall(r'\\d', 'a1'))\n"
    filed(run_decide(sa, "py - <<'EOF'\n" + src + "EOF\n", "Bash", snips))
    assert split_file(snip_files(snips)[0])[1] == src.encode("utf-8")


def test_opt_out_marker_lets_the_control_character_through(sa, snips):
    src = SRC_TRAP + "# autofile: control-chars-ok\n"
    filed(run_decide(sa, "py -c '" + src + "'", "Bash", snips))
    assert split_file(snip_files(snips)[0])[1] == src.encode("utf-8")


# ---------------------------------------------------------------------------------- 3. untouched

SHORT_CLEAN = [
    ("bash-sq", "Bash", "py -c 'print(1)'"),
    ("bash-dq", "Bash", 'py -c "import sys; print(sys.version_info[:2])"'),
    ("bash-heredoc", "Bash", "py - <<'EOF'\nprint('short heredoc')\nEOF\n"),
    ("bash-dq-dollar-short", "Bash", "py -c \"print('$HOME')\""),
    ("bash-short-syntax-error", "Bash", "py -c 'print(1 +)'"),
    ("ps-sq", "PowerShell", "py -c 'print(2)'"),
    ("ps-dq-dollar-short", "PowerShell", "py -c \"print('$env:USERNAME')\""),
    ("ps-sq-double-quote-short", "PowerShell", "py -c 'print(\"hi\")'"),
    ("ps-herestring", "PowerShell", "@'\nprint(3)\n'@ | py -"),
]


@pytest.mark.parametrize("tool,command", [c[1:] for c in SHORT_CLEAN],
                         ids=[c[0] for c in SHORT_CLEAN])
def test_short_clean_snippets_pass_untouched(sa, snips, tool, command):
    assert run_decide(sa, command, tool, snips) is None
    assert snip_files(snips) == []


def test_a_long_snippet_without_backslashes_is_filed(sa, snips):
    four = "import sys\na = 1\nb = 2\nprint(a + b)\n"
    filed(run_decide(sa, "py -c '" + four + "'", "Bash", snips))
    long_line = "print(" + " + ".join(["1"] * 120) + ")"
    assert len(long_line) > 300
    filed(run_decide(sa, "py -c '" + long_line + "'", "Bash", snips / "two"))
    three = "import sys\na = 1\nprint(a)\n"
    assert run_decide(sa, "py -c '" + three + "'", "Bash", snips / "three") is None


UNKNOWN = [
    ("script-file", "Bash", "py script.py '\\d+\\b' --flag"),
    ("module", "Bash", "py -m pytest -k 'a\\b' tests/"),
    ("inside-a-string", "Bash", "echo \"py -c 'print(\\\"\\\\d\\\")'\""),
    ("grep-c", "Bash", "grep -c '\\d' file.txt"),
    ("ansi-c-quoting", "Bash", "python -c $'print(\"\\\\x41\")'"),
    ("combined-flags", "Bash", "py -uc 'import re; print(re.escape(\"a\\\\b\"))'"),
    ("heredoc-to-cat", "Bash", "cat <<'EOF' | py -\nimport re\nprint(re.findall(r'\\d', 'a1'))\nEOF\n"),
    ("heredoc-strip-tabs", "Bash", "py - <<-'EOF'\n\timport re\n\tprint(re.findall(r'\\d', 'a1'))\n\tEOF\n"),
    ("bash-herestring", "Bash", "py <<<'import re; print(re.findall(r\"\\d\", \"a1\"))'"),
    ("mypy", "Bash", "mypy -c 'x = \"\\d\"'"),
    ("pytest-c", "Bash", "pytest -c 'a\\b'"),
    ("comment", "Bash", "# py -c 'print(\"\\d\")'\necho hi"),
    ("unterminated", "Bash", "py -c 'print(\"\\d\")"),
    ("no-argument", "Bash", "py -c"),
    ("mixed-quoting", "Bash", "py -c 'a'\\''b\\d'"),
    ("timeout-prefix", "Bash", "timeout 60 py -c 'import re; print(re.findall(r\"\\d\", \"a1\"))'"),
    ("ps-inside-a-string", "PowerShell", "Write-Output 'py -c ''print(\"\\d\")'''"),
    ("ps-script-file", "PowerShell", "py script.py '\\d'"),
    ("ps-quoted-name", "PowerShell", "& 'py' -c 'import re; print(re.findall(r''\\d'', ''a1''))'"),
    ("ps-stop-parsing", "PowerShell", "py --% -c 'import re; print(1)' \\d"),
    ("ps-variable-arg", "PowerShell", "$code = 'print(1)\\n'; py -c $code"),
    ("ps-word-continues", "PowerShell", "py -c 'it''s'\\d"),
    ("ps-unterminated", "PowerShell", "py -c 'import re\\d"),
]


@pytest.mark.parametrize("tool,command", [c[1:] for c in UNKNOWN], ids=[c[0] for c in UNKNOWN])
def test_unknown_shapes_pass_untouched(sa, snips, tool, command):
    assert run_decide(sa, command, tool, snips) is None
    assert snip_files(snips) == []


def test_from_future_snippets_pass_untouched(sa, snips):
    """The file's second header line restores -c semantics in code; a __future__ import must be
    the first statement, so such a snippet cannot be filed faithfully and is left alone."""
    src = 'from __future__ import annotations\nimport re\nprint(re.findall(r"\\d", "a1"))\n'
    assert run_decide(sa, "py -c '" + src + "'", "Bash", snips) is None


@pytest.mark.parametrize("bad", [
    {"tool_name": "Edit", "tool_input": {"command": "py -c '" + SRC_BASH_SQ + "'"}},
    {"tool_name": "Bash", "tool_input": None},
    {"tool_name": "Bash", "tool_input": "py -c 'x'"},
    {"tool_name": "Bash", "tool_input": {"command": 5}},
    {"tool_name": "Bash"},
    {"tool_input": {"command": "py -c '" + SRC_BASH_SQ + "'"}},
    [],
    None,
])
def test_malformed_payloads_pass_untouched(sa, snips, bad):
    assert sa.decide(bad, snips_root=str(snips), now=NOW) is None


# ---------------------------------------------------------------------------------- 4. the rewrite

def test_bash_surroundings_are_kept_byte_for_byte(sa, snips):
    head = "cd /e/AI-Setup && PYTHONIOENCODING=utf-8 py -X utf8 -u "
    tail = " arg1 \"arg 2\" 2>&1 | tail -n 3 > out.txt; echo done"
    h = filed(run_decide(sa, head + "-c '" + SRC_BASH_SQ + "'" + tail, "Bash", snips))
    assert h["updatedInput"]["command"] == head + bq(snip_files(snips)[0]) + tail


def test_bash_heredoc_rewrite_keeps_the_line_and_drops_only_the_body(sa, snips):
    cmd = "py -X utf8 - a1 'a 2' <<'EOF' 2>&1 | sort && echo ok\n" + BODY + "EOF\necho after\n"
    h = filed(run_decide(sa, cmd, "Bash", snips))
    f = snip_files(snips)[0]
    assert h["updatedInput"]["command"] == (
        "py -X utf8 " + bq(f) + " a1 'a 2' </dev/null 2>&1 | sort && echo ok\necho after\n")


def test_bash_implicit_heredoc_rewrite_inserts_the_file(sa, snips):
    cmd = 'python3 <<"PY" > out.txt\n' + BODY + "PY\necho after"
    h = filed(run_decide(sa, cmd, "Bash", snips))
    f = snip_files(snips)[0]
    assert h["updatedInput"]["command"] == "python3 " + bq(f) + " </dev/null > out.txt\necho after"


def test_ps_surroundings_are_kept_byte_for_byte(sa, snips):
    head = "Set-Location E:\\AI-Setup; py -X utf8 "
    tail = " a1 'b 2' 2>&1 | Select-Object -First 3"
    cmd = head + "-c '" + ps_sq(SRC_PS_SQ) + "'" + tail
    h = filed(run_decide(sa, cmd, "PowerShell", snips))
    assert h["updatedInput"]["command"] == head + pq(snip_files(snips)[0]) + tail


def test_ps_herestring_rewrite_keeps_the_pipeline(sa, snips):
    cmd = "$x = 1\n@'\n" + BODY_HS + "\n'@ | py -X utf8 - a1 | Out-String"
    h = filed(run_decide(sa, cmd, "PowerShell", snips))
    f = snip_files(snips)[0]
    assert h["updatedInput"]["command"] == "$x = 1\npy -X utf8 " + pq(f) + " a1 | Out-String"


def test_two_snippets_in_one_command_are_both_filed(sa, snips):
    a = "import re\nprint(re.findall(r'\\d', 'a1'))\n"
    b = "import re\nprint(re.findall(r'\\w', 'b2'))\n"
    cmd = 'py -c "' + bash_dq(a) + '" && py -c "' + bash_dq(b) + '"'
    h = filed(run_decide(sa, cmd, "Bash", snips))
    by_body = {split_file(f)[1].decode("utf-8"): f for f in snip_files(snips)}
    assert set(by_body) == {a, b}
    assert h["updatedInput"]["command"] == "py " + bq(by_body[a]) + " && py " + bq(by_body[b])


def test_a_heredoc_that_feeds_data_to_py_c_is_left_in_place(sa, snips):
    src = "import sys\ndata = sys.stdin.read()\nprint(len(data))\nprint(repr(data))\n"
    rest = " <<'EOF'\nline one\nEOF\n"
    h = filed(run_decide(sa, "py -c '" + src + "'" + rest, "Bash", snips))
    assert h["updatedInput"]["command"] == "py " + bq(snip_files(snips)[0]) + rest


def test_updated_input_is_the_complete_original_with_only_command_replaced(sa, snips):
    p = payload("py -c '" + SRC_BASH_SQ + "'")
    p["tool_input"]["dangerouslyDisableSandbox"] = False
    before = json.loads(json.dumps(p))
    h = check_contract(sa.decide(p, snips_root=str(snips), now=NOW))
    ui = h["updatedInput"]
    assert list(ui) == list(p["tool_input"])
    for key, value in p["tool_input"].items():
        if key != "command":
            assert ui[key] == value
    assert ui["command"] != p["tool_input"]["command"]
    assert p == before                                   # the caller's payload is not mutated


def test_additional_context_is_one_line_naming_the_file_and_the_habit(sa, snips):
    h = filed(run_decide(sa, "py -c '" + SRC_BASH_SQ + "'", "Bash", snips))
    ctx = h["additionalContext"]
    assert "\n" not in ctx and "\r" not in ctx
    assert str(snip_files(snips)[0]) in ctx
    assert "Write a file" in ctx


# ---------------------------------------------------------------------------------- 5. files

def test_missing_x_drive_falls_back_to_temp(sa, tmp_path, monkeypatch):
    gone = tmp_path / "no-such-drive"
    monkeypatch.setattr(sa, "PRIMARY_DRIVE", str(gone) + os.sep)
    monkeypatch.setattr(sa, "PRIMARY_ROOT", str(gone / "Temp" / "snips"))
    monkeypatch.setenv("TEMP", str(tmp_path / "temp"))
    monkeypatch.setenv("TMP", str(tmp_path / "temp"))
    filed(run_decide(sa, "py -c '" + SRC_BASH_SQ + "'", "Bash", None))
    assert len(snip_files(tmp_path / "temp" / "snips")) == 1
    assert not gone.exists()


def test_present_x_drive_is_used(sa, tmp_path, monkeypatch):
    monkeypatch.setattr(sa, "PRIMARY_DRIVE", str(tmp_path) + os.sep)
    monkeypatch.setattr(sa, "PRIMARY_ROOT", str(tmp_path / "ram" / "Temp" / "snips"))
    monkeypatch.setenv("TEMP", str(tmp_path / "temp"))
    monkeypatch.setenv("TMP", str(tmp_path / "temp"))
    filed(run_decide(sa, "py -c '" + SRC_BASH_SQ + "'", "Bash", None))
    assert len(snip_files(tmp_path / "ram" / "Temp" / "snips")) == 1
    assert snip_files(tmp_path / "temp") == []


def test_spec_constants(sa):
    assert sa.PRIMARY_ROOT == "X:\\Temp\\snips"
    assert sa.KEEP_FILES == 2000


def test_per_agent_folders_differ_by_transcript(sa, snips, monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "pin-agent")
    one = 'import re\nprint(re.findall(r"\\d", "one1"))\n'
    two = 'import re\nprint(re.findall(r"\\d", "two2"))\n'
    filed(run_decide(sa, "py -c '" + one + "'", "Bash", snips, transcript="C:/t/a.jsonl"))
    filed(run_decide(sa, "py -c '" + two + "'", "Bash", snips, transcript="C:/t/b.jsonl"))
    folders = {f.parent for f in snip_files(snips)}
    assert len(folders) == 2
    assert all(d.parent == snips and d.name.startswith("pin-agent") for d in folders)
    filed(run_decide(sa, "py -c '" + two + "x = 1\n'", "Bash", snips, transcript="C:/t/a.jsonl"))
    assert {f.parent for f in snip_files(snips)} == folders


def test_hostile_agent_id_stays_inside_the_snips_root(sa, snips, monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "..\\..\\evil:x/../y")
    filed(run_decide(sa, "py -c '" + SRC_BASH_SQ + "'", "Bash", snips))
    f = snip_files(snips)[0]
    assert f.parent.parent == snips and ".." not in f.parent.name


def test_rotation_keeps_the_newest_n(sa, snips, monkeypatch):
    monkeypatch.setattr(sa, "KEEP_FILES", 3)
    sources = [f'import re\nprint(re.findall(r"\\d", "n{i}"))\n' for i in range(5)]
    for i, src in enumerate(sources):
        filed(run_decide(sa, "py -c '" + src + "'", "Bash", snips, now=NOW + 60 * i))
    kept = {split_file(f)[1].decode("utf-8") for f in snip_files(snips)}
    assert kept == set(sources[2:])


# ---------------------------------------------------------------------------------- 6. spawn

def _env():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_intended(src, folder, args=()):
    path = Path(folder) / "intended_source.py"
    path.write_bytes(src.encode("utf-8"))
    return subprocess.run(["py", str(path), *args], cwd=folder, capture_output=True,
                          env=_env(), timeout=120)


def run_bash(command, folder, scratch):
    script = Path(scratch) / "rewritten.sh"
    script.write_bytes(command.encode("utf-8"))
    return subprocess.run([str(BASH), "--noprofile", "--norc", str(script).replace("\\", "/")],
                          cwd=folder, capture_output=True, env=_env(), timeout=120)


def run_ps(command, folder):
    encoded = base64.b64encode(command.encode("utf-16-le")).decode("ascii")
    return subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                          cwd=folder, capture_output=True, env=_env(), timeout=120)


def assert_same_stdout(reference, rewritten):
    assert reference.returncode == 0, reference.stderr.decode("utf-8", "replace")
    assert rewritten.returncode == 0, rewritten.stderr.decode("utf-8", "replace")
    assert reference.stdout.strip(), "a pin on empty output certifies nothing"
    assert rewritten.stdout.replace(b"\r\n", b"\n") == reference.stdout.replace(b"\r\n", b"\n")


SP_BASH_SQ = fill(r'''import re, sys
words = re.findall(r"\b\w+\d\b", "x caf<E> abc1 d22")
print(ascii(words), ascii("tab:<TAB>end"), ascii("caf<E> <K>"))
print(len("back\\slash"), sys.argv[1:])
''')

SP_BASH_DQ = fill(r'''import re, sys
print(ascii(re.findall(r'\d+\b', 'a1 b22')), "dq", '$x', '`', ascii('caf<E>'))
print(len('a\\b'), sys.argv[1:])''')

SP_BODY = fill(r'''import re, sys
print(ascii(re.findall(r"\bcaf\w\b", "a caf<E> b")))
print("$HOME stays", "`tick`", sys.argv[1:])
print(ascii("tab:<TAB>end <U><K>"))
''')

SP_PS_SQ = fill(r'''import re, sys
words = re.findall(r'\b\w+\d\b', 'x caf<E> abc1 d22')
print(ascii(words), ascii('tab:<TAB>end'), ascii('caf<E> <K> it' + chr(39) + 's'))
print(len('back\\slash'), sys.argv[1:])''')

SPAWN_BASH = [
    ("c-single", "py -c '" + SP_BASH_SQ + "' one 'two words' | cat", SP_BASH_SQ,
     ["one", "two words"]),
    ("c-double", 'py -c "' + bash_dq(SP_BASH_DQ) + '" one', SP_BASH_DQ, ["one"]),
    ("heredoc", "py - a1 <<'EOF' | cat\n" + SP_BODY + "EOF\n", SP_BODY, ["a1"]),
]


@need_bash
@pytest.mark.parametrize("command,src,args", [c[1:] for c in SPAWN_BASH],
                         ids=[c[0] for c in SPAWN_BASH])
def test_spawn_bash_rewrite_prints_what_the_source_prints(sa, tmp_path, command, src, args):
    h = filed(run_decide(sa, command, "Bash", tmp_path / "snips"))
    work = tmp_path / "work"
    work.mkdir()
    assert_same_stdout(run_intended(src, work, args),
                       run_bash(h["updatedInput"]["command"], work, tmp_path))


SPAWN_PS = [
    ("c-single", "py -c '" + ps_sq(SP_PS_SQ) + "' one 'two words'", SP_PS_SQ, ["one", "two words"]),
    ("herestring", "@'\n" + SP_BODY.rstrip("\n") + "\n'@ | py - a1", SP_BODY, ["a1"]),
]


@need_ps
@pytest.mark.parametrize("command,src,args", [c[1:] for c in SPAWN_PS], ids=[c[0] for c in SPAWN_PS])
def test_spawn_powershell_rewrite_prints_what_the_source_prints(sa, tmp_path, command, src, args):
    h = filed(run_decide(sa, command, "PowerShell", tmp_path / "snips"))
    work = tmp_path / "work"
    work.mkdir()
    assert_same_stdout(run_intended(src, work, args), run_ps(h["updatedInput"]["command"], work))


SP_IMPORT = "import afmod_pin_7f3\nprint(afmod_pin_7f3.VALUE)\nprint('line three')\nprint('line four')\n"


def _work_with_module(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "afmod_pin_7f3.py").write_text("VALUE = 42\n", encoding="utf-8")
    return work


@need_bash
def test_spawn_bash_snippet_still_imports_from_the_cwd(sa, tmp_path):
    """-c puts the cwd on sys.path; a file puts ITS folder there. Every house snippet that says
    py -c 'from core...' from E:/AI-Setup depends on the first, so the file must keep it."""
    h = filed(run_decide(sa, 'py -c "' + SP_IMPORT + '"', "Bash", tmp_path / "snips"))
    work = _work_with_module(tmp_path)
    reference = run_intended(SP_IMPORT, work)
    assert reference.stdout.split()[0] == b"42"
    assert_same_stdout(reference, run_bash(h["updatedInput"]["command"], work, tmp_path))


@need_ps
def test_spawn_powershell_snippet_still_imports_from_the_cwd(sa, tmp_path):
    h = filed(run_decide(sa, "py -c '" + ps_sq(SP_IMPORT) + "'", "PowerShell", tmp_path / "snips"))
    work = _work_with_module(tmp_path)
    assert_same_stdout(run_intended(SP_IMPORT, work), run_ps(h["updatedInput"]["command"], work))


SP_SEMANTICS = ('import sys\nprint(sys.argv[0])\nprint(repr(sys.path[0]))\n'
                'print("__file__" in globals(), globals().get("__file__"))\nprint(sys.argv[1:])\n')


@need_bash
def test_spawn_bash_c_keeps_argv0_path0_and_file_semantics(sa, tmp_path):
    h = filed(run_decide(sa, "py -c '" + SP_SEMANTICS + "' a1", "Bash", tmp_path / "snips"))
    work = _work_with_module(tmp_path)
    reference = subprocess.run(["py", "-c", SP_SEMANTICS, "a1"], cwd=work, capture_output=True,
                               env=_env(), timeout=120)
    assert reference.stdout.startswith(b"-c")
    assert_same_stdout(reference, run_bash(h["updatedInput"]["command"], work, tmp_path))


@need_bash
def test_spawn_bash_heredoc_keeps_stdin_mode_semantics(sa, tmp_path):
    cmd = "py - a1 <<'EOF'\n" + SP_SEMANTICS + "EOF\n"
    h = filed(run_decide(sa, cmd, "Bash", tmp_path / "snips"))
    work = _work_with_module(tmp_path)
    reference = subprocess.run(["py", "-", "a1"], input=SP_SEMANTICS.encode("utf-8"), cwd=work,
                               capture_output=True, env=_env(), timeout=120)
    assert reference.stdout.startswith(b"-")
    assert_same_stdout(reference, run_bash(h["updatedInput"]["command"], work, tmp_path))


@need_ps
def test_spawn_powershell_implicit_stdin_keeps_its_semantics(sa, tmp_path):
    cmd = "@'\n" + SP_SEMANTICS.rstrip("\n") + "\n'@ | py"
    h = filed(run_decide(sa, cmd, "PowerShell", tmp_path / "snips"))
    work = _work_with_module(tmp_path)
    reference = subprocess.run(["py"], input=SP_SEMANTICS.encode("utf-8"), cwd=work,
                               capture_output=True, env=_env(), timeout=120)
    assert_same_stdout(reference, run_ps(h["updatedInput"]["command"], work))


# ---------------------------------------------------------------------------------- 7. main()

def _run_main(stdin_bytes, env_extra):
    env = _env()
    env.update(env_extra)
    return subprocess.run([sys.executable, str(HOOK)], input=stdin_bytes, capture_output=True,
                          env=env, timeout=120)


def test_main_files_from_utf8_stdin_and_prints_the_hook_json(tmp_path):
    root = tmp_path / "main-snips"
    data = json.dumps(payload("py -c '" + SRC_BASH_SQ + "'"), ensure_ascii=False).encode("utf-8")
    r = _run_main(data, {"AKASHIC_SNIPS_ROOT": str(root), "AKASHIC_AGENT_ID": "pin-main"})
    assert r.returncode == 0, r.stderr
    h = check_contract(json.loads(r.stdout.decode("ascii")))
    assert "updatedInput" in h
    files = snip_files(root)
    assert len(files) == 1 and split_file(files[0])[1] == SRC_BASH_SQ.encode("utf-8")


def test_main_prints_a_deny_for_a_refusal(tmp_path):
    data = json.dumps(payload("py -c '" + SRC_TRAP + "'")).encode("utf-8")
    r = _run_main(data, {"AKASHIC_SNIPS_ROOT": str(tmp_path / "s")})
    assert r.returncode == 0
    h = check_contract(json.loads(r.stdout))
    assert h["permissionDecision"] == "deny"


def test_main_prints_a_hint_and_leaves_the_command_alone(tmp_path):
    data = json.dumps(payload(R_BASH_DQ_DOLLAR)).encode("utf-8")
    r = _run_main(data, {"AKASHIC_SNIPS_ROOT": str(tmp_path / "s")})
    assert r.returncode == 0
    h = check_contract(json.loads(r.stdout))
    assert set(h) == {"hookEventName", "additionalContext"} and "$HOME" in h["additionalContext"]


@pytest.mark.parametrize("stdin_bytes", [b"", b"not json{", b"[1, 2]", b"\xff\xfe\x00garbage"])
def test_main_is_silent_on_bad_stdin(tmp_path, stdin_bytes):
    r = _run_main(stdin_bytes, {"AKASHIC_SNIPS_ROOT": str(tmp_path / "s")})
    assert r.returncode == 0 and r.stdout == b""


def test_main_is_silent_when_there_is_nothing_to_do(tmp_path):
    r = _run_main(json.dumps(payload("git status")).encode(), {"AKASHIC_SNIPS_ROOT": str(tmp_path)})
    assert r.returncode == 0 and r.stdout == b""


def test_main_fails_open_and_logs_an_internal_exception(sa, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AKASHIC_SNIPS_ROOT", str(tmp_path / "logroot"))

    def boom(*_a, **_k):
        raise RuntimeError("pin-boom-7c1")

    monkeypatch.setattr(sa, "decide", boom)

    class _Stdin:
        buffer = io.BytesIO(json.dumps(payload("py -c '" + SRC_BASH_SQ + "'")).encode("utf-8"))

    monkeypatch.setattr(sys, "stdin", _Stdin())
    assert sa.main() == 0
    assert capsys.readouterr().out == ""
    logs = list((tmp_path / "logroot").rglob("*.log"))
    assert logs and any("pin-boom-7c1" in p.read_text(encoding="utf-8") for p in logs)


def test_main_kill_switch(tmp_path):
    data = json.dumps(payload("py -c '" + SRC_BASH_SQ + "'")).encode("utf-8")
    r = _run_main(data, {"AKASHIC_SNIPS_ROOT": str(tmp_path / "s"), "AKASHIC_SNIPPET_AUTOFILE": "0"})
    assert r.returncode == 0 and r.stdout == b""
    assert snip_files(tmp_path / "s") == []


# ------------------------------------------------------------------ Heimdall's fence read, 2026-10-13
# His findings 1-3 (bus 21:39Z). Finding 1 read the dry-run _apply in decide() as dead code with
# the wrong tuple shape; it is a deliberate overlap check, so it is pinned here rather than removed.

HD_BODY = "import re\nprint(re.findall(r'\\d', 'a1'))\n"


def test_overlapping_edits_leave_the_command_untouched_and_write_nothing(sa, snips, monkeypatch):
    command = "py - <<'EOF'\n" + HD_BODY + "EOF\n"
    real = sa._find_bash(command)
    assert real, "the fixture must be a shape the hook handles"
    # two snippets claiming the same span: the dry run must refuse them before any file is written
    monkeypatch.setattr(sa, "_find_bash", lambda _c: list(real) + list(real))
    assert run_decide(sa, command, root=snips) is None
    assert snip_files(snips) == []


def test_a_bash_locale_string_after_dash_c_is_left_alone(sa, snips):
    # $"..." is bash's locale-translated string; v1 does not decode it, so it must pass untouched
    assert run_decide(sa, 'py -c $"import re; print(re.findall(r\'\\d\', \'a1\'))"', root=snips) is None
    assert snip_files(snips) == []


@pytest.mark.parametrize("command, keep", [
    ("py - <<'EOF' && echo done\n" + HD_BODY + "EOF\n", " && echo done\n"),
    ("py - <<'EOF' > out.txt\n" + HD_BODY + "EOF\n", " > out.txt\n"),
    ("py - <<'EOF'\n" + HD_BODY + "EOF\necho after | cat\n", "echo after | cat\n"),
], ids=["and-on-the-first-line", "redirect-on-the-first-line", "a-command-after-the-delimiter"])
def test_what_surrounds_a_heredoc_stays_byte_for_byte(sa, snips, command, keep):
    h = filed(run_decide(sa, command, root=snips))
    rewritten = h["updatedInput"]["command"]
    assert keep in rewritten, rewritten
    assert "EOF" not in rewritten and "<<" not in rewritten, rewritten
    (path,) = snip_files(snips)
    assert split_file(path)[1] == HD_BODY.encode("utf-8")


@need_bash
def test_a_command_after_the_heredoc_still_runs(sa, snips, tmp_path):
    command = "py - <<'EOF'\n" + HD_BODY + "EOF\necho after-7f3\n"
    h = filed(run_decide(sa, command, root=snips))
    work = tmp_path / "work"
    work.mkdir()
    r = run_bash(h["updatedInput"]["command"], work, tmp_path)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert r.stdout.replace(b"\r\n", b"\n") == b"['1']\nafter-7f3\n"
