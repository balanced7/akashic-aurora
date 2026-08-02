"""
BlobStore (Slice B1) -- a content-addressed blob store for Bifrost media/large payloads.

Semantic Relationship: LargePayload stored_as Blob, referenced_by Pointer (lossless-pointer rule)

The bus stays light: a Message carries small `Part`s, and large/media content is stored here as a
content-addressed blob with only a tiny `blob:<sha>` pointer on the wire. The bytes are fetched on
demand. For local agents the filesystem IS the shared store -- both Claude and Cursor read the same
`blobs/` dir -- so no Redis round-trip for media.

Safety (design delta F2 -- the failure modes a naive media-by-reference hits):
  * **blob-before-pointer.** `put` writes to a temp file then atomically renames, and only THEN returns
    the ref -- so a pointer is never handed out before the bytes are durably readable (no race).
  * **dedup + immutability.** The id is `sha256(content)` -- identical content yields the same ref, and a
    blob never changes under a ref.
  * **dangling pointer is not fatal.** `get` of a missing/garbage ref returns None, never raises.
"""
import hashlib
import os
from pathlib import Path
from typing import Optional

def _repo_root_str() -> str:
    """AI_SETUP override, else the root DERIVED from this file (core/paths).

    Was os.getenv("AI_SETUP", <hardcoded absolute path>). The default was a
    specific machine's path, and AI_SETUP was never actually set anywhere -- so
    every call here silently used that literal and the repo only ran from one
    directory on one disk.
    """
    from core.paths import root_str
    import os as _os
    return (_os.getenv("AI_SETUP") or "").strip() or root_str()


PREFIX = "blob:"
_SHA_LEN = 24                       # 96 bits of sha256 -- ample for a single-user blob store


def _default_base() -> Path:
    return Path(_repo_root_str()) / "blobs"


class BlobStore:
    def __init__(self, base_dir: Optional[str] = None):
        self.base = Path(base_dir) if base_dir else _default_base()

    def _path(self, sha: str) -> Path:
        return self.base / sha

    @staticmethod
    def _sha_of_ref(ref: str) -> Optional[str]:
        s = str(ref or "")
        return s[len(PREFIX):] if s.startswith(PREFIX) else None

    def put(self, data) -> str:
        """Store bytes (or a str, utf-8 encoded). Returns a `blob:<sha>` ref. Idempotent (dedup),
        and the ref is returned ONLY after the bytes are durably on disk (blob-before-pointer)."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("BlobStore.put expects bytes or str")
        sha = hashlib.sha256(bytes(data)).hexdigest()[:_SHA_LEN]
        path = self._path(sha)
        if not path.exists():                          # dedup
            self.base.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(bytes(data))
            tmp.replace(path)                          # atomic -> ref valid only after a full write
        return f"{PREFIX}{sha}"

    def put_path(self, path) -> str:
        return self.put(Path(path).read_bytes())

    def get(self, ref: str) -> Optional[bytes]:
        """The bytes for a ref, or None if the ref is missing/garbage (never raises)."""
        sha = self._sha_of_ref(ref)
        if not sha:
            return None
        p = self._path(sha)
        try:
            return p.read_bytes() if p.exists() else None
        except OSError:
            return None

    def exists(self, ref: str) -> bool:
        sha = self._sha_of_ref(ref)
        return bool(sha) and self._path(sha).exists()


_INSTANCE: Optional[BlobStore] = None


def get_blob_store() -> BlobStore:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = BlobStore()
    return _INSTANCE
