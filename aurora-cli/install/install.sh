#!/bin/sh
# Install the `aurora` command on macOS or Linux.
#
#   curl -fsSL https://github.com/balanced7/akashic-aurora/releases/latest/download/install.sh | sh
#   curl -fsSL .../install.sh | sh -s -- --version 0.1.0      # a specific release
#   curl -fsSL .../install.sh | sh -s -- --no-modify-path     # leave shell profiles alone
#
# What it does, in order (run it again to update; every step is idempotent):
#   1. finds uv, or installs it with Astral's own installer (https://docs.astral.sh/uv/)
#   2. resolves the release (the latest, unless --version / AURORA_VERSION says otherwise)
#   3. `uv tool install`s the launcher wheel from that release: `aurora` lands in uv's tool bin
#      (~/.local/bin), with a Python uv manages -- nothing touches the system Python
#   4. `uv tool update-shell` puts that bin on PATH (skipped with --no-modify-path)
#   5. `aurora self install` fetches the matching Aurora bundle, checks its sha256, and builds
#      its locked environment, so the first real command starts at full speed
#
# Environment: AURORA_VERSION, AURORA_HOME (default ~/.aurora), AURORA_NO_MODIFY_PATH=1,
# AURORA_RELEASE_BASE (a URL or directory holding the release assets; {version} is substituted).
set -eu

REPO_SLUG="balanced7/akashic-aurora"
version="${AURORA_VERSION:-}"
modify_path=1
[ -n "${AURORA_NO_MODIFY_PATH:-}" ] && modify_path=0

say() { printf '\033[1maurora-install:\033[0m %s\n' "$*"; }
die() { printf 'aurora-install: ERROR: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --version) [ $# -ge 2 ] || die "--version needs a value"; version="$2"; shift 2 ;;
    --version=*) version="${1#--version=}"; shift ;;
    --no-modify-path) modify_path=0; shift ;;
    -h|--help) sed -n '2,22p' "$0" 2>/dev/null || true; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
done

case "$(uname -s)" in
  Linux|Darwin) ;;
  MINGW*|MSYS*|CYGWIN*) die "this is the macOS/Linux installer. On Windows run, in PowerShell:
  powershell -ExecutionPolicy ByPass -c \"irm https://github.com/$REPO_SLUG/releases/latest/download/install.ps1 | iex\"" ;;
  *) die "unsupported OS: $(uname -s)" ;;
esac

if command -v curl >/dev/null 2>&1; then
  fetch() { curl -fsSL "$1"; }
  final_url() { curl -fsSLI -o /dev/null -w '%{url_effective}' "$1"; }
elif command -v wget >/dev/null 2>&1; then
  fetch() { wget -qO- "$1"; }
  final_url() { wget -S --spider --max-redirect=5 "$1" 2>&1 | sed -n 's/^ *[Ll]ocation: //p' | tail -1; }
else
  die "need curl or wget"
fi

# 1. uv ---------------------------------------------------------------------------------------
PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  say "installing uv (Astral's Python package manager), which runs Aurora"
  if [ "$modify_path" = 1 ]; then
    fetch https://astral.sh/uv/install.sh | sh
  else
    fetch https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
  fi
  command -v uv >/dev/null 2>&1 || die "uv installed but is not on PATH; open a new shell and run this again"
fi
say "using $(uv --version)"

# 2. which release ----------------------------------------------------------------------------
if [ -z "$version" ]; then
  tag_url="$(final_url "https://github.com/$REPO_SLUG/releases/latest" || true)"
  version="${tag_url##*/}"
  case "$version" in
    v[0-9]*) ;;
    *) die "could not find the latest release of $REPO_SLUG (got '${tag_url:-nothing}'); pass --version X.Y.Z" ;;
  esac
fi
version="${version#v}"
base="${AURORA_RELEASE_BASE:-https://github.com/$REPO_SLUG/releases/download/v{version\}}"
base="$(printf '%s' "$base" | sed "s/{version}/$version/g")"
base="${base%/}"
wheel="$base/akashic_aurora_cli-$version-py3-none-any.whl"

# 3. the launcher -----------------------------------------------------------------------------
say "installing aurora $version"
uv tool install --force --quiet --python 3.12 "$wheel" || die "uv could not install $wheel"
bin_dir="$(uv tool dir --bin)"

# 4. PATH -------------------------------------------------------------------------------------
if [ "$modify_path" = 1 ]; then
  uv tool update-shell >/dev/null 2>&1 || true
fi

# 5. the program ------------------------------------------------------------------------------
if [ -n "${AURORA_RELEASE_BASE:-}" ]; then export AURORA_RELEASE_BASE; fi
"$bin_dir/aurora" self install || die "aurora was installed but could not fetch its bundle; run: aurora self install"

say "done. aurora $version is at $bin_dir/aurora"
case ":$PATH:" in
  *":$bin_dir:"*) ;;
  *) [ "$modify_path" = 1 ] && say "open a new terminal (or run: export PATH=\"$bin_dir:\$PATH\") so your shell finds it" ;;
esac
cat <<EOF

  Next:
    aurora setup                        # wire your agent harness (hooks, MCP, agent id), step by step
    aurora boot <your-agent-id> --task "what you are doing"
    aurora discover                     # every command, one line each

  Update: run this installer again, or: aurora self update
EOF
