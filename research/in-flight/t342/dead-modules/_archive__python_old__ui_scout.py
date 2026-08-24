"""
Enhanced UI Inspection with Naturo
====================================
Deep UI element detection for any application.

Usage:
    from ui_scout import see, find, list_apps, highlight_element
    
    # Quick overview
    list_apps()
    
    # Deep inspection of a window
    see("OpenCode", depth=5)
    
    # Find specific element
    find("button", "Submit")
    
    # Highlight elements
    highlight_element("OpenCode", depth=3)
"""
import subprocess
import sys
import json
import os

NATURO_CMD = r"C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe"

def _run_naturo(args, timeout=30):
    """Run naturo command and return output"""
    cmd = [NATURO_CMD, "-m", "naturo"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr
    except Exception as e:
        return "", str(e)

def list_apps():
    """List all applications with UI elements"""
    stdout, _ = _run_naturo(["list", "apps", "--json"])
    if stdout:
        try:
            apps = json.loads(stdout)
            print("=== APPLICATIONS ===")
            for app in apps[:20]:
                print(f"  {app.get('name', 'unknown')} - {app.get('windows', 0)} windows")
            return apps
        except:
            pass
    
    # Fallback to windows
    stdout, _ = _run_naturo(["list", "windows"])
    print("=== WINDOWS ===")
    print(stdout)
    return None

def list_windows():
    """List all visible windows"""
    stdout, _ = _run_naturo(["list", "windows"])
    print("=== WINDOWS ===")
    print(stdout)
    return stdout

def see(window_pattern=None, depth=3, mode="full", annotate=True):
    """
    Inspect UI elements in a window.
    
    Args:
        window_pattern: Window title to match (partial)
        depth: How deep to traverse the UI tree (1-50)
        mode: full, interactive, or fast
        annotate: Add labels to screenshot
    """
    args = ["see"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    args.extend(["-d", str(depth), "--mode", mode])
    if annotate:
        args.append("--annotate")
    args.append("--json")
    
    stdout, stderr = _run_naturo(args, timeout=60)
    
    if stdout:
        try:
            # Find JSON in output (may have prefix text)
            start = stdout.find('{')
            if start >= 0:
                json_str = stdout[start:]
                data = json.loads(json_str)
            else:
                data = json.loads(stdout)
            
            # Build element list from tree
            elements = []
            def extract_elements(node, depth=0):
                if depth > 10:  # Limit recursion
                    return
                role = node.get("role", "?")
                name = node.get("name", "")
                bounds = f"[{node.get('x',0)},{node.get('y',0)} {node.get('width',0)}x{node.get('height',0)}]"
                if name:
                    elements.append({"role": role, "name": name[:60], "bounds": bounds, "id": node.get("id")})
                for child in node.get("children", []):
                    extract_elements(child, depth+1)
            
            extract_elements(data)
            
            print(f"=== UI INSPECTION: {window_pattern or 'foreground'} ===")
            print(f"Elements found: {len(elements)}")
            print(f"Screen: {data.get('width', '?')}x{data.get('height', '?')}")
            
            # Print element tree from extracted elements
            for el in elements[:30]:
                role = el.get("role", "?")
                name = el.get("name", "")
                bounds = el.get("bounds", "")
                print(f"  [{role}] {name[:60]} {bounds}")
            
            # Screenshot path
            if data.get("screenshot"):
                print(f"\nScreenshot: {data['screenshot']}")
            
            return data
        except json.JSONDecodeError:
            print("=== UI INSPECTION ===")
            print(stdout)
            return {"raw": stdout}
    
    print(f"Error: {stderr}")
    return None

def find(query, window_pattern=None, limit=20):
    """
    Find UI elements matching a query.
    
    Args:
        query: Search term (matches role, name, id)
        window_pattern: Window to search in
        limit: Max results
    """
    args = ["find", query, "-l", str(limit)]
    if window_pattern:
        args.extend(["--window", window_pattern])
    args.append("--json")
    
    stdout, _ = _run_naturo(args, timeout=30)
    
    if stdout:
        try:
            data = json.loads(stdout)
            results = data.get("results", [])
            print(f"=== FIND: '{query}' ({len(results)} results) ===")
            for r in results:
                print(f"  [{r.get('role')}] {r.get('name', '')[:50]} at {r.get('bounds', '')}")
            return results
        except:
            print(stdout)
            return []
    
    return []

def highlight(window_pattern=None, depth=3, duration=5):
    """
    Highlight UI elements on screen for visual reference.
    """
    args = ["highlight"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    args.extend(["-d", str(depth), "--duration", str(duration)])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def capture(window_pattern=None, path=None):
    """
    Capture screenshot of a window.
    """
    args = ["capture"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    if path:
        args.extend(["-o", path])
    args.append("--json")
    
    stdout, _ = _run_naturo(args, timeout=30)
    
    if stdout:
        try:
            data = json.loads(stdout)
            print(f"Screenshot: {data.get('path')}")
            return data.get("path")
        except:
            pass
    return None

def diff(window1, window2=None):
    """
    Compare UI element trees to detect changes.
    """
    args = ["diff", window1]
    if window2:
        args.append(window2)
    args.append("--json")
    
    stdout, _ = _run_naturo(args, timeout=30)
    
    if stdout:
        try:
            data = json.loads(stdout)
            print(f"=== UI CHANGES ===")
            added = data.get("added", [])
            removed = data.get("removed", [])
            changed = data.get("changed", [])
            
            print(f"Added: {len(added)}")
            print(f"Removed: {len(removed)}")
            print(f"Changed: {len(changed)}")
            
            return data
        except:
            print(stdout)
    return None

def quick_scan(app_name=None):
    """Fast scan of UI - just clickable elements"""
    if app_name:
        return see(app_name, depth=2, mode="fast", annotate=False)
    return see(None, depth=2, mode="fast", annotate=False)


# ============ INTERACTION COMMANDS ============
def click(element_id=None, x=None, y=None, window_pattern=None):
    """
    Click on a UI element or coordinates.
    
    Args:
        element_id: Element ID from see command (e.g., "e5")
        x, y: Direct coordinates
        window_pattern: Window to click in
    """
    args = ["click"]
    if element_id:
        args.extend(["--id", element_id])
    elif x is not None and y is not None:
        args.extend(["--coords", str(x), str(y)])
    
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def double_click(x, y, window_pattern=None):
    """Double-click at coordinates"""
    args = ["click", "--coords", str(x), str(y), "--double"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def right_click(x, y, window_pattern=None):
    """Right-click at coordinates"""
    args = ["click", "--coords", str(x), str(y), "--right"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def type_text(text, window_pattern=None):
    """Type text at current focus"""
    args = ["type", text]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def press_keys(keys, window_pattern=None):
    """Press keyboard shortcut"""
    args = ["press", keys]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout

def move_mouse(x, y):
    """Move mouse to coordinates"""
    args = ["move", str(x), str(y)]
    stdout, _ = _run_naturo(args, timeout=10)
    return stdout

def scroll(direction="down", amount=3, window_pattern=None):
    """Scroll in a direction"""
    args = ["scroll", direction, str(amount)]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=10)
    print(stdout)
    return stdout


# ============ DRAG AND DROP ============
def drag(start_x, start_y, end_x, end_y, window_pattern=None):
    """
    Drag from one position to another.
    
    Args:
        start_x, start_y: Starting coordinates
        end_x, end_y: Ending coordinates
        window_pattern: Window to drag in
    """
    args = ["drag", "--from-coords", str(start_x), str(start_y), 
            "--to-coords", str(end_x), str(end_y)]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=15)
    print(stdout)
    return stdout

def drag_element(element_id, dest_x, dest_y, window_pattern=None):
    """
    Drag an element to a position.
    
    Args:
        element_id: Element ID from see command
        dest_x, dest_y: Destination coordinates
        window_pattern: Window
    """
    args = ["drag", "--from", element_id, "--to-coords", str(dest_x), str(dest_y)]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=15)
    print(stdout)
    return stdout

def drag_to_element(from_x, from_y, to_element_id, window_pattern=None):
    """
    Drag from coordinates to a UI element.
    """
    args = ["drag", "--from-coords", str(from_x), str(from_y), "--to", to_element_id]
    if window_pattern:
        args.extend(["--window", window_pattern])
    
    stdout, _ = _run_naturo(args, timeout=15)
    print(stdout)
    return stdout


# ============ HYBRID OCR + UI INSPECTION ============
def hybrid_inspect(window_pattern=None, depth=5):
    """
    Combine UI automation (Naturo) with OCR (Tesseract) for complete coverage.
    
    1. First tries Naturo to get accessible UI elements
    2. Falls back to OCR for rendered content (images, canvas, games)
    """
    results = {
        "ui_elements": None,
        "ocr_text": None,
        "combined": []
    }
    
    # Step 1: Get UI tree with Naturo
    ui_data = see(window_pattern, depth=depth, annotate=True)
    if ui_data:
        results["ui_elements"] = ui_data
        
        # Extract text from UI elements
        def extract_text(node):
            text = node.get("name", "")
            for child in node.get("children", []):
                text += " " + extract_text(child)
            return text
        
        if "id" in ui_data:
            results["combined"].append({"source": "naturo", "text": extract_text(ui_data)})
    
    # Step 2: OCR any visual content
    try:
        from ai_helper import ocr
        ocr_text = ocr()
        if ocr_text and len(ocr_text.strip()) > 5:
            results["ocr_text"] = ocr_text
            results["combined"].append({"source": "ocr", "text": ocr_text[:500]})
    except Exception as e:
        results["combined"].append({"source": "ocr", "error": str(e)})
    
    return results

def smart_find(search_term, window_pattern=None):
    """
    Smart search - tries both UI automation and OCR.
    
    Returns first match from either method.
    """
    # Try UI first
    ui_results = find(search_term, window_pattern, limit=5)
    if ui_results:
        return {"method": "naturo", "results": ui_results}
    
    # Fall back to OCR
    try:
        from ai_helper import ocr
        text = ocr()
        if search_term.lower() in text.lower():
            # Found in OCR - return approximate location
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if search_term.lower() in line.lower():
                    return {
                        "method": "ocr",
                        "results": [{"line": i, "text": line.strip(), "source": "screen OCR"}]
                    }
    except:
        pass
    
    return {"method": "none", "results": []}

def get_visual_context(window_pattern=None):
    """
    Get comprehensive visual context using both methods.
    Returns structured data with:
    - UI element tree
    - All visible text (from UI + OCR)
    - Clickable regions with coordinates
    """
    context = {
        "elements": [],
        "text_regions": [],
        "clickable": []
    }
    
    # Get UI tree
    ui_data = see(window_pattern, depth=10, annotate=True)
    if ui_data:
        # Extract all elements
        def process_node(node):
            role = node.get("role", "")
            name = node.get("name", "")
            x, y = node.get("x", 0), node.get("y", 0)
            w, h = node.get("width", 0), node.get("height", 0)
            
            if role and (name or w > 0):
                context["elements"].append({
                    "role": role,
                    "name": name,
                    "bounds": {"x": x, "y": y, "width": w, "height": h}
                })
                
                # Clickable elements
                if role in ["Button", "MenuItem", "TabItem", "Hyperlink", "ListItem"]:
                    context["clickable"].append({
                        "name": name,
                        "bounds": {"x": x, "y": y, "width": w, "height": h}
                    })
            
            for child in node.get("children", []):
                process_node(child)
        
        if "id" in ui_data:
            process_node(ui_data)
    
    # Get OCR text
    try:
        from ai_helper import ocr
        text = ocr()
        if text:
            context["text_regions"].append({"source": "ocr", "text": text[:1000]})
    except:
        pass
    
    return context


# ============ EXPORT FOR AI HELPER ============
def get_ui_tree(window_title, max_depth=5):
    """Get full UI tree as structured data"""
    data = see(window_title, depth=max_depth, mode="full", annotate=False)
    return data

def get_clickable_elements(window_title):
    """Get only interactive elements (buttons, inputs, etc)"""
    data = see(window_title, depth=10, mode="interactive")
    return data

def locate_element(window_title, search_text):
    """Find element containing specific text"""
    return find(search_text, window_pattern=window_title)


def bring_to_front(window_pattern=None):
    """
    Bring a window to the foreground/activate it.
    This ensures the target window is not occluded before screen capture.
    
    Args:
        window_pattern: Window title to match (partial). If None, uses foreground window.
    
    Returns:
        True if successful, False otherwise
    """
    args = ["app", "focus"]
    if window_pattern:
        args.extend(["--app", window_pattern])
    
    stdout, stderr = _run_naturo(args, timeout=10)
    
    if stderr and "error" in stderr.lower():
        print(f"[bring_to_front] Failed: {stderr}")
        return False
    
    print(f"[bring_to_front] Window '{window_pattern or 'foreground'}' brought to front")
    return True


def capture_window(window_pattern=None, output_path=None):
    """
    Capture screenshot of a specific window (isolated from other windows).
    Window is brought to front automatically before capture.
    
    Args:
        window_pattern: Window title to match (partial)
        output_path: Optional path to save screenshot
    
    Returns:
        Path to screenshot or None
    """
    # First bring window to front
    bring_to_front(window_pattern)
    
    import time
    time.sleep(0.3)  # Allow window to settle
    
    # Capture with window-specific targeting
    args = ["capture"]
    if window_pattern:
        args.extend(["--window", window_pattern])
    if output_path:
        args.extend(["--output", output_path])
    
    stdout, stderr = _run_naturo(args, timeout=15)
    
    if stdout and "saved" in stdout.lower():
        # Extract path
        for line in stdout.split('\n'):
            if 'saved' in line.lower() or '.png' in line.lower():
                print(f"[capture_window] {line.strip()}")
                return line.strip()
    
    print(f"[capture_window] Capture output: {stdout}")
    return stdout.strip() if stdout else None


def screenshot_isolated(window_pattern=None, output_path=None):
    """
    Capture isolated screenshot of window after bringing it to front.
    This is the RECOMMENDED way to capture a specific window's content.
    
    Usage:
        path = screenshot_isolated("AI Control Center")
        # Or with custom output:
        path = screenshot_isolated("OpenCode", "C:/temp/screenshot.png")
    """
    import tempfile
    import os
    import time
    
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"ui_capture_{int(time.time())}.png")
    
    return capture_window(window_pattern, output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ui_scout.py <command> [args]")
        print("Commands: list, see <window>, find <query>, highlight <window>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_apps()
    elif cmd == "see":
        window = sys.argv[2] if len(sys.argv) > 2 else None
        see(window, depth=5)
    elif cmd == "find":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        find(query)
    elif cmd == "highlight":
        window = sys.argv[2] if len(sys.argv) > 2 else None
        highlight(window)
    else:
        print(f"Unknown command: {cmd}")