# Optional: one shared MCP process for Cursor + Claude (warm imports, single Redis pool).
# Run at sign-in or before sessions:  powershell -File $Root\mcp_global\start_akashic_aurora_mcp_http.ps1
# Then merge mcp_global/akashic_aurora_http.cursor.json into ~/.cursor/mcp.json (or use only this server).
$ErrorActionPreference = "Stop"
# Root derived from this script's own location, never hardcoded.
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $Root
py -3 ai_setup_mcp.py --http --port 18765
