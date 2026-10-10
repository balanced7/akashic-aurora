#!/usr/bin/env sh
# Fuzz smoke for the gate and CI: every target, seeded from fuzz/seeds, for SECONDS each.
# Needs nightly and cargo-fuzz (`cargo install cargo-fuzz`). Exit non-zero on the first crash.
set -eu
cd "$(dirname "$0")/.."
SECONDS_EACH="${1:-30}"
for t in record acl_entries invite cert frame; do
  mkdir -p "fuzz/corpus/$t"
  cp -n fuzz/seeds/"$t"/* "fuzz/corpus/$t/" 2>/dev/null || true
  cargo +nightly fuzz run "$t" -- -max_total_time="$SECONDS_EACH" -rss_limit_mb=4096
done
