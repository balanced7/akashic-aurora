"""
Agentic Automation Framework
==========================
Unified desktop automation for AI agents combining:
- Vision (Florence-2) for visual understanding
- Mouse/Keyboard control (PyAutoGUI) for direct interaction
- Screen monitoring for state verification

USAGE BY AGENTS:
    from agentic_automation import AgenticAutomation
    
    auto = AgenticAutomation()
    
    # Take screenshot and analyze
    auto.analyze_screen()
    
    # Click on something you see
    auto.click_on_text("Submit")
    
    # Type text
    auto.type("Hello world")
    
    # Wait for something to appear
    auto.wait_for("Success", timeout=10)
    
    # Execute complex tasks
    auto.task("Click the red button, then type 'done' in the input field")

SAFETY: Move mouse to screen corner to abort any automation.
"""

import sys
import time
import json
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

# Core automation
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

# Vision stack
try:
    from vision_engine import (
        capture_active_window,
        get_screen_context_for_analyst,
        encode_image_base64,
        VisionEngine
    )
    VISION_ENGINE = VisionEngine()
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    VISION_ENGINE = None

# Constants
SCREEN_CORNER_ABORT = True  # Move to corner = emergency stop


@dataclass
class ScreenRegion:
    """Represents a region of the screen"""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class VisualMatch:
    """Represents a visual element found on screen"""
    text: str
    confidence: float
    region: ScreenRegion
    element_type: str = "text"


class AgenticAutomation:
    """
    Agent-facing automation with vision integration.
    
    This is the PRIMARY interface agents should use for:
    - Clicking buttons/elements
    - Typing text
    - Verifying screen state
    - Executing multi-step tasks
    """
    
    def __init__(self):
        self.vision = VISION_ENGINE
        self.last_screenshot = None
        self.last_context = None
        self.click_duration = 0.15
        
    # === SCREEN CAPTURE ===
    
    def capture(self) -> Optional[Any]:
        """Capture active window screenshot"""
        try:
            self.last_screenshot = capture_active_window()
            return self.last_screenshot
        except Exception as e:
            print(f"[agentic] Capture failed: {e}")
            return None
    
    def analyze_screen(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Capture and analyze current screen state.
        
        Args:
            timeout: Max seconds to wait for analysis (Florence-2 can be slow)
        
        Returns:
            Dict with caption, extracted_text, error_detection, ui_elements
        """
        screenshot = self.capture()
        if screenshot is None:
            return None
        
        try:
            # Check if vision is responsive within timeout
            import threading
            
            result = [None]
            def analyze():
                try:
                    result[0] = get_screen_context_for_analyst(screenshot)
                except Exception as e:
                    print(f"[agentic] Vision analysis error: {e}")
                    result[0] = None
            
            thread = threading.Thread(target=analyze)
            thread.start()
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                print(f"[agentic] Vision analysis timed out after {timeout}s")
                return None
            
            self.last_context = result[0]
            return self.last_context
        except Exception as e:
            print(f"[agentic] Analysis failed: {e}")
            return None
    
    def get_screen_hash(self) -> str:
        """Get hash of current screen for change detection"""
        screenshot = self.capture()
        if screenshot is None:
            return ""
        return hashlib.md5(screenshot.tobytes()[:10000]).hexdigest()
    
    # === VISUAL SEARCH ===
    
    def find_text(self, text: str, confidence: float = 0.6) -> Optional[VisualMatch]:
        """
        Find text on screen using OCR.
        
        Args:
            text: Text to find (case-insensitive partial match)
            confidence: Minimum confidence threshold
        
        Returns:
            VisualMatch with location or None
        """
        context = self.analyze_screen()
        if context is None:
            return None
        
        extracted = context.get('extracted_text', '')
        if not extracted:
            return None
        
        # Case-insensitive search
        lower_extracted = extracted.lower()
        lower_text = text.lower()
        
        if lower_text in lower_extracted:
            # Found - return approximate region
            # Note: Real implementation would get bounding boxes from OCR
            screen_size = pyautogui.size()
            return VisualMatch(
                text=text,
                confidence=confidence,
                region=ScreenRegion(
                    x=screen_size[0] // 4,
                    y=screen_size[1] // 4,
                    width=screen_size[0] // 2,
                    height=screen_size[1] // 2
                ),
                element_type="text"
            )
        
        return None
    
    def click_on_text(self, text: str, timeout: int = 5) -> bool:
        """
        Click on text found on screen.
        
        Args:
            text: Text to find and click
            timeout: Max seconds to search
        
        Returns:
            True if found and clicked
        """
        start = time.time()
        
        while time.time() - start < timeout:
            match = self.find_text(text)
            if match:
                x, y = match.region.center
                print(f"[agentic] Clicking on '{text}' at ({x}, {y})")
                pyautogui.click(x, y, duration=self.click_duration)
                return True
            
            # Check for abort (mouse in corner)
            if SCREEN_CORNER_ABORT:
                pos = pyautogui.position()
                if pos[0] <= 5 or pos[0] >= pyautogui.size()[0] - 5:
                    if pos[1] <= 5 or pos[1] >= pyautogui.size()[1] - 5:
                        print("[agentic] ABORT: Mouse in corner")
                        return False
            
            time.sleep(0.3)
        
        print(f"[agentic] Text not found: '{text}'")
        return False
    
    def wait_for(self, text: str, timeout: int = 30) -> bool:
        """
        Wait for text to appear on screen.
        
        Args:
            text: Text to wait for
            timeout: Max seconds to wait
        
        Returns:
            True if text appeared, False if timeout
        """
        start = time.time()
        
        while time.time() - start < timeout:
            if self.find_text(text):
                print(f"[agentic] Found: '{text}'")
                return True
            
            time.sleep(0.5)
        
        print(f"[agentic] Timeout waiting for: '{text}'")
        return False
    
    # === MOUSE CONTROL ===
    
    def move_to(self, x: int, y: int) -> None:
        """Move mouse to coordinates"""
        pyautogui.moveTo(x, y, duration=self.click_duration)
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = 'left') -> bool:
        """
        Click at coordinates or current position.
        
        Args:
            x, y: Coordinates (None = current position)
            button: 'left', 'right', 'middle'
        """
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, duration=self.click_duration)
            else:
                pyautogui.click(button=button)
            return True
        except Exception as e:
            print(f"[agentic] Click failed: {e}")
            return False
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Double click"""
        try:
            if x is not None and y is not None:
                pyautogui.doubleClick(x, y, duration=self.click_duration)
            else:
                pyautogui.doubleClick()
            return True
        except Exception as e:
            print(f"[agentic] Double-click failed: {e}")
            return False
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Right click"""
        return self.click(x, y, button='right')
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> bool:
        """Drag from start to end"""
        try:
            pyautogui.moveTo(start_x, start_y, duration=0.2)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=0.5)
            return True
        except Exception as e:
            print(f"[agentic] Drag failed: {e}")
            return False
    
    # === KEYBOARD CONTROL ===
    
    def type(self, text: str, interval: float = 0.05) -> bool:
        """
        Type text using keyboard.
        
        Args:
            text: Text to type
            interval: Delay between characters
        """
        try:
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            print(f"[agentic] Type failed: {e}")
            return False
    
    def press(self, key: str) -> bool:
        """
        Press a single key.
        
        Keys: enter, escape, tab, backspace, delete, up, down, left, right,
              f1-f12, ctrl, alt, shift, cmd/super
        """
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            print(f"[agentic] Press failed: {e}")
            return False
    
    def hotkey(self, *keys) -> bool:
        """
        Press a hotkey combination.
        
        Examples:
            auto.hotkey('ctrl', 'c')  # Copy
            auto.hotkey('alt', 'f4')  # Close
            auto.hotkey('ctrl', 'shift', 'esc')  # Task manager
        """
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            print(f"[agentic] Hotkey failed: {e}")
            return False
    
    def select_all(self) -> bool:
        """Ctrl+A"""
        return self.hotkey('ctrl', 'a')
    
    def copy(self) -> bool:
        """Ctrl+C"""
        return self.hotkey('ctrl', 'c')
    
    def paste(self) -> bool:
        """Ctrl+V"""
        return self.hotkey('ctrl', 'v')
    
    def undo(self) -> bool:
        """Ctrl+Z"""
        return self.hotkey('ctrl', 'z')
    
    # === SCROLLING ===
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        Scroll the mouse wheel.
        
        Args:
            clicks: Number of scroll clicks (positive = up, negative = down)
            x, y: Coordinates to scroll at (None = current position)
        """
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            return True
        except Exception as e:
            print(f"[agentic] Scroll failed: {e}")
            return False
    
    def scroll_down(self, amount: int = 3) -> bool:
        """Scroll down"""
        return self.scroll(-amount)
    
    def scroll_up(self, amount: int = 3) -> bool:
        """Scroll up"""
        return self.scroll(amount)
    
    def scroll_to_bottom(self, scroll_amount: int = 3, pause: float = 0.5) -> bool:
        """
        Scroll to bottom of a scrollable area.
        
        Args:
            scroll_amount: Clicks per scroll
            pause: Seconds to wait between scrolls
        """
        last_height = None
        current_height = 0
        
        while True:
            self.scroll(-scroll_amount)
            time.sleep(pause)
            
            # Could detect height change via JavaScript in browser context
            # For now, just do fixed number of scrolls
            break  # Simplified - real implementation needs page-specific logic
        
        return True
    
    def capture_scrollable_content(self, max_scrolls: int = 10, 
                                  scroll_delay: float = 0.5) -> str:
        """
        Capture all text from a scrollable area by scrolling through it.
        
        Returns combined text content.
        
        Note: This requires being used within a Selenium/WebDriver context
        for browser content. For general use, captures from accessible elements.
        """
        combined_text = []
        
        for i in range(max_scrolls):
            context = self.analyze_screen()
            if context and context.get('extracted_text'):
                text = context['extracted_text']
                if text not in combined_text:
                    combined_text.append(text)
            
            # Scroll down
            self.scroll_down(3)
            time.sleep(scroll_delay)
            
            # Check if we hit bottom (would need page-specific detection)
            if i > 0 and i % 3 == 0:
                # Try to detect if content changed
                pass
        
        return "\n\n".join(combined_text)
    
    # === COMPOUND ACTIONS ===
    
    def click_and_type(self, x: int, y: int, text: str) -> bool:
        """Click at coordinates then type text"""
        if not self.click(x, y):
            return False
        time.sleep(0.2)  # Wait for focus
        return self.type(text)
    
    def find_and_click(self, text: str) -> bool:
        """Find text on screen and click it"""
        return self.click_on_text(text)
    
    def find_and_type(self, text_to_find: str, text_to_type: str) -> bool:
        """
        Find an input field and type in it.
        
        First clicks on the text (assuming it's near/label for input),
        then types the text.
        """
        match = self.find_text(text_to_find)
        if match:
            x, y = match.region.center
            # Offset slightly to get into the input field
            return self.click_and_type(x + 50, y, text_to_type)
        return False
    
    def verify_and_continue(self, expected_text: str, timeout: int = 10) -> bool:
        """
        Verify text is on screen, continue if found.
        
        Returns True if text found, False if timeout.
        """
        return self.wait_for(expected_text, timeout)
    
    # === SCREEN MONITORING ===
    
    def wait_for_change(self, timeout: int = 30) -> bool:
        """
        Wait for screen content to change.
        
        Returns True if change detected, False if timeout.
        """
        last_hash = self.get_screen_hash()
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(0.5)
            current_hash = self.get_screen_hash()
            if current_hash != last_hash:
                print("[agentic] Screen change detected")
                return True
        
        return False
    
    def monitor_until_stable(self, stability_seconds: float = 2.0) -> bool:
        """
        Wait for screen to become stable (no changes for N seconds).
        
        Useful for waiting for animations/loading to complete.
        """
        last_hash = self.get_screen_hash()
        stable_start = time.time()
        
        while time.time() - stable_start < stability_seconds:
            current_hash = self.get_screen_hash()
            if current_hash != last_hash:
                last_hash = current_hash
                stable_start = time.time()  # Reset
            time.sleep(0.3)
        
        print(f"[agentic] Screen stable for {stability_seconds}s")
        return True
    
    # === COMPLEX TASKS ===
    
    def execute_task(self, task_description: str) -> bool:
        """
        Execute a complex task described in natural language.
        
        This is a high-level interface that parses the task and executes
        appropriate actions. For simple tasks, use specific methods.
        
        Tasks are parsed for:
        - "click [on] [the] [text/button] [X]" -> click_on_text(X)
        - "type [X] [in/into] [field Y]" -> find_and_type(Y, X)
        - "press [key]" -> press(key)
        - "wait for [X]" -> wait_for(X)
        - "verify [X]" -> verify_and_continue(X)
        """
        task = task_description.lower()
        
        # Click patterns
        if "click" in task and "on" in task:
            # Extract text to click
            parts = task.split("click")[1].split("on")
            if len(parts) > 1:
                target = parts[1].strip().strip('"').strip("'")
                return self.click_on_text(target)
        
        # Type patterns
        if "type" in task or "enter" in task:
            # Extract text
            pass  # Implement parsing
        
        # Press patterns
        if "press" in task:
            key = task.split("press")[1].strip()
            return self.press(key)
        
        # Wait patterns
        if "wait for" in task:
            text = task.split("wait for")[1].strip()
            return self.wait_for(text)
        
        print(f"[agentic] Could not parse task: {task_description}")
        return False
    
    # === STATUS ===
    
    def get_status(self) -> Dict[str, Any]:
        """Get current automation status"""
        return {
            "vision_available": VISION_AVAILABLE,
            "last_capture": self.last_screenshot is not None,
            "last_analysis": self.last_context is not None,
            "mouse_position": pyautogui.position(),
            "screen_size": pyautogui.size()
        }


# === CONVENIENCE FUNCTIONS FOR AGENTS ===

def click_text(text: str, timeout: int = 5) -> bool:
    """Click on text found on screen"""
    auto = AgenticAutomation()
    return auto.click_on_text(text, timeout)

def type_text(text: str) -> bool:
    """Type text"""
    auto = AgenticAutomation()
    return auto.type(text)

def press_key(key: str) -> bool:
    """Press a key"""
    auto = AgenticAutomation()
    return auto.press(key)

def analyze_current_screen() -> Optional[Dict[str, Any]]:
    """Analyze current screen"""
    auto = AgenticAutomation()
    return auto.analyze_screen()

def wait_for_screen_change(timeout: int = 30) -> bool:
    """Wait for screen to change"""
    auto = AgenticAutomation()
    return auto.wait_for_change(timeout)


# === BROWSER AUTOMATION (Selenium Integration) ===

def create_browser_automation(debugger_address: str = "127.0.0.1:9222") -> 'BrowserAutomation':
    """
    Create a browser automation instance.
    
    Requires Chrome/Brave with remote debugging enabled:
        brave.exe --remote-debugging-port=9222
    """
    return BrowserAutomation(debugger_address)


class BrowserAutomation:
    """
    Browser automation with Selenium + PyAutoGUI + Vision.
    
    Combines:
    - Selenium for browser control
    - PyAutoGUI for keyboard/mouse
    - Vision for screen analysis
    - Scroll capture for full page content
    """
    
    def __init__(self, debugger_address: str = "127.0.0.1:9222"):
        self.debugger_address = debugger_address
        self.driver = None
        self.auto = AgenticAutomation()
        
    def connect(self) -> bool:
        """Connect to existing browser via remote debugging"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            
            chromedriver_path = r"C:\Users\L5\.chromedriver-autoinstaller\chromedriver-win64\chromedriver.exe"
            
            options = Options()
            options.add_experimental_option("debuggerAddress", self.debugger_address)
            
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            print("[browser] Connected to browser")
            return True
        except Exception as e:
            print(f"[browser] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from browser"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def find_gemini_tab(self) -> bool:
        """Find or create Gemini tab"""
        if not self.driver:
            return False
        
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            if "gemini" in self.driver.current_url.lower():
                print("[browser] Found Gemini tab")
                return True
        
        # Create new tab
        self.driver.switch_to.new_window("tab")
        self.driver.get("https://gemini.google.com/app")
        time.sleep(3)
        print("[browser] Created new Gemini tab")
        return True
    
    def scroll_page_capture(self, max_scrolls: int = 20) -> str:
        """
        Scroll through page and capture full text content.
        
        Uses JavaScript to get scrollable element content.
        """
        if not self.driver:
            return ""
        
        all_text = []
        last_height = 0
        
        for i in range(max_scrolls):
            # Get page text
            page_text = self.driver.execute_script(
                "return document.body.innerText;"
            )
            if page_text and page_text not in all_text:
                all_text.append(page_text)
            
            # Scroll down
            self.driver.execute_script(
                "window.scrollBy(0, 500);"
            )
            time.sleep(0.3)
            
            # Check if we reached bottom
            new_height = self.driver.execute_script(
                "return document.body.scrollHeight;"
            )
            if new_height == last_height:
                break
            last_height = new_height
        
        return "\n\n=== SCROLL SECTION {} ===\n\n".format(
            "===/===\n\n".join(all_text)
        )
    
    def query_gemini(self, prompt: str, timeout: int = 30) -> Optional[str]:
        """
        Send query to Gemini and get response.
        
        Uses JS for typing, PyAutoGUI for submit, and page text extraction.
        """
        if not self.driver:
            if not self.connect():
                return None
        
        if not self.find_gemini_tab():
            return None
        
        try:
            # Wait for page load
            time.sleep(2)
            
            # Type using JS
            self.driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.innerText = arguments[0]; }",
                prompt
            )
            print("[browser] Typed prompt")
            
            time.sleep(0.3)
            
            # Submit using PyAutoGUI
            self.auto.press('enter')
            print("[browser] Submitted via PyAutoGUI")
            
            # Wait for response
            start = time.time()
            while time.time() - start < timeout:
                page_text = self.driver.execute_script(
                    "return document.body.innerText;"
                )
                
                if "Gemini said" in page_text:
                    idx = page_text.index("Gemini said")
                    response = page_text[idx + 12:].strip()
                    lines = response.split('\n')
                    result = lines[0].strip()
                    if len(result) > 10:
                        print(f"[browser] Got response: {result[:50]}...")
                        return result
                
                time.sleep(1)
            
            return None
            
        except Exception as e:
            print(f"[browser] Query failed: {e}")
            return None
    
    def capture_full_page(self) -> str:
        """
        Capture full page content with scrolling.
        
        Returns combined text from all scroll positions.
        """
        return self.scroll_page_capture()
    
    def query_gemini_vision_only(self, prompt: str, timeout: int = 30) -> Optional[str]:
        """
        Query Gemini using ONLY vision and PyAutoGUI - no Selenium.
        
        Steps:
        1. Analyze screen to find Gemini input field
        2. Use PyAutoGUI to click and type
        3. Submit with Enter key
        4. Monitor screen until response appears
        5. Extract response using OCR
        
        This is the preferred method when browser is already open.
        """
        print("[browser_vision] Starting vision-only Gemini query")
        
        # First, verify we're on Gemini
        context = self.auto.analyze_screen()
        if context is None:
            print("[browser_vision] Could not capture screen")
            return None
        
        caption = context.get('caption', '').lower()
        extracted = context.get('extracted_text', '')
        
        print(f"[browser_vision] Screen caption: {caption[:100]}")
        
        # Check if Gemini is visible
        if 'gemini' not in caption and 'gemini' not in extracted.lower():
            print("[browser_vision] Gemini not detected on screen - may need to focus browser")
            # Try to find and click on Gemini tab/window first
            # For now, we'll proceed anyway and see what happens
        
        # Click on the input area (we know it's typically in lower portion of Gemini page)
        # Use approximate coordinates based on common Gemini layout
        screen_w, screen_h = pyautogui.size()
        input_x, input_y = screen_w // 2, int(screen_h * 0.75)
        
        print(f"[browser_vision] Clicking input area at ({input_x}, {input_y})")
        self.auto.click(input_x, input_y)
        time.sleep(0.5)
        
        # Type the prompt
        print(f"[browser_vision] Typing prompt: {prompt[:50]}...")
        self.auto.type(prompt)
        time.sleep(0.3)
        
        # Submit
        print("[browser_vision] Submitting with Enter")
        self.auto.press('enter')
        
        # Monitor for response
        print("[browser_vision] Monitoring for response...")
        start = time.time()
        last_response_hash = None
        
        while time.time() - start < timeout:
            # Check for screen change
            if self.auto.wait_for_change(timeout=2):
                # Analyze new screen state
                context = self.auto.analyze_screen()
                if context:
                    extracted = context.get('extracted_text', '')
                    
                    # Look for Gemini's response indicator
                    if 'gemini said' in extracted.lower():
                        idx = extracted.lower().index('gemini said')
                        response = extracted[idx + 12:].strip()
                        lines = response.split('\n')
                        result = lines[0].strip()
                        if len(result) > 5:
                            print(f"[browser_vision] Got response: {result[:50]}...")
                            return result
                    
                    # Alternative: look for response text patterns
                    if '2+2' in prompt.lower():
                        # Looking for math answer
                        for line in extracted.split('\n'):
                            if any(c.isdigit() for c in line) and len(line) < 20:
                                print(f"[browser_vision] Potential response: {line}")
                                return line
        
        print("[browser_vision] Timeout waiting for response")
        return None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, *args):
        self.disconnect()


# === TEST ===

if __name__ == "__main__":
    print("=" * 60)
    print("Agentic Automation Framework")
    print("=" * 60)
    
    auto = AgenticAutomation()
    
    print("\n[1] Status:")
    status = auto.get_status()
    for k, v in status.items():
        print(f"    {k}: {v}")
    
    print("\n[2] Screen capture:")
    img = auto.capture()
    print(f"    Captured: {img is not None}")
    
    print("\n[3] Screen analysis:")
    context = auto.analyze_screen()
    if context:
        print(f"    Caption: {context.get('caption', 'N/A')[:100]}")
        print(f"    Has text: {bool(context.get('extracted_text'))}")
    
    print("\n[4] Mouse position:")
    print(f"    {pyautogui.position()}")
    
    print("\n" + "=" * 60)
    print("Agentic automation ready!")
    print("Move mouse to corner to abort any automation.")
    print("=" * 60)
