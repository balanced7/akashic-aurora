"""One way for every CLI verb to print: TOON for agents, colour and layout for humans.

A verb builds plain data (dicts, lists, primitives) and hands it to emit(). The mode
(core/axi/mode.py) picks the renderer:

    agent  TOON on stdout (core/axi/toon.py), with next-step hints in a `help` field, per AXI
           (https://axi.md): token-efficient, definitive, and self-describing.
    human  a terminal layout built with rich: aligned key/value pairs, tables for lists,
           colour for status words, and the next steps set apart at the bottom. Colour follows
           the usual conventions (NO_COLOR, FORCE_COLOR, a pipe gets none).

Errors use fail(): agent mode prints {error, code, help} on stdout, which is where an agent
reads; human mode prints a red line on stderr. Exit codes follow AXI: 0 success (including
"nothing to do"), 1 error, 2 usage error.

The human renderer is generic so every verb gets a readable layout for free; a verb that wants
more passes its own `human=` function, which receives a rich Console and the same data.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from core.axi import mode as _mode
from core.axi.toon import encode

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2

#: Status words coloured in human mode, by meaning.
GOOD = {"ok", "yes", "true", "live", "pass", "passed", "green", "healthy", "done", "active", "up", "armed", "match"}
WARN = {"warn", "warning", "stale", "partial", "pending", "degraded", "open", "draft", "unknown", "skipped"}
BAD = {"error", "fail", "failed", "dead", "down", "red", "no", "false", "blocked", "drift", "missing", "offline"}


def is_agent(stream=None) -> bool:
    return _mode.resolve(stream) == _mode.AGENT


# ------------------------------------------------------------------ building blocks


def truncate(text: str | None, limit: int = 800) -> tuple[str, bool]:
    """(text cut to `limit` characters with a size note, was it cut). AXI section 3: never drop a
    long field, show a preview and say how much is missing."""
    text = "" if text is None else " ".join(str(text).split())
    if len(text) <= limit:
        return text, False
    return f"{text[:limit].rstrip()}... (truncated, {len(text)} chars total)", True


def fields_arg(requested: str | None, default: Sequence[str], available: Sequence[str]) -> list[str]:
    """Resolve a --fields value: the default schema plus any extra fields asked for by name, in
    the available order. `--fields all` gives every available field. Unknown names raise
    ValueError naming them and the valid ones."""
    if not requested:
        return list(default)
    asked = [f.strip() for f in requested.split(",") if f.strip()]
    if asked == ["all"]:
        return list(available)
    unknown = [f for f in asked if f not in available]
    if unknown:
        raise ValueError(f"unknown field(s) {', '.join(unknown)}; available: {', '.join(available)}")
    want = {*default, *asked}
    return [f for f in available if f in want]


# ------------------------------------------------------------------ emit / fail


def emit(
    data: Mapping[str, Any],
    *,
    hints: Sequence[str] = (),
    human: Callable[[Any, Mapping[str, Any]], None] | None = None,
    title: str | None = None,
    stream=None,
) -> int:
    """Print `data` for the current audience and return EXIT_OK.

    `help` holds next-step commands (AXI section 9); pass none when the output answers the
    question by itself. `title` heads the human view only.
    """
    stream = sys.stdout if stream is None else stream
    if is_agent(stream):
        stream.write(agent_text(data, hints) + "\n")
        return EXIT_OK
    console = _console(stream)
    if title:
        console.print(f"[bold cyan]{_esc(title)}[/]")
    if human is not None:
        human(console, data)
    else:
        render_human(console, data)
    if hints:
        _render_help(console, hints)
    return EXIT_OK


def fail(
    message: str,
    *,
    code: str = "ERROR",
    hints: Sequence[str] = (),
    exit_code: int = EXIT_ERROR,
    details: Mapping[str, Any] | None = None,
) -> int:
    """Report an error and return the exit code for the caller to return.

    Agent mode: {error, code, ...details, help} as TOON on stdout. Human mode: a red line and
    the suggested fixes on stderr.
    """
    if is_agent(sys.stdout):
        doc: dict[str, Any] = {"error": message, "code": code}
        if details:
            doc.update(details)
        sys.stdout.write(agent_text(doc, hints) + "\n")
        return exit_code
    console = _console(sys.stderr)
    console.print(f"[bold red]✗ error:[/] {_esc(message)}")
    for k, v in (details or {}).items():
        console.print(f"  [dim]{_esc(str(k))}:[/] {_esc(_text(v))}")
    if hints:
        _render_help(console, hints, label="Try")
    return exit_code


def agent_text(data: Mapping[str, Any], hints: Sequence[str] = ()) -> str:
    """The agent rendering: the data as TOON, then the next steps as AXI writes them --
    `help[N]:` and one command per indented line, unquoted, so a command reads exactly as it is
    typed. (Inside the TOON document a list of commands would be one comma-joined line with every
    quote escaped.)"""
    text = encode(dict(data)) if data else ""
    if hints:
        lines = [f"help[{len(hints)}]:"] + [f"  {' '.join(str(h).split())}" for h in hints]
        text = (text + "\n" if text else "") + "\n".join(lines)
    return text


# ------------------------------------------------------------------ human rendering


def _console(stream):
    from rich.console import Console

    force = os.getenv("FORCE_COLOR") not in (None, "", "0")
    return Console(
        file=stream,
        highlight=False,
        soft_wrap=False,
        force_terminal=True if force else None,
        no_color=bool(os.getenv("NO_COLOR")),
    )


def _esc(text: str) -> str:
    from rich.markup import escape

    return escape(text)


def _text(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:,.3f}".rstrip("0").rstrip(".")
    if isinstance(v, (list, tuple)) and all(not isinstance(x, (dict, list, tuple)) for x in v):
        return ", ".join(_text(x) for x in v) if v else "none"
    return str(v)


def styled(v) -> str:
    """Rich markup for one value: status words coloured by meaning, numbers bold, None dim."""
    if v is None:
        return "[dim]—[/]"
    if isinstance(v, bool):
        return "[green]yes[/]" if v else "[red]no[/]"
    if isinstance(v, (int, float)):
        return f"[bold]{_esc(_text(v))}[/]"
    s = _text(v)
    word = s.strip().lower()
    if word in GOOD:
        return f"[green]{_esc(s)}[/]"
    if word in WARN:
        return f"[yellow]{_esc(s)}[/]"
    if word in BAD:
        return f"[red]{_esc(s)}[/]"
    return _esc(s)


def _is_table(v) -> bool:
    return (
        isinstance(v, list)
        and bool(v)
        and all(isinstance(r, Mapping) for r in v)
        and all(not isinstance(x, (dict, list)) for r in v for x in r.values())
    )


def table(rows: Sequence[Mapping[str, Any]], *, title: str | None = None, columns: Sequence[str] | None = None):
    """A rich Table for uniform rows, status words coloured."""
    from rich import box
    from rich.table import Table

    cols = list(columns or (rows[0].keys() if rows else []))
    t = Table(box=box.SIMPLE_HEAD, title=title, title_justify="left", title_style="bold", header_style="bold cyan")
    for c in cols:
        t.add_column(str(c).replace("_", " "), overflow="fold")
    for r in rows:
        t.add_row(*(styled(r.get(c)) for c in cols))
    return t


def render_human(console, data: Mapping[str, Any], *, indent: int = 0) -> None:
    """The generic human layout: scalars as an aligned list, flat row lists as tables, nested
    objects as indented sections."""
    pad = "  " * indent
    scalars = {k: v for k, v in data.items() if not isinstance(v, (Mapping, list))}
    if scalars:
        width = max(len(str(k)) for k in scalars)
        for k, v in scalars.items():
            console.print(f"{pad}[dim]{_esc(str(k).replace('_', ' ')).ljust(width)}[/]  {styled(v)}")
    for k, v in data.items():
        if k in scalars or k == "help":
            continue
        label = str(k).replace("_", " ")
        if isinstance(v, list) and not v:
            console.print(f"{pad}[dim]{_esc(label)}: none[/]")
        elif _is_table(v):
            console.print(table(v, title=f"{pad}{label} ({len(v)})"))
        elif isinstance(v, list):
            console.print(f"{pad}[bold]{_esc(label)}[/] [dim]({len(v)})[/]")
            for item in v:
                if isinstance(item, Mapping):
                    render_human(console, item, indent=indent + 1)
                    console.print()
                else:
                    console.print(f"{pad}  • {styled(item)}")
        else:
            console.print(f"{pad}[bold]{_esc(label)}[/]")
            render_human(console, v, indent=indent + 1)


def _render_help(console, hints: Sequence[str], *, label: str = "Next") -> None:
    console.print()
    console.print(f"[bold]{label}:[/]")
    for h in hints:
        console.print(f"  [cyan]›[/] {_esc(h)}")
