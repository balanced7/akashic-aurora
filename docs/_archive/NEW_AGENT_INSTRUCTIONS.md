# OpenCode Agent Instructions

## YOUR TASK

You are a NEW OpenCode agent that needs to get up to speed with the Akashic Aurora project. Follow these steps in order:

### STEP 1: Read Bootstrap File
Read and execute `E:\AI-Setup\bootstrap.md` to initialize all services:
- Start Redis HA cluster
- Start Redis sync service
- Initialize project context
- Start MCP server

### STEP 2: Read Architecture & Project Context
1. Read `E:\AI-Setup\STARTUP.md` for system overview
2. Read `E:\AI-Setup\ARCHITECTURE.md` for detailed architecture
3. Get full project context by running:
   ```
   python E:\AI-Setup\project_context.py --context
   ```

### STEP 3: Learn Screenspace Tools
Read `E:\AI-Setup\SCREENSPACE_TOOLKIT.md` to understand:
- Windows-MCP for GUI automation
- Naturo/UI Scout for window inspection
- Vision Engine for screen understanding
- OCR tools available

### STEP 4: Install MCP Integration
Create a NEW terminal window and install OpenCode MCP integration:

1. First, check if windows-mcp is installed:
   ```
   pip show windows-mcp
   ```

2. If not installed, install it:
   ```
   pip install windows-mcp
   ```

3. Add MCP servers to OpenCode config at `C:\Users\L5\.config\opencode\mcp.json`:
   ```json
   {
     "mcpServers": {
       "ai-setup": {
         "command": "python",
         "args": ["E:\\AI-Setup\\ai_setup_mcp.py"]
       },
       "windows-mcp": {
         "command": "uvx",
         "args": ["windows-mcp"]
       }
     }
   }
   ```

4. Restart OpenCode to load MCP servers

### STEP 5: Verify MCP Integration
After restarting, verify MCP servers are loaded by asking OpenCode to:
- List available MCP tools
- Get project context via MCP
- Take a screenshot using windows-mcp

### REPORT BACK
After completing all steps, report:
1. Which services are running
2. What's in the project context
3. What screenspace tools are available
4. Whether MCP integration succeeded
