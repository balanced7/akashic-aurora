"""app_package -- the rung the ladder did not have on 2026-08-24.

On that day Claude Desktop died at 12:01:59 (Electron GPU subprocess crash,
exitCode 101457950) and did not return until 14:45:52. The documented recovery --
taskkill the zombie and relaunch -- was INAPPLICABLE, because there was no zombie:
the crash left MSIX `Claude_1.28929.0.0` in status `Modified, NeedsRemediation`,
and Windows kept auto-registering the package and logging that ACL repair
SUCCEEDED while the status never cleared. Two AppsFolder activations produced no
process at all.

Daniil ran `!spawn` three times and `!revive` twice from Discord. Every lever
returned a green receipt. None of them touched the fault, because
`scripts/revive.py` began at redis: the application layer that HOSTS the conductor
seat was not in the ladder's ontology at all. Sol (codex) recovered the machine by
hand in ten minutes. This module is that recovery turned into a rung.

------------------------------------------------------------------ the design law

From the capstone of the instrument-honesty arc, [[the-stop-sign-and-the-green-light]]:

    A refusal must name a specific condition to fire -- it can only exist if somebody
    asked what would be wrong here, so it arrives carrying its own reason. A
    confirmation can be produced by absence: a decode that failed and returned empty,
    a list that ran out at its cap, a query that matched nothing.

So the load-bearing function in this file is `clear_refusals` -- the door that says
NO -- and the pass path is one line. THE SPECIFIC DEFECT THIS FORBIDS: Sol's receipt
reads "11411 blocks, zero mismatches". If the block-map read fails and returns empty,
"zero mismatches" over ZERO blocks is a pass produced by absence -- byte-for-byte the
`commits_since -> 0` defect (997f997a) that told every runner it was current for two
days because one emoji would not decode. That defect inside the lever that resurrects
the conductor is the outcome these refusals exist to prevent.

Hence: this module asserts POSITIVE counts (blocks > 0 AND blocks == the map's own
declared total), never the absence of mismatches; and missing evidence is a REFUSAL,
never a pass.

And the recovery oracle is OUTSIDE the instrument. `verify_recovered` launches the
app and confirms it stays up -- it never re-reads the status field it just wrote,
because asking the gauge how it is feeling is how the fleet certified a dead seat.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

#: The package the conductor's seat lives in. Env-overridable so a peer machine or a
#: renamed build does not need a code change.
PACKAGE_NAME = os.environ.get("AKASHIC_APP_PACKAGE", "Claude")

#: The AppxBlockMap block size. Fixed by the format, not by us.
BLOCK_SIZE = 64 * 1024

#: The ONE status this rung knows how to repair, plus the flag that rides with it.
#: A status outside this set is REFUSED BY NAME -- we do not guess that an unknown
#: bad state is the one bad state we happen to have a lever for.
HANDLED_STATUS_TOKENS = {"modified", "needsremediation"}

_PS = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]


# --------------------------------------------------------------------- the proof
@dataclass
class PayloadProof:
    """What a payload verification ACTUALLY established. Note that every field is a
    measurement, and that `declared_*` (what the block map says should exist) is kept
    separately from `files`/`blocks` (what was actually read and hashed). The gap
    between them is the whole point: a verification that covered 9000 of 11411 blocks
    found no mismatch in the 9000 and says NOTHING about the other 2411."""
    files: int
    blocks: int
    bytes: int
    mismatches: List[str] = field(default_factory=list)
    declared_files: int = 0
    declared_blocks: int = 0
    #: set when the READ ITSELF failed. Distinct from "read fine, found nothing wrong".
    error: Optional[str] = None

    @property
    def complete(self) -> bool:
        """Did the check cover everything the map declared? Positive counts only."""
        return (self.error is None
                and self.declared_blocks > 0 and self.declared_files > 0
                and self.blocks == self.declared_blocks
                and self.files == self.declared_files)


def proof_receipt(proof: PayloadProof) -> str:
    """The receipt line. Carries the numbers EVALUATED, never the bare word 'verified'
    -- a green must be traceable to a condition that was actually checked."""
    if proof.error:
        return f"UNVERIFIABLE: payload read failed ({proof.error})"
    if proof.declared_blocks <= 0 or proof.declared_files <= 0:
        return ("UNVERIFIABLE: the block map declared 0 files / 0 blocks -- an empty "
                "proof is a failed read, not an intact payload")
    verb = "verified" if proof.complete and not proof.mismatches else "INCOMPLETE"
    return (f"{verb} {proof.files}/{proof.declared_files} files, "
            f"{proof.blocks}/{proof.declared_blocks} blocks, {proof.bytes} bytes, "
            f"{len(proof.mismatches)} mismatch(es) (SHA-256)")


# ------------------------------------------------------------------- THE DOOR
def clear_refusals(pkg: Optional[Dict[str, Any]], proof: PayloadProof,
                   *, elevated: bool) -> List[str]:
    """Every reason NOT to clear `PackageStatus.Modified`, named. Empty list == may
    proceed.

    This is the door, not a check-then-proceed. The design effort lives here because
    this is the half that carries information; the caller's pass path is one `if`.
    """
    out: List[str] = []

    # -- the package itself ---------------------------------------------------
    if not pkg:
        out.append(f"no package found matching {PACKAGE_NAME!r} -- there is nothing "
                   f"to repair, and 'no mismatches over no package' is not a pass")
        return out                      # everything below would be about a ghost

    status = str(pkg.get("status") or "").strip()
    tokens = {t.strip().lower() for t in status.replace(",", " ").split() if t.strip()}
    if not tokens:
        out.append("the package status could not be read -- an unreadable status is a "
                   "refusal, not a healthy package")
    elif tokens == {"ok"}:
        out.append("package status is Ok -- healthy; this rung does not 'repair' a "
                   "working package")
    else:
        unhandled = tokens - HANDLED_STATUS_TOKENS - {"ok"}
        if unhandled:
            out.append(f"package status {status!r} contains state(s) this rung has no "
                       f"lever for: {', '.join(sorted(unhandled))} -- refusing to treat "
                       f"an unknown bad state as the one bad state we can fix")
        elif "modified" not in tokens:
            out.append(f"package status {status!r} does not include Modified -- "
                       f"nothing for ClearPackageStatus(Modified) to clear")

    # -- the authority --------------------------------------------------------
    # An unelevated ClearPackageStatus fails without raising in some shells. A silent
    # no-op that hands back a green receipt is the exact failure this arc is about.
    if not elevated:
        out.append("not elevated -- ClearPackageStatus requires administrator; "
                   "refusing rather than attempting a clear that can no-op silently "
                   "and be reported as success")

    # -- the payload ----------------------------------------------------------
    if proof.error:
        out.append(f"payload verification failed to run ({proof.error}) -- a failed "
                   f"read is not a clean payload")
    if proof.declared_blocks <= 0:
        out.append("the block map declared ZERO blocks -- empty is a failed read, not "
                   "an intact payload; 'zero mismatches' over zero blocks is a pass "
                   "produced by absence")
    if proof.declared_files <= 0:
        out.append("the block map declared ZERO files -- see above; this rung asserts "
                   "positive counts, never the absence of failures")
    if proof.declared_files > 0 and proof.files != proof.declared_files:
        out.append(f"incomplete verification: read {proof.files} file(s) against a "
                   f"declared {proof.declared_files}")
    if proof.declared_blocks > 0 and proof.blocks != proof.declared_blocks:
        out.append(f"incomplete verification: hashed {proof.blocks} block(s) against a "
                   f"declared {proof.declared_blocks} -- no mismatch in the part read "
                   f"says nothing about the part skipped")
    if proof.mismatches:
        shown = "; ".join(proof.mismatches[:3])
        more = f" (+{len(proof.mismatches) - 3} more)" if len(proof.mismatches) > 3 else ""
        out.append(f"payload MISMATCH in {len(proof.mismatches)} block(s): {shown}{more} "
                   f"-- the package is damaged; clearing the status would launch a "
                   f"corrupt app. Repair or replace it instead")

    return out


# ------------------------------------------------------------------- the probes
def _ps(script: str, timeout: int = 60) -> str:
    try:
        r = subprocess.run(_PS + [script], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout or ""
    except Exception as e:                                              # noqa: BLE001
        return f"__ERROR__{type(e).__name__}: {e}"


def is_elevated() -> bool:
    """Fails toward NOT elevated: an unreadable answer must refuse, not proceed."""
    out = _ps("$p = New-Object Security.Principal.WindowsPrincipal("
              "[Security.Principal.WindowsIdentity]::GetCurrent()); "
              "$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)",
              timeout=30).strip()
    return out.lower().startswith("true")


def query_package(name: str = PACKAGE_NAME) -> Optional[Dict[str, Any]]:
    """The installed package, or None. None means ABSENT and is treated as a refusal
    upstream -- never as 'nothing wrong'."""
    out = _ps(f"$p = Get-AppxPackage | Where-Object {{ $_.Name -like '*{name}*' }} | "
              f"Select-Object -First 1; if ($null -ne $p) {{ [pscustomobject]@{{"
              f"name=$p.Name; full_name=$p.PackageFullName; status=[string]$p.Status; "
              f"install_location=$p.InstallLocation; version=[string]$p.Version "
              f"}} | ConvertTo-Json -Compress }}", timeout=60)
    if out.startswith("__ERROR__") or not out.strip():
        return None
    try:
        rec = json.loads(out.strip())
    except ValueError:
        return None
    return rec if isinstance(rec, dict) else None


def verify_payload(install_location: str,
                   max_seconds: float = 600.0) -> PayloadProof:
    """Hash every block the AppxBlockMap declares and compare to its declared SHA-256.

    Returns a PayloadProof whose `declared_*` fields come from the map and whose
    `files`/`blocks` are what was actually read -- so an incomplete pass is VISIBLE
    rather than rounding to 'no mismatches found'.
    """
    import xml.etree.ElementTree as ET

    bm_path = os.path.join(install_location or "", "AppxBlockMap.xml")
    if not install_location or not os.path.isfile(bm_path):
        return PayloadProof(0, 0, 0, error=f"no AppxBlockMap.xml at {bm_path!r}")
    try:
        root = ET.parse(bm_path).getroot()
    except Exception as e:                                              # noqa: BLE001
        return PayloadProof(0, 0, 0, error=f"block map unparseable: {type(e).__name__}")

    ns = {"b": "http://schemas.microsoft.com/appx/2010/blockmap"}
    decl_files = root.findall("b:File", ns) or root.findall("File")
    declared_files = len(decl_files)
    declared_blocks = sum(len(f.findall("b:Block", ns) or f.findall("Block"))
                          for f in decl_files)
    if declared_files == 0 or declared_blocks == 0:
        return PayloadProof(0, 0, 0, declared_files=declared_files,
                            declared_blocks=declared_blocks,
                            error="block map declared no files/blocks")

    deadline = time.time() + max_seconds
    files = blocks = total_bytes = 0
    mismatches: List[str] = []

    for fel in decl_files:
        if time.time() > deadline:
            return PayloadProof(files, blocks, total_bytes, mismatches,
                                declared_files, declared_blocks,
                                error="verification exceeded its deadline")
        rel = (fel.get("Name") or "").replace("\\", os.sep)
        path = os.path.join(install_location, rel)
        decl_blocks = fel.findall("b:Block", ns) or fel.findall("Block")
        try:
            with open(path, "rb") as fh:
                for bel in decl_blocks:
                    chunk = fh.read(BLOCK_SIZE)
                    if not chunk:
                        mismatches.append(f"{rel}: file shorter than its block map")
                        break
                    got = base64.b64encode(hashlib.sha256(chunk).digest()).decode()
                    blocks += 1
                    total_bytes += len(chunk)
                    if got != (bel.get("Hash") or ""):
                        mismatches.append(f"{rel} block {blocks}")
        except OSError as e:
            mismatches.append(f"{rel}: unreadable ({type(e).__name__})")
            continue
        files += 1

    return PayloadProof(files, blocks, total_bytes, mismatches,
                        declared_files, declared_blocks)


# ------------------------------------------------------------------ the levers
def clear_modified_status(full_name: str) -> tuple:
    """Clear ONLY PackageStatus.Modified. No reinstall, no Reset-AppxPackage, no
    profile wipe -- Sol's repair kept every byte of state and so does this.

    Returns (ok, detail). `ok` is about the CALL; proof of recovery is a launch."""
    out = _ps(
        "$t = [Type]::GetType('Windows.Management.Deployment.PackageManager, "
        "Windows.Management.Deployment, ContentType=WindowsRuntime'); "
        "$pm = [Activator]::CreateInstance($t); "
        f"$pm.ClearPackageStatus('{full_name}', "
        "[Windows.Management.Deployment.PackageStatus]::Modified); 'CLEARED'",
        timeout=120)
    if out.startswith("__ERROR__"):
        return False, out[len("__ERROR__"):]
    return ("CLEARED" in out), out.strip()[:200]


def verify_recovered(full_name: str, *, settle_s: float = 20.0,
                     process_name: str = "claude.exe") -> tuple:
    """THE ORACLE, and it is deliberately OUTSIDE the instrument we just wrote to.

    Sol's step 6 was a real launch. If this function re-read the status field that
    `clear_modified_status` had just set, it would be asking the gauge how it is
    feeling -- which is exactly how `PROVE daemon: verified alive` certified a dead
    seat. So recovery is proven by launching the app and confirming a process is
    STILL running after it has had time to fall over.

    Returns (recovered, detail).
    """
    launched = _ps(f"Start-Process 'shell:AppsFolder\\{full_name}!Claude'; 'LAUNCHED'",
                   timeout=90)
    if launched.startswith("__ERROR__"):
        return False, f"launch call failed: {launched[len('__ERROR__'):]}"
    time.sleep(settle_s)
    alive = _ps(f"@(Get-Process -Name "
                f"'{process_name.replace('.exe', '')}' -ErrorAction SilentlyContinue)"
                f".Count", timeout=30).strip()
    try:
        n = int(alive.splitlines()[0]) if alive.splitlines() else 0
    except ValueError:
        return False, f"could not count processes after launch (got {alive!r})"
    if n <= 0:
        return False, (f"launched, but no {process_name} process survived {settle_s:.0f}s "
                       f"-- the clear did not restore a runnable app")
    return True, f"launched and {n} {process_name} process(es) still up after {settle_s:.0f}s"


# ------------------------------------------------------------- the rung's face
def observe_app(name: str = PACKAGE_NAME) -> Dict[str, Any]:
    """The revive-ladder observation for this rung. Cheap: status only, no hashing --
    the 629 MB verification is part of the HEAL, not the every-few-minutes probe."""
    pkg = query_package(name)
    if not pkg:
        return {"healthy": False, "repairable": False, "pkg": None,
                "detail": f"no {name!r} package found (not installed, or the query "
                          f"failed -- either way this rung cannot prove it healthy)"}
    status = str(pkg.get("status") or "")
    tokens = {t.strip().lower() for t in status.replace(",", " ").split() if t.strip()}
    healthy = tokens == {"ok"}
    repairable = "modified" in tokens and not (tokens - HANDLED_STATUS_TOKENS - {"ok"})
    return {"healthy": healthy, "repairable": repairable, "pkg": pkg,
            "detail": (f"{pkg.get('name')} {pkg.get('version')} status={status or '?'}"
                       + ("" if healthy else
                          " -- REPAIRABLE (verify-then-clear)" if repairable else
                          " -- unhealthy and NOT repairable by this rung"))}
