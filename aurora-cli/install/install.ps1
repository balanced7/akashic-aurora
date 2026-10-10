# Install the `aurora` command on Windows.
#
#   powershell -ExecutionPolicy ByPass -c "irm https://github.com/balanced7/akashic-aurora/releases/latest/download/install.ps1 | iex"
#
# What it does, in order (run it again to update; every step is idempotent):
#   1. finds uv, or installs it with Astral's own installer (https://docs.astral.sh/uv/)
#   2. resolves the release (the latest, unless $env:AURORA_VERSION says otherwise)
#   3. `uv tool install`s the launcher wheel from that release: aurora.exe lands in uv's tool bin
#      (%USERPROFILE%\.local\bin), with a Python uv manages -- the system Python is untouched
#   4. `uv tool update-shell` puts that bin on your user PATH (skip: $env:AURORA_NO_MODIFY_PATH=1)
#   5. `aurora self install` fetches the matching Aurora bundle, checks its sha256, and builds
#      its locked environment, so the first real command starts at full speed
#
# Environment: AURORA_VERSION, AURORA_HOME (default ~\.aurora), AURORA_NO_MODIFY_PATH=1,
# AURORA_RELEASE_BASE (a URL or directory holding the release assets; {version} is substituted).

$ErrorActionPreference = 'Stop'
$RepoSlug = 'balanced7/akashic-aurora'

function Say([string]$msg) { Write-Host "aurora-install: $msg" }
function Die([string]$msg) { Write-Host "aurora-install: ERROR: $msg" -ForegroundColor Red; exit 1 }

# 1. uv ---------------------------------------------------------------------------------------
$localBin = Join-Path $HOME '.local\bin'
$env:Path = "$localBin;$env:Path"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Say "installing uv (Astral's Python package manager), which runs Aurora"
    if ($env:AURORA_NO_MODIFY_PATH) { $env:UV_NO_MODIFY_PATH = '1' }
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Die 'uv installed but is not on PATH; open a new PowerShell window and run this again' }
}
Say "using $(uv --version)"

# 2. which release ----------------------------------------------------------------------------
$version = $env:AURORA_VERSION
if (-not $version) {
    try {
        $version = (Invoke-RestMethod "https://api.github.com/repos/$RepoSlug/releases/latest").tag_name
    } catch {
        Die "could not find the latest release of $RepoSlug ($($_.Exception.Message)); set `$env:AURORA_VERSION = 'X.Y.Z'"
    }
}
$version = $version.TrimStart('v')
$base = if ($env:AURORA_RELEASE_BASE) { $env:AURORA_RELEASE_BASE } else { "https://github.com/$RepoSlug/releases/download/v{version}" }
$base = $base.Replace('{version}', $version).TrimEnd('/', '\')
$wheel = "$base/akashic_aurora_cli-$version-py3-none-any.whl"

# 3. the launcher -----------------------------------------------------------------------------
Say "installing aurora $version"
uv tool install --force --quiet --python 3.12 $wheel
if ($LASTEXITCODE -ne 0) { Die "uv could not install $wheel" }
$binDir = (uv tool dir --bin).Trim()

# 4. PATH -------------------------------------------------------------------------------------
if (-not $env:AURORA_NO_MODIFY_PATH) { uv tool update-shell *> $null }

# 5. the program ------------------------------------------------------------------------------
& (Join-Path $binDir 'aurora.exe') self install
if ($LASTEXITCODE -ne 0) { Die 'aurora was installed but could not fetch its bundle; run: aurora self install' }

Say "done. aurora $version is at $(Join-Path $binDir 'aurora.exe')"
Say 'open a new terminal if `aurora` is not found yet'
Write-Host @'

  Next:
    aurora setup                        # wire your agent harness (hooks, MCP, agent id), step by step
    aurora boot <your-agent-id> --task "what you are doing"
    aurora discover                     # every command, one line each

  Update: run this installer again, or: aurora self update
'@
