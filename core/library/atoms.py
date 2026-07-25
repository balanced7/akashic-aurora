"""The artifact-atom family (A1 core) -- atoms as truth, JSONL as the durable record.

Spec: docs/library/design/20260701_artifact-substrate-the-reconciled-design_8ea728.md sections 1-2 + docs/taxonomy-ergonomics-
reconciliation-2026-07.md section 7 (constants) + docs/library/design/20260701_super-wiki-aurora-atlas-the-reconciled-e_13c268.md
section 1 (typed edges). Ratified 2026-07-23 (Daniel G1-G6 + build license).

Shape: every artifact is an append-only, supersession-aware atom.
  - Store keys (fast current state): artifact:<id> JSON + artifact:index:* sets/zsets.
  - store/docs/<type>.jsonl (git-tracked): one JSON line per atom VERSION EVENT (mint,
    status flip). Latest line wins per id on replay; rebuild() restores the store from
    the JSONL, so the file record is the recovery truth and git is the history.
Supersession is a first-class field pair, never deletion; concurrent supersedes are
guarded by the store's CAS (update_atomic).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from core.library import taxonomy as tx

# Doc-plane types only (LIBRARY.md canon); machine/file-plane kinds (skill, pin,
# receipt, machine:*) stay files. `fossil` is a STATUS here, not a type.
DOC_TYPES: tuple[str, ...] = (
    "contract", "map", "design", "brief", "report", "chronicle", "ledger", "ruling",
)
STATUSES: tuple[str, ...] = ("current", "draft", "superseded", "fossil")

# v1.1 (atom-design reconciled, Daniel gate 2026-07-24): the FAMILY shape is versioned.
# Readers default absent -> 1 (the pre-version corpus IS v1; append-only history stays
# untouched) and refuse LOUD on newer-than-known (fail-closed -- kimi's lie-killer:
# silent format drift is the belief-vs-state disease at the schema layer).
SCHEMA_VERSION = 1
SCHEMA_KNOWN_MAX = 1

KEY_PREFIX = "artifact:"
IDX_ALL = "artifact:index:all"           # zset id -> created_ts
DEFAULT_JSONL_DIR = os.path.join("store", "docs")


class AtomError(ValueError):
    """Invalid atom input -- the door refuses loudly, never silently."""


def _slug(title: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:max_len].rstrip("-") or "untitled"


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:12]


def _idx_key(facet: str, value: str) -> str:
    return f"artifact:index:{facet}:{value}"


class AtomFamily:
    """Mint / get / supersede / find over an injected Store + JSONL dir.

    The store instance and jsonl_dir are injectable for tests and for the
    isolation flag's fixture path (T069/T070 lineage).
    """

    def __init__(self, store: Any, jsonl_dir: str = DEFAULT_JSONL_DIR, repo_root: str = "E:\\AI-Setup"):
        self.store = store
        self.jsonl_dir = jsonl_dir if os.path.isabs(jsonl_dir) else os.path.join(repo_root, jsonl_dir)

    # ---------- validation ----------

    def _validate(self, type_: str, title: str, categories: List[str],
                  citations: List[Dict[str, str]], origin: str, settled: str,
                  status: str, body_type: str = "markdown",
                  body_type_source: str = "unstated") -> List[str]:
        if type_ not in DOC_TYPES:
            raise AtomError(f"type '{type_}' not in DOC_TYPES {DOC_TYPES} -- machine/file kinds stay files")
        if not (title or "").strip():
            raise AtomError("title is required")
        if status not in STATUSES:
            raise AtomError(f"status '{status}' not in {STATUSES}")
        if origin not in tx.ORIGINS:
            raise AtomError(f"origin '{origin}' not in {tx.ORIGINS}")
        if settled not in tx.SETTLED_STATES:
            raise AtomError(f"settled '{settled}' not in {tx.SETTLED_STATES}")
        if body_type not in tx.BODY_TYPES:
            raise AtomError(f"body_type '{body_type}' not in {tx.BODY_TYPES} (T034 roster; segments-v2 lifts this enum)")
        if body_type_source not in tx.BODY_TYPE_SOURCES:
            raise AtomError(f"body_type_source '{body_type_source}' not in {tx.BODY_TYPE_SOURCES}")
        resolved: List[str] = []
        for c in categories or []:
            r = tx.resolve(c)
            if r is None:
                raise AtomError(f"category '{c}' not in the governed roster (propose-category door to grow it)")
            if r not in resolved:
                resolved.append(r)
        if len(resolved) > tx.CATEGORY_CAP_PER_ATOM:
            raise AtomError(f"max {tx.CATEGORY_CAP_PER_ATOM} categories (PRIMARY first); needing more means split the artifact")
        for c in citations or []:
            # v1.1: rel names resolve through the fold table (legacy 'cites' -> 'discusses');
            # the STORED value is always roster-true. Unknown rels refuse loud.
            r = tx.resolve_rel(c.get("rel"))
            if r is None:
                raise AtomError(f"rel '{c.get('rel')}' not in REL_ROSTER {tx.REL_ROSTER} (supersession rides its own fields)")
            c["rel"] = r
            if not c.get("target"):
                raise AtomError("citation needs a target atom id")
        return resolved

    # ---------- durable record ----------

    def _append_jsonl(self, atom: Dict[str, Any]) -> None:
        os.makedirs(self.jsonl_dir, exist_ok=True)
        path = os.path.join(self.jsonl_dir, f"{atom['header']['type']}.jsonl")
        line = json.dumps(atom, ensure_ascii=False, sort_keys=True)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")

    # ---------- index maintenance ----------

    def _index(self, atom: Dict[str, Any]) -> None:
        h = atom["header"]
        self.store.zadd(IDX_ALL, {atom["id"]: float(atom["created_ts"])})
        self.store.sadd(_idx_key("type", h["type"]), atom["id"])
        self.store.sadd(_idx_key("status", h["status"]), atom["id"])
        if h.get("arc"):
            self.store.sadd(_idx_key("arc", h["arc"]), atom["id"])
        for c in h.get("category", []):
            self.store.sadd(_idx_key("category", c), atom["id"])
        # v1.1 inverse indexes (backlinks O(corpus)->O(1)). DERIVED belief surfaces:
        # rebuild() recomputes them from citation truth, and verify_backlink_index()
        # is the A2 lie-detector row they ship with (the audit law: a cache without
        # its cross-read rots silently).
        for c in atom.get("citations_out", []):
            if c.get("target"):
                self.store.sadd(_idx_key("cited-by", c["target"]), atom["id"])
        if atom.get("supersedes"):
            self.store.sadd(_idx_key("supersedes", atom["supersedes"]), atom["id"])

    def _move_status_index(self, atom_id: str, old: str, new: str) -> None:
        self.store.srem(_idx_key("status", old), atom_id)
        self.store.sadd(_idx_key("status", new), atom_id)

    # ---------- operations ----------

    def mint(self, type_: str, title: str, body: str, *, arc: Optional[str] = None,
             seats: Optional[List[str]] = None, categories: Optional[List[str]] = None,
             citations: Optional[List[Dict[str, str]]] = None, status: str = "current",
             origin: str = "authored", speakers: Optional[List[str]] = None,
             source_thread: Optional[str] = None, settled: str = "settled",
             tenant: str = "solo", visibility: str = "fleet",
             body_type: Optional[str] = None, body_type_source: str = "unstated",
             supersedes: Optional[str] = None, date: Optional[str] = None,
             gist: Optional[str] = None, category_sources: Optional[List[str]] = None,
             now: Optional[float] = None) -> Dict[str, Any]:
        # v1.1: absent body_type auto-detects (source stamped 'auto' so a wrong stamp
        # is VISIBLE -- kimi hardening); an explicit value should arrive with source
        # 'flag'. tenant is accepted for compat but NO LONGER STORED (demoted to a
        # door-default until S-1b enforces it; visibility stays -- it is enforced).
        if body_type is None:
            body_type = tx.detect_body_type(body or "")
            if body_type_source == "unstated":
                body_type_source = "auto"
        cats = self._validate(type_, title, categories or [], citations or [], origin,
                              settled, status, body_type, body_type_source)
        # kimi (fence round 1): inference provenance is PERSISTED, not just printed --
        # the library lint reads recorded [flag|auto] sources instead of re-deriving.
        srcs = list(category_sources or [])[:len(cats)]
        srcs += ["unstated"] * (len(cats) - len(srcs))
        ts = float(now if now is not None else time.time())
        day = date or time.strftime("%Y-%m-%d", time.localtime(ts))
        slug = _slug(title)
        atom_id = f"art_{day.replace('-', '')}_{slug}_{_sha12(f'{title}|{ts}|{seats}')[:6]}"
        atom: Dict[str, Any] = {
            "id": atom_id,
            "schema_version": SCHEMA_VERSION,
            "header": {
                "status": status, "type": type_, "arc": arc, "seats": seats or [],
                "date": day, "title": title.strip(), "category": cats,
                "visibility": visibility, "body_type": body_type,
                # kimi R3: recall surfaces are capped and silent-when-empty -- a doc
                # that cannot render in one line gets dropped, so the gist is born-with.
                "gist": (gist or re.sub(r"\s+", " ", (body or "")).strip()[:140]),
            },
            "body_type_source": body_type_source,
            "body": body or "",
            "body_sha": _sha12(body or ""),
            "category_sources": srcs,
            "citations_out": citations or [],
            "supersedes": supersedes, "superseded": None,
            "origin": origin, "speakers": speakers or [],
            "captured_at": ts if origin == "conversation" else None,
            "source_thread": source_thread,
            "settled": settled,
            "version": 1, "created_ts": ts, "updated_ts": ts,
        }
        self.store.set(KEY_PREFIX + atom_id, json.dumps(atom, ensure_ascii=False, sort_keys=True))
        self._index(atom)
        self._append_jsonl(atom)
        return atom

    def get(self, atom_id: str) -> Optional[Dict[str, Any]]:
        raw = self.store.get(KEY_PREFIX + atom_id)
        if not raw:
            return None
        atom = json.loads(raw)
        # v1.1 version gate (fail-closed): absent -> 1 (the pre-version corpus IS v1);
        # newer-than-known refuses LOUD -- a wrong render that LOOKS right is worse
        # than a refusal (the migrate_schema door is the sanctioned path forward).
        v = int(atom.get("schema_version", 1))
        if v > SCHEMA_KNOWN_MAX:
            raise AtomError(f"atom {atom_id} is schema v{v}; this reader knows <= v{SCHEMA_KNOWN_MAX} "
                            f"-- upgrade the reader (or run the migrate_schema door), never guess-render")
        return atom

    def supersede(self, old_id: str, *, title: Optional[str] = None, body: str,
                  now: Optional[float] = None, **mint_kwargs: Any) -> Dict[str, Any]:
        """Mint the successor, then CAS-flip the ancestor (append-only everywhere).

        Known window (deepseek fence, round 1): the successor exists BEFORE the ancestor
        flip confirms; if the CAS exhausts retries, two atoms briefly claim current --
        exactly the duplicate-current row the audit library domain photographs, and the
        --repair pass reconciles at team scale."""
        old = self.get(old_id)
        if old is None:
            raise AtomError(f"cannot supersede unknown atom {old_id}")
        h = old["header"]
        successor = self.mint(
            mint_kwargs.pop("type_", h["type"]),
            title or h["title"],
            body,
            arc=mint_kwargs.pop("arc", h["arc"]),
            categories=mint_kwargs.pop("categories", list(h.get("category", []))),
            body_type=mint_kwargs.pop("body_type", h.get("body_type")),
            body_type_source=mint_kwargs.pop("body_type_source",
                                             old.get("body_type_source", "unstated")),
            supersedes=old_id,
            now=now,
            **mint_kwargs,
        )

        def _flip(raw: Optional[str]) -> Optional[str]:
            if raw is None:
                return None
            cur = json.loads(raw)
            cur["header"]["status"] = "superseded"
            cur["superseded"] = successor["id"]
            cur["updated_ts"] = successor["created_ts"]
            cur["version"] = int(cur.get("version", 1)) + 1
            return json.dumps(cur, ensure_ascii=False, sort_keys=True)

        flipped_raw = self.store.update_atomic(KEY_PREFIX + old_id, _flip)
        flipped = json.loads(flipped_raw) if flipped_raw else None
        if flipped:
            self._move_status_index(old_id, h["status"], "superseded")
            self._append_jsonl(flipped)
        return successor

    def find(self, *, type_: Optional[str] = None, arc: Optional[str] = None,
             category: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Index-intersection find; newest first. Facets are ANDed."""
        sets: List[set] = []
        if type_:
            sets.append(set(self.store.smembers(_idx_key("type", type_))))
        if arc:
            sets.append(set(self.store.smembers(_idx_key("arc", arc))))
        if category:
            r = tx.resolve(category)
            sets.append(set(self.store.smembers(_idx_key("category", r or category))))
        if status:
            sets.append(set(self.store.smembers(_idx_key("status", status))))
        if sets:
            ids = set.intersection(*sets) if len(sets) > 1 else sets[0]
        else:
            ids = set(self.store.zrange(IDX_ALL, 0, -1))
        atoms = [a for a in (self.get(i) for i in ids) if a]
        return sorted(atoms, key=lambda a: a["created_ts"], reverse=True)

    def backlinks(self, atom_id: str, *, lineage: bool = False) -> List[Dict[str, Any]]:
        """v1.1: O(1) read off the cited-by inverse index (was a full-corpus scan).
        lineage=True aggregates across the whole supersession chain -- the resolve-forward
        law's answer to citation decay (a successor is born with zero direct backlinks;
        the LINEAGE keeps them all). The index is DERIVED: rebuild() recomputes it and
        verify_backlink_index() photographs drift (the A2 lie-detector row)."""
        ids = self.lineage(atom_id) if lineage else [atom_id]
        out: List[Dict[str, Any]] = []
        seen: set = set()
        for aid in ids:
            for src_id in self.store.smembers(_idx_key("cited-by", aid)):
                atom = self.get(src_id)
                if atom is None:
                    continue
                for c in atom.get("citations_out", []):
                    if c.get("target") == aid:
                        key = (atom["id"], aid, c.get("rel"))
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append({"source": atom["id"], "target": aid,
                                    "rel": tx.resolve_rel(c.get("rel")) or c.get("rel"),
                                    "status": atom["header"]["status"]})
        return out

    def backlinks_scan(self, atom_id: str) -> List[Dict[str, Any]]:
        """The pre-v1.1 full scan, kept as the TRUTH SIDE of the index cross-read
        (never the serving path)."""
        out: List[Dict[str, Any]] = []
        for atom in self.find():
            for c in atom.get("citations_out", []):
                if c.get("target") == atom_id:
                    out.append({"source": atom["id"], "rel": c.get("rel"),
                                "status": atom["header"]["status"]})
        return out

    def verify_backlink_index(self) -> List[str]:
        """The lie-detector: BELIEF (cited-by sets) vs STATE (citations_out truth).
        Returns drift rows; empty = the cache tells the truth. A2's founding row."""
        truth: Dict[str, set] = {}
        for atom in self.find():
            for c in atom.get("citations_out", []):
                if c.get("target"):
                    truth.setdefault(c["target"], set()).add(atom["id"])
        rows: List[str] = []
        targets = set(truth)
        for aid in self.store.zrange(IDX_ALL, 0, -1):
            targets.add(aid)
        for t in sorted(targets):
            believed = set(self.store.smembers(_idx_key("cited-by", t)))
            actual = truth.get(t, set())
            for missing in sorted(actual - believed):
                rows.append(f"INDEX-MISSING cited-by:{t} lacks {missing}")
            for phantom in sorted(believed - actual):
                rows.append(f"INDEX-PHANTOM cited-by:{t} claims {phantom}")
        return rows

    # ---------- resolution laws (v1.1) ----------

    def lineage(self, atom_id: str) -> List[str]:
        """The full supersession chain containing atom_id, oldest-first. Bounded walk
        (a cycle -- impossible by construction, photographed by A2 if real -- stops)."""
        a = self.get(atom_id)
        if a is None:
            return [atom_id]
        back: List[str] = []
        cur, hops = a, 0
        while cur and cur.get("supersedes") and hops < 100:
            back.append(cur["supersedes"])
            cur = self.get(cur["supersedes"])
            hops += 1
        fwd: List[str] = []
        cur, hops = a, 0
        while cur and cur.get("superseded") and hops < 100:
            fwd.append(cur["superseded"])
            cur = self.get(cur["superseded"])
            hops += 1
        return list(reversed(back)) + [atom_id] + fwd

    def resolve_current(self, atom_id: str) -> Optional[Dict[str, Any]]:
        """Resolve-forward: hand back the CURRENT head of atom_id's chain (never read a
        fossil thinking it is live; the receipt stays one hop away via 'supersedes')."""
        a = self.get(atom_id)
        hops = 0
        while a and a.get("superseded") and hops < 100:
            nxt = self.get(a["superseded"])
            if nxt is None:
                break
            a = nxt
            hops += 1
        return a

    # ---------- recovery ----------

    def rebuild(self) -> int:
        """Replay store/docs/*.jsonl into the store (latest line wins per id).

        The JSONL is the durable record; this is the machine-loss recovery path
        (git clone -> rebuild -> the store is whole again).

        v1.1 schema gate (kimi's evolution-round find, 2026-07-24: rebuild breaks FIRST
        under an unshimmed v2 -- it wrote raw disk JSON into the store with no version
        check, poisoning every index before any reader's fail-closed gate could fire):
        newer-than-known atoms are PARKED loudly per line -- the v1 corpus restores in
        full, recovery never bricks on one alien line, and nothing newer-than-known is
        ever indexed. The migrate_schema door is the sanctioned path for parked lines."""
        latest: Dict[str, Dict[str, Any]] = {}
        parked: List[str] = []
        if not os.path.isdir(self.jsonl_dir):
            return 0
        for name in sorted(os.listdir(self.jsonl_dir)):
            if not name.endswith(".jsonl"):
                continue
            with open(os.path.join(self.jsonl_dir, name), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    atom = json.loads(line)
                    if int(atom.get("schema_version", 1)) > SCHEMA_KNOWN_MAX:
                        parked.append(atom.get("id", "?"))
                        continue
                    prev = latest.get(atom["id"])
                    if prev is None or atom.get("version", 1) >= prev.get("version", 1):
                        latest[atom["id"]] = atom
        for atom in latest.values():
            self.store.set(KEY_PREFIX + atom["id"], json.dumps(atom, ensure_ascii=False, sort_keys=True))
            self._index(atom)
            h = atom["header"]
            for st in STATUSES:
                if st != h["status"]:
                    self.store.srem(_idx_key("status", st), atom["id"])
        if parked:
            print(f"[rebuild] PARKED {len(parked)} newer-than-v{SCHEMA_KNOWN_MAX} atom line(s) "
                  f"(schema gate; migrate_schema is the door): " + ", ".join(sorted(set(parked))[:5]))
        return len(latest)
