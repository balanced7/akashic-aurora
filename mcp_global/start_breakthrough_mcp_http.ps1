# Optional: one shared MCP process for Cursor + Claude (warm imports, single Redis pool).
# Run at sign-in or before sessions:  powershell -File E:\AI-Setup\mcp_global\start_breakthrough_mcp_http.ps1
# Then merge mcp_global/breakthrough_stack_http.cursor.json into ~/.cursor/mcp.json (or use only this server).
$ErrorActionPreference = "Stop"
Set-Location E:\AI-Setup
py -3 ai_setup_mcp.py --http --port 18765
