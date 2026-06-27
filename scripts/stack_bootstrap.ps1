# DAG orchestrator — starts BreakThrough services in dependency order.
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File E:\AI-Setup\scripts\stack_bootstrap.ps1 start
#
# Commands match: python -m stack_manager.cli <command>

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
if ($args.Count -eq 0) {
    python -m stack_manager.cli
    exit $LASTEXITCODE
}
python -m stack_manager.cli @args
exit $LASTEXITCODE
