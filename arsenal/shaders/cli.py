"""py -m arsenal shader <verb> -- the shader school's door. Every verb prints a short human answer, or JSON with --json.

    ingest <bundle.json>         save a browser harvest bundle into the private corpus
    list [--set S] [--limit N]   the corpus, optionally one named set (loved, love_top) in its own order
    show <id|name>               one shader's facts: author, licence, passes, inputs, sets
    missing                      ids a set names but the corpus lacks, and media the shaders sample but we lack
    harvest-js                   print the path of the browser helper to inject into a shadertoy.com tab

Further verbs register themselves in VERBS as their modules land (dissect, census, render, check, lab...).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Dict, List

from . import corpus as C

HERE = Path(__file__).resolve().parent


def _print(obj, as_json: bool, human: Callable[[object], str]) -> None:
    text = json.dumps(obj, indent=1, ensure_ascii=False) if as_json else human(obj)
    stream = getattr(sys.stdout, "buffer", None)
    if stream is not None:  # shader names carry any script; write UTF-8 even when stdout is a cp1252 pipe
        sys.stdout.flush()
        stream.write((text + "\n").encode("utf-8"))
        stream.flush()
    else:
        print(text)


def read_clipboard_text() -> str:
    """The Windows clipboard as text (CF_UNICODETEXT), through the Win32 API so no console code page can mangle it.

    WHY A CLIPBOARD DOOR. Brave asks where to save every download, and a second download from one page waits on a
    permission prompt, so a harvest that runs while Daniel sleeps cannot leave the browser as a file. A real Ctrl+C
    on a selected textarea (harvest.js stage(), then the browser tool's key press) can, and this reads it back."""
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.WinDLL("user32"), ctypes.WinDLL("kernel32")
    user32.GetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    CF_UNICODETEXT = 13
    if not user32.OpenClipboard(None):
        raise OSError("could not open the clipboard")
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        p = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p)
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def cmd_ingest(ns) -> int:
    if ns.clipboard:
        text = read_clipboard_text()
        if C.HARVEST_API not in text[:200]:
            print(f"the clipboard does not hold a harvest bundle (starts {text[:60]!r})", file=sys.stderr)
            return 2
        stage = C.CORPUS / "harvests" / "_clipboard.json"
        stage.parent.mkdir(parents=True, exist_ok=True)
        stage.write_text(text, encoding="utf-8")
        ns.bundle = str(stage)
    if not ns.bundle:
        print("give a bundle path, or --clipboard", file=sys.stderr)
        return 2
    report = C.ingest_bundle(Path(ns.bundle))
    _print(report, ns.json, lambda r: (
        f"ingested {r['shaders_written']} shaders into {r['corpus']}\n"
        f"  new set members: {r['sets_new']}  media written: {r['media_written']}\n"
        f"  bundle kept as harvests/{r['sha256'][:16]}....json"))
    return 0


def _row(meta: dict) -> str:
    lic = meta["license"]["license"]
    passes = "+".join(p["type"][0].upper() if p["type"] != "common" else "c" for p in meta["passes"])
    return f"{meta['id']}  {meta['name'][:34]:<34} {meta['author'][:14]:<14} {passes:<8} {lic}"


def cmd_list(ns) -> int:
    sets = C.load_sets()
    ids = sets.get(ns.set, []) if ns.set else C.all_ids()
    rows = []
    for sid in ids[: ns.limit or None]:
        try:
            rows.append(C.load_meta(sid))
        except FileNotFoundError:
            rows.append({"id": sid, "missing": True})
    def human(rs):
        out = [f"{len(rs)} shaders" + (f" in set {ns.set!r}" if ns.set else "") + "   (passes: I image, B buffer, c common, S sound, C cube)"]
        out += [(f"{r['id']}  (not saved yet)" if r.get("missing") else _row(r)) for r in rs]
        return "\n".join(out)
    _print(rows if ns.json else rows, ns.json, human)
    return 0


def cmd_show(ns) -> int:
    hits = C.resolve(ns.query)
    if not hits:
        print(f"no shader matches {ns.query!r}; try: py -m arsenal shader list", file=sys.stderr)
        return 2
    sets = C.load_sets()
    metas = []
    for sid in hits[:10]:
        m = C.load_meta(sid)
        m["sets"] = {k: v.index(sid) + 1 for k, v in sets.items() if not k.startswith("_") and sid in v}
        m["dir"] = str(C.CORPUS / "shaders" / sid)
        metas.append(m)
    def human(ms):
        out = []
        for m in ms:
            out.append(f"{m['name']} by {m['author']}  ({m['id']}, {m['url']})")
            out.append(f"  licence: {m['license']['license']}" + (f"  \"{m['license']['line']}\"" if m['license']['line'] else ""))
            out.append(f"  likes {m['likes']}  views {m['views']}  sets {m['sets']}  tags {', '.join(m['tags'][:8])}")
            for p in m["passes"]:
                ins = ", ".join(f"ch{i['channel']}={i['type']}" + (f":{Path(i['src']).name[:12]}" if i['src'] else "")
                                for i in p["inputs"])
                out.append(f"  - {p['name']:<9} {p['type']:<8} {p['lines']:>4} lines  {p['file']:<14} {ins}")
            out.append(f"  files: {m['dir']}")
        return "\n".join(out)
    _print(metas, ns.json, human)
    return 0


def cmd_missing(ns) -> int:
    res = {"ids": C.missing_ids(), "media": C.missing_media()}
    _print(res, ns.json, lambda r: (
        "ids named by a set but not saved: " + json.dumps(r["ids"]) + "\n"
        f"media sampled but not saved ({len(r['media'])}):\n  " + "\n  ".join(r["media"])))
    return 0


MEDIA_BUNDLE = "shadertoy-media.json"


def media_snippet(paths: List[str], bundle_name: str = MEDIA_BUNDLE) -> str:
    """A console snippet for a signed-in shadertoy.com tab: the harvest helper, then one paced run that fetches every
    path and saves ONE bundle file (Brave asks where to save; that click is the only human step). The paths are
    shadertoy's own content-hash names, so the snippet carries nothing private."""
    helper = (HERE / "harvest.js").read_text(encoding="utf-8")
    return (helper.rstrip() + "\n" +
            f"__st.run('media', async () => {{ const m = await __st.media({json.dumps(paths)}); "
            f"__st.download({json.dumps(bundle_name)}, {{ media: m }}); return Object.keys(m).length; }});\n")


def cmd_harvest_js(ns) -> int:
    if not ns.media:
        print(HERE / "harvest.js")
        return 0
    paths = C.media_to_fetch()
    if not paths:
        print("the corpus already holds every medium its shaders sample", file=sys.stderr)
        return 0
    if ns.json:
        _print({"paths": paths, "snippet": media_snippet(paths)}, True, str)
        return 0
    print(f"// {len(paths)} media to fetch. Paste into the DevTools console of a signed-in shadertoy.com tab (type"
          f" 'allow pasting' first if Brave asks), save the file it offers, then:\n"
          f"//   py -m arsenal shader ingest <the saved {MEDIA_BUNDLE}>")
    print(media_snippet(paths))
    return 0


VERBS: Dict[str, Callable] = {}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="py -m arsenal shader", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    p = sub.add_parser("ingest", help="save a browser harvest bundle into the private corpus")
    p.add_argument("bundle", nargs="?")
    p.add_argument("--clipboard", action="store_true", help="read the bundle from the clipboard (harvest.js stage())")
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("list", help="list the corpus, or one named set in order")
    p.add_argument("--set")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="one shader's facts")
    p.add_argument("query")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("missing", help="ids and media the corpus still lacks")
    p.set_defaults(fn=cmd_missing)
    p = sub.add_parser("harvest-js", help="path of the browser harvest helper, or (--media) a ready-to-paste snippet "
                                          "that fetches every texture the corpus still lacks into one bundle file")
    p.add_argument("--media", action="store_true")
    p.set_defaults(fn=cmd_harvest_js)
    for name, register in VERBS.items():
        register(sub)
    for action in sub.choices.values():
        action.add_argument("--json", action="store_true", help="machine-readable output")
    return ap


def _load_extensions() -> None:
    """Modules that add verbs call cli.VERBS[name] = register(sub). Missing modules are simply absent verbs."""
    import importlib
    for mod in ("modules", "dissect", "census", "render", "lab", "school", "licence_line", "atlas", "shelf", "cards",
                "explain"):
        try:
            importlib.import_module(f"arsenal.shaders.{mod}")
        except ModuleNotFoundError as exc:
            if exc.name != f"arsenal.shaders.{mod}":
                raise


def main(argv: List[str] = None) -> int:
    _load_extensions()
    ns = build_parser().parse_args(argv)
    return ns.fn(ns) or 0


if __name__ == "__main__":
    sys.exit(main())
