"""
Bifrost Console -- a live chat window onto the Bifrost bus.

A terminal chat you keep open: watch the agents (claude / cursor / ...) talk in real time, and
jump in as a participant. This IS the "wake mechanism" -- but as a thing you WATCH, not OS toasts
or sounds. (Pull-first stays the floor: agents still see mail on their next boot; this just lets a
human see + steer the conversation live.)

  py scripts/bifrost_console.py                 # join as 'human'
  py scripts/bifrost_console.py --agent ben      # join under another id

In the input line:
  hello everyone            -> broadcast to all agents
  @claude can you ...       -> direct message to one agent
  /who                      -> who's online      /help                      /quit

No Windows notifications, no sounds -- just the visible transcript.
"""
import argparse
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus, NS, _loads

# ---- look: per-agent colors (Akashic Aurora palette) ---------------------------------------
_FIXED = {
    "claude": "#d97757",   # clay
    "cursor": "#6cb6ff",   # blue
    "human":  "#7ee787",   # green
    "gemini": "#c29fff",   # violet
    "system": "#8b949e",   # gray
}
_PALETTE = ["#e3b341", "#56d4bc", "#ff9bce", "#a5d6ff", "#d2a8ff", "#f0883e"]


def color_for(agent: str) -> str:
    a = (agent or "system").lower()
    if a in _FIXED:
        return _FIXED[a]
    return _PALETTE[sum(ord(c) for c in a) % len(_PALETTE)]


def parse_input(text: str):
    """A console line -> an action dict. Pure (testable)."""
    t = (text or "").strip()
    if not t:
        return {"action": "noop"}
    if t.startswith("/"):
        cmd = t[1:].split(maxsplit=1)
        return {"action": "command", "cmd": cmd[0].lower(), "arg": cmd[1] if len(cmd) > 1 else ""}
    if t.startswith("@"):
        head, _, body = t[1:].partition(" ")
        return {"action": "send", "to": head, "kind": "chat", "body": body.strip()}
    return {"action": "send", "to": "*", "kind": "chat", "body": t}   # default: broadcast


def format_message(frm, to, kind, content, ts):
    """A message -> prompt_toolkit FormattedText (list of (style, text)). Pure (testable)."""
    when = ""
    try:
        when = datetime.fromisoformat(str(ts)).strftime("%H:%M")
    except (ValueError, TypeError):
        pass
    arrow = "all" if to in ("*", "") else to
    body = content if isinstance(content, str) else str(content)
    head_style = f"fg:{color_for(frm)} bold"
    return [
        ("", "\n"),
        (head_style, f"{frm}"),
        ("fg:#8b949e", f"  -> {arrow}  .{kind}.  {when}\n"),
        ("", f"  {body}\n"),
    ]


# ---- the app -------------------------------------------------------------------------------
def _streams(client):
    keys = []
    try:
        keys = [k for k in client.keys(f"{NS}:inbox:*")]
    except Exception:
        keys = []
    return keys + [f"{NS}:broadcast"]


def _render(pft):
    from prompt_toolkit import print_formatted_text
    from prompt_toolkit.formatted_text import FormattedText
    print_formatted_text(FormattedText(pft))


def _reader(client, my_id, stop):
    """Monitor every inbox + broadcast stream and render new messages (skip our own echo)."""
    last = {s: "$" for s in _streams(client)}   # live-only: from when the console opened
    while not stop.is_set():
        streams = _streams(client)
        for s in streams:
            last.setdefault(s, "$")
        try:
            res = client.xread({s: last[s] for s in streams}, block=1000, count=50)
        except Exception:
            time.sleep(1)
            continue
        for stream, entries in res or []:
            for sid, fields in entries:
                last[stream] = sid
                frm = fields.get("frm", "")
                if frm == my_id:
                    continue                     # we already echoed our own line on send
                _render(format_message(frm, fields.get("to", ""), fields.get("kind", ""),
                                       _loads(fields.get("content")), fields.get("ts", "")))


def _heartbeat(bus, stop):
    while not stop.is_set():
        bus.register()
        stop.wait(30)


def _banner(bus):
    from rich.console import Console
    from rich.panel import Panel
    c = Console()
    online = ", ".join(p["agent"] for p in bus.presence()) or "(nobody yet)"
    c.print(Panel.fit(
        "[bold #d97757]Bifrost Console[/]  ·  Akashic Aurora\n"
        "[#8b949e]watch the agents talk; type to join. "
        "[/][#7ee787]@agent[/][#8b949e] = direct, plain = broadcast, /who /help /quit[/]\n"
        f"[#8b949e]online:[/] {online}",
        border_style="#6cb6ff"))


def main():
    ap = argparse.ArgumentParser(description="Bifrost live chat console")
    ap.add_argument("--agent", default="human", help="your id on the bus (default: human)")
    args = ap.parse_args()
    my_id = args.agent

    bus = Bus(my_id)
    if not bus.online:
        print("Bifrost bus is OFFLINE (Redis unreachable). Start Redis and retry.")
        return 1
    bus.register()
    reader_client = bus._client.__class__(connection_pool=bus._client.connection_pool) \
        if hasattr(bus._client, "connection_pool") else bus._client

    _banner(bus)

    from prompt_toolkit import PromptSession, print_formatted_text
    from prompt_toolkit.formatted_text import FormattedText
    from prompt_toolkit.patch_stdout import patch_stdout

    stop = threading.Event()
    threading.Thread(target=_reader, args=(reader_client, my_id, stop), daemon=True).start()
    threading.Thread(target=_heartbeat, args=(bus, stop), daemon=True).start()

    session = PromptSession()
    prompt = FormattedText([(f"fg:{color_for(my_id)} bold", f"{my_id} "), ("fg:#7ee787", "> ")])
    try:
        while True:
            with patch_stdout():
                line = session.prompt(prompt)
            act = parse_input(line)
            if act["action"] == "noop":
                continue
            if act["action"] == "command":
                cmd = act["cmd"]
                if cmd in ("quit", "q", "exit"):
                    break
                if cmd == "who":
                    print_formatted_text(FormattedText([("fg:#8b949e",
                        "online: " + (", ".join(p["agent"] for p in bus.presence()) or "(nobody)"))]))
                elif cmd == "help":
                    print_formatted_text(FormattedText([("fg:#8b949e",
                        "plain text = broadcast · @agent text = direct · /who · /quit")]))
                else:
                    print_formatted_text(FormattedText([("fg:#f0883e", f"unknown command /{cmd}")]))
                continue
            # send + echo our own line locally (the reader skips it)
            to, kind, body = act["to"], act["kind"], act["body"]
            if not body:
                continue
            if to == "*":
                bus.broadcast(kind, body)
            else:
                bus.send(to, kind, body)
            _render(format_message(my_id, to, kind, body, datetime.now().isoformat()))
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        stop.set()
    print("bifrost console closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
