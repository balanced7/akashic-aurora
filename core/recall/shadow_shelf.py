"""Offline shadow-shelf substrate for T370 Slice 0.

This module is deliberately boring.  It owns an isolated observation register, an
independent judgment register, and a bounded deterministic reader over the two.  It
does not import or call the live recall path, a communication surface, an event log,
or a canonical-memory writer.  A later adapter may hand it terminal candidate slots;
that adapter is explicitly outside this module and outside Slice 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Callable, Iterable, Mapping, Optional


ENVELOPE_CAP = 8 * 1024
DEFAULT_WAL_PAUSE_BYTES = 100 * 1024 * 1024
DEFAULT_BACKLOG_MULTIPLIER = 2.0

_TERMINALS = {"emitted", "silent", "abstained", "error"}
_CONTRACT_NAMES: dict[str, str] = {}
_CONTRACT_IDENTITIES: dict[str, str] = {}


class ContractAliasRefused(ValueError):
    """Raised when a second name tries to alias an existing contract tuple."""


def _jsonable(value: Any) -> Any:
    """Return a stable JSON shape for contract hashes and persisted envelopes."""
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [_jsonable(item) for item in value]
        return sorted(converted, key=lambda item: _canonical_json(item))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _sha256(value: Any) -> str:
    body = _canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _now() -> tuple[str, int]:
    stamp_ns = time.time_ns()
    stamp = datetime.fromtimestamp(stamp_ns / 1_000_000_000, timezone.utc)
    return stamp.isoformat().replace("+00:00", "Z"), stamp_ns


def contract_id(
    *,
    input_kind: Any,
    outcome_schema: Any,
    comparison: Any,
    retention: Any,
    writers: Any,
    reader: Any,
    delivery: Any,
) -> str:
    """Hash the complete seven-member behavior contract tuple."""
    return _sha256(
        [
            input_kind,
            outcome_schema,
            comparison,
            retention,
            writers,
            reader,
            delivery,
        ]
    )


def register_contract(name: str, **members: Any) -> str:
    """Register one name per tuple and one tuple per name.

    Re-registering the same name with the same tuple is idempotent.  A new name for
    an existing tuple is refused because it would create a ghost category; a known
    name pointing at new semantics is a version conflict and is also refused.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("contract name must be a non-empty string")
    identity = contract_id(**members)
    old_identity = _CONTRACT_NAMES.get(name)
    if old_identity is not None:
        if old_identity != identity:
            raise ValueError(f"contract name {name!r} already points at different semantics")
        return identity
    old_name = _CONTRACT_IDENTITIES.get(identity)
    if old_name is not None and old_name != name:
        raise ContractAliasRefused(
            f"contract tuple is already registered as {old_name!r}; alias {name!r} refused"
        )
    _CONTRACT_NAMES[name] = identity
    _CONTRACT_IDENTITIES[identity] = name
    return identity


@dataclass(frozen=True)
class CategoryContract:
    """A category identity plus non-identifying read-time facets."""

    input_schema: Any
    candidate_schema: Any
    comparison: Any
    retention: Any
    writers: Any
    reader: Any
    delivery: Any
    facets: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def identity(self) -> str:
        return contract_id(
            input_kind=self.input_schema,
            outcome_schema=self.candidate_schema,
            comparison=self.comparison,
            retention=self.retention,
            writers=self.writers,
            reader=self.reader,
            delivery=self.delivery,
        )

    def with_facets(self, **facets: Any) -> "CategoryContract":
        merged = dict(self.facets)
        merged.update(facets)
        return replace(self, facets=merged)


def _terminal(slot: Mapping[str, Any]) -> str:
    value = slot.get("terminal", slot.get("outcome", "error"))
    return str(value)


def _item_identities(slot: Mapping[str, Any]) -> list[str]:
    identities = []
    for item in slot.get("items") or []:
        if isinstance(item, Mapping) and "ref" in item:
            identities.append(_canonical_json(item["ref"]))
        else:
            identities.append(_canonical_json(item))
    return sorted(set(identities))


def compare(champion: Mapping[str, Any], challenger: Mapping[str, Any]) -> str:
    """Return the exact six-state terminal comparison."""
    left = _terminal(champion)
    right = _terminal(challenger)
    if left == "error" and right == "error":
        return "unavailable"
    if "error" in (left, right):
        return "incomplete"
    if left == "abstained" and right == "abstained":
        return "unevaluated"
    if "abstained" in (left, right):
        return "abstention_delta"
    if left == "emitted" and right == "emitted":
        return "agreement" if _item_identities(champion) == _item_identities(challenger) else "disagreement"
    if left == right == "silent":
        return "agreement"
    return "disagreement"


def _normalise_slot(role: str, value: Any, version: int) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        value = {"outcome": "error", "reason": "candidate slot was not a mapping"}
    raw_size = len(_canonical_json(value).encode("utf-8"))
    if raw_size > ENVELOPE_CAP:
        terminal = "error"
        items: list[Any] = []
        reason = f"candidate output exceeded {ENVELOPE_CAP} byte cap ({raw_size} bytes)"
    else:
        terminal = _terminal(value)
        items = list(value.get("items") or [])
        reason = str(value.get("reason") or value.get("error_reason") or "")
        if terminal not in _TERMINALS:
            reason = f"invalid terminal outcome: {terminal!r}"
            terminal = "error"
            items = []
        if terminal == "error" and not reason:
            reason = "candidate reported an error without a reason"
    slot = {
        "role": role,
        "version": int(value.get("version") or version),
        "terminal": terminal,
        "outcome": terminal,
        "items": items,
        "error_reason": reason,
    }
    if reason:
        slot["reason"] = reason
    return slot


class _SQLiteRegister:
    """Small register base with loud cross-plane type metadata."""

    KIND = "register"

    def __init__(self, path: os.PathLike[str] | str):
        self.path = os.path.realpath(os.fspath(path))
        self._conn: Optional[sqlite3.Connection] = None
        self._degraded_reason = ""
        parent = os.path.dirname(self.path) or os.curdir
        if not os.path.isdir(parent):
            self._degraded_reason = f"parent directory does not exist: {parent}"
            return
        try:
            conn = sqlite3.connect(self.path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS shadow_shelf_meta "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            existing = conn.execute(
                "SELECT value FROM shadow_shelf_meta WHERE key='store_kind'"
            ).fetchone()
            if existing is not None and existing["value"] != self.KIND:
                conn.close()
                raise ValueError(
                    f"{self.path} is a {existing['value']} register, not {self.KIND}"
                )
            if existing is None:
                conn.execute(
                    "INSERT INTO shadow_shelf_meta(key, value) VALUES('store_kind', ?)",
                    (self.KIND,),
                )
            self._conn = conn
            self._create_schema()
        except ValueError:
            raise
        except (OSError, sqlite3.Error) as exc:
            self._degraded_reason = f"register unavailable: {type(exc).__name__}: {exc}"
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @property
    def available(self) -> bool:
        return self._conn is not None and not self._degraded_reason

    @property
    def reason(self) -> str:
        return self._degraded_reason

    def _require_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError(self._degraded_reason or "register is unavailable")
        return self._conn

    def _create_schema(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class ObservationStore(_SQLiteRegister):
    """Observation-only complete cohort-envelope register."""

    KIND = "observation"

    def _create_schema(self) -> None:
        conn = self._require_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS envelopes (
                cohort_id TEXT PRIMARY KEY,
                source_fingerprint TEXT NOT NULL,
                subject TEXT NOT NULL,
                purpose TEXT NOT NULL,
                category TEXT NOT NULL,
                category_contract_hash TEXT NOT NULL,
                cohort_version INTEGER NOT NULL,
                state TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                observed_ns INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS envelopes_subject_purpose
                ON envelopes(subject, purpose);
            CREATE INDEX IF NOT EXISTS envelopes_state_time
                ON envelopes(state, observed_ns DESC);
            CREATE TABLE IF NOT EXISTS manifests (
                cohort_id TEXT PRIMARY KEY,
                source_fingerprint TEXT NOT NULL,
                subject TEXT NOT NULL,
                purpose TEXT NOT NULL,
                category TEXT NOT NULL,
                category_contract_hash TEXT NOT NULL,
                state TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                reason TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                compacted_at TEXT NOT NULL,
                compacted_ns INTEGER NOT NULL,
                control_flag INTEGER NOT NULL,
                known_wrong_flag INTEGER NOT NULL,
                snapshot TEXT NOT NULL
            );
            """
        )

    def _find(self, cohort_id: str) -> Optional[dict[str, Any]]:
        if not self.available:
            return None
        row = self._require_connection().execute(
            "SELECT rowid AS sequence, payload, content_hash FROM envelopes WHERE cohort_id=?",
            (cohort_id,),
        ).fetchone()
        return self._decode_envelope(row) if row is not None else None

    @staticmethod
    def _decode_envelope(row: sqlite3.Row) -> dict[str, Any]:
        value = json.loads(row["payload"])
        value.setdefault("content_hash", row["content_hash"])
        value["_sequence"] = int(row["sequence"])
        return value

    def write_envelope(
        self,
        envelope: Mapping[str, Any],
        *,
        before_commit: Optional[Callable[[], Any]] = None,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        value = dict(_jsonable(envelope))
        cohort_id = str(value.get("cohort_id") or value.get("evaluation_id") or "").strip()
        if not cohort_id:
            raise ValueError("a complete envelope requires cohort_id")
        existing = self._find(cohort_id)
        if existing is not None:
            existing.pop("_sequence", None)
            return existing

        observed_at = str(value.get("observed_at") or "")
        if observed_at:
            observed_ns = time.time_ns()
        else:
            observed_at, observed_ns = _now()
            value["observed_at"] = observed_at
        value["cohort_id"] = cohort_id
        value.setdefault("evaluation_id", cohort_id)
        source = str(value.get("source_fingerprint") or value.get("source") or "unknown")
        subject = str(value.get("subject") or "")
        purpose = str(value.get("purpose") or value.get("purpose_id") or "")
        category = str(value.get("category") or value.get("contract_id") or "unknown")
        category_hash = str(
            value.get("category_contract_hash") or value.get("contract_id") or category
        )
        version = int(value.get("cohort_version") or value.get("version") or 1)
        state = str(value.get("state") or "unknown")
        payload = _canonical_json(value)
        content_hash = _sha256(value)

        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO envelopes(
                    cohort_id, source_fingerprint, subject, purpose, category,
                    category_contract_hash, cohort_version, state, observed_at,
                    observed_ns, content_hash, payload
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cohort_id,
                    source,
                    subject,
                    purpose,
                    category,
                    category_hash,
                    version,
                    state,
                    observed_at,
                    observed_ns,
                    content_hash,
                    payload,
                ),
            )
            if before_commit is not None:
                before_commit()
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        result = dict(value)
        result["content_hash"] = content_hash
        return result

    def list_envelopes(
        self, *, subject: Optional[str] = None, purpose: Optional[str] = None
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        clauses: list[str] = []
        values: list[Any] = []
        if subject is not None:
            clauses.append("subject=?")
            values.append(subject)
        if purpose is not None:
            clauses.append("purpose=?")
            values.append(purpose)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._require_connection().execute(
            "SELECT rowid AS sequence, payload, content_hash FROM envelopes"
            + where
            + " ORDER BY observed_ns DESC, rowid DESC",
            values,
        ).fetchall()
        return [self._decode_envelope(row) for row in rows]

    def count(self) -> int:
        if not self.available:
            return 0
        row = self._require_connection().execute("SELECT COUNT(*) AS n FROM envelopes").fetchone()
        return int(row["n"])

    def compact(self, cohort_id: str, reason: str) -> Optional[dict[str, Any]]:
        manifests = self._compact_rows([cohort_id], reason=reason)
        return manifests[0] if manifests else None

    def compact_before(self, before_hours: float, reason: str = "retention-expired") -> list[dict[str, Any]]:
        if not self.available:
            return []
        cutoff_ns = time.time_ns() - int(float(before_hours) * 3_600_000_000_000)
        rows = self._require_connection().execute(
            "SELECT cohort_id FROM envelopes WHERE observed_ns <= ? ORDER BY observed_ns",
            (cutoff_ns,),
        ).fetchall()
        return self._compact_rows([str(row["cohort_id"]) for row in rows], reason=reason)

    def _compact_rows(self, cohort_ids: Iterable[str], *, reason: str) -> list[dict[str, Any]]:
        conn = self._require_connection()
        identifiers = list(dict.fromkeys(str(value) for value in cohort_ids))
        if not identifiers:
            return []
        compacted_at, compacted_ns = _now()
        manifests: list[dict[str, Any]] = []
        try:
            conn.execute("BEGIN IMMEDIATE")
            for cohort_id in identifiers:
                row = conn.execute(
                    "SELECT * FROM envelopes WHERE cohort_id=?", (cohort_id,)
                ).fetchone()
                if row is None:
                    continue
                value = json.loads(row["payload"])
                manifest = {
                    "cohort_id": cohort_id,
                    "source_fingerprint": row["source_fingerprint"],
                    "subject": row["subject"],
                    "purpose": row["purpose"],
                    "category": row["category"],
                    "category_contract_hash": row["category_contract_hash"],
                    "state": row["state"],
                    "content_hash": row["content_hash"],
                    "reason": str(reason),
                    "observed_at": row["observed_at"],
                    "compacted_at": compacted_at,
                    "control": bool(value.get("control")),
                    "known_wrong": bool(value.get("known_wrong")),
                }
                conn.execute(
                    """
                    INSERT OR REPLACE INTO manifests(
                        cohort_id, source_fingerprint, subject, purpose, category,
                        category_contract_hash, state, content_hash, reason, observed_at,
                        compacted_at, compacted_ns, control_flag, known_wrong_flag, snapshot
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cohort_id,
                        row["source_fingerprint"],
                        row["subject"],
                        row["purpose"],
                        row["category"],
                        row["category_contract_hash"],
                        row["state"],
                        row["content_hash"],
                        str(reason),
                        row["observed_at"],
                        compacted_at,
                        compacted_ns,
                        int(bool(value.get("control"))),
                        int(bool(value.get("known_wrong"))),
                        _canonical_json(manifest),
                    ),
                )
                conn.execute("DELETE FROM envelopes WHERE cohort_id=?", (cohort_id,))
                manifests.append(manifest)
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        return manifests

    def list_manifests(
        self,
        *,
        limit: Optional[int] = None,
        subject: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        clauses: list[str] = []
        values: list[Any] = []
        if subject is not None:
            clauses.append("subject=?")
            values.append(subject)
        if purpose is not None:
            clauses.append("purpose=?")
            values.append(purpose)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = "SELECT snapshot FROM manifests" + where + " ORDER BY compacted_ns DESC"
        if limit is not None:
            sql += " LIMIT ?"
            values.append(max(0, int(limit)))
        rows = self._require_connection().execute(sql, values).fetchall()
        return [json.loads(row["snapshot"]) for row in rows]


class JudgmentStore(_SQLiteRegister):
    """Append-only retrospective preference and seen-receipt register."""

    KIND = "judgment"

    def _create_schema(self) -> None:
        conn = self._require_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS judgments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cohort_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                candidate_version INTEGER NOT NULL,
                principal TEXT NOT NULL,
                pref TEXT NOT NULL CHECK(pref IN ('KEEP', 'DROP')),
                created_at TEXT NOT NULL,
                snapshot TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS judgments_cohort ON judgments(cohort_id);
            CREATE TABLE IF NOT EXISTS peek_receipts (
                cohort_id TEXT NOT NULL,
                principal TEXT NOT NULL,
                peeked_at TEXT NOT NULL,
                PRIMARY KEY(cohort_id, principal)
            );
            """
        )

    def append(
        self,
        *,
        cohort_id: str,
        candidate_id: str,
        candidate_version: int,
        principal: str,
        pref: str,
    ) -> dict[str, Any]:
        conn = self._require_connection()
        if isinstance(candidate_version, bool) or not isinstance(candidate_version, int):
            raise TypeError("candidate_version must be a positive integer")
        if candidate_version <= 0:
            raise ValueError("candidate_version must be a positive integer")
        if pref not in ("KEEP", "DROP"):
            raise ValueError("judgment pref must be KEEP or DROP")
        if not str(cohort_id).strip() or not str(candidate_id).strip() or not str(principal).strip():
            raise ValueError("cohort_id, candidate_id, and principal are required")
        created_at, _ = _now()
        value = {
            "cohort_id": str(cohort_id),
            "candidate_id": str(candidate_id),
            "candidate_version": candidate_version,
            "principal": str(principal),
            "pref": pref,
            "created_at": created_at,
        }
        conn.execute(
            """
            INSERT INTO judgments(
                cohort_id, candidate_id, candidate_version, principal, pref,
                created_at, snapshot
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                value["cohort_id"],
                value["candidate_id"],
                value["candidate_version"],
                value["principal"],
                value["pref"],
                value["created_at"],
                _canonical_json(value),
            ),
        )
        return value

    def list(self) -> list[dict[str, Any]]:
        if not self.available:
            return []
        rows = self._require_connection().execute(
            "SELECT snapshot FROM judgments ORDER BY id"
        ).fetchall()
        return [json.loads(row["snapshot"]) for row in rows]

    def _mark_seen(self, cohort_id: str, principal: str) -> None:
        conn = self._require_connection()
        peeked_at, _ = _now()
        conn.execute(
            """
            INSERT INTO peek_receipts(cohort_id, principal, peeked_at)
            VALUES(?, ?, ?)
            ON CONFLICT(cohort_id, principal) DO UPDATE SET peeked_at=excluded.peeked_at
            """,
            (str(cohort_id), str(principal), peeked_at),
        )

    def _was_seen(self, cohort_id: str) -> bool:
        if not self.available:
            return False
        row = self._require_connection().execute(
            "SELECT 1 FROM peek_receipts WHERE cohort_id=? LIMIT 1", (str(cohort_id),)
        ).fetchone()
        return row is not None


def open_observation(path: os.PathLike[str] | str) -> ObservationStore:
    return ObservationStore(path)


def open_judgment(path: os.PathLike[str] | str) -> JudgmentStore:
    return JudgmentStore(path)


def _functional_envelope(
    *,
    source_fingerprint: str,
    subject: str,
    purpose_id: str,
    contract: str,
    cohort_version: int,
    watcher_incarnation: str,
    decisions: Mapping[str, Any],
) -> dict[str, Any]:
    evaluation_id = _sha256(
        {
            "source_fingerprint": source_fingerprint,
            "subject": subject,
            "purpose_id": purpose_id,
            "contract_id": contract,
            "cohort_version": cohort_version,
        }
    )
    champion = _normalise_slot("champion", decisions.get("champion"), cohort_version)
    challenger = _normalise_slot("challenger", decisions.get("challenger"), cohort_version)
    state = compare(champion, challenger)
    observed_at, _ = _now()
    return {
        "evaluation_id": evaluation_id,
        "cohort_id": evaluation_id,
        "source_fingerprint": str(source_fingerprint),
        "source": str(source_fingerprint),
        "subject": str(subject),
        "purpose_id": str(purpose_id),
        "purpose": str(purpose_id),
        "contract_id": str(contract),
        "category": str(contract),
        "category_contract_hash": str(contract),
        "cohort_version": int(cohort_version),
        "version": int(cohort_version),
        "watcher_incarnation": str(watcher_incarnation),
        "observed_at": observed_at,
        "decisions": {"champion": champion, "challenger": challenger},
        "champion": champion,
        "challenger": challenger,
        "state": state,
    }


def record_envelope(
    store: ObservationStore,
    *,
    source_fingerprint: str,
    subject: str,
    purpose_id: str,
    contract_id: str,
    cohort_version: int,
    watcher_incarnation: str,
    decisions: Mapping[str, Any],
    before_commit: Optional[Callable[[], Any]] = None,
) -> dict[str, Any]:
    value = _functional_envelope(
        source_fingerprint=source_fingerprint,
        subject=subject,
        purpose_id=purpose_id,
        contract=contract_id,
        cohort_version=cohort_version,
        watcher_incarnation=watcher_incarnation,
        decisions=decisions,
    )
    existing = store._find(value["cohort_id"])
    if existing is not None:
        existing.pop("_sequence", None)
        return existing
    return store.write_envelope(value, before_commit=before_commit)


def count_envelopes(store: ObservationStore) -> int:
    return store.count()


def list_envelopes(store: ObservationStore) -> list[dict[str, Any]]:
    rows = store.list_envelopes()
    for row in rows:
        row.pop("_sequence", None)
    return rows


def compact(store: ObservationStore, *, before_hours: float) -> dict[str, Any]:
    manifests = store.compact_before(before_hours)
    return {"removed": len(manifests), "reason": "retention-expired", "manifests": manifests}


def read_manifest(store: ObservationStore) -> list[dict[str, Any]]:
    return store.list_manifests()


def append_judgment(
    store: JudgmentStore,
    *,
    target_evaluation: str,
    candidate_id: str,
    candidate_version: int,
    verdict: str,
    principal: str,
) -> dict[str, Any]:
    return store.append(
        cohort_id=target_evaluation,
        candidate_id=candidate_id,
        candidate_version=candidate_version,
        principal=principal,
        pref=verdict,
    )


def list_judgments(store: JudgmentStore) -> list[dict[str, Any]]:
    return store.list()


def resource_report(path: os.PathLike[str] | str) -> dict[str, Any]:
    """Measure the isolated register without fabricating healthy zeroes for absence."""
    resolved = os.path.realpath(os.fspath(path))
    empty = {
        "rows": None,
        "bytes_per_envelope": None,
        "db_bytes": None,
        "wal_bytes": None,
        "backlog": None,
    }
    if not os.path.isfile(resolved):
        return {
            "status": "unavailable",
            **empty,
            "reason": "observation register does not exist",
            "unavailable_reasons": {"db": "path_missing"},
        }
    try:
        db_bytes = os.path.getsize(resolved)
        wal_path = resolved + "-wal"
        wal_bytes = os.path.getsize(wal_path) if os.path.isfile(wal_path) else 0
        conn = sqlite3.connect(resolved)
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='envelopes'"
            ).fetchone()
            rows = int(conn.execute("SELECT COUNT(*) FROM envelopes").fetchone()[0]) if table else 0
        finally:
            conn.close()
        return {
            "status": "ok",
            "rows": rows,
            "bytes_per_envelope": (db_bytes + wal_bytes) / rows if rows else 0.0,
            "db_bytes": db_bytes,
            "wal_bytes": wal_bytes,
            "backlog": 0,
            "unavailable_reasons": {},
        }
    except (OSError, sqlite3.Error) as exc:
        return {
            "status": "unavailable",
            **empty,
            "reason": f"resource measurement failed: {type(exc).__name__}: {exc}",
            "unavailable_reasons": {"db": "measurement_failed"},
        }


def should_pause(
    *,
    wal_bytes: int,
    backlog_ratio: float,
    wal_pause_bytes: int = DEFAULT_WAL_PAUSE_BYTES,
    backlog_multiplier: float = DEFAULT_BACKLOG_MULTIPLIER,
) -> bool:
    return int(wal_bytes) > int(wal_pause_bytes) or float(backlog_ratio) > float(backlog_multiplier)


def _blank_counters() -> dict[str, Any]:
    return {
        "processing": {"persisted": 0, "eligible": 0},
        "comparison": {
            "agreement": 0,
            "disagreement": 0,
            "abstention_delta": 0,
            "incomplete": 0,
            "unevaluated": 0,
            "unavailable": 0,
            "cohorts": 0,
        },
        "judgment": {
            "judged": 0,
            "candidate_slots": 0,
            "keep": 0,
            "drop": 0,
            "coverage": {"numerator": 0, "denominator": 0},
        },
    }


_STATE_PRIORITY = {
    "disagreement": 0,
    "abstention_delta": 1,
    "incomplete": 2,
    "unevaluated": 3,
    "unavailable": 3,
    "agreement": 4,
}


class ShadowShelfReader:
    """Bounded, no-model read model over observation plus optional judgment."""

    def __init__(
        self,
        observation_store: ObservationStore,
        judgment_store: Optional[JudgmentStore],
    ) -> None:
        self.observation_store = observation_store
        self.judgment_store = judgment_store
        self._head_resolver: Optional[Callable[[str], Any]] = None

    def set_contract_head_resolver(self, resolver: Callable[[str], Any]) -> None:
        self._head_resolver = resolver

    def health(self) -> dict[str, Any]:
        report = resource_report(self.observation_store.path)
        return {
            "state": report["status"],
            "rows": report["rows"],
            "bytes_per_envelope": report["bytes_per_envelope"],
            "db_bytes": report["db_bytes"],
            "wal_bytes": report["wal_bytes"],
            "backlog": report["backlog"],
            "reasons": report.get("unavailable_reasons", {}),
        }

    def _counters(self, envelopes: list[dict[str, Any]]) -> dict[str, Any]:
        counters = _blank_counters()
        total = len(envelopes)
        counters["processing"].update(persisted=total, eligible=total)
        counters["comparison"]["cohorts"] = total
        for envelope in envelopes:
            state = str(envelope.get("state") or "")
            if state in counters["comparison"]:
                counters["comparison"][state] += 1

        candidate_slots = 0
        cohort_ids = set()
        for envelope in envelopes:
            cohort_ids.add(str(envelope.get("cohort_id")))
            if "champion" in envelope and "challenger" in envelope:
                candidate_slots += 2
            elif isinstance(envelope.get("decisions"), Mapping):
                candidate_slots += len(envelope["decisions"])
        judgments = []
        if self.judgment_store is not None and self.judgment_store.available:
            judgments = [
                value
                for value in self.judgment_store.list()
                if str(value.get("cohort_id")) in cohort_ids
            ]
        keep = sum(1 for value in judgments if value.get("pref") == "KEEP")
        drop = sum(1 for value in judgments if value.get("pref") == "DROP")
        counters["judgment"].update(
            judged=len(judgments),
            candidate_slots=candidate_slots,
            keep=keep,
            drop=drop,
            coverage={"numerator": len(judgments), "denominator": candidate_slots},
        )
        return counters

    def peek(
        self,
        *,
        subject: str,
        purpose: str,
        limit: int,
        include_stale: bool = False,
    ) -> dict[str, Any]:
        health = self.health()
        if not self.observation_store.available:
            return {
                "status": "unavailable",
                "reasons": [self.observation_store.reason or "observation register unavailable"],
                "rows": [],
                "controls": [],
                "counters": _blank_counters(),
                "health": health,
            }

        reasons: list[str] = []
        status = "ok"
        if self.judgment_store is None or not self.judgment_store.available:
            status = "partial"
            reasons.append(
                "judgment register unavailable"
                if self.judgment_store is None
                else self.judgment_store.reason or "judgment register unavailable"
            )

        envelopes = self.observation_store.list_envelopes(subject=subject, purpose=purpose)
        rows: list[dict[str, Any]] = []
        for envelope in envelopes:
            row = dict(envelope)
            sequence = int(row.pop("_sequence", 0))
            cohort_id = str(row.get("cohort_id") or "")
            row["peek_state"] = (
                "fresh"
                if self.judgment_store is not None
                and self.judgment_store.available
                and self.judgment_store._was_seen(cohort_id)
                else "unpeeked"
            )
            row["_sequence"] = sequence
            if self._head_resolver is not None:
                try:
                    row["contract_head"] = self._head_resolver(cohort_id)
                except Exception as exc:
                    status = "unknown"
                    reasons.append(
                        f"contract head unresolved for {cohort_id}: {type(exc).__name__}: {exc}"
                    )
            rows.append(row)

        rows.sort(
            key=lambda row: (
                _STATE_PRIORITY.get(str(row.get("state")), 3),
                -int(row.get("_sequence", 0)),
            )
        )
        if include_stale:
            for manifest in self.observation_store.list_manifests(
                subject=subject, purpose=purpose
            ):
                stale = dict(manifest)
                stale["peek_state"] = "stale"
                stale["_sequence"] = -1
                rows.append(stale)
        bound = max(0, int(limit))
        rows = rows[:bound]
        for row in rows:
            row.pop("_sequence", None)
        controls = [
            row for row in rows if row.get("control") is True and row.get("known_wrong") is True
        ]
        return {
            "status": status,
            "reasons": reasons,
            "rows": rows,
            "controls": controls,
            "counters": self._counters(envelopes),
            "health": health,
        }

    def mark_peeked(self, *, cohort_id: str, principal: str) -> None:
        if self.judgment_store is None or not self.judgment_store.available:
            raise RuntimeError("judgment register unavailable; cannot persist peek receipt")
        self.judgment_store._mark_seen(cohort_id, principal)

    def control_sample(self, *, limit: int) -> list[dict[str, Any]]:
        rows = self.observation_store.list_envelopes()
        selected = [
            value
            for value in rows
            if value.get("control") is True and value.get("known_wrong") is True
        ]
        selected.sort(key=lambda value: -int(value.get("_sequence", 0)))
        result = selected[: max(0, int(limit))]
        for value in result:
            value.pop("_sequence", None)
        return result

    def manifests(self, *, limit: int) -> list[dict[str, Any]]:
        return self.observation_store.list_manifests(limit=max(0, int(limit)))


def replay_fixture(root: os.PathLike[str] | str, **_: Any) -> dict[str, Any]:
    """Replay two deterministic terminal cohorts into isolated registers.

    The champion and challenger here are fixtures, not calls to the production ranker.
    The return value says so explicitly to prevent the recording from acquiring false
    detector authority merely because it shares a category name.
    """
    directory = os.path.realpath(os.fspath(root))
    os.makedirs(directory, exist_ok=True)
    observation = ObservationStore(os.path.join(directory, "shadow-observation.sqlite"))
    judgment = JudgmentStore(os.path.join(directory, "shadow-judgment.sqlite"))
    fixtures = [
        {
            "source_fingerprint": "fixture:agreement:1",
            "subject": "fixture-seat",
            "purpose_id": "recall-at-action",
            "contract_id": "recall.at_action.rank.v1",
            "cohort_version": 1,
            "watcher_incarnation": "offline-fixture",
            "decisions": {
                "champion": {"outcome": "emitted", "items": [{"ref": "fixture:A"}]},
                "challenger": {"outcome": "emitted", "items": [{"ref": "fixture:A"}]},
            },
        },
        {
            "source_fingerprint": "fixture:disagreement:1",
            "subject": "fixture-seat",
            "purpose_id": "recall-at-action",
            "contract_id": "recall.at_action.rank.v1",
            "cohort_version": 1,
            "watcher_incarnation": "offline-fixture",
            "decisions": {
                "champion": {"outcome": "emitted", "items": [{"ref": "fixture:B"}]},
                "challenger": {"outcome": "silent", "items": []},
            },
        },
    ]
    rows = [record_envelope(observation, **fixture) for fixture in fixtures]
    reader = ShadowShelfReader(observation, judgment)
    peek = reader.peek(subject="fixture-seat", purpose="recall-at-action", limit=10)
    result = {
        "authority": "offline-fixture-recording",
        "detector_exercised": False,
        "contract": "recall.at_action.rank.v1",
        "persisted": len(rows),
        "states": [row["state"] for row in rows],
        "peek": peek,
        "health": reader.health(),
    }
    observation.close()
    judgment.close()
    return result


__all__ = [
    "CategoryContract",
    "ContractAliasRefused",
    "DEFAULT_BACKLOG_MULTIPLIER",
    "DEFAULT_WAL_PAUSE_BYTES",
    "ENVELOPE_CAP",
    "JudgmentStore",
    "ObservationStore",
    "ShadowShelfReader",
    "append_judgment",
    "compact",
    "compare",
    "contract_id",
    "count_envelopes",
    "list_envelopes",
    "list_judgments",
    "open_judgment",
    "open_observation",
    "read_manifest",
    "record_envelope",
    "register_contract",
    "replay_fixture",
    "resource_report",
    "should_pause",
]
