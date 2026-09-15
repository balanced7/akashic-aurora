"""The jam verbs of py -m arsenal.pianocue (jam-spec 7): cards, the deck, loops, try, runs and templates.

arsenal/pianocue.py adds them with add_verbs(sub) and dispatches with run(args, out). Every verb talks to the server's
routes (arsenal/jam/runs.py JamApi) on --port (default 8793). With no server answering, the card, deck and template
verbs call the same routes in-process on the files under --jam-root (default state/arsenal/jam), and say so; play,
show, loop, try and jam need the server.

  card add|list|info|edit|rm|restore|trash|keep|play|show|open     deck [order|seed]
  loop start|stop|tempo|next|set|mute|unmute                       try CARD|CHORDS
  jam status|runs|mark                                             template save-from-moment|save-last

CARD is an id or a unique id prefix. CARD|CHORDS also takes a chord line in the 4.1 string form
("1maj9:4 | [6 major] | 1add9:4 | rest:2"), which needs --key. Slots on the command line count from 1.

Exit codes: 0 done; 2 bad input (the message names the flag); 3 no jam page; 4 no server, an old server, or the
voicing bridge unavailable; 5 conflict (the card or run changed underneath: run it again).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlencode

from arsenal.jam import schemas as S
from arsenal.jam.resolve import midi_name, parse_line, parse_notes

VERBS = ("card", "deck", "loop", "try", "jam", "template")
DEFAULT_PORT = 8793
OK, BAD_INPUT, NO_PAGE, NO_SERVER, CONFLICT = 0, 2, 3, 4, 5
NO_LISTENER = "no piano page is listening - open http://127.0.0.1:{port}/piano"
RELOAD = "the piano page is open but predates the jam space - reload the piano page"
FIELD_FLAGS = {"title": "--title", "meaning": "--meaning", "group": "--group", "kind": "--kind", "key": "--key",
               "chords": "--chords", "explanation": "--explain", "why": "--why", "try": "--try",
               "listen_for": "--listen-for", "tempo": "--bpm", "bars": "--bars", "checks": "--check",
               "moments": "--moment", "replay": "--replay", "tags": "--tag", "related": "--related",
               "variants": "--variant", "voicing": "--voicing", "playback": "--vel", "theory_name": "--theory-name",
               "also_in": "--also-in", "style": "--style", "groove": "--groove", "backing": "--backing"}


class CliError(Exception):
    def __init__(self, message: str, code: int = BAD_INPUT):
        super().__init__(message)
        self.code = code


# ================================================================================================= client
class Client:
    """The server's routes over HTTP; with no server and offline=True, the same routes in-process."""

    def __init__(self, port: int, jam_root: Optional[str] = None, offline: bool = False, err=None):
        self.port = port
        self.jam_root = jam_root
        self.offline_ok = offline
        self.offline = False
        self.err = err or sys.stderr
        self._api = None

    def call(self, method: str, path: str, body: Optional[dict] = None, query: Optional[dict] = None
             ) -> Tuple[int, dict]:
        query = {k: v for k, v in (query or {}).items() if v is not None}
        if self.offline:
            return self._local(method, path, body, query)
        url = f"http://127.0.0.1:{self.port}{path}" + (f"?{urlencode(query)}" if query else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw or b"null")
            except ValueError:
                payload = {"error": raw.decode("utf-8", "replace")[:300]}
            if exc.code == 404 and "no route" in str((payload or {}).get("error", "")):
                raise CliError(f"the server on 127.0.0.1:{self.port} predates the jam routes - restart "
                               f"py -m arsenal serve --port {self.port}", NO_SERVER)
            return exc.code, payload or {}
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            if not self.offline_ok:
                raise CliError(f"no arsenal server answers on 127.0.0.1:{self.port} "
                               f"({getattr(exc, 'reason', exc)}) - start it with py -m arsenal serve --port "
                               f"{self.port}", NO_SERVER)
            self.offline = True
            from arsenal.jam.cards import DEFAULT_ROOT
            print(f"no server on 127.0.0.1:{self.port}: writing the files under {self.jam_root or DEFAULT_ROOT} "
                  f"directly", file=self.err)
            return self._local(method, path, body, query)

    def _local(self, method, path, body, query):
        if self._api is None:
            from arsenal.jam.runs import JamApi
            self._api = JamApi(root=self.jam_root)
        return self._api.handle(method, path, {k: [str(v)] for k, v in query.items()}, body)


def _check(status: int, reply: dict, flags: Optional[dict] = None) -> dict:
    if status == 200:
        return reply
    message = (reply or {}).get("error") or f"the server answered {status}"
    field = (reply or {}).get("field")
    flag = (flags or FIELD_FLAGS).get(str(field).split(".")[0].split("[")[0]) if field else None
    if flag and flag not in message:
        message += f" ({flag})"
    if status == 409:
        raise CliError(f"conflict: {message}; run it again", CONFLICT)
    if status in (503, 403, 413):
        raise CliError(message, NO_SERVER)
    raise CliError(message, BAD_INPUT)


# ================================================================================================= helpers
def _names(notes) -> str:
    return " ".join(midi_name(n) for n in notes)


def _one_based(value: str, flag: str) -> int:
    if not re.fullmatch(r"\d{1,3}", str(value)) or int(value) < 1:
        raise CliError(f"{flag} takes a slot number from 1 (got {value!r})")
    return int(value) - 1


def _find_card(client: Client, ref: str) -> Optional[dict]:
    """The stored card an id or unique prefix names, or None when nothing matches."""
    if S.ID_RE.match(ref or ""):
        status, reply = client.call("GET", f"/api/piano/deck/cards/{ref}")
        if status == 200:
            return reply["card"]
    status, reply = client.call("GET", "/api/piano/deck", query={"archived": "1"})
    ids = [c["id"] for c in _check(status, reply)["cards"] if c["id"].startswith(ref or "\0")]
    if len(ids) > 1:
        raise CliError(f"{ref!r} matches {len(ids)} cards: {', '.join(ids[:8])}")
    if len(ids) == 1:
        return _check(*client.call("GET", f"/api/piano/deck/cards/{ids[0]}"))["card"]
    return None


def _card(client: Client, ref: str) -> dict:
    card = _find_card(client, ref)
    if card is None:
        raise CliError(f"no card {ref}")
    return card


def _target(client: Client, text: str, key: Optional[str]) -> dict:
    """{card_id} or {chords, key} for a CARD|CHORDS argument."""
    card = _find_card(client, text)
    if card is not None:
        out = {"card_id": card["id"]}
        if key:
            out["key"] = key
        return out
    try:
        items = parse_line(text)
    except ValueError as exc:
        raise CliError(f"{text!r} is no card and no chord line: {exc}")
    if not key:
        raise CliError(f"{text!r} is a chord line, which needs --key (e.g. --key \"Eb major\")")
    return {"chords": items, "key": key}


def _jam_page(client: Client) -> None:
    status, st = client.call("GET", "/api/piano/cues/status")
    st = _check(status, st)
    if "caps" not in st:
        raise CliError(f"the server on 127.0.0.1:{client.port} predates the jam space - restart it", NO_SERVER)
    if st["caps"].get("jam1", 0) == 0:
        raise CliError(RELOAD if st.get("listeners") else NO_LISTENER.format(port=client.port), NO_PAGE)


def _slot_rows(d: dict, backing: Optional[str] = None, loop: bool = False) -> List[str]:
    rows = []
    m = d["beats_per_bar"]
    show = backing or d["backing"]
    show = show if show in ("full", "comp", "bass") else "comp"
    name_w = max([len(s["name"] or "") for s in d["slots"]] + [6])
    num_w = max([len(s["n"] or "notes") for s in d["slots"]] + [5])
    last_key = d["key"]
    for s in d["slots"]:
        if s["key"] != last_key:
            rows.append(f"  [in {s['key']}]")
            last_key = s["key"]
        bar, beat = divmod(s["at_beat"], m)
        where = f"bar {int(bar) + 1}" + (f" beat {beat + 1:g}" if beat else "")
        pr = s["page_reads"] or {}
        if s["upper_same"]:
            reads = "(upper same)"
        elif pr.get("name") and pr.get("name") != s["name"]:
            reads = f"page reads {pr['name']}" + (f" ({pr['number']})" if pr.get("number") else "") + \
                f": {pr['match']}"
        else:
            reads = f"page reads {pr.get('name') or s['name']}"
        notes = s["voicings"][show] if loop else s["voicings"]["play"]
        label = f"{show} " if loop else ""
        rows.append(f"  {where:<11} {s['name'] or '':<{name_w}}  {s['n'] or 'notes':<{num_w}}  "
                    f"{label}{_names(notes):<24}  {reads}")
        for w in s["warnings"]:
            rows.append(f"              note: {w}")
    return rows


def _print_card(client: Client, card: dict, out, key=None, variant=None, backing=None, texts=True) -> None:
    kind, ckey = card["kind"], card["key"]
    tempo = S.card_settings(card)["tempo"]
    bars = S.card_settings(card)["bars"]
    print(f"card {card['id']} rev {card['rev']} ({kind}, {key or ckey}, {tempo['bpm']:g} bpm"
          + (f", {bars} bars" if bars else "") + f"): {card['title']}", file=out)
    print(f"  {card['meaning']}", file=out)
    lines = [variant] if variant not in (None, "all") else \
        ([None] if card.get("chords") else []) + [v["id"] for v in card.get("variants") or []]
    if variant == "all":
        lines = [v["id"] for v in card.get("variants") or []] or [None]
    for v in lines:
        query = {"key": key, "variant": v, "backing": backing}
        d = _check(*client.call("GET", f"/api/piano/deck/cards/{card['id']}/resolve", query=query))["def"]
        if v is not None:
            label = next((x.get("label") for x in card.get("variants") or [] if x["id"] == v), None)
            print(f"  variant {v}" + (f": {label}" if label else ""), file=out)
        for row in _slot_rows(d):
            print(row, file=out)
        for w in d["warnings"]:
            print(f"  note: {w}", file=out)
    if texts:
        for field, label in (("explanation", "what"), ("why", "why"), ("try", "try"), ("listen_for", "listen")):
            if card.get(field):
                print(f"  {label:<6} {card[field]}", file=out)


# ================================================================================================= card
def _hold(text: str):
    if text in ("legato", "detached"):
        return text
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        raise CliError(f"--hold takes legato, detached or a number of beats (got {text!r})")


def _check_flag(text: str, i: int) -> dict:
    m = re.match(r"(.*?)\bsay=(.*)$", text.strip())
    head, say = (m.group(1), m.group(2)) if m else (text, None)
    check = {}
    for part in head.split():
        if "=" not in part:
            raise CliError(f"--check takes key=value parts, like \"slot=2 role=#11 want=present say=...\" "
                           f"(got {part!r})")
        k, v = part.split("=", 1)
        if k == "slot":
            check["slot"] = _one_based(v, "--check slot")
        elif k in ("role", "want", "relative_to", "variant", "id"):
            check[k] = v
        else:
            raise CliError(f"--check has no {k!r} (use slot, role, want, relative_to, variant, id, say)")
    if say is not None:
        check["say"] = say.strip()
    check.setdefault("id", f"check-{i + 1}")
    return check


def _moment_flag(text: str) -> dict:
    m = re.fullmatch(r"([^@\s]+)@(\d{1,3}:[0-5]\d)(?:-(\d{1,3}:[0-5]\d))?(?:=(.+))?", text.strip())
    if not m:
        raise CliError(f"--moment takes SESSION@m:ss[-m:ss][=label] (got {text!r})")
    return {"session": m.group(1), "at": m.group(2), "until": m.group(3), "label": m.group(4)}


def _replay_flag(text: str) -> dict:
    m = re.fullmatch(r"([^@\s]+)@(\d{1,3}:[0-5]\d)\+(\d+(?:\.\d+)?)", text.strip())
    if not m:
        raise CliError(f"--replay takes SESSION@m:ss+SECONDS (got {text!r})")
    return {"session": m.group(1), "at": m.group(2), "seconds": float(m.group(3)), "speed": 1}


def _chord_items(line_items: List[dict]) -> List[dict]:
    return [it for it in line_items if "key" not in it and "rest" not in it]


def _apply_line_flags(chords: List[dict], args) -> None:
    items = _chord_items(chords)
    for spec in args.notes_for or []:
        if "=" not in spec:
            raise CliError(f'--notes-for takes SLOT="NOTES" (got {spec!r})')
        slot, notes = spec.split("=", 1)
        i = _one_based(slot, "--notes-for")
        if i >= len(items):
            raise CliError(f"--notes-for slot {i + 1}: the line has {len(items)} chords")
        try:
            items[i]["notes"] = parse_notes(notes.strip().strip('"'))
        except ValueError as exc:
            raise CliError(f"--notes-for slot {i + 1}: {exc}")
    for slot in args.upper_same or []:
        i = _one_based(slot, "--upper-same")
        if i >= len(items):
            raise CliError(f"--upper-same slot {i + 1}: the line has {len(items)} chords")
        items[i]["upper"] = "same"


def _names_line(text: str, key: Optional[str]) -> List[dict]:
    from arsenal import nashville
    if not key:
        raise CliError("--names needs --key to number the chords")
    items = []
    for seg in text.split("|"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.fullmatch(r"(.+?)(?::(\d+(?:\.\d+)?))?", seg)
        got = nashville.nashville_from_name(m.group(1), key)
        if not got or got.get("kind") != "chord" or not S.NUMBER_RE.match(got.get("text") or ""):
            raise CliError(f"--names: {m.group(1)!r} has no Nashville number in {key}")
        item = {"n": got["text"]}
        if m.group(2):
            beats = float(m.group(2))
            item["beats"] = int(beats) if beats.is_integer() else beats
        items.append(item)
    return items


def _card_from_flags(args, base: Optional[dict] = None) -> dict:
    card = dict(base or {})
    for flag, field in (("id", "id"), ("title", "title"), ("meaning", "meaning"), ("theory_name", "theory_name"),
                        ("group", "group"), ("kind", "kind"), ("key", "key"), ("style", "style"),
                        ("explain", "explanation"), ("why", "why"), ("try_text", "try"), ("listen_for", "listen_for"),
                        ("groove", "groove"), ("backing", "backing")):
        value = getattr(args, flag, None)
        if value is not None:
            card[field] = value
    if getattr(args, "bars", None) is not None:
        card["bars"] = args.bars
    if getattr(args, "also_in", None):
        card["also_in"] = args.also_in
    sources = [x for x in ("chords", "names", "notes") if getattr(args, x, None)]
    if len(sources) > 1:
        raise CliError(f"give one of --chords, --names or --notes (got {', '.join('--' + s for s in sources)})")
    try:
        if getattr(args, "chords", None):
            card["chords"] = parse_line(args.chords)
        elif getattr(args, "names", None):
            card["chords"] = _names_line(args.names, card.get("key"))
        elif getattr(args, "notes", None):
            card["chords"] = [{"n": None, "beats": 4, "notes": parse_notes(args.notes)}]
    except ValueError as exc:
        raise CliError(f"--{sources[0]}: {exc}")
    if card.get("chords") is not None and (getattr(args, "notes_for", None) or getattr(args, "upper_same", None)):
        _apply_line_flags(card["chords"], args)
    variants = {v["id"]: v for v in card.get("variants") or []}
    for spec in getattr(args, "variant", None) or []:
        m = re.fullmatch(r"([a-f])(?:=(.*?))?:\s+(.+)", spec.strip())
        if not m:
            raise CliError(f'--variant takes "b=label: 1maj9:4 | 5^7:8" (got {spec!r})')
        try:
            v = {"id": m.group(1), "chords": parse_line(m.group(3))}
        except ValueError as exc:
            raise CliError(f"--variant {m.group(1)}: {exc}")
        if m.group(2):
            v["label"] = m.group(2).strip()
        variants[m.group(1)] = v
    for spec in getattr(args, "variant_key", None) or []:
        m = re.fullmatch(r"([a-f])=(.+)", spec.strip())
        if not m or m.group(1) not in variants:
            raise CliError(f'--variant-key takes b="b7 major" for a variant given with --variant (got {spec!r})')
        variants[m.group(1)]["key"] = m.group(2).strip().strip('"')
    if variants:
        card["variants"] = [variants[k] for k in sorted(variants)]
    if getattr(args, "bpm", None) is not None or getattr(args, "beats_per_bar", None) is not None:
        tempo = dict(card.get("tempo") or {"bpm": 66, "beats_per_bar": 4, "feel": "straight"})
        if args.bpm is not None:
            tempo["bpm"] = int(args.bpm) if float(args.bpm).is_integer() else args.bpm
        if args.beats_per_bar is not None:
            tempo["beats_per_bar"] = args.beats_per_bar
        card["tempo"] = tempo
    if getattr(args, "voicing", None) or getattr(args, "voice_lead", False):
        voicing = dict(card.get("voicing") or {"style": "spread", "voice_lead": False, "octave": None})
        if args.voicing:
            voicing["style"] = args.voicing
        if args.voice_lead:
            voicing["voice_lead"] = True
        card["voicing"] = voicing
    if any(getattr(args, f, None) is not None for f in ("vel", "arp", "hold")):
        playback = dict(card.get("playback") or {"velocity": 48, "arpeggio_ms": 0, "hold": "legato", "count": None})
        if args.vel is not None:
            playback["velocity"] = args.vel
        if args.arp is not None:
            playback["arpeggio_ms"] = args.arp
        if args.hold is not None:
            playback["hold"] = _hold(args.hold)
        card["playback"] = playback
    if getattr(args, "check", None):
        card["checks"] = [_check_flag(c, i) for i, c in enumerate(args.check)]
    if getattr(args, "tag", None):
        card["tags"] = args.tag
    if getattr(args, "moment", None):
        card["moments"] = [_moment_flag(m) for m in args.moment]
    if getattr(args, "replay", None):
        card["replay"] = _replay_flag(args.replay)
    if getattr(args, "related", None):
        card["related"] = args.related
    return card


def _cmd_card(args, client: Client, out) -> int:
    verb = args.card_verb
    if verb == "add":
        base = None
        if args.from_json:
            try:
                base = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise CliError(f"--from-json: {exc}")
        card = _card_from_flags(args, base)
        card.setdefault("created_by", args.by)
        if args.dry_run:
            print(json.dumps({"card": card, "by": args.by}, indent=2, ensure_ascii=False), file=out)
            return OK
        reply = _check(*client.call("POST", "/api/piano/deck/cards", {"card": card, "by": args.by}))
        return _report_card(client, reply, args, out)
    if verb == "list":
        doc = _check(*client.call("GET", "/api/piano/deck", query={
            "group": args.group, "kind": args.kind, "tag": args.tag, "by": args.author,
            "archived": "1" if args.archived else None}))
        return _print_deck(doc, args, out)
    if verb == "info":
        card = _card(client, args.card)
        if args.json:
            d = _check(*client.call("GET", f"/api/piano/deck/cards/{card['id']}/resolve",
                                    query={"key": args.key, "variant": args.variant, "backing": args.backing}))
            print(json.dumps({"card": card, "def": d["def"]}, indent=2, ensure_ascii=False), file=out)
            return OK
        _print_card(client, card, out, args.key, args.variant, args.backing)
        return OK
    if verb == "edit":
        card = _card(client, args.card)
        patch = _edit_patch(card, args)
        if not patch:
            raise CliError("card edit: nothing to change (give a flag such as --title or --set FIELD=JSON)")
        body = {"patch": patch, "if_rev": args.if_rev if args.if_rev is not None else card["rev"], "by": args.by}
        if args.dry_run:
            print(json.dumps(body, indent=2, ensure_ascii=False), file=out)
            return OK
        reply = _check(*client.call("POST", f"/api/piano/deck/cards/{card['id']}/update", body))
        return _report_card(client, reply, args, out)
    if verb == "rm":
        card = _card(client, args.card)
        body = {"if_rev": args.if_rev if args.if_rev is not None else card["rev"], "by": args.by}
        if args.dry_run:
            print(json.dumps(body), file=out)
            return OK
        reply = _check(*client.call("POST", f"/api/piano/deck/cards/{card['id']}/delete", body))
        print(f"card {card['id']} moved to {reply['trashed']} (card restore {card['id']} brings it back)", file=out)
        return OK
    if verb == "restore":
        reply = _check(*client.call("POST", f"/api/piano/deck/cards/{args.card}/restore", {"by": args.by}))
        print(f"card {reply['id']} restored as rev {reply['rev']}", file=out)
        return OK
    if verb == "trash":
        reply = _check(*client.call("GET", "/api/piano/deck/trash"))
        if args.json:
            print(json.dumps(reply, indent=2, ensure_ascii=False), file=out)
            return OK
        print(f"trash: {len(reply['trash'])} card{'s' if len(reply['trash']) != 1 else ''}", file=out)
        for t in reply["trash"]:
            print(f"  {t['id']:<32} rev {t['rev']:<3} {t['trashed_at']}  {t.get('title') or ''}", file=out)
        return OK
    if verb == "keep":
        card = _card(client, args.card)
        body = {"by": args.by}
        if args.key:
            body["key"] = args.key
        reply = _check(*client.call("POST", f"/api/piano/deck/cards/{card['id']}/keep", body))
        return _report_card(client, reply, args, out)
    if verb == "play":
        return _start(args, client, out, "play")
    if verb == "show":
        return _show(args, client, out)
    if verb == "open":
        card = _card(client, args.card)
        reply = _check(*client.call("POST", "/api/piano/deck/open", {"card_id": card["id"], "by": args.by}))
        print(f"opened the deck on {card['id']} for {reply['listeners']} deck page"
              f"{'s' if reply['listeners'] != 1 else ''}", file=out)
        if reply["listeners"] == 0:
            status, st = client.call("GET", "/api/piano/cues/status")
            print(RELOAD if status == 200 and st.get("listeners") else NO_LISTENER.format(port=client.port),
                  file=sys.stderr)
            return NO_PAGE
        return OK
    raise CliError(f"card {verb}?")


def _edit_patch(card: dict, args) -> dict:
    new = _card_from_flags(args, card)
    patch = {}
    for key, value in new.items():
        if key in S.CARD_UNPATCHABLE or key in ("updated_at", "updated_by"):
            continue
        if card.get(key) != value:
            patch[key] = value
    if args.notes_for or args.upper_same:
        if not args.chords:
            chords = json.loads(json.dumps(card.get("chords") or []))
            _apply_line_flags(chords, args)
            patch["chords"] = chords
    tags = list(patch.get("tags", card.get("tags") or []))
    for t in args.add_tag or []:
        if t not in tags:
            tags.append(t)
    for t in args.rm_tag or []:
        tags = [x for x in tags if x != t]
    if tags != (card.get("tags") or []):
        patch["tags"] = tags
    moments = list(patch.get("moments", card.get("moments") or []))
    for m in args.add_moment or []:
        moments.append(_moment_flag(m))
    for n in sorted((_one_based(x, "--rm-moment") for x in args.rm_moment or []), reverse=True):
        if n >= len(moments):
            raise CliError(f"--rm-moment {n + 1}: the card has {len(moments)} moments")
        moments.pop(n)
    if moments != (card.get("moments") or []):
        patch["moments"] = moments
    for spec in args.set or []:
        if "=" not in spec:
            raise CliError(f"--set takes FIELD=JSON (got {spec!r})")
        field, raw = spec.split("=", 1)
        try:
            patch[field] = json.loads(raw)
        except ValueError:
            patch[field] = raw
    for flag, field, value in (("favorite", "favorite", True), ("unfavorite", "favorite", False),
                               ("archive", "archived", True), ("unarchive", "archived", False)):
        if getattr(args, flag, False):
            patch[field] = value
    return patch


def _report_card(client: Client, reply: dict, args, out) -> int:
    card = reply["card"]
    if getattr(args, "json", False):
        print(json.dumps(reply, indent=2, ensure_ascii=False), file=out)
        return OK
    _print_card(client, card, out, texts=False)
    for w in reply.get("warnings") or []:
        print(f"  note: {w}", file=out)
    return OK


def _print_deck(doc: dict, args, out) -> int:
    if getattr(args, "json", False):
        print(json.dumps(doc, indent=2, ensure_ascii=False), file=out)
        return OK
    cards = doc["cards"]
    by_claude = sum(1 for c in cards if c["created_by"] == "claude")
    print(f"deck rev {doc['rev']}: {len(cards)} card{'s' if len(cards) != 1 else ''} ({by_claude} by claude, "
          f"{len(cards) - by_claude} by daniel)", file=out)
    for c in cards:
        numbers = c["numbers"] or " ".join(c["variants"])
        print(f"  {c['group']:<6} {c['kind']:<12} {c['id']:<28} {c['key']:<9} {numbers[:34]:<34} {c['title']}",
              file=out)
    return OK


# ================================================================================================= play, show, loop, try
def _start(args, client: Client, out, mode: str) -> int:
    _jam_page(client)
    body = _target(client, args.target, args.key)
    body.update(mode=mode, by="claude")
    for flag, field in (("variant", "variant"), ("bpm", "bpm"), ("count_in", "count_in"), ("passes", "passes"),
                        ("groove", "groove"), ("humanize", "humanize"), ("seed", "seed"), ("walk", "walk"),
                        ("level", "level"), ("voicing", "voicing"), ("arp", "arp_ms"), ("vel", "velocity")):
        value = getattr(args, flag, None)
        if value is not None:
            body[field] = int(value) if isinstance(value, float) and value.is_integer() else value
    if getattr(args, "slot", None) is not None:
        body["slot"] = _one_based(args.slot, "--slot")
    if mode == "try":
        body["try_backing"] = args.backing or "bass"
        body.setdefault("passes", 2)
    elif getattr(args, "backing", None):
        body["backing"] = args.backing
    if args.now:
        body["now"] = True
    reply = _check(*client.call("POST", "/api/piano/jam/start", body),
                   {**FIELD_FLAGS, "card_id": "CARD", "count_in": "--count-in", "try_backing": "--backing"})
    d = reply["def"]
    title = d["card"]["title"] if d["card"] else "chords"
    bars = d["cycle_beats"] // d["beats_per_bar"]
    settings = body
    what = {"play": "play", "loop": "loop", "try": "try"}[mode]
    extra = ""
    if mode == "loop":
        st = _check(*client.call("GET", "/api/piano/jam"))
        s0 = (st.get("run") or {}).get("settings", [{}])[0] if (st.get("run") or {}).get("run") == reply["run"] else {}
        extra = f", {s0.get('groove', settings.get('groove') or '?')}/{s0.get('backing', d['backing'])}"
        passes = body.get("passes")
        extra += f", {passes} passes" if passes else ", until stopped"
    elif mode == "try":
        extra = f", {body['try_backing']} backing, {body['passes']} passes"
    print(f"run {reply['run']}: {what} \"{title}\" in {d['key']}, {reply['bpm']:g} bpm, {bars} bar"
          f"{'s' if bars != 1 else ''}{extra}", file=out)
    for row in _slot_rows(d, loop=mode != "play"):
        print(row, file=out)
    for w in d["warnings"]:
        print(f"  note: {w}", file=out)
    pages = reply.get("jam_pages", 0)
    owner = f" (owner {reply['owner']})" if reply.get("owner") else ""
    if reply["state"] == "pending":
        print(f"waiting for Daniel's pause on {pages} jam page{'s' if pages != 1 else ''}{owner}; --now skips the wait",
              file=out)
    else:
        lead = (reply["start_epoch_ms"] - _now_ms()) / 1000
        print(f"starts in {max(0.0, lead):.1f} s on {pages} jam page{'s' if pages != 1 else ''}{owner}"
              + (f", on the bar where {reply['swapped_from']} stops" if reply.get("swapped_from") else ""), file=out)
    return OK


def _now_ms() -> float:
    import time
    return time.time() * 1000


def _show(args, client: Client, out) -> int:
    target = _target(client, args.target, args.key)
    slot = _one_based(args.slot, "--slot") if args.slot is not None else 0
    if "card_id" in target:
        d = _check(*client.call("GET", f"/api/piano/deck/cards/{target['card_id']}/resolve",
                                query={"key": args.key, "variant": args.variant, "slot": slot}))["def"]
    else:
        from arsenal.jam.resolve import BridgeUnavailable, ResolveError, Resolver
        try:
            d = Resolver().resolve_chords(target["chords"], target["key"], slot=slot)
        except ResolveError as exc:
            raise CliError(str(exc))
        except BridgeUnavailable as exc:
            raise CliError(str(exc), NO_SERVER)
    s = d["slots"][0]
    cue = {"type": "hover", "notes": s["voicings"]["play"], "label": s["name"],
           "detail": f"{s['n']} in {s['key']}" if s["n"] else s["key"], "source": "claude",
           "hold_ms": int(round((args.hold or 0) * 1000))}
    reply = _check(*client.call("POST", "/api/piano/cue", {"cue": cue}))
    print(f"show {s['name']} ({_names(s['voicings']['play'])}): cue #{reply['id']} to {reply['listeners']} "
          f"listener{'s' if reply['listeners'] != 1 else ''}", file=out)
    if reply["listeners"] == 0:
        print(NO_LISTENER.format(port=client.port), file=sys.stderr)
        return NO_PAGE
    return OK


def _running(client: Client) -> dict:
    st = _check(*client.call("GET", "/api/piano/jam"))
    run = st.get("run")
    if not run or run["closed"]:
        raise CliError("no loop or try is running")
    return st


def _control(client: Client, run: dict, body: dict, out, verb: str) -> int:
    reply = _check(*client.call("POST", f"/api/piano/jam/runs/{run['run']}/control", body),
                   {"bpm": "BPM", "at": "--at", "settings": "--groove", "card_id": "CARD", "key": "--key",
                    "variant": "--variant"})
    wait = (reply["epoch_ms"] - _now_ms()) / 1000
    where = f"bar {reply['effective_bar']}" if reply.get("effective_bar") is not None else "now"
    print(f"version {reply['version']}: {verb} from {where} (in {max(0.0, wait):.1f} s)", file=out)
    if reply.get("note"):
        print(f"  note: {reply['note']}", file=out)
    return OK


def _cmd_loop(args, client: Client, out) -> int:
    verb = args.loop_verb
    if verb == "start":
        return _start(args, client, out, "loop")
    st = _running(client)
    run = st["run"]
    if verb == "stop":
        at = "now" if args.now else (args.at or "bar")
        return _control(client, run, {"op": "stop", "at": at, "by": "claude"}, out, "stop")
    if verb == "tempo":
        value = args.bpm
        bpm = value if re.fullmatch(r"[+-]\d+(\.\d+)?", value) else _float(value, "BPM")
        return _control(client, run, {"op": "tempo", "bpm": bpm, "at": args.at or "bar", "by": "claude"}, out,
                        f"tempo {value}")
    if verb == "next":
        body = {"op": "next", "by": "claude"}
        if args.target:
            body.update(_target(client, args.target, args.key or (st.get("def") or {}).get("key")))
        if args.variant:
            body["variant"] = args.variant
        if args.key:
            body["key"] = args.key
        if args.at:
            body["at"] = args.at
        return _control(client, run, body, out, "next")
    if verb == "set":
        settings = {k: getattr(args, k) for k in ("groove", "backing", "humanize", "walk", "level")
                    if getattr(args, k) is not None}
        if not settings:
            raise CliError("loop set: give --groove, --backing, --humanize, --walk or --level")
        return _control(client, run, {"op": "set", "settings": settings, "at": args.at or "bar", "by": "claude"},
                        out, "set " + " ".join(f"{k}={v}" for k, v in settings.items()))
    return _control(client, run, {"op": verb, "by": "claude"}, out, verb)


def _float(text: str, flag: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise CliError(f"{flag} must be a number or +N / -N (got {text!r})")
    return int(value) if value.is_integer() else value


# ================================================================================================= jam, deck, template
def _cmd_jam(args, client: Client, out) -> int:
    verb = args.jam_verb
    if verb == "mark":
        reply = _check(*client.call("POST", "/api/piano/jam/mark", {"text": " ".join(args.text), "by": "claude"}))
        print(f"marked run {reply['run']} (line {reply['seq']})", file=out)
        return OK
    if verb == "runs":
        query = {"limit": args.limit}
        if args.card:
            query["card"] = _card(client, args.card)["id"]
        reply = _check(*client.call("GET", "/api/piano/jam/runs", query=query))
        if args.json:
            print(json.dumps(reply, indent=2, ensure_ascii=False), file=out)
            return OK
        for run in reply["runs"]:
            print("  " + _run_line(run), file=out)
        if not reply["runs"]:
            print("no runs yet", file=out)
        return OK
    st = _check(*client.call("GET", "/api/piano/jam"))
    cues = _check(*client.call("GET", "/api/piano/cues/status"))
    deck = _check(*client.call("GET", "/api/piano/deck"))
    runs = _check(*client.call("GET", "/api/piano/jam/runs", query={"limit": args.runs}))["runs"]
    if args.json:
        print(json.dumps({"jam": st, "cues": cues, "deck": {"rev": deck["rev"], "cards": len(deck["cards"])},
                          "runs": runs}, indent=2, ensure_ascii=False), file=out)
        return OK
    owner = st.get("owner")
    lease = f", lease {max(0, (owner['lease_until_epoch_ms'] - st['now_epoch_ms']) / 1000):.0f} s" if owner else ""
    print(f"pages  {cues['listeners']} listening ({cues.get('caps', {}).get('jam1', 0)} with jam1), sound owner "
          f"{owner['page_id'] if owner else 'none'}{lease}", file=out)
    run = st.get("run")
    if run:
        d = st.get("def") or {}
        p = st.get("position")
        title = (run.get("card") or {}).get("title") or "chords"
        bpm = p["bpm"] if p else (run["segments"][0]["bpm"] if run["segments"] else "?")  # the tempo sounding now
        print(f"{run['mode']:<6} {run['run']}  \"{title}\", {d.get('key', run['key'])}, {bpm} bpm, "
              f"version {run['last_version']}, {run['state']}", file=out)
        if p:
            slot = d["slots"][p["slot"]] if p.get("slot") is not None and d.get("slots") else None
            print(f"       bar {p['bar']} beat {int(p['beat']) + 1} (pass {p['pass'] + 1}"
                  + (f", slot {p['slot'] + 1}: {slot['name']}" if slot else "") + ")"
                  + (" counting in" if p.get("counting_in") else ""), file=out)
        if run["closed"]:
            print(f"       stops at bar {run['stop_bar']} ({run['stop_reason']})", file=out)
    else:
        print("run    none", file=out)
    for waiting in st.get("pending") or []:
        title = (waiting.get("card") or {}).get("title") or "chords"
        print(f"knock  {waiting['mode']} {waiting['run']}  \"{title}\", waiting for Daniel's pause", file=out)
    print(f"deck   {len(deck['cards'])} cards, rev {deck['rev']}", file=out)
    if runs:
        print("runs   " + " | ".join(f"{(r.get('card') or {}).get('id') or 'chords'} ({r['mode']}, {r['state']})"
                                     for r in runs), file=out)
    return OK


def _run_line(run: dict) -> str:
    title = (run.get("card") or {}).get("title") or "chords"
    return f"{run['run']}  {run['mode']:<5} {run['state']:<8} {title} ({run['key']})" + \
        (f", stopped: {run['stop_reason']}" if run.get("stop_reason") else "")


def _cmd_deck(args, client: Client, out) -> int:
    if args.action is None:
        if args.cards:
            raise CliError(f"deck takes order or seed before card ids (got {args.cards[0]!r})")
        doc = _check(*client.call("GET", "/api/piano/deck", query={"group": args.group}))
        return _print_deck(doc, args, out)
    if args.action == "order":
        if not args.cards:
            raise CliError("deck order needs card ids, first to last")
        ids = [_card(client, ref)["id"] for ref in args.cards]
        rev = _check(*client.call("GET", "/api/piano/deck"))["rev"]
        if args.dry_run:
            print(json.dumps({"order": ids, "if_rev": rev}), file=out)
            return OK
        reply = _check(*client.call("POST", "/api/piano/deck/order", {"order": ids, "if_rev": rev, "by": "claude"}))
        print(f"deck rev {reply['rev']}: {', '.join(ids)} first", file=out)
        return OK
    body = {"update": args.update, "dry_run": args.dry_run, "by": "claude"}
    if args.moments:
        try:
            body["moments"] = json.loads(Path(args.moments).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CliError(f"--moments: {exc}")
    reply = _check(*client.call("POST", "/api/piano/deck/seed", body))
    if args.json:
        print(json.dumps(reply, indent=2), file=out)
        return OK
    head = "would install" if args.dry_run else "installed"
    print(f"seed: {head} {len(reply['installed'])}, updated {len(reply['updated'])}, kept {len(reply['kept'])}"
          f" ({reply['moments']} moment links)", file=out)
    for label in ("installed", "updated", "kept"):
        if reply[label]:
            print(f"  {label}: {', '.join(reply[label])}", file=out)
    return OK


def _cmd_template(args, client: Client, out) -> int:
    from arsenal.performance import PerformanceError, PerformanceStore
    store = PerformanceStore(args.root)
    session = args.session if getattr(args, "session", "latest") != "latest" else store.latest()
    if args.template_verb == "save-last":
        session = store.latest()
    if not session:
        raise CliError(f"no practice sessions under {store.root}")
    try:
        moment = moment_from_log(store, session, getattr(args, "at", None), getattr(args, "until", None),
                                 getattr(args, "key", "auto"), last=args.template_verb == "save-last")
    except PerformanceError as exc:
        raise CliError(f"cannot read session {session}: {exc}")
    except ValueError as exc:
        raise CliError(str(exc))
    if args.title:
        moment["title"] = args.title
    if getattr(args, "id", None):
        moment["id"] = args.id
    if getattr(args, "beats", None) is not None:
        moment["beats"] = int(args.beats) if float(args.beats).is_integer() else args.beats
    if args.dry_run:
        print(json.dumps({"moment": moment, "by": "claude"}, indent=2, ensure_ascii=False), file=out)
        return OK
    reply = _check(*client.call("POST", "/api/piano/deck/templates", {"moment": moment, "by": "claude"}))
    return _report_card(client, reply, args, out)


def moment_from_log(store, session: str, at: Optional[str], until: Optional[str], key: str = "auto",
                    last: bool = False) -> dict:
    """The harmonic window at AT (or the longest overlapping AT..UNTIL, or the last one) read into a moment: the
    distinct MIDI notes heard for at least half the window, none below its main bass note, at most 16 (DATA 2.10)."""
    from arsenal import practice
    from arsenal.jam.cards import TEMPLATE_MAX_NOTES
    from arsenal.jam.resolve import note_midi
    from arsenal.pianocue import parse_clock
    events, _problems = practice.read_events(store, session)
    if not events:
        raise ValueError(f"session {session} has no notes")
    doc = practice.analyze(events)
    rows = [r for r in doc["windows"] if r.get("start_ms") is not None]
    if not rows:
        raise ValueError(f"session {session} has no harmonic windows")
    if last:
        chordal = [r for r in rows if r.get("kind") == "chord"] or rows
        row = chordal[-1]
    else:
        start = parse_clock(at)
        if until:
            end = parse_clock(until)
            overlap = [(min(r["end_ms"], end) - max(r["start_ms"], start), r) for r in rows
                       if r["start_ms"] < end and r["end_ms"] > start]
            if not overlap:
                raise ValueError(f"no harmonic window between {at} and {until}")
            row = max(overlap, key=lambda x: x[0])[1]
        else:
            hits = [r for r in rows if r["start_ms"] <= start < r["end_ms"]]
            if not hits:
                raise ValueError(f"no harmonic window at {at} in session {session}")
            row = hits[0]
    w0, w1 = row["start_ms"], row["end_ms"]
    length = max(1, w1 - w0)
    heard = {}
    for n in practice.sounding(events)["notes"]:
        ov = min(n["end_ms"], w1) - max(n["on_ms"], w0)
        if ov > 0:
            heard[n["note"]] = heard.get(n["note"], 0) + ov
    notes = [note for note, ms in heard.items() if ms / length >= practice.CHORD_SHARE]
    bass_name = (row.get("bass") or {}).get("note")
    try:
        bass = note_midi(bass_name) if bass_name else None
    except ValueError:
        bass = None
    if bass is not None:
        notes = [n for n in notes if n >= bass]
    notes = sorted(set(notes))
    if not notes:
        raise ValueError(f"nothing sounds for half of the window at {practice.clock(w0)}")
    if len(notes) > TEMPLATE_MAX_NOTES:
        keep = sorted(notes[1:], key=lambda n: (-heard[n], -n))[:TEMPLATE_MAX_NOTES - 1]
        notes = sorted([notes[0]] + keep)
    return {"session": session, "at_ms": int(w0), "until_ms": int(w1), "notes": notes,
            "name": row.get("analysed_as") or row.get("name"), "number": row.get("number"),
            "key": row.get("key") if key in (None, "auto") else key, "beats": 4}


# ================================================================================================= parser
def add_verbs(sub) -> None:
    def common(p, writes=False):
        p.add_argument("--port", type=int, default=DEFAULT_PORT, help="the arsenal server's port (default 8793)")
        p.add_argument("--jam-root", help="the jam files when no server answers (default state/arsenal/jam)")
        if writes:
            p.add_argument("--json", action="store_true", help="print the server's answer as JSON")
            p.add_argument("--dry-run", action="store_true", help="print the request and send nothing")

    def card_fields(p, adding):
        p.add_argument("--title")
        p.add_argument("--meaning")
        p.add_argument("--theory-name")
        p.add_argument("--group", choices=S.GROUPS)
        p.add_argument("--kind", choices=S.KINDS)
        p.add_argument("--key")
        p.add_argument("--chords", help='"1maj9:4 | [6 major] | 4maj7#11:4 | rest:2"')
        p.add_argument("--names", help='chord names numbered in --key: "Ebmaj9:4 | Abmaj7#11:4"')
        p.add_argument("--notes", help='one chord from exact notes: "Ab2 Eb3 G3 C4"')
        if adding:
            p.add_argument("--from-json", help="start from a card in a JSON file")
            p.add_argument("--id")
        p.add_argument("--also-in", action="append")
        p.add_argument("--notes-for", action="append", metavar='SLOT="NOTES"')
        p.add_argument("--upper-same", action="append", metavar="SLOT")
        p.add_argument("--variant", action="append", metavar='"b=label: LINE"')
        p.add_argument("--variant-key", action="append", metavar='b="b7 major"')
        p.add_argument("--bpm", type=float)
        p.add_argument("--beats-per-bar", type=int)
        p.add_argument("--bars", type=int)
        p.add_argument("--voicing", choices=S.VOICING_STYLES)
        p.add_argument("--voice-lead", action="store_true")
        p.add_argument("--groove", choices=S.GROOVES_V1)
        p.add_argument("--backing", choices=S.BACKINGS_V1)
        p.add_argument("--vel", type=int)
        p.add_argument("--arp", type=int)
        p.add_argument("--hold")
        p.add_argument("--style")
        p.add_argument("--explain")
        p.add_argument("--why")
        p.add_argument("--try", dest="try_text")
        p.add_argument("--listen-for")
        p.add_argument("--check", action="append")
        p.add_argument("--tag", action="append")
        p.add_argument("--moment", action="append", metavar="SESSION@m:ss[-m:ss][=label]")
        p.add_argument("--replay", metavar="SESSION@m:ss+SECONDS")
        p.add_argument("--related", action="append")
        p.add_argument("--by", choices=S.AUTHORS, default="claude")

    cp = sub.add_parser("card", help="jam cards: add, list, info, edit, rm, restore, trash, keep, play, show, open")
    cs = cp.add_subparsers(dest="card_verb", required=True)
    p = cs.add_parser("add", help="publish a card")
    card_fields(p, True)
    common(p, True)
    p = cs.add_parser("list", help="the cards, filtered")
    p.add_argument("--group", choices=S.GROUPS)
    p.add_argument("--kind", choices=S.KINDS)
    p.add_argument("--tag")
    p.add_argument("--by", dest="author", choices=S.AUTHORS)
    p.add_argument("--archived", action="store_true")
    common(p, True)
    p = cs.add_parser("info", help="a card resolved in a key")
    p.add_argument("card")
    p.add_argument("--key")
    p.add_argument("--variant")
    p.add_argument("--backing", choices=S.BACKINGS_V1)
    common(p, True)
    p = cs.add_parser("edit", help="change a card (a merge patch)")
    p.add_argument("card")
    card_fields(p, False)
    p.add_argument("--add-tag", action="append")
    p.add_argument("--rm-tag", action="append")
    p.add_argument("--add-moment", action="append")
    p.add_argument("--rm-moment", action="append", metavar="N")
    p.add_argument("--set", action="append", metavar="FIELD=JSON")
    for flag in ("--favorite", "--unfavorite", "--archive", "--unarchive"):
        p.add_argument(flag, action="store_true")
    p.add_argument("--if-rev", type=int)
    common(p, True)
    for name, helptext in (("rm", "move a card to the trash"), ("restore", "bring back a trashed card"),
                           ("keep", "copy a card into Kept")):
        p = cs.add_parser(name, help=helptext)
        p.add_argument("card")
        if name == "rm":
            p.add_argument("--if-rev", type=int)
        if name == "keep":
            p.add_argument("--key")
        p.add_argument("--by", choices=S.AUTHORS, default="claude")
        common(p, True)
    p = cs.add_parser("trash", help="what is in the trash")
    common(p, True)
    p = cs.add_parser("play", help="play a card or chords once (a play run)")
    p.add_argument("target", metavar="CARD|CHORDS")
    p.add_argument("--key")
    p.add_argument("--variant")
    p.add_argument("--slot", help="one chord, counted from 1")
    p.add_argument("--bpm", type=float)
    p.add_argument("--voicing", choices=S.VOICING_STYLES)
    p.add_argument("--arp", type=int)
    p.add_argument("--vel", type=int)
    p.add_argument("--now", action="store_true", help="skip waiting for Daniel's pause")
    common(p)
    p = cs.add_parser("show", help="silent ghost keys of one chord (a hover cue, not a run)")
    p.add_argument("target", metavar="CARD|CHORDS")
    p.add_argument("--key")
    p.add_argument("--variant")
    p.add_argument("--slot")
    p.add_argument("--hold", type=float, help="seconds (default 0: until cleared)")
    common(p)
    p = cs.add_parser("open", help="open the deck on a card")
    p.add_argument("card")
    p.add_argument("--by", choices=S.AUTHORS, default="claude")
    common(p)

    dp = sub.add_parser("deck", help="the deck: list, order CARD..., seed [--update]")
    dp.add_argument("action", nargs="?", choices=("order", "seed"))
    dp.add_argument("cards", nargs="*")
    dp.add_argument("--group", choices=S.GROUPS)
    dp.add_argument("--update", action="store_true")
    dp.add_argument("--moments", metavar="FILE")
    common(dp, True)

    lp = sub.add_parser("loop", help="loops: start, stop, tempo, next, set, mute, unmute")
    ls = lp.add_subparsers(dest="loop_verb", required=True)
    p = ls.add_parser("start", help="loop a card or chords with the band")
    p.add_argument("target", metavar="CARD|CHORDS")
    p.add_argument("--key")
    p.add_argument("--variant")
    p.add_argument("--bpm", type=float)
    p.add_argument("--groove", choices=S.GROOVES_V1)
    p.add_argument("--backing", choices=S.BACKINGS_V1)
    p.add_argument("--count-in", type=int, choices=(0, 1, 2))
    p.add_argument("--passes", type=int)
    p.add_argument("--humanize", type=float)
    p.add_argument("--seed", type=int)
    p.add_argument("--walk", type=int, choices=(0, 1))
    p.add_argument("--level", type=int)
    p.add_argument("--now", action="store_true")
    common(p)
    p = ls.add_parser("stop")
    p.add_argument("--now", action="store_true")
    p.add_argument("--at", choices=("bar", "pass"))
    common(p)
    p = ls.add_parser("tempo")
    p.add_argument("bpm", metavar="BPM|+N|-N")
    p.add_argument("--at", choices=("beat", "bar"))
    common(p)
    p = ls.add_parser("next")
    p.add_argument("target", nargs="?", metavar="CARD|CHORDS")
    p.add_argument("--variant")
    p.add_argument("--key")
    p.add_argument("--at", choices=("bar", "pass"))
    common(p)
    p = ls.add_parser("set")
    p.add_argument("--groove", choices=S.GROOVES_V1)
    p.add_argument("--backing", choices=S.BACKINGS_V1)
    p.add_argument("--humanize", type=float)
    p.add_argument("--walk", type=int, choices=(0, 1))
    p.add_argument("--level", type=int)
    p.add_argument("--at", choices=("bar", "pass"))
    common(p)
    for name in ("mute", "unmute"):
        common(ls.add_parser(name))

    tp = sub.add_parser("try", help="Try in time: a count-in, ghosts of each chord, a bass to keep time")
    tp.add_argument("target", metavar="CARD|CHORDS")
    tp.add_argument("--key")
    tp.add_argument("--variant")
    tp.add_argument("--bpm", type=float)
    tp.add_argument("--count-in", type=int, choices=(0, 1, 2))
    tp.add_argument("--backing", choices=S.TRY_BACKINGS)
    tp.add_argument("--passes", type=int, default=2)
    tp.add_argument("--now", action="store_true")
    common(tp)

    jp = sub.add_parser("jam", help="runs: status, runs, mark TEXT")
    js = jp.add_subparsers(dest="jam_verb", required=True)
    p = js.add_parser("status")
    p.add_argument("--runs", type=int, default=5)
    common(p, True)
    p = js.add_parser("runs")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--card")
    common(p, True)
    p = js.add_parser("mark")
    p.add_argument("text", nargs="+")
    common(p)

    tmp = sub.add_parser("template", help="keep Daniel's voicing from the practice log as a card")
    ts = tmp.add_subparsers(dest="template_verb", required=True)
    p = ts.add_parser("save-from-moment")
    p.add_argument("session", help="a session id, or latest")
    p.add_argument("at", help="m:ss into the session")
    p.add_argument("--until")
    p.add_argument("--title")
    p.add_argument("--key", default="auto")
    p.add_argument("--beats", type=float, default=4)
    p.add_argument("--id")
    p.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")
    common(p, True)
    p = ts.add_parser("save-last")
    p.add_argument("--title")
    p.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")
    common(p, True)


def run(args, out=None) -> int:
    out = out or sys.stdout
    offline = args.verb in ("card", "deck", "template") and \
        not (args.verb == "card" and args.card_verb in ("play", "show", "open"))
    client = Client(args.port, getattr(args, "jam_root", None), offline=offline)
    try:
        if args.verb == "card":
            return _cmd_card(args, client, out)
        if args.verb == "deck":
            return _cmd_deck(args, client, out)
        if args.verb == "loop":
            return _cmd_loop(args, client, out)
        if args.verb == "try":
            return _start(args, client, out, "try")
        if args.verb == "jam":
            return _cmd_jam(args, client, out)
        if args.verb == "template":
            return _cmd_template(args, client, out)
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    return BAD_INPUT


def card_path(card_id: str) -> str:
    return f"/api/piano/deck/cards/{quote(card_id)}"
