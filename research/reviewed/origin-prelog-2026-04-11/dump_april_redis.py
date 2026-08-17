"""Dump the restored April-2026 Redis to a verbatim text artifact.

READ-ONLY against a THROWAWAY restore of a COPY of the original volume. The source volume
(redis_redis-master-data) is never touched -- the dump.rdb was copied out first and this reads
the copy. Provenance chain: volume -> copy -> restore -> this dump.
"""
import subprocess, json, sys

C = "origin-redis"


def cli(*args):
    out = subprocess.run(["docker", "exec", C, "redis-cli", *args],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return out.stdout.rstrip("\n")


keys = [k for k in cli("--scan").splitlines() if k.strip()]
keys.sort()
print(f"keys: {len(keys)}", file=sys.stderr)

lines = ["# The April 2026 Redis, recovered verbatim",
         "#",
         "# Source: docker volume redis_redis-master-data -> dump.rdb (98,574 bytes, last",
         "#   written 2026-04-30 23:38; sibling appendonlydir.bak dated 2026-04-15 05:28).",
         "# Method: dump.rdb COPIED to a scratch volume, restored into a throwaway redis:8",
         "#   container, read read-only. The original volume was never mounted writable.",
         "# Note: redis:7 REFUSED this file ('Can't handle RDB format version 13') -- the",
         "#   archive was written by a newer Redis than the house default. Not corruption.",
         f"# Keys: {len(keys)}",
         ""]

for k in keys:
    t = cli("TYPE", k)
    lines.append(f"\n{'='*78}\n## {k}   [{t}]\n{'='*78}")
    if t == "string":
        v = cli("GET", k)
        try:
            v = json.dumps(json.loads(v), indent=1, ensure_ascii=False)
        except Exception:
            pass
        lines.append(v)
    elif t == "list":
        n = cli("LLEN", k)
        lines.append(f"({n} item(s))")
        for i, item in enumerate(cli("LRANGE", k, "0", "40").splitlines()):
            try:
                item = json.dumps(json.loads(item), indent=1, ensure_ascii=False)
            except Exception:
                pass
            lines.append(f"--- [{i}] ---\n{item}")
    elif t == "hash":
        lines.append(cli("HGETALL", k))
    elif t == "set":
        lines.append(cli("SMEMBERS", k))
    elif t == "zset":
        lines.append(cli("ZRANGE", k, "0", "40", "WITHSCORES"))
    else:
        lines.append(f"(unhandled type {t})")

out = "\n".join(lines)
p = r"C:\Users\L5\AppData\Local\Temp\claude\E--\18762fcf-658e-4576-8558-6008ca0fbf55\scratchpad\archive\april-redis-recovered.md"
open(p, "w", encoding="utf-8").write(out)
print(f"chars: {len(out):,}", file=sys.stderr)
print(p, file=sys.stderr)
