"""Claude Code PreToolUse hook: inline Python goes to a file first (snippet auto-file, version 1).

WHY. One night of the shader school: about 2,100 inline snippets (560 heredocs, 1,533 `py -c`),
29 quoting failures, 2 silent corruptions (one where "\\b" in a regex became a backspace byte).
Daniel, 2026-10-13: "For point 1, can we put in an intelligent parser that creates the file in the
ramdisk x and runs it automagically?" then "Yes please". Spec (binding):
research/in-flight/snippet-autofile-2026-10-13/design-notes.md, "Version 1 spec" and "Heimdall's
fence read". Pins: tests/test_snippet_autofile.py.

WHAT IT DOES. It sees the command exactly as the agent wrote it, before any shell parses it.
  * Layer 1, auto-file. A handled shape whose snippet holds a backslash, or runs past 3 lines or
    300 characters, is written to X:\\Temp\\snips\\<agent>\\<sha12>.py (%TEMP%\\snips when X: is
    absent) and the command is rewritten to run that file. Everything around the replaced span
    (flags, trailing args, pipes, &&, redirects) is kept byte for byte. Short clean snippets and
    every shape v1 does not know pass untouched: a bounded scope beats a wrong rewrite.
  * Layer 2, read before run. The extracted source is compiled (never run); a SyntaxError is a
    deny naming line and column. A non-raw string holding \\x07 \\x08 \\x0b or \\x0c (what \\a \\b \\v
    \\f become outside a raw string) is a deny naming the exact escape. The marker comment
    "# autofile: control-chars-ok" opts a snippet out. Never a silent rewrite (Heimdall point 2).
  * EXPANSION, a hint and nothing else. When the shell will change the source on purpose -- bash
    expands a $ or backquote in "...", an unquoted heredoc processes \\ $ or backquote, PowerShell
    expands $ or a backtick in "..." -- the snippet is NOT filed and NOT denied: one line of
    additionalContext under 200 characters names what will be expanded, and the command runs
    exactly as written. The census that set this rule (coordinator, 2026-10-13): 168 of 9,260
    real commands relied on expansion on purpose; refusing them added the friction this hook
    exists to remove. The third hint inside ten minutes for one agent folder names its count
    ("the second press is a question"); the count lives in that folder (_expansion_hints.json).
  * HARD REFUSALS only for certain bugs: the SyntaxError, the control-character trap, and two
    manglings measured on Windows PowerShell 5.1 -- a bash-style \\` inside "..." (5.1 keeps the
    backslash and treats `X as its own escape) and a double quote inside a -c argument (5.1 hands
    it to py unescaped; py's parser drops it and splits the code at spaces) -- each reason saying
    what PowerShell would have done (Heimdall point 1: refuse where a step silently re-parses).
  * Every hint and refusal applies only to a snippet the hook would otherwise file; a short one
    passes untouched, as it does today.

SHAPES HANDLED.
  Bash:        [NAME=val ...] py|python|python3 [flags] -c '<src>' | "<src>" [args]
               py [flags] - [args] <<'EOF' (or <<"EOF", <<EOF with a literal body), and the same
               with no "-" (python3 <<"PY"). The heredoc becomes </dev/null: the original program
               also reached Python on stdin, which Python then saw at EOF.
  PowerShell:  py [flags] -c '<src>' | "<src>" | @'...'@ | @"..."@ [args]
               @'...'@ | py [flags] - [args]   and   @'...'@ | py [flags]   (also @"..."@)
  Flags: -X v, -W v, -Xv, -Wv, combined letters from bBdEIOPqRsSuv, and the py launcher's -3.11.

THE FILE. LF header of two lines, then the source byte for byte. Line 1 names the snippet hash,
the original command's hash and the time. Line 2 restores what the inline run had and a file run
does not: sys.path[0] (the cwd for -c, not the snips folder -- every "py -c 'from core...'" from
E:\\AI-Setup depends on it), sys.argv[0] ('-c', '-' or '') and __file__ (absent for -c, '<stdin>'
for a piped program). Because line 2 is code, a snippet with a __future__ import (which must be
the first statement) passes untouched. Traceback line numbers are therefore +2.

CONTRACT. Never returns permissionDecision "allow" or "ask" (it must not widen permissions; the
harness's own rules still judge the rewritten command); only "deny" for a refusal. updatedInput is
the COMPLETE tool_input with only "command" replaced (the harness validates it against the tool's
schema). Fails OPEN: any internal exception prints nothing, exits 0, and is logged to
<snips root>\\_errors.log. Kill switch: AKASHIC_SNIPPET_AUTOFILE=0. AKASHIC_SNIPS_ROOT overrides the
root. Version 1 ships UN-WIRED until the live harness test passes (design notes, "live test owed").
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

# ast, hashlib, io, tempfile, tokenize, traceback, unicodedata and warnings are imported where
# they are used: the hook runs before EVERY shell call, most calls never reach the analysis, and
# importing them up front measured +36 ms on a 109 ms interpreter floor (2026-10-13).

PRIMARY_DRIVE = "X:\\"
PRIMARY_ROOT = "X:\\Temp\\snips"
KEEP_FILES = 2000                      # newest files kept per agent folder (spec)
KEEP_BYTES = 50 * 1024 * 1024          # and at most this much per folder (design notes, X: facts)
MAX_LINES = 3                          # a snippet longer than this is filed
MAX_CHARS = 300                        # likewise
SHELL_TOOLS = ("Bash", "PowerShell")
INTERPRETERS = ("py", "python", "python3")

MARKER_RE = re.compile(r"#\s*autofile:\s*control-chars-ok")
CONTROL_NAMES = {0x07: "BEL (bell, 0x07)", 0x08: "BS (backspace, 0x08)",
                 0x0B: "VT (vertical tab, 0x0b)", 0x0C: "FF (form feed, 0x0c)"}
CONTROL_STR = "".join(chr(c) for c in CONTROL_NAMES)

_FLAG_RE = re.compile(r"-[bBdEIOPqRsSuv]+|-[XW]\S+|-[0-9][0-9.]*(?:-(?:32|64))?")
_PLAIN_RE = re.compile(r"[A-Za-z0-9_.,:=+/@%-]+")
_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")

# Bash
_B_OPS = (";;&", "&>>", "<<<", "<<-", "&&", "||", ";;", ";&", "|&", "&>", "<<", "<>", "<&", ">&",
          ">>", ">|", "<(", ">(", "<", ">", "|", "&", ";", "(", ")")
_B_REDIR = {"<", ">", ">>", "<>", "<&", ">&", ">|", "&>", "&>>", "<<<", "<<", "<<-"}
_B_STDIN = {"<", "<<", "<<-", "<<<", "<>", "<&"}
_B_META = " \t\n;&|<>()"
_B_PREFIX = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "time"}

# PowerShell: it treats the typographic quotes as quotes, and a doubled pair as one character
# (the second: measured on 5.1, 'a<U+2019><U+2019>b' -> a<U+2019>b and 'a'<U+2019>b' -> a<U+2019>b).
_PS_SQ = "'\u2018\u2019\u201a\u201b"
_PS_DQ = '"\u201c\u201d\u201e'
_PS_WS = " \t\f\v\u00a0"
_PS_TERM = set(_PS_WS + "\r\n;|&(){}<>")
_PS_SEP = {";", "|", "&&", "||", "(", ")", "{", "}", "$(", "@(", "@{"}
_PS_REDIR_RE = re.compile(r"[0-6*]?>>?(?:&[12])?|<")


class _Unknown(Exception):
    """The command holds something v1 does not understand: leave the whole command untouched."""


class _Tok:
    __slots__ = ("kind", "start", "end", "text", "op", "ionum", "hd", "content")

    def __init__(self, kind, start, end, text):
        self.kind, self.start, self.end, self.text = kind, start, end, text
        self.op = self.ionum = self.hd = self.content = None


class _Snippet:
    """One inline program found in the command, before judgement."""
    __slots__ = ("mode", "source", "raw", "hint", "mangle", "edits")

    def __init__(self, mode, source, raw, edits, hint=None, mangle=None):
        self.mode = mode            # "c" | "dash" | "implicit": how Python received the program
        self.source = source        # the intended source, or None when the shell will expand it
        self.raw = raw              # the text as written, for the "would this be filed" test
        self.edits = edits          # [(start, end, prefix, needs_path, suffix)]
        self.hint = hint            # {"kind", "token", "delim"}: the shell expands it on purpose
        self.mangle = mangle        # refusal text: PowerShell would silently change the code


# =============================================================================== small helpers

def _where(text, idx):
    line = text.count("\n", 0, idx) + 1
    col = idx - (text.rfind("\n", 0, idx) + 1) + 1
    return f"line {line}, column {col}"


def _line_count(text):
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _would_file(text):
    return text is not None and ("\\" in text or len(text) > MAX_CHARS
                                 or _line_count(text) > MAX_LINES)


def _clip(text, n):
    return text if len(text) <= n else text[:n - 3] + "..."


def _shell_token(s, at, powershell=False):
    """The expansion starting at s[at], as the hint names it: $NAME, ${...}, $(...), `...`."""
    if s[at] == "`":
        if powershell:
            return s[at:at + 2]                          # a PowerShell escape: `t, `n, ...
        end = s.find("`", at + 1)
        return s[at:end + 1] if 0 < end - at <= 24 else "`...`"
    if s.startswith("$(", at):
        return "$(...)"
    if s.startswith("${", at):
        end = s.find("}", at)
        return s[at:end + 1] if 0 < end - at <= 24 else "${...}"
    pattern = (r"\$(?:[A-Za-z_][A-Za-z0-9_]*:)?[A-Za-z_][A-Za-z0-9_]*" if powershell
               else r"\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9@*#?$!-])")
    m = re.match(pattern, s[at:])
    return m.group() if m else "$"


# =============================================================================== bash lexer

def _bash_op(s, i):
    if s[i] not in "&|;<>()":
        return None
    for op in _B_OPS:
        if s.startswith(op, i):
            return op
    return None


def _bash_sq_end(s, j):
    k = s.find("'", j + 1)
    if k < 0:
        raise _Unknown("unterminated single quote")
    return k + 1


def _bash_dq_end(s, j):
    n, k = len(s), j + 1
    while k < n:
        c = s[k]
        if c == "\\":
            k += 2
        elif c == '"':
            return k + 1
        elif c == "`":
            k = _bash_bq_end(s, k)
        elif c == "$":
            k = _bash_dollar_end(s, k)
        else:
            k += 1
    raise _Unknown("unterminated double quote")


def _bash_bq_end(s, j):
    n, k = len(s), j + 1
    while k < n:
        if s[k] == "\\":
            k += 2
        elif s[k] == "`":
            return k + 1
        else:
            k += 1
    raise _Unknown("unterminated backquote")


def _bash_dollar_end(s, k):
    if s.startswith("$(", k):
        return _bash_group_end(s, k + 1, "(", ")")
    if s.startswith("${", k):
        return _bash_group_end(s, k + 1, "{", "}")
    if s.startswith("$'", k):
        n, m = len(s), k + 2
        while m < n:
            if s[m] == "\\":
                m += 2
            elif s[m] == "'":
                return m + 1
            else:
                m += 1
        raise _Unknown("unterminated $'")
    if s.startswith('$"', k):
        return _bash_dq_end(s, k + 1)
    return k + 1


def _bash_group_end(s, p, open_ch, close_ch):
    """s[p] == open_ch; the index after its matching close_ch, quote-aware."""
    n, depth, m = len(s), 0, p
    while m < n:
        c = s[m]
        if c == "\\":
            m += 2
            continue
        if c == "'":
            m = _bash_sq_end(s, m)
            continue
        if c == '"':
            m = _bash_dq_end(s, m)
            continue
        if c == "`":
            m = _bash_bq_end(s, m)
            continue
        if c == "$" and m + 1 < n and s[m + 1] in "({":
            m = _bash_dollar_end(s, m)
            continue
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return m + 1
        m += 1
    raise _Unknown("unbalanced group")


def _bash_word_end(s, i):
    n, j = len(s), i
    while j < n:
        c = s[j]
        if c in _B_META:
            break
        if c == "\\":
            j += 2
        elif c == "'":
            j = _bash_sq_end(s, j)
        elif c == '"':
            j = _bash_dq_end(s, j)
        elif c == "`":
            j = _bash_bq_end(s, j)
        elif c == "$":
            j = _bash_dollar_end(s, j)
        else:
            j += 1
    if j > n:
        raise _Unknown("dangling backslash")
    return j


def _bash_heredoc_delim(word):
    """(delimiter after quote removal, quoted?) for the word after << or <<-."""
    if "$" in word or "`" in word:
        raise _Unknown("expansion in a heredoc delimiter")
    quoted = any(ch in word for ch in "'\"\\")
    out, i, n = [], 0, len(word)
    while i < n:
        ch = word[i]
        if ch == "'":
            j = word.find("'", i + 1)
            if j < 0:
                raise _Unknown("bad delimiter")
            out.append(word[i + 1:j])
            i = j + 1
        elif ch == '"':
            j, buf = i + 1, []
            while j < n and word[j] != '"':
                if word[j] == "\\" and j + 1 < n and word[j + 1] in '"\\':
                    buf.append(word[j + 1])
                    j += 2
                else:
                    buf.append(word[j])
                    j += 1
            if j >= n:
                raise _Unknown("bad delimiter")
            out.append("".join(buf))
            i = j + 1
        elif ch == "\\":
            if i + 1 >= n:
                raise _Unknown("bad delimiter")
            out.append(word[i + 1])
            i += 2
        else:
            out.append(ch)
            i += 1
    delim = "".join(out)
    if not delim or "\n" in delim:
        raise _Unknown("bad delimiter")
    return delim, quoted


def _bash_heredoc_body(s, i, hd):
    """Read one heredoc body starting at s[i]; record its span; return the index after it."""
    n, start = len(s), i
    while True:
        j = s.find("\n", i)
        line = s[i:n if j < 0 else j]
        if (line.lstrip("\t") if hd["strip"] else line) == hd["delim"]:
            hd["body_start"], hd["body_end"] = start, i
            hd["end"] = n if j < 0 else j + 1
            return hd["end"]
        if j < 0:
            raise _Unknown("heredoc never terminated")
        i = j + 1


def _bash_redirect(s, i, op, ionum, toks, pending):
    start = ionum[0] if ionum else i
    n, j = len(s), i + len(op)
    while j < n and s[j] in " \t":
        j += 1
    if j >= n or s[j] in _B_META:
        raise _Unknown("redirect without a target")
    k = _bash_word_end(s, j)
    word = s[j:k]
    if pending and "\n" in word:
        raise _Unknown("newline inside a word while a heredoc is pending")
    tok = _Tok("redir", start, k, s[start:k])
    tok.op, tok.ionum = op, (ionum[1] if ionum else None)
    if op in ("<<", "<<-"):
        delim, quoted = _bash_heredoc_delim(word)
        tok.kind = "heredoc"
        tok.hd = {"delim": delim, "quoted": quoted, "strip": op == "<<-"}
        pending.append(tok.hd)
    toks.append(tok)
    return k


def _bash_tokens(s):
    toks, pending = [], []
    n, i = len(s), 0
    while i < n:
        c = s[i]
        if c in " \t":
            i += 1
            continue
        if c == "\\" and s.startswith("\n", i + 1):
            if pending:
                raise _Unknown("line continuation while a heredoc is pending")
            i += 2
            continue
        if c == "\n":
            toks.append(_Tok("nl", i, i + 1, "\n"))
            i += 1
            for hd in pending:
                i = _bash_heredoc_body(s, i, hd)
            pending = []
            continue
        if c == "#":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        op = _bash_op(s, i)
        if op in ("<(", ">("):
            j = _bash_group_end(s, i + 1, "(", ")")
            toks.append(_Tok("word", i, j, s[i:j]))
            i = j
            continue
        if op in _B_REDIR:
            i = _bash_redirect(s, i, op, None, toks, pending)
            continue
        if op:
            toks.append(_Tok("op", i, i + len(op), op))
            i += len(op)
            continue
        j = _bash_word_end(s, i)
        text = s[i:j]
        if pending and "\n" in text:
            raise _Unknown("newline inside a word while a heredoc is pending")
        if re.fullmatch(r"[0-9]+", text) and j < n and s[j] in "<>":
            op = _bash_op(s, j)
            if op in _B_REDIR:
                i = _bash_redirect(s, j, op, (i, text), toks, pending)
                continue
        toks.append(_Tok("word", i, j, text))
        i = j
    if pending:
        raise _Unknown("heredoc never terminated")
    return toks


def _bash_dq_decode(s, start, end):
    """Bash's double-quote rules on s[start:end] (both quotes included): \\\\ \\" \\$ \\` and
    backslash-newline are the only escapes. Returns (source, None) or (None, index of the first
    unescaped $ or backquote)."""
    out, k, stop = [], start + 1, end - 1
    while k < stop:
        c = s[k]
        if c == "\\":
            d = s[k + 1]
            if d in '\\"$`':
                out.append(d)
                k += 2
            elif d == "\n":
                k += 2
            else:
                out.append(c)
                k += 1
            continue
        if c in "$`":
            return None, k
        out.append(c)
        k += 1
    return "".join(out), None


# =============================================================================== shared flag scan

def _scan_flags(tokens, is_arg, is_plain):
    """Walk the interpreter's flags. Returns (mode, index of the -c/- token, last flag token) with
    mode "c", "dash" or "implicit", or None for any shape v1 does not handle (a script, -m, ...)."""
    last, k = None, 0
    while k < len(tokens):
        t = tokens[k]
        if not is_arg(t):
            k += 1                      # a redirect among the flags
            continue
        w = t.text
        if w == "-c":
            return "c", k, last
        if w == "-":
            return "dash", k, last
        if not is_plain(t):
            return None
        if w in ("-X", "-W"):
            if k + 1 >= len(tokens) or not is_plain(tokens[k + 1]):
                return None
            last = tokens[k + 1]
            k += 2
            continue
        if _FLAG_RE.fullmatch(w) and not (w[1:2].isdigit() and last is not None):
            last = t
            k += 1
            continue
        return None
    return "implicit", None, last


# =============================================================================== bash shapes

def _bash_is_plain(t):
    return t.kind == "word" and _PLAIN_RE.fullmatch(t.text) is not None


def _bash_snippet(s, cmd):
    words = [k for k, t in enumerate(cmd) if t.kind == "word"]
    w = 0
    while w < len(words) and (cmd[words[w]].text in _B_PREFIX
                              or _ASSIGN_RE.match(cmd[words[w]].text)):
        w += 1
    if w >= len(words) or cmd[words[w]].text not in INTERPRETERS:
        return None
    name_at = words[w]
    name, rest = cmd[name_at], cmd[name_at + 1:]
    scan = _scan_flags(rest, lambda t: t.kind == "word", _bash_is_plain)
    if scan is None:
        return None
    mode, k, last = scan

    if mode == "c":
        if k + 1 >= len(rest) or rest[k + 1].kind != "word":
            return None
        dash_c, code = rest[k], rest[k + 1]
        text = code.text
        edits = [(dash_c.start, code.end, "", True, "")]
        if len(text) >= 2 and text[0] == "'" and text.find("'", 1) == len(text) - 1:
            return _Snippet("c", text[1:-1], text[1:-1], edits)
        if len(text) >= 2 and text[0] == '"' and _bash_dq_end(s, code.start) == code.end:
            source, at = _bash_dq_decode(s, code.start, code.end)
            raw = text[1:-1]
            if at is None:
                return _Snippet("c", source, raw, edits)
            return _Snippet("c", None, raw, edits,
                            hint={"kind": "bash-dq", "token": _shell_token(s, at)})
        return None

    heredocs = [t for t in cmd if t.kind == "heredoc"]
    stdin = [t for t in cmd if t.kind in ("redir", "heredoc") and t.op in _B_STDIN
             and t.ionum in (None, "0")]
    if len(heredocs) != 1 or stdin != heredocs or heredocs[0].op != "<<":
        return None
    hd_tok = heredocs[0]
    hd = hd_tok.hd
    body = s[hd["body_start"]:hd["body_end"]]
    if mode == "dash":
        edits = [(rest[k].start, rest[k].end, "", True, "")]
    else:
        at = (last or name).end
        edits = [(at, at, " ", True, "")]
    edits += [(hd_tok.start, hd_tok.end, "</dev/null", False, ""),
              (hd["body_start"], hd["end"], "", False, "")]
    if not hd["quoted"]:
        m = re.search(r"[$`]", body)
        if m:
            hint = {"kind": "heredoc", "token": _shell_token(s, hd["body_start"] + m.start()),
                    "delim": hd["delim"]}
            return _Snippet(mode, None, body, edits, hint=hint)
        if "\\" in body:
            return _Snippet(mode, None, body, edits,
                            hint={"kind": "heredoc-backslash", "delim": hd["delim"]})
    return _Snippet(mode, body, body, edits)


def _find_bash(s):
    toks = _bash_tokens(s)
    found, cur = [], []
    for t in toks + [_Tok("nl", len(s), len(s), "")]:
        if t.kind in ("nl", "op"):
            if cur:
                sn = _bash_snippet(s, cur)
                if sn:
                    found.append(sn)
            cur = []
        else:
            cur.append(t)
    return found


# =============================================================================== PowerShell lexer

def _ps_sq_end(s, j):
    n, k = len(s), j + 1
    while k < n:
        if s[k] in _PS_SQ:
            if k + 1 < n and s[k + 1] in _PS_SQ:
                k += 2
                continue
            return k + 1
        k += 1
    raise _Unknown("unterminated single quote")


def _ps_dq_end(s, j):
    n, k = len(s), j + 1
    while k < n:
        c = s[k]
        if c == "`":
            k += 2
        elif c in _PS_DQ:
            if k + 1 < n and s[k + 1] in _PS_DQ:
                k += 2
                continue
            return k + 1
        elif c == "$" and k + 1 < n and s[k + 1] == "(":
            k = _ps_tokens(s, k + 2, close_paren=True)[1]
        else:
            k += 1
    raise _Unknown("unterminated double quote")


def _ps_herestring(s, i):
    """s[i] == '@' followed by a quote: a here-string token, or _Unknown."""
    n, dq = len(s), s[i + 1] in _PS_DQ
    j = i + 2
    while j < n and s[j] in " \t":
        j += 1
    if s.startswith("\r\n", j):
        j += 2
    elif j < n and s[j] == "\n":
        j += 1
    else:
        raise _Unknown("here-string header must end its line")
    closers, cs, k = (_PS_DQ if dq else _PS_SQ), j, j
    while True:
        if k + 1 < n and s[k] in closers and s[k + 1] == "@":
            if k == cs:
                ce = k
            else:
                ce = k - 2 if (k - 2 >= cs and s[k - 2] == "\r") else k - 1
            tok = _Tok("hs_dq" if dq else "hs_sq", i, k + 2, s[i:k + 2])
            tok.content = (cs, ce)
            return tok
        nl = s.find("\n", k)
        if nl < 0:
            raise _Unknown("unterminated here-string")
        k = nl + 1


def _ps_word(s, i):
    n, j = len(s), i
    while j < n:
        c = s[j]
        if c in _PS_TERM:
            break
        if c == "`":
            j += 2
        elif c in _PS_SQ:
            j = _ps_sq_end(s, j)
        elif c in _PS_DQ:
            j = _ps_dq_end(s, j)
        elif c == "$" and j + 1 < n and s[j + 1] == "(":
            j = _ps_tokens(s, j + 2, close_paren=True)[1]
        elif c == "$" and j + 1 < n and s[j + 1] == "{":
            e = s.find("}", j)
            if e < 0:
                raise _Unknown("unterminated ${")
            j = e + 1
        else:
            j += 1
    if j > n:
        raise _Unknown("dangling backtick")
    if s[i] in _PS_SQ and _ps_sq_end(s, i) == j:
        return j, "sq"
    if s[i] in _PS_DQ and _ps_dq_end(s, i) == j:
        return j, "dq"
    return j, "word"


def _ps_tokens(s, i=0, close_paren=False):
    """Flat PowerShell tokens from s[i]. With close_paren, stop after the ')' that closes a $(
    already opened, and return (tokens, index after it)."""
    toks, n, depth = [], len(s), 0
    while i < n:
        c = s[i]
        if c in _PS_WS:
            i += 1
            continue
        if c == "`" and i + 1 < n and s[i + 1] in "\r\n":
            i += 3 if s.startswith("\r\n", i + 1) else 2
            continue
        if c in "\r\n":
            j = i + 2 if s.startswith("\r\n", i) else i + 1
            toks.append(_Tok("nl", i, j, s[i:j]))
            i = j
            continue
        if s.startswith("<#", i):
            j = s.find("#>", i + 2)
            if j < 0:
                raise _Unknown("unterminated block comment")
            i = j + 2
            continue
        if c == "#":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "@" and i + 1 < n and (s[i + 1] in _PS_SQ or s[i + 1] in _PS_DQ):
            tok = _ps_herestring(s, i)
            toks.append(tok)
            i = tok.end
            continue
        if s.startswith(("@(", "@{", "$("), i):
            toks.append(_Tok("op", i, i + 2, s[i:i + 2]))
            if s[i + 1] == "(":
                depth += 1
            i += 2
            continue
        if s.startswith("&&", i) or s.startswith("||", i):
            toks.append(_Tok("op", i, i + 2, s[i:i + 2]))
            i += 2
            continue
        if c in ";|&(){}":
            if close_paren and c == ")":
                if depth == 0:
                    return toks, i + 1
                depth -= 1
            elif c == "(":
                depth += 1
            toks.append(_Tok("op", i, i + 1, c))
            i += 1
            continue
        if c in "<>" or (c in "0123456*" and i + 1 < n and s[i + 1] == ">"):
            m = _PS_REDIR_RE.match(s, i)
            toks.append(_Tok("op", i, m.end(), m.group()))
            i = m.end()
            continue
        j, kind = _ps_word(s, i)
        toks.append(_Tok(kind, i, j, s[i:j]))
        i = j
    if close_paren:
        raise _Unknown("unbalanced $(")
    return toks, i


def _ps_elements(toks):
    """Pipeline elements as (separator before, tokens). A leading & is the call operator."""
    elems, cur, sep = [], [], None
    for t in toks:
        if t.kind == "nl" or (t.kind == "op" and (t.text in _PS_SEP or (t.text == "&" and cur))):
            if cur:
                elems.append((sep, cur))
            cur, sep = [], ("\n" if t.kind == "nl" else t.text)
            continue
        cur.append(t)
    if cur:
        elems.append((sep, cur))
    return elems


# What Windows PowerShell 5.1 makes of `X inside "..." (measured on 5.1.26100, 2026-10-13): these
# letters become control characters; every other X stays itself and the backtick is dropped.
_PS_ESCAPES = {"0": "a NUL character", "a": "a bell character (0x07)", "b": "a backspace (0x08)",
               "f": "a form feed (0x0c)", "n": "a newline", "r": "a carriage return",
               "t": "a tab", "v": "a vertical tab (0x0b)"}


def _ps_backslash_backtick(s, at):
    """Refusal text for a bash-style \\` at s[at] inside a PowerShell double-quoted string."""
    x = s[at + 2:at + 3]
    if x in _PS_ESCAPES and x:
        effect = f"turned `{x} into {_PS_ESCAPES[x]}"
    elif x == "`":
        effect = "read `` as one backtick"
    else:
        effect = f"dropped the backtick (`{x} became {x})"
    return (f"{_where(s, at)} of the command: \\` is a bash escape, but inside a PowerShell "
            "double-quoted string the backtick is PowerShell's own escape character. Windows "
            f"PowerShell 5.1 would have kept the backslash and {effect}, so Python would not "
            "receive the literal backtick you meant. Fix: use single quotes ('...' or @'...'@), "
            "where a backtick is literal, or Write a file and run it.")


def _ps_unquote(s, tok):
    """(decoded value, raw inner text, index of the first $ or backtick PowerShell would expand
    or None, index of a bash-style \\` PowerShell would mangle or None, (inner start, end))."""
    double = tok.kind in ("dq", "hs_dq")
    if tok.kind in ("hs_sq", "hs_dq"):
        cs, ce = tok.content
    else:
        cs, ce = tok.start + 1, tok.end - 1
    raw = s[cs:ce]
    if double:
        bad = raw.find("\\`")
        if bad >= 0:
            return None, raw, None, cs + bad, (cs, ce)
        m = re.search(r"[$`]", raw)
        if m:
            return None, raw, cs + m.start(), None, (cs, ce)
    if tok.kind in ("hs_sq", "hs_dq"):
        return raw, raw, None, None, (cs, ce)
    quotes = _PS_SQ if tok.kind == "sq" else _PS_DQ
    out, k = [], cs
    while k < ce:
        c = s[k]
        if c in quotes and k + 1 < ce and s[k + 1] in quotes:
            out.append(s[k + 1])
            k += 2
            continue
        out.append(c)
        k += 1
    return "".join(out), raw, None, None, (cs, ce)


def _ps_snippet(s, elems, idx):
    sep, el = elems[idx]
    if el and el[0].kind == "op" and el[0].text == "&":
        el = el[1:]
    if not el or el[0].kind != "word" or el[0].text.lower() not in INTERPRETERS:
        return None
    name, rest = el[0], el[1:]
    scan = _scan_flags(rest, lambda t: t.kind != "op",
                       lambda t: t.kind == "word" and _PLAIN_RE.fullmatch(t.text) is not None)
    if scan is None:
        return None
    mode, k, last = scan

    if mode == "c":
        if k + 1 >= len(rest) or rest[k + 1].kind not in ("sq", "dq", "hs_sq", "hs_dq"):
            return None
        code = rest[k + 1]
        edits = [(rest[k].start, code.end, "", True, "")]
        source, raw, at, bad, (cs, ce) = _ps_unquote(s, code)
        if bad is not None:
            return _Snippet("c", None, raw, edits, mangle=_ps_backslash_backtick(s, bad))
        if at is not None:
            return _Snippet("c", None, raw, edits,
                            hint={"kind": "ps-dq", "token": _shell_token(s, at, powershell=True)})
        if '"' in source:
            # Measured on 5.1 (2026-10-13): 'a"b' 'c d' arrived in py as ['ab c', 'd e'].
            q = s.find('"', cs, ce)
            q = code.start if q < 0 else q
            why = (f"{_where(s, q)} of the command: the -c argument holds a double quote. Windows "
                   "PowerShell 5.1 would have handed it to py unescaped, and py's command-line "
                   "parser reads a bare quote as a quoting toggle: the quote vanishes and the code "
                   "is cut or merged at spaces (measured: 'a\"b' 'c d' arrived as 'ab c', 'd e'). "
                   "Fix: Write the code to a file and run it, or pipe a single-quoted here-string "
                   "instead: @'<newline>...<newline>'@ | py -")
            return _Snippet("c", source, raw, edits, mangle=why)
        return _Snippet("c", source, raw, edits)

    # A piped here-string: the element before must be the here-string alone, then "|".
    if idx == 0 or sep != "|":
        return None
    psep, pel = elems[idx - 1]
    if len(pel) != 1 or pel[0].kind not in ("hs_sq", "hs_dq") or psep == "|":
        return None
    hs = pel[0]
    if mode == "dash":
        edits = [(hs.start, rest[k].end, s[name.start:rest[k].start], True, "")]
    else:
        at = (last or name).end
        edits = [(hs.start, at, s[name.start:at] + " ", True, "")]
    source, raw, at, bad, _ = _ps_unquote(s, hs)
    if bad is not None:
        return _Snippet(mode, None, raw, edits, mangle=_ps_backslash_backtick(s, bad))
    if at is not None:
        return _Snippet(mode, None, raw, edits,
                        hint={"kind": "ps-herestring", "token": _shell_token(s, at, powershell=True)})
    return _Snippet(mode, source, raw, edits)


def _find_ps(s):
    elems = _ps_elements(_ps_tokens(s)[0])
    found = []
    for idx in range(len(elems)):
        sn = _ps_snippet(s, elems, idx)
        if sn:
            found.append(sn)
    return found


# =============================================================================== layer 2: lint

def _string_hits(text, row, col):
    """Control characters a single STRING token produces: [(row, col0, shown)]."""
    import unicodedata
    m = re.match(r"[A-Za-z]*", text)
    prefix = m.group().lower()
    raw, is_bytes = "r" in prefix, "b" in prefix
    body = len(prefix)
    q = text[body:body + 3] if text[body:body + 3] in ('"""', "'''") else text[body:body + 1]
    k, stop, hits = body + len(q), len(text) - len(q), []

    def mark(at, shown):
        nl = text.rfind("\n", 0, at)
        hits.append((row + text.count("\n", 0, at), (col + at) if nl < 0 else (at - nl - 1), shown))

    while k < stop:
        ch = text[k]
        if ch in CONTROL_STR:
            mark(k, f"a literal {CONTROL_NAMES[ord(ch)]} character")
            k += 1
            continue
        if ch != "\\" or raw:
            k += 1
            continue
        d = text[k + 1:k + 2]
        span, value = 2, None
        if d in ("a", "b", "f", "v"):
            value = {"a": 7, "b": 8, "f": 12, "v": 11}[d]
        elif d == "x" and re.fullmatch(r"[0-9a-fA-F]{2}", text[k + 2:k + 4]):
            span, value = 4, int(text[k + 2:k + 4], 16)
        elif d and d in "01234567":
            oct_digits = re.match(r"[0-7]{1,3}", text[k + 1:]).group()
            span, value = 1 + len(oct_digits), int(oct_digits, 8)
        elif not is_bytes and d == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", text[k + 2:k + 6]):
            span, value = 6, int(text[k + 2:k + 6], 16)
        elif not is_bytes and d == "U" and re.fullmatch(r"[0-9a-fA-F]{8}", text[k + 2:k + 10]):
            span, value = 10, int(text[k + 2:k + 10], 16)
        elif not is_bytes and d == "N":
            named = re.match(r"\{([^}]*)\}", text[k + 2:])
            if named:
                span = 2 + len(named.group())
                try:
                    value = ord(unicodedata.lookup(named.group(1)))
                except (KeyError, TypeError):
                    value = None
        if value in CONTROL_NAMES:
            mark(k, text[k:k + span])
        k += span
    return hits


def _lint(src):
    """None when the source may run, else the refusal text (line/column of the snippet + fix)."""
    import ast
    import io
    import tokenize
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            compile(src, "<snippet>", "exec", dont_inherit=True)
        except SyntaxError as exc:
            line, col = exc.lineno or 1, exc.offset or 1
            shown = (exc.text or "").strip()
            return (f"line {line}, column {col} of the snippet: SyntaxError: {exc.msg}: {shown!r}. "
                    "Nothing ran. Fix the code (or Write it to a file and run it).")
        except ValueError as exc:                       # 3.11: NUL bytes in the source
            at = src.find("\x00")
            return (f"{_where(src, max(at, 0))} of the snippet: {exc}. Nothing ran. Write the code "
                    "to a file and run it.")
        tree = ast.parse(src)
    if MARKER_RE.search(src):
        return None
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            v = node.value
            if (isinstance(v, str) and any(c in v for c in CONTROL_STR)) or (
                    isinstance(v, bytes) and any(b in CONTROL_NAMES for b in v)):
                bad.append(node)
    if not bad:
        return None
    hits = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.STRING:
                hits.extend(_string_hits(tok.string, tok.start[0], tok.start[1]))
    except (tokenize.TokenError, SyntaxError):
        hits = []
    if not hits:                                        # fall back to where the constant starts
        node = bad[0]
        line_bytes = src.split("\n")[node.lineno - 1].encode("utf-8")
        hits = [(node.lineno, len(line_bytes[:node.col_offset].decode("utf-8", "replace")),
                 "a string")]
    row, col0, shown = hits[0]
    if shown == "\\b":
        meaning = ("is the control character BS (backspace, 0x08), not a regex word boundary. "
                   "Did you mean r'\\b'?")
    elif shown.startswith("\\"):
        value = _escape_value(shown)
        meaning = f"is the control character {CONTROL_NAMES.get(value, 'U+%04X' % (value or 0))}."
    else:
        meaning = "holds a control character."
    more = f" ({len(hits) - 1} more like it)" if len(hits) > 1 else ""
    return (f"line {row}, column {col0 + 1} of the snippet: {shown} in a non-raw string {meaning}"
            f"{more} Fix: make it a raw string, r'...', or double the backslash. If the control "
            "character is intended, add the comment # autofile: control-chars-ok")


def _escape_value(shown):
    import ast
    try:
        v = ast.literal_eval('"' + shown + '"')
        return ord(v) if len(v) == 1 else None
    except Exception:
        return None


def _has_future_import(src):
    import ast
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tree = ast.parse(src)
    return any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in tree.body)


def _judge(sn):
    """("skip" | "hint" | "refuse" | "file", hint info or refusal text or None). Only a snippet
    the hook would otherwise file earns a hint or a refusal; a short one runs exactly as today."""
    if not (_would_file(sn.raw) or _would_file(sn.source)):
        return "skip", None
    if sn.mangle is not None:
        return "refuse", sn.mangle
    if sn.hint is not None:
        return "hint", sn.hint
    problem = _lint(sn.source)
    if problem:
        return "refuse", problem
    if _has_future_import(sn.source):
        return "skip", None
    return "file", None


# =============================================================================== the file

def _semantics_line(mode):
    """Header line 2: give the file run what the inline run had."""
    if mode == "c":
        path0, argv0, file_stmt = "''", "'-c'", "del __file__"
    elif mode == "dash":
        path0, argv0, file_stmt = ("_af_os.path.dirname(_af_os.path.abspath('-'))", "'-'",
                                   "__file__ = '<stdin>'")
    else:
        path0, argv0, file_stmt = "''", "''", "__file__ = '<stdin>'"
    return ("import os as _af_os, sys as _af_sys; _af_sys.path[0:1] = [" + path0 + "] if "
            "_af_sys.path[0:1] and _af_os.path.normcase(_af_sys.path[0]) == _af_os.path.normcase("
            "_af_os.path.dirname(_af_os.path.abspath(__file__))) else _af_sys.path[0:1]; "
            "_af_sys.argv[0] = " + argv0 + "; " + file_stmt + "; del _af_os, _af_sys"
            "  # snippet-autofile: the inline run's sys.path[0], argv[0] and __file__\n")


def _render(sn, tool, command, when):
    import hashlib
    line2 = _semantics_line(sn.mode)
    sha12 = hashlib.sha256((line2 + sn.source).encode("utf-8")).hexdigest()[:12]
    cmd12 = hashlib.sha256(command.encode("utf-8", "surrogatepass")).hexdigest()[:12]
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(when))
    line1 = (f"# snippet-autofile {sha12} | from a {tool} command {cmd12} | {stamp} | "
             "the snippet starts on line 3\n")
    return f"{sha12}.py", (line1 + line2).encode("utf-8") + sn.source.encode("utf-8")


def _roots(snips_root):
    if snips_root:
        return [os.path.normpath(os.fspath(snips_root))]
    override = os.environ.get("AKASHIC_SNIPS_ROOT")
    if override:
        return [os.path.normpath(override)]
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if not temp:
        import tempfile
        temp = tempfile.gettempdir()
    fallback = os.path.join(temp, "snips")
    if os.path.isdir(PRIMARY_DRIVE):
        return [PRIMARY_ROOT, fallback]
    return [fallback]


def _agent_dir(payload):
    import hashlib
    agent = os.environ.get("AKASHIC_AGENT_ID") or "agent"
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", agent).strip("_")[:40] or "agent"
    key = "\n".join(str(payload.get(k) or "") for k in ("session_id", "transcript_path", "agent_id"))
    return f"{safe}-{hashlib.sha256(key.encode('utf-8', 'surrogatepass')).hexdigest()[:8]}"


def _write(folder, name, data, when):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    tmp = f"{path}.{os.getpid()}.{time.perf_counter_ns()}.tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    try:
        os.replace(tmp, path)
    except OSError:
        # A sibling call may be running this very file right now. Same name = same code.
        try:
            os.remove(tmp)
        except OSError:
            pass
        try:
            with open(path, "rb") as fh:
                same = fh.read().split(b"\n", 1)[1:] == data.split(b"\n", 1)[1:]
        except OSError:
            same = False
        if not same:
            raise
    try:
        os.utime(path, (when, when))
    except OSError:
        pass
    return path


def _rotate(folder, when):
    """Keep the newest KEEP_FILES snippets (and at most KEEP_BYTES) in this agent's folder."""
    entries = []
    with os.scandir(folder) as it:
        for e in it:
            if not e.is_file():
                continue
            st = e.stat()
            if e.name.endswith(".tmp"):
                if when - st.st_mtime > 3600:
                    try:
                        os.remove(e.path)
                    except OSError:
                        pass
            elif e.name.endswith(".py"):
                entries.append((st.st_mtime_ns, e.name, st.st_size, e.path))
    entries.sort(reverse=True)
    total = 0
    for idx, (_, _, size, path) in enumerate(entries):
        total += size
        if idx >= KEEP_FILES or (idx > 0 and total > KEEP_BYTES):
            try:
                os.remove(path)
            except OSError:
                pass


HINT_FILE = "_expansion_hints.json"     # per agent folder: the times of recent expansion hints
HINT_WINDOW = 600                       # seconds: "the last 10 minutes"
HINT_COUNT_FROM = 3                     # the third hint inside the window names its count
HINT_MAX = 199                          # characters: "keep the hint under 200"


def _count_hint(payload, snips_root, when):
    """Record one expansion hint in the agent's folder and return how many the folder has had in
    the last HINT_WINDOW seconds, this one included; 0 when the count cannot be kept."""
    agent_dir = _agent_dir(payload)
    for root in _roots(snips_root):
        folder = os.path.join(root, agent_dir)
        path = os.path.join(folder, HINT_FILE)
        try:
            os.makedirs(folder, exist_ok=True)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    stamps = json.load(fh)
            except (OSError, ValueError):
                stamps = []
            if not isinstance(stamps, list):
                stamps = []
            stamps = [t for t in stamps
                      if isinstance(t, (int, float)) and 0 <= when - t < HINT_WINDOW] + [when]
            tmp = f"{path}.{os.getpid()}.{time.perf_counter_ns()}.tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(stamps, fh)
            os.replace(tmp, path)
            return len(stamps)
        except OSError:
            continue
    return 0


def _hint_text(info, count):
    """One line under 200 characters: what the shell will expand, and the way out."""
    token = _clip(info.get("token", ""), 24)
    delim = _clip(info.get("delim", ""), 12)
    kind = info["kind"]
    if kind == "bash-dq":
        body = (f"This snippet relies on bash expanding {token}; if you meant a literal, use "
                "single quotes or Write a file and run it.")
    elif kind == "heredoc":
        body = (f"This heredoc relies on bash expanding {token}; if you meant a literal, quote the "
                f"delimiter (<<'{delim}') or Write a file and run it.")
    elif kind == "heredoc-backslash":
        body = ("This unquoted heredoc lets bash process its backslashes; to keep them, quote the "
                f"delimiter (<<'{delim}') or Write a file and run it.")
    elif kind == "ps-herestring":
        body = (f"This here-string relies on PowerShell expanding {token}; if you meant a literal, "
                "use @'...'@ or Write a file and run it.")
    else:
        body = (f"This snippet relies on PowerShell expanding {token}; if you meant a literal, use "
                "single quotes or Write a file and run it.")
    head = "[snippet-autofile] "
    if count >= HINT_COUNT_FROM:
        head += f"(hint {count} in 10 min) "
    return _clip(head + body, HINT_MAX)


def _quote_bash(path):
    p = path.replace("\\", "/")
    return "'" + p.replace("'", "'\\''") + "'"


def _quote_ps(path):
    return "'" + "".join(ch + ch if ch in _PS_SQ else ch for ch in path) + "'"


def _apply(command, edits):
    edits = sorted(edits, key=lambda e: (e[0], e[1]))
    for a, b in zip(edits, edits[1:]):
        if a[1] > b[0]:
            raise _Unknown("overlapping edits")
    out, pos = [], 0
    for start, end, text in edits:
        out.append(command[pos:start])
        out.append(text)
        pos = end
    out.append(command[pos:])
    return "".join(out)


def _edit_texts(sn, quoted_path):
    return [(a, b, pre + (quoted_path if needs else "") + post) for a, b, pre, needs, post in sn.edits]


def _epoch(now):
    if now is None:
        return time.time()
    if hasattr(now, "timestamp"):
        return float(now.timestamp())
    return float(now)


# =============================================================================== decide / main

def decide(payload, *, snips_root=None, now=None):
    """The hook's whole decision for one PreToolUse payload: None (untouched), a filing
    (hookSpecificOutput.updatedInput + additionalContext), a hint (additionalContext only: the
    command runs exactly as written), or a deny. Writes the snippet file(s) when it files and the
    hint counter when it hints; pure otherwise. Raises only on an internal bug (main() fails
    open on it)."""
    if not isinstance(payload, dict) or payload.get("tool_name") not in SHELL_TOOLS:
        return None
    tool = payload["tool_name"]
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return None
    command = ti.get("command")
    if not isinstance(command, str) or "py" not in command.lower():
        return None
    try:
        snippets = _find_bash(command) if tool == "Bash" else _find_ps(command)
        verdicts = [(sn,) + _judge(sn) for sn in snippets]
        refusals = [why for _, verdict, why in verdicts if verdict == "refuse"]
        if refusals:
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "[snippet-autofile] Not run. " + "\n".join(refusals)}}
        to_file = [sn for sn, verdict, _ in verdicts if verdict == "file"]
        hints = [info for _, verdict, info in verdicts if verdict == "hint"]
        if not to_file and not hints:
            return None
        if to_file:
            # DRY RUN, result unused on purpose: _apply raises _Unknown on overlapping edits, and
            # this catches that BEFORE any snippet file is written (the command is then left
            # untouched). The real splice with the real paths happens below. Pinned by
            # test_overlapping_edits_leave_the_command_untouched_and_write_nothing.
            _apply(command, [e for sn in to_file for e in _edit_texts(sn, "''")])
    except _Unknown:
        return None

    when = _epoch(now)
    hint_line = _hint_text(hints[0], _count_hint(payload, snips_root, when)) if hints else ""
    if not to_file:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                       "additionalContext": hint_line}}
    rendered = [_render(sn, tool, command, when) for sn in to_file]
    agent_dir, error, paths, folder = _agent_dir(payload), None, None, None
    for root in _roots(snips_root):
        folder = os.path.join(root, agent_dir)
        try:
            paths = [_write(folder, name, data, when) for name, data in rendered]
            break
        except OSError as exc:
            error = exc
    if paths is None:
        raise error
    try:
        _rotate(folder, when)
    except OSError:
        pass
    quote = _quote_bash if tool == "Bash" else _quote_ps
    edits = [e for sn, path in zip(to_file, paths) for e in _edit_texts(sn, quote(path))]
    updated = dict(ti)
    updated["command"] = _apply(command, edits)
    shown = ", ".join(dict.fromkeys(paths))
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": updated,
        "additionalContext": (f"[snippet-autofile] Inline Python saved as {shown} and run from that "
                              "file instead (its first two lines are a header, so traceback line "
                              "numbers are +2); next time, Write a file and run it."
                              + (" " + hint_line if hint_line else ""))}}


def _log_exception():
    import traceback
    for root in _roots(None):
        try:
            os.makedirs(root, exist_ok=True)
            path = os.path.join(root, "_errors.log")
            if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
                os.replace(path, path + ".old")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} pid {os.getpid()}\n"
                         f"{traceback.format_exc()}\n")
            return
        except Exception:
            continue


def main():
    """stdin: the PreToolUse payload (UTF-8 JSON). stdout: the hook JSON, or nothing. Always 0."""
    try:
        if os.environ.get("AKASHIC_SNIPPET_AUTOFILE", "").strip() == "0":
            return 0
        raw = sys.stdin.buffer.read()
        if not raw.strip():
            return 0
        out = decide(json.loads(raw.decode("utf-8-sig")))
        if out is not None:
            text = json.dumps(out)                      # ASCII: safe on any console code page
            sys.stdout.write(text)
            sys.stdout.flush()
    except Exception:
        _log_exception()
    return 0


if __name__ == "__main__":
    sys.exit(main())
