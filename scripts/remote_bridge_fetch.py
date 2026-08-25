"""Follow a blob ref across the bridge and write the bytes to disk.

    py scripts/remote_bridge_fetch.py blob:<sha> --out corpus.json
    py scripts/remote_bridge_fetch.py blob:<sha> --out corpus.json --peer chronos

This is the DOOR for the pointer. A peer announces `blob:<sha>` in a normal bridge message;
this is what turns that pointer back into a file. It exists because a pointer nobody can
follow is worse than a clip that admits the loss — it looks like the data is reachable.

THE REF IS THE INTEGRITY CHECK, and this refuses to write bytes that fail it. Content
addressing means a truncated, mangled or substituted body simply is not that ref any more, so
there is nothing to compare by hand and no fingerprint ceremony to forget. That property is
here specifically because two key transfers were silently corrupted in one night, and both
were caught only because a human thought to hash them.

It writes to a temp file and renames on success, so a failed or interrupted fetch never leaves
a half-file wearing the name of a whole one.
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.comm import remote_relay as RR  # noqa: E402


def fetch(ref: str, peer: str = "", timeout: int = 120):
    """Request one blob from a peer. Returns (bytes, error). NEVER RAISES."""
    url = RR.peer_url(peer)
    if not url:
        return None, (f"no route to peer {peer or '(default)'} — set peer.url in "
                      f"state/coord/remote_bridge.json")
    key = RR._outbound_key_for(peer)
    if not key:
        return None, f"no outbound key for peer {peer or '(default)'} — the bridge is unkeyed"

    payload = {"v": 1, "ref": ref, "sent_at": int(time.time())}
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    env = {"body": base64.b64encode(body).decode(), "sig": RR.sign(body, key)}
    blob_url = url.rsplit("/", 1)[0] + "/blob"
    req = urllib.request.Request(blob_url, data=json.dumps(env).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except urllib.error.HTTPError as e:
        # Their refusal is flat BY DESIGN and tells us nothing — not a bug, and not something
        # to retry blindly. The reason exists in THEIR log; ask, do not guess.
        return None, (f"peer refused ({e.code}). The refusal is deliberately uninformative — "
                      f"the reason is in THEIR listener log. Common causes, in order: they do "
                      f"not hold that ref, clock skew beyond the window, or a key mismatch.")
    except Exception as e:                                        # noqa: BLE001
        return None, f"could not reach {blob_url} ({type(e).__name__}: {e})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch a blob announced across the bridge")
    ap.add_argument("ref", help="blob:<sha> as given in the announcement")
    ap.add_argument("--out", required=True, help="where to write it")
    ap.add_argument("--peer", default="", help="which peer to ask (default: the only one)")
    a = ap.parse_args(argv)

    if not str(a.ref).startswith("blob:"):
        print(f"not a blob ref: {a.ref!r} (expected blob:<sha>)", file=sys.stderr)
        return 2

    print(f"fetching {a.ref} from {a.peer or 'the default peer'} …", flush=True)
    data, err = fetch(a.ref, a.peer)
    if data is None:
        print(f"FAILED: {err}", file=sys.stderr)
        return 1

    if not RR.blob_matches_ref(data, a.ref):
        # The whole point. Do not write it, do not report success, do not let the caller
        # decide -- bytes that are not the ref are not the file, and writing them under the
        # intended name is how a corrupted transfer becomes a mystery three days later.
        print(f"INTEGRITY FAILURE: {len(data)} bytes received, but they do not hash to "
              f"{a.ref}. NOT WRITTEN. Ask for a re-announce.", file=sys.stderr)
        return 1

    out = Path(a.out)
    tmp = out.with_suffix(out.suffix + ".part")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        tmp.replace(out)                        # rename on success: no half-file wearing a whole name
    except OSError as e:
        print(f"could not write {out}: {e}", file=sys.stderr)
        return 1

    print(f"OK  {len(data):,} bytes -> {out}")
    print(f"    verified: the bytes hash to their own ref, so this IS what was sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
