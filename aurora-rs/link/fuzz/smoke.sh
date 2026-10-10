#!/usr/bin/env sh
# Fuzz smoke for the gate and CI: every target, seeded from fuzz/seeds, for SECONDS each.
# Needs nightly and cargo-fuzz (`cargo install cargo-fuzz`). Exit non-zero if any target crashes.
# The targets build once, then run side by side: each still gets its full SECONDS of fuzzing (one
# libFuzzer process per target), and the wall time is one target's, not five.
set -eu
cd "$(dirname "$0")/.."
SECONDS_EACH="${1:-30}"
TARGETS="record acl_entries invite cert frame"
# The toolchain's own host triple: a prebuilt cargo-fuzz may be a musl binary and would otherwise
# build for musl, where the address sanitizer cannot run.
HOST="$(rustc +nightly -vV | sed -n 's/^host: //p')"
LOGS="$(mktemp -d)"
cargo +nightly fuzz build --target "$HOST"
pids=""
for t in $TARGETS; do
  mkdir -p "fuzz/corpus/$t"
  cp -n fuzz/seeds/"$t"/* "fuzz/corpus/$t/" 2>/dev/null || true
  cargo +nightly fuzz run --target "$HOST" "$t" -- -max_total_time="$SECONDS_EACH" -rss_limit_mb=4096 \
    >"$LOGS/$t.log" 2>&1 &
  pids="$pids $t:$!"
done
failed=""
for tp in $pids; do
  wait "${tp#*:}" || failed="$failed ${tp%%:*}"
done
for t in $TARGETS; do
  tail -n 3 "$LOGS/$t.log" | sed "s/^/[$t] /"
done
if [ -n "$failed" ]; then
  for t in $failed; do
    echo "=== $t crashed ===" >&2
    tail -n 60 "$LOGS/$t.log" >&2
  done
  exit 1
fi
