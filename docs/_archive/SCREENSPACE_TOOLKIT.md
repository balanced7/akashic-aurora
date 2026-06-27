# SCREENSPACE TOOLKIT - Comprehensive GUI Automation
> **Purpose**: Enable agents to perform any action a human user can do on a Windows desktop.
> **Version**: 1.0 | **Updated**: 2026-04-15

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SCREENSPACE TOOLKIT LAYERS                       │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1: Agent Brain (LLM + Decision Making)                      │
│  └── Interprets screen state, decides actions                       │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2: MCP Server (windows-mcp / agent_comm)                    │
│  └── Exposes tools via Model Context Protocol                        │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3: Automation Foundation                                    │
│  ├── Windows UI Automation (UIA) - Primary                         │
│  ├── PyAutoGUI - Fallback for non-UIA apps                          │
│  ├── Naturo - Window inspection & control                           │
│  └── Vision Engine (Florence-2) - Screen understanding             │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4: Specialized APIs (Creative Tools)                        │
│  ├── Adobe ExtendedScript (Premiere, After Effects)                 │
│  ├── FL Studio Python API                                           │
│  └── Browser DevTools Protocol (Brave, Chrome)                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TOOL CATEGORIES

### Category 1: Core Automation (Windows-MCP)

**Windows-MCP** (`pip install windows-mcp`) is the primary MCP server for Windows GUI automation.

| Tool | Capability |
|------|------------|
| `click` | Click at coordinates |
| `type` | Type text into elements |
| `scroll` | Vertical/horizontal scrolling |
| `move` | Mouse movement and drag |
| `shortcut` | Keyboard shortcuts (Ctrl+C, Alt+Tab, etc.) |
| `wait` | Pause execution |
| `screenshot` | Fast desktop capture |
| `snapshot` | Full UI tree extraction |
| `app` | Launch, resize, move windows |
| `shell` | PowerShell command execution |
| `scrape` | Webpage content extraction |
| `clipboard` | Read/write clipboard |
| `process` | List/kill processes |
| `notification` | Windows toast notifications |
| `registry` | Read/write Windows Registry |

**Installation:**
```bash
# Option A: PyPI (recommended)
pip install windows-mcp

# Option B: uvx (latest)
uvx windows-mcp

# Add to OpenCode MCP config:
{
  "mcpServers": {
    "windows-mcp": {
      "command": "uvx",
      "args": ["windows-mcp"]
    }
  }
}
```

### Category 2: UI Inspection (Naturo)

**Naturo** - Native UI element inspection via Windows UI Automation.

```python
# Available via ui_scout.py wrapper
from ui_scout import list_apps, list_windows, see, find, bring_to_front

# List all windows
list_windows()

# Inspect specific window
see("Adobe Premiere Pro", depth=5)

# Find element by text
find("button", "Export")

# Bring window to front
bring_to_front("Premiere Pro")
```

### Category 3: Screen Understanding (Vision Engine)

**Florence-2** - Vision-language model for screen understanding.

```python
from vision_engine import VisionEngine, capture_active_window

# Quick capture
screenshot = capture_active_window()

# Full analysis
engine = VisionEngine()
result = engine.analyze_screen(screenshot, task="detailed_caption")

# OCR
result = engine.analyze_screen(screenshot, task="ocr")

# Object detection
result = engine.analyze_screen(screenshot, task="od")
```

### Category 4: OCR (Multiple Engines)

| Engine | Best For | Speed | Accuracy |
|--------|----------|-------|----------|
| **Tesseract** | General text | Fast | Good |
| **PaddleOCR** | Document扫描 | Medium | Very Good |
| **EasyOCR** | Multi-language | Slow | Good |
| **Windows.UI** | Native UI | Fast | Good |
| **Florence-2** | Semantic understanding | Medium | Excellent |

```python
# ai_helper.ocr() - Tesseract wrapper
from ai_helper import ocr
text = ocr(screenshot)

# fast_ocr.py - Multi-engine fallback
# Tries: Tesseract → PaddleOCR → EasyOCR
python E:\AI-Setup\fast_ocr.py
```

### Category 5: Window Management

```python
from ai_helper import (
    track_window_order,      # Capture z-order before changes
    restore_window_order,    # Restore original z-order
    focus_this_terminal,    # Bring terminal to front
    WindowZOrder             # Context manager for automatic restore
)

# Context manager usage
with WindowZOrder() as z:
    bring_to_front("Target Window")
    # ... work ...
    # Automatic restore on exit
```

---

## CREATIVE TOOL AUTOMATION

### Adobe Premiere Pro & After Effects

**Method 1: ExtendedScript (JavaScript API)**
```javascript
// Example: Export sequence in Premiere
var proj = app.project;
var seq = proj.activeSequence;
var outputPath = "C:/exports/output.mp4";

app.encodeToFile(seq, outputPath, function(result) {
    if (result.success) {
        alert("Export complete!");
    }
});
```

**Method 2: UI Automation (for UI interactions)**
```python
import uiautomation as auto

# Find Premiere window
premiere = auto.WindowControl(searchDepth=1, Name="Adobe Premiere Pro")
if premiere.Exists(5, 1):
    # Navigate to Export menu via UI
    premiere.MenuBarControl().MenuItemControl(Name="File").Click()
    premiere.MenuItemControl(Name="Export").Click()
```

**Method 3: Keyboard Macros (via PyAutoGUI)**
```python
import pyautogui

# Export sequence shortcut
pyautogui.hotkey('ctrl', 'm')  # Export Media shortcut
pyautogui.press('enter')        # Confirm export
```

### FL Studio

**Method 1: Python API (flbot)**
```python
# FL Studio Python API
import flbot

# Control playback
flbot.transport.play()
flbot.transport.stop()
flbot.transport.record()

# Mixer operations
flbot.mixer.set_volume(1, 0.75)  # Channel 1, 75% volume
flbot.mixer.set_pan(1, 0.0)      # Center pan
```

**Method 2: Keyboard Macros**
```python
import pyautogui

# Common FL Studio shortcuts
pyautogui.hotkey('space')        # Play/Stop
pyautogui.hotkey('ctrl', 's')    # Save
pyautogui.hotkey('ctrl', 'r')    # Render
```

**Method 3: UI Automation**
```python
import uiautomation as auto

fl = auto.WindowControl(searchDepth=1, Name="FL Studio")
if fl.Exists(3):
    # Click on mixer channel
    fl.ButtonControl(Name="Channel 1").Click()
```

---

## WEB BROWSER AUTOMATION

### Brave (Chrome-based)

**Method 1: Selenium WebDriver**
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
driver = webdriver.Chrome(options=options)

driver.get("https://example.com")
element = driver.find_element("name", "q")
element.send_keys("search query")
element.submit()
```

**Method 2: Browser DevTools Protocol (via Windows-MCP)**
```bash
# Windows-MCP Scrape tool
scrape --url "https://example.com" --selector ".content"
```

**Method 3: Native Browser Automation (Windows-MCP)**
```
Use the `app` tool to control browser windows:
- app --action focus --app "Brave"
- Use Screenshot + OCR for reading content
- Use Type + Click for interactions
```

---

## ADVANCED FEATURES

### Window Z-Order Preservation

**Problem**: When automating windows, other windows may get focus/restacked.

**Solution**: Track and restore window order.

```python
from ai_helper import track_window_order, restore_window_order, bring_to_front

# Before any bring_to_front
track_window_order()

# Do your work
bring_to_front("Target Window")
# ... automation ...

# Restore original order
restore_window_order()
```

### Multi-Monitor Support

```python
import pyautogui

# Get monitor info
pyautogui.size()           # Primary monitor size
pyautogui.screensize()     # All monitors combined

# Move to specific monitor
pyautogui.moveTo(x=3000, y=500)  # Second monitor

# Capture specific monitor
import mss
with mss.mss() as sct:
    monitor = sct.monitors[2]  # Second monitor
    sct.grab(monitor)
```

### Safe Automation Practices

```python
# 1. Always track window order for GUI-heavy tasks
track_window_order()

# 2. Use failsafe - move mouse to corner to abort
import pyautogui
pyautogui.FAILSAFE = True

# 3. Add delays for UI to settle
import time
time.sleep(0.5)

# 4. Verify actions
from vision_engine import capture_active_window
screenshot = capture_active_window()
# Analyze to confirm expected state

# 5. Restore window order after
restore_window_order()
```

---

## INTEGRATION WITH OPENCODE

### MCP Server Setup

Add to OpenCode MCP config (`C:\Users\L5\.config\opencode\mcp.json`):

```json
{
  "mcpServers": {
    "windows-mcp": {
      "command": "uvx",
      "args": ["windows-mcp"]
    },
    "agent_comm": {
      "command": "python",
      "args": ["-m", "agent_comm", "serve"],
      "cwd": "E:\\AI-Setup\\mcp_servers\\agent_comm"
    }
  }
}
```

### Tool Usage in OpenCode

```
Agent can now use natural language:
- "Take a screenshot of Premiere Pro"
- "Click the Export button in Premiere"
- "Find the timeline window in After Effects"
- "Export the current sequence as MP4"
```

---

## INSTALLATION COMMANDS

```powershell
# Core tools
pip install windows-mcp          # Primary MCP server
pip install uiautomation        # Windows UI Automation
pip install pyautography        # Desktop automation
pip install pytesseract         # Tesseract OCR
pip install mss                 # Multi-monitor screenshots
pip install pillow              # Image processing

# Vision
pip install torch
pip install transformers        # Florence-2

# Browser automation
pip install selenium
pip install webdriver-manager

# Creative tools
# FL Studio: Enable Python API in FL Studio settings
# Adobe: Built-in ExtendScript (no install needed)
```

---

## TROUBLESHOOTING

### Window Not Found
```python
# Use ui_scout.list_windows() to find exact window name
from ui_scout import list_windows
print(list_windows())
```

### UIA Not Working (Requires Admin)
```powershell
# Run as Administrator for full UIA access
Start-Process python -Verb RunAs
```

### OCR Poor Quality
```python
# Preprocess image for better OCR
from PIL import Image, ImageEnhance

def preprocess_for_ocr(image_path):
    img = Image.open(image_path).convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    return img
```

### Browser Not Responding
```python
# Use Windows-MCP app tool to focus first
# Then wait for window to settle
import time
time.sleep(1)
```

---

## ROADMAP

### Phase 1: Core (DONE)
- [x] Windows-MCP integration
- [x] Naturo/UI Scout for inspection
- [x] Vision Engine (Florence-2)
- [x] Tesseract/PaddleOCR/EasyOCR
- [x] Window z-order preservation

### Phase 2: Creative Tools (In Progress)
- [ ] Adobe ExtendScript integration
- [ ] Premiere Pro automation recipes
- [ ] After Effects automation recipes
- [ ] FL Studio API recipes

### Phase 3: Advanced
- [ ] Template matching for unreliable UI
- [ ] Multi-agent coordinated automation
- [ ] Recording and playback of user actions
- [ ] Custom skill training for specific apps

---

## QUICK REFERENCE

```python
# Essential imports
from ui_scout import bring_to_front, screenshot_isolated, list_windows
from vision_engine import capture_active_window, VisionEngine
from ai_helper import track_window_order, restore_window_order, ocr
import pyautogui

# Basic workflow
track_window_order()
bring_to_front("Target App")
screenshot = screenshot_isolated("Target App")
text = ocr(screenshot)
# ... analyze and act ...
restore_window_order()

# Launch app via Windows-MCP
# Use: app --action launch --app "Premiere Pro"
```

---

**Last Updated**: 2026-04-15
