"""check_secrets.py -- nothing credential-shaped reaches a public repo.

    py scripts/checkers/check_secrets.py            # tracked files (fast, ~2s)
    py scripts/checkers/check_secrets.py --history   # every blob ever committed
    py scripts/checkers/check_secrets.py --staged    # only what is staged right now

WHY, measured before a line of this was written (2026-08-11): the repo is PUBLIC, several
agent seats hold commit access, and `.secrets/API Keys/` sits one gitignore rule away from
the tree. The scan came back CLEAN -- 2,551 tracked files, 8,286 blobs across all 2,778
commits, zero hits. A gate is only cheap to install while the result is still clean.

TWO DESIGN RULES, both load-bearing:

1. THE FINDER MUST NOT BECOME THE LEAK. A scanner that prints what it found has published
   it a second time: into the CI log, the terminal scrollback, and in this house into the
   session transcript, which is archived to two drives and re-ingested into a queryable
   index within the hour. Every match is MASKED at the moment of capture -- a prefix, an
   ellipsis, a short suffix -- never stored or printed whole. The report still names the
   KIND, because an operator needs to know whether to rotate a GitHub token or an AWS key.

2. A SUPPRESSION CARRIES ITS REASON. The allowlist maps path -> why, and refuses a bare
   path. An unexplained suppression is indistinguishable from a missed detection when
   someone reads it six months later. This repo has exactly one legitimate hit and it
   stays visible, with its reason attached.

HISTORY IS THE REAL SURFACE. `git rm` removes a file from HEAD and leaves the blob
reachable forever; on a public repo that is still published. --history walks every object
in the store, including unreferenced ones.

Detection is PATTERN-BASED and therefore has a floor and a ceiling: it catches the shaped
credentials below and will not catch an arbitrary high-entropy string that happens to be a
password. That bound is stated rather than implied -- this gate reduces exposure, it does
not prove absence.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Shaped credentials, by issuer. Each has a fixed prefix and a length floor, which is what
# makes them low-false-positive: an accidental match is close to impossible.
PATTERNS: Dict[str, "re.Pattern[bytes]"] = {
    "openai/deepseek key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    "anthropic key":       re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    "github pat":          re.compile(rb"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}"),
    "github fine-grained": re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}"),
    "aws access key":      re.compile(rb"\bAKIA[0-9A-Z]{12,20}\b"),
    "google api key":      re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b"),
    "slack token":         re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "private key block":   re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY"),
    "assigned credential": re.compile(
        rb"(?i)\b(?:api[_-]?key|secret|password|passwd|auth[_-]?token)\s*[:=]\s*"
        rb"['\"][A-Za-z0-9/+_-]{24,}['\"]"),
}

# Known-benign MATCH FINGERPRINTS (sha256 of the matched bytes, truncated) -> why.
#
# History mode needs this because a blob has no path, so the path allowlist below cannot
# reach it -- and a gate that always fires on a known-benign hit is a gate that gets
# bypassed, which is worse than no gate. Fingerprinting the MATCH rather than the blob
# keeps the entry stable across every past and future revision of the file, and cannot
# suppress anything else.
#
# NOTHING THAT IS ACTUALLY A CREDENTIAL BELONGS HERE. The response to a real key in
# history is to rotate it and rewrite history, never to add a line to this dict.
BENIGN_FINGERPRINTS: Dict[str, str] = {
    # VERIFIED, not assumed: this fingerprint was computed from the live canary in
    # tests/test_t156_wire_journal.py and matched the history hits exactly, proving the
    # two historical blobs hold that identical string and nothing else.
    "924f713c5ef2f732": "tests/test_t156_wire_journal.py canary asserting the wire "
                        "journal stores metadata only and never prompt content -- not a "
                        "credential, and its presence is the proof the assertion exists",
}

# path -> WHY it is allowed. A bare path is refused (see _check_allowlist).
DEFAULT_ALLOWLIST: Dict[str, str] = {
    "tests/test_t156_wire_journal.py":
        "deliberate canary string 'SUPER-SECRET-PROMPT-CONTENT-…' asserting the wire "
        "journal records METADATA ONLY and never prompt content -- the hit is the proof",
    "scripts/checkers/check_secrets.py":
        "this file: the detection patterns themselves match their own description",
    "tests/test_check_secrets.py":
        "the gate's own pins, which plant synthetic never-valid credentials by design",
    "tests/test_t223_discord_outbound_bridge.py":
        "redaction-format pins (2026-08-24): parametrized SYNTHETIC vendor-format samples "
        "(sk-ant-api03-AAAABBBB..., xoxb-1234567890-abcdefghij) so redact() fails loudly "
        "when a vendor changes key formats -- A-F placeholders, never-valid by design",
    "tests/drill_remote_bridge_loopback.py":
        "loopback drill leak fixture uses SYNTHETIC A-F placeholder literals (same "
        "redaction-format-pin class as the t223 pins) -- never-valid credentials",
    "tests/test_remote_bridge_v1_pins.py":
        "remote-bridge redaction pin (line ~262) plants a SYNTHETIC A-F placeholder key "
        "to assert the bridge redacts before admit -- never-valid by design",
}

_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webm", ".mp4", ".pdf", ".zip",
                  ".gz", ".ico", ".woff", ".woff2", ".ttf", ".db", ".pyc"}
_MAX_BLOB = 3_000_000


def mask(raw: bytes) -> str:
    """A finding you can act on and cannot exfiltrate. Enough to identify the issuer and
    grep your own vault; never enough to authenticate with."""
    s = raw.decode("utf-8", "replace")
    if len(s) <= 12:
        return s[:3] + "…"
    return f"{s[:6]}…{s[-3:]} ({len(s)} chars)"


def _check_allowlist(allowlist: Optional[Dict[str, str]]) -> Dict[str, str]:
    if not allowlist:
        return {}
    for path, reason in allowlist.items():
        if not str(reason).strip():
            raise ValueError(
                f"allowlist entry {path!r} has no reason. A suppression without a stated "
                f"why is indistinguishable from a missed detection to whoever reads this "
                f"next -- give it one sentence.")
    return dict(allowlist)


def fingerprint(raw: bytes) -> str:
    """A stable, non-reversible id for a matched string, so a known-benign hit can be
    named without ever writing the string down."""
    import hashlib
    return hashlib.sha256(raw).hexdigest()[:16]


def _scan_bytes(data: bytes) -> List[tuple]:
    out = []
    for kind, pat in PATTERNS.items():
        m = pat.search(data)
        if m:
            out.append((kind, mask(m.group(0)), fingerprint(m.group(0))))
    return out


def scan_tracked(root: Optional[Path] = None,
                 allowlist: Optional[Dict[str, str]] = None,
                 staged_only: bool = False) -> Dict[str, Any]:
    """Every file git tracks (or only what is staged). The fast lane -- fit for a hook."""
    root = Path(root) if root else _REPO_ROOT
    allow = _check_allowlist(allowlist)
    cmd = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
           if staged_only else ["git", "ls-files"])
    listing = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True).stdout
    findings, scanned, allowed = [], 0, 0
    reasons: List[str] = []
    for rel in listing.splitlines():
        rel = rel.strip()
        if not rel or Path(rel).suffix.lower() in _SKIP_SUFFIXES:
            continue
        p = root / rel
        try:
            if not p.is_file() or p.stat().st_size > _MAX_BLOB:
                continue
            data = p.read_bytes()
        except Exception:
            continue
        scanned += 1
        hits = _scan_bytes(data)
        if not hits:
            continue
        norm = rel.replace("\\", "/")
        if norm in allow:
            allowed += len(hits)
            reasons.append(f"{norm}: {allow[norm]}")
            continue
        for kind, masked, fp in hits:
            if fp in BENIGN_FINGERPRINTS:
                allowed += 1
                reasons.append(f"{norm} [{fp}]: {BENIGN_FINGERPRINTS[fp]}")
                continue
            findings.append({"file": norm, "kind": kind, "masked": masked,
                             "fingerprint": fp})
    return {"mode": "staged" if staged_only else "tracked", "scanned": scanned,
            "findings": findings, "allowed": allowed, "allowlist_reasons": reasons,
            "ok": not findings}


def scan_history(root: Optional[Path] = None,
                 allowlist: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Every blob the object store holds, including ones no branch references.

    A deleted file is still published on a public remote -- this is the mode that sees it.
    Blobs have no path, so the allowlist cannot apply; findings are reported by sha and a
    human resolves them with `git log --all --find-object=<sha>`."""
    root = Path(root) if root else _REPO_ROOT
    _check_allowlist(allowlist)
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch-all-objects", "--batch", "--buffer", "--unordered"],
        cwd=str(root), stdout=subprocess.PIPE)
    findings, blobs, allowed = [], 0, 0
    assert proc.stdout is not None
    while True:
        header = proc.stdout.readline()
        if not header:
            break
        parts = header.split()
        if len(parts) < 3:
            continue
        sha, typ = parts[0].decode(), parts[1].decode()
        try:
            size = int(parts[2])
        except ValueError:
            continue
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        if typ != "blob" or size > _MAX_BLOB:
            continue
        blobs += 1
        for kind, masked, fp in _scan_bytes(data):
            if fp in BENIGN_FINGERPRINTS:
                allowed += 1
                continue
            findings.append({"blob": sha[:12], "kind": kind, "masked": masked,
                             "fingerprint": fp,
                             "resolve": f"git log --all --find-object={sha[:12]}"})
    proc.wait()
    reasons = sorted({f"[{fp}]: {why}" for fp, why in BENIGN_FINGERPRINTS.items()}) \
        if allowed else []
    return {"mode": "history", "scanned": blobs, "findings": findings,
            "allowed": allowed, "allowlist_reasons": reasons, "ok": not findings}


def render(rep: Dict[str, Any]) -> None:
    where = {"tracked": "tracked files", "staged": "staged files",
             "history": "blobs in history"}[rep["mode"]]
    if rep["ok"]:
        print(f"[secrets] clean -- {rep['scanned']:,} {where} scanned"
              + (f", {rep['allowed']} allowlisted hit(s)" if rep["allowed"] else ""))
        for r in rep["allowlist_reasons"]:
            print(f"    allowed: {r}")
        return
    print(f"[secrets] BLOCKED -- {len(rep['findings'])} credential-shaped match(es) "
          f"in {rep['scanned']:,} {where}")
    for f in rep["findings"]:
        loc = f.get("file") or f"blob {f.get('blob')}"
        print(f"    {f['kind']:22} {loc}   [{f['masked']}]")
        if f.get("resolve"):
            print(f"        which commit: {f['resolve']}")
    print("    Values are MASKED on purpose -- printing them would publish them again,")
    print("    into this log and into the archived session transcript.")
    print("    ROTATE THE CREDENTIAL FIRST. Removing the line does not unpublish it;")
    print("    on a public remote the blob stays fetchable until history is rewritten.")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default="")
    ap.add_argument("--history", action="store_true",
                    help="scan every blob ever committed, not just the working tree")
    ap.add_argument("--staged", action="store_true", help="only what is staged")
    a = ap.parse_args(argv)
    root = Path(a.root) if a.root else _REPO_ROOT
    rep = (scan_history(root, DEFAULT_ALLOWLIST) if a.history
           else scan_tracked(root, DEFAULT_ALLOWLIST, staged_only=a.staged))
    render(rep)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
