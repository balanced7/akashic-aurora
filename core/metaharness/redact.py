"""Redaction for anything the meta-harness keeps: archived transcripts, scenario prompts, fixtures.

Two halves, kept together on purpose. `redact` rewrites credential-shaped text VISIBLY
(`[REDACTED-...]`, never a silent deletion). `find_secrets` is the CHECK that runs after every
archive write: it uses a stricter, wider pattern set than the rewrite, so a shape the rewrite
missed fails the write instead of landing on disk. A redactor that is never checked is how a
key ends up in a corpus that is then shared with a proposer model.
"""

from __future__ import annotations

import re

_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
        "[REDACTED-PRIVATE-KEY]",
    ),
    (re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_\-]{6,}[A-Za-z0-9]"), "[REDACTED-KEY]"),
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"), "[REDACTED-KEY]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "[REDACTED-KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,20}\b"), "[REDACTED-KEY]"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}"), "[REDACTED-KEY]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}"), "[REDACTED-KEY]"),
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._\-]{16,}"), r"\1[REDACTED]"),
    (
        re.compile(
            r"(?i)((?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd)[\"']?\s*[=:]\s*[\"']?)([^\s\"',}]{6,})"
        ),
        r"\1[REDACTED]",
    ),
    (re.compile(r"(https://discord(?:app)?\.com/api/webhooks/\d+/)(\S+)"), r"\1[REDACTED]"),
)

#: The check: deliberately broader than the rewrite. A hit here after redaction is a bug.
_CHECKS: dict[str, re.Pattern[str]] = {
    "provider key": re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}"),
    "github token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}"),
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google api key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY"),
}


def redact(text: str) -> str:
    out = str(text or "")
    for pat, repl in _REWRITES:
        out = pat.sub(repl, out)
    return out


def find_secrets(text: str) -> list[str]:
    """Names of the secret shapes still present (empty means clean). Never returns the match."""
    return [name for name, pat in _CHECKS.items() if pat.search(text or "")]
