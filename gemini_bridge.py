"""
Gemini Bridge - Remote Debugging Automation
========================================
Uses Chrome DevTools Protocol directly to query Gemini without API keys.

This script uses Remote Debugging to attach to an already-open Brave window.
This is the preferred method because:
1. No "Profile in Use" error
2. Uses your existing authenticated session
3. Zero performance impact

Usage:
    # First, launch Brave with debugging:
    # brave.exe --remote-debugging-port=9222
    
    # Then in Python:
    from gemini_bridge import query_active_session
    response = query_active_session({"problem": "OCR failing"})
"""

import os
import sys
import time
import json
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# Optional imports
try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("[gemini_bridge] websocket-client not installed. Run: pip install websocket-client")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[gemini_bridge] Selenium not installed. Run: pip install selenium")

# Constants
GEMINI_URL = "https://gemini.google.com/app"
DEBUGGING_PORT = "127.0.0.1:9222"
DEBUGGING_URL = f"http://{DEBUGGING_PORT}"
DEFAULT_TIMEOUT = 5  # 5 seconds max to determine bridge failure


class CDPBridge:
    """
    Chrome DevTools Protocol bridge for Gemini.
    
    Uses CDP directly via HTTP/WebSocket instead of Selenium.
    Works with Brave remote debugging without chromedriver version issues.
    """
    
    def __init__(self, debugging_address: str = DEBUGGING_URL):
        self.debugging_address = debugging_address
        self.ws_url = None
        self.ws = None
    
    def connect(self) -> bool:
        """Get CDP websocket URL from debugging endpoint"""
        try:
            req = urllib.request.Request(f"{self.debugging_address}/json")
            with urllib.request.urlopen(req, timeout=5) as response:
                pages = json.loads(response.read())
                
            for page in pages:
                if "gemini.google.com" in page.get("url", ""):
                    self.ws_url = page.get("webSocketDebuggerUrl")
                    if self.ws_url:
                        print(f"[cdp_bridge] Found Gemini page")
                        return True
            
            if pages:
                self.ws_url = pages[0].get("webSocketDebuggerUrl")
                print(f"[cdp_bridge] Using first available page")
                return bool(self.ws_url)
            
            return False
        except Exception as e:
            print(f"[cdp_bridge] Failed to connect: {e}")
            return False
    
    def health_check(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """Fast health check - verify CDP endpoint is responsive"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                req = urllib.request.Request(f"{self.debugging_address}/json")
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False
    
    def query(self, prompt: str, timeout: int = 30, fast_fail: int = DEFAULT_TIMEOUT) -> Optional[str]:
        """
        Query Gemini via CDP by injecting JavaScript.
        """
        try:
            import websocket
            
            if not self.ws_url:
                if not self.connect():
                    return None
            
            ws = websocket.create_connection(self.ws_url, timeout=10)
            
            # Navigate to Gemini
            navigate_cmd = json.dumps({
                "id": 1,
                "method": "Page.navigate",
                "params": {"url": GEMINI_URL}
            })
            ws.send(navigate_cmd)
            
            # Wait for page load
            time.sleep(2)
            
            # Find input and type prompt
            escaped_prompt = prompt.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            
            # Click on input area first
            click_cmd = json.dumps({
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {"expression": "document.querySelector('div[role=\"textbox\"]')?.click()", "returnByValue": True}
            })
            ws.send(click_cmd)
            time.sleep(0.5)
            
            # Type using keyboard events
            type_cmd = json.dumps({
                "id": 3,
                "method": "Runtime.evaluate",
                "params": {"expression": f"document.querySelector('div[role=\"textbox\"]')?.focus()", "returnByValue": True}
            })
            ws.send(type_cmd)
            time.sleep(0.5)
            
            # Use clipboard to paste (more reliable)
            paste_cmd = json.dumps({
                "id": 4,
                "method": "Runtime.evaluate",
                "params": {"expression": f"""
                    (function() {{
                        var input = document.querySelector('div[role=\"textbox\"]');
                        if (!input) return 'no_input';
                        
                        // Create a paste event with the text
                        var text = `{escaped_prompt}`;
                        navigator.clipboard.writeText(text);
                        input.focus();
                        
                        // Simulate Ctrl+V
                        var pasteEvent = new KeyboardEvent('keydown', {{key: 'v', keyCode: 86, ctrlKey: true}});
                        input.dispatchEvent(pasteEvent);
                        
                        return 'pasted';
                    }})()
                """, "returnByValue": True}
            })
            ws.send(paste_cmd)
            time.sleep(1)
            
            # Press Enter
            enter_cmd = json.dumps({
                "id": 5,
                "method": "Runtime.evaluate",
                "params": {"expression": "var evt = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13}); document.querySelector('div[role=\"textbox\"]')?.dispatchEvent(evt)", "returnByValue": True}
            })
            ws.send(enter_cmd)
            
            # Poll for response
            start = time.time()
            last_response = None
            
            while time.time() - start < timeout:
                ws.settimeout(1)
                try:
                    msg = ws.recv()
                    data = json.loads(msg)
                    
                    # Look for response content in page
                    check_cmd = json.dumps({
                        "id": 100,
                        "method": "Runtime.evaluate",
                        "params": {"expression": """
                            (function() {
                                var responses = document.querySelectorAll('div.model-response-text, div[class*="response"], article');
                                if (responses && responses.length > 0) {
                                    return responses[responses.length - 1].innerText;
                                }
                                return null;
                            })()
                        """, "returnByValue": True}
                    })
                    ws.send(check_cmd)
                    
                    result = ws.recv()
                    result_data = json.loads(result)
                    if result_data.get('result', {}).get('result'):
                        text = result_data['result']['result']['value']
                        if text and len(text) > 20:
                            ws.close()
                            return text
                except Exception as e:
                    pass
            
            ws.close()
            return last_response
            
        except Exception as e:
            print(f"[cdp_bridge] Query failed: {e}")
            return None
    
    def disconnect(self):
        """Close websocket if open"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None


class GeminiBridgeRemote:
    """
    Remote debugging bridge to Gemini.
    
    Attaches to an already-open Brave window via remote debugging port.
    Does NOT close the browser when done - preserves your session.
    """
    
    def __init__(self, debugging_address: str = DEBUGGING_PORT):
        self.debugging_address = debugging_address
        self.driver = None
    
    def connect(self) -> bool:
        """Connect to existing Brave via remote debugging"""
        if not SELENIUM_AVAILABLE:
            print("[gemini_bridge] Selenium not available")
            return False
        
        try:
            from selenium.webdriver.chrome.service import Service
            
            chromedriver_path = r"C:\Users\L5\.chromedriver-autoinstaller\chromedriver-win64\chromedriver.exe"
            
            options = Options()
            options.add_experimental_option("debuggerAddress", self.debugging_address)
            
            service = Service(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            print("[gemini_bridge] Connected to Brave via remote debugging")
            return True
            
        except Exception as e:
            print(f"[gemini_bridge] Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect WITHOUT closing browser"""
        if self.driver:
            try:
                # Don't quit() - we want to keep the browser open
                self.driver.close()
            except:
                pass
            self.driver = None

    def health_check(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Fast health check - verifies bridge is responsive within N seconds.
        
        Returns True if we can communicate with Gemini within timeout.
        Returns False if bridge is unresponsive (allows fail-fast).
        
        This prevents getting stuck waiting for a response that never comes.
        """
        if not self.driver:
            if not self.connect():
                return False
        
        start = time.time()
        try:
            # Check if we can navigate to Gemini
            self.driver.get(GEMINI_URL)
            
            # Wait for page to load (check every 0.5s)
            while time.time() - start < timeout:
                if "gemini.google.com" in self.driver.current_url:
                    return True
                time.sleep(0.5)
            
            return False
        except Exception as e:
            print(f"[gemini_bridge] Health check failed: {e}")
            return False
    
    def _find_input_box(self):
        """Find the Gemini input box"""
        if not self.driver:
            return None
        
        # Try multiple selectors for different Gemini UI versions
        selectors = [
            "div[role='textbox']",
            "textarea[name='message']", 
            "div[contenteditable='true']",
            "input[placeholder*='message']",
            "input[type='text']"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    print(f"[gemini_bridge] Found input: {selector}")
                    return element
            except:
                continue
        
        return None
    
    def _find_response(self) -> Optional[str]:
        """Find the latest Gemini response"""
        if not self.driver:
            return None
        
        selectors = [
            "div.model-response-text",
            "div[class*='response']",
            "div[class*='content']",
            "article",
            "div[role='region']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Get last (most recent) response
                    text = elements[-1].text
                    if len(text) > 20:
                        return text
            except:
                continue
        
        return None
    
    def query(self, prompt: str, timeout: int = 30, fast_fail: int = DEFAULT_TIMEOUT) -> Optional[str]:
        """
        Send query to Gemini and get response.
        
        Uses JavaScript execution instead of Selenium element interaction
        to avoid crashes with React-based Gemini UI.
        
        Args:
            prompt: The prompt to send
            timeout: Maximum wait time for full response
            fast_fail: Max seconds to wait for INITIAL response before bailing
        
        Returns:
            Gemini's response text or None if failed
        """
        if not self.driver:
            if not self.connect():
                return None
        
        try:
            # Find or navigate to Gemini tab
            gemini_handle = None
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "gemini" in self.driver.current_url.lower():
                    gemini_handle = handle
                    break
            
            if not gemini_handle:
                self.driver.switch_to.new_window("tab")
                self.driver.get(GEMINI_URL)
                time.sleep(3)
                gemini_handle = self.driver.current_window_handle
            else:
                self.driver.switch_to.window(gemini_handle)
                self.driver.get(GEMINI_URL)
                time.sleep(2)
            
            print("[gemini_bridge] Waiting for page load...")
            
            # Wait for page to be ready
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            # Type prompt using JavaScript (more reliable than Selenium.send_keys)
            self.driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.innerText = arguments[0]; }",
                prompt
            )
            print("[gemini_bridge] Typed prompt via JS")
            
            time.sleep(0.5)
            
            # Submit using PyAutoGUI (more reliable than JS events)
            import pyautogui
            pyautogui.press('enter')
            print("[gemini_bridge] Submitted query via PyAutoGUI, waiting for response...")
            
            # Poll for response with vision monitoring
            start = time.time()
            response = None
            last_page_text = ""
            
            while time.time() - start < timeout:
                # Check if page crashed
                if "data:" in self.driver.current_url:
                    print("[gemini_bridge] Page crashed!")
                    return None
                
                # Get response from page text
                page_text = self.driver.execute_script(
                    "var text = document.body.innerText || '';"
                    "return text;"
                )
                
                # Check if Gemini said something new
                if "Gemini said" in page_text and page_text != last_page_text:
                    idx = page_text.index("Gemini said")
                    response_candidate = page_text[idx + 12:].strip()
                    lines = response_candidate.split('\n')
                    response = lines[0].strip() if lines else response_candidate
                    if len(response) > 10 and response != last_page_text:
                        print(f"[gemini_bridge] Response received ({len(response)} chars)")
                        return response
                    last_page_text = page_text
                
                time.sleep(1)
            
            print("[gemini_bridge] Timeout waiting for response")
            return None
            
        except Exception as e:
            print(f"[gemini_bridge] Query failed: {e}")
            return None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close browser - just detach
        self.disconnect()


class GeminiBridgeNew:
    """
    Launches a NEW Brave instance (fallback if remote debugging unavailable).
    """
    
    def __init__(
        self,
        brave_path: str = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        headless: bool = True
    ):
        self.brave_path = brave_path
        self.headless = headless
        self.driver = None
    
    def connect(self) -> bool:
        """Launch new Brave instance"""
        if not SELENIUM_AVAILABLE:
            return False
        
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            options.binary_location = self.brave_path
            options.add_argument("--user-data-dir=C:\\Users\\l5\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")
            options.add_argument("--profile-directory=Default")
            
            if self.headless:
                options.add_argument("--headless=new")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("[gemini_bridge] Launched new Brave session")
            return True
            
        except Exception as e:
            print(f"[gemini_bridge] Failed to launch: {e}")
            return False
    
    def disconnect(self):
        """Close the browser we opened"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def health_check(self, timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Fast health check - verifies bridge is responsive within N seconds.
        """
        if not self.driver:
            if not self.connect():
                return False
        
        start = time.time()
        try:
            self.driver.get(GEMINI_URL)
            
            while time.time() - start < timeout:
                if "gemini.google.com" in self.driver.current_url:
                    return True
                time.sleep(0.5)
            
            return False
        except Exception as e:
            print(f"[gemini_bridge] Health check failed: {e}")
            return False
    
    def query(self, prompt: str, timeout: int = 30, fast_fail: int = DEFAULT_TIMEOUT) -> Optional[str]:
        """Send query - same interface as GeminiBridgeRemote"""
        if not self.driver:
            if not self.connect():
                return None
        
        try:
            self.driver.get(GEMINI_URL)
            time.sleep(2)
            
            # Find input
            wait = WebDriverWait(self.driver, 10)
            input_box = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
            )
            
            input_box.clear()
            input_box.send_keys(prompt)
            input_box.send_keys("\n")
            
            print("[gemini_bridge] Waiting for response...")
            
            # FAST FAIL: Check for initial response within fast_fail seconds
            start = time.time()
            initial_response_received = False
            
            while time.time() - start < fast_fail:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "div.model-response-text")
                    if elements:
                        response = elements[-1].text
                        if len(response) > 10:
                            initial_response_received = True
                            print("[gemini_bridge] Initial response detected")
                            break
                except:
                    pass
                time.sleep(0.5)
            
            if not initial_response_received:
                print(f"[gemini_bridge] No response within {fast_fail}s - bailing out")
                return None
            
            # Continue polling for full response
            for _ in range(timeout // 2):
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "div.model-response-text")
                    if elements:
                        response = elements[-1].text
                        if len(response) > 10:
                            return response
                except:
                    pass
                time.sleep(2)
            
            return None
            
        except Exception as e:
            print(f"[gemini_bridge] Query failed: {e}")
            return None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# Convenience functions
def query_active_session(payload_json: Dict[str, Any]) -> Optional[str]:
    """
    Connect to already-open Brave and query Gemini.
    
    This is the preferred method. Requires Brave to be running with:
        brave.exe --remote-debugging-port=9222 --remote-allow-origins=*
    
    Uses Selenium with chromedriver-autoinstaller for version matching.
    Uses 5-second fast_fail to prevent hanging.
    """
    prompt = f"""SENIOR ARCHITECT REVIEW REQUIRED

Hardware: {payload_json.get('hardware', 'AMD 9950X3D + 9070 XT')}

Issue: {payload_json.get('problem', 'Unknown')}

Vision Analysis: {json.dumps(payload_json.get('vision_grounding', {}), indent=2)}

Local Attempt: {payload_json.get('local_attempt', 'None')}

Task: Provide an architectural strategy for the local Analyst.
"""
    
    # Use Selenium with manually downloaded chromedriver
    try:
        with GeminiBridgeRemote() as bridge:
            return bridge.query(prompt, fast_fail=DEFAULT_TIMEOUT)
    except Exception as e:
        print(f"[gemini_bridge] Session failed: {e}")
        return None


def query_new_session(prompt: str) -> Optional[str]:
    """Fallback: Launch new Brave and query"""
    try:
        with GeminiBridgeNew(headless=True) as bridge:
            return bridge.query(prompt)
    except Exception as e:
        print(f"[gemini_bridge] New session failed: {e}")
        return None


def query_gemini_architect(payload_json: Dict[str, Any]) -> Optional[str]:
    """
    Query Gemini as Senior Architect.
    
    Tries remote debugging first, falls back to new browser.
    """
    return query_active_session(payload_json) or query_new_session(str(payload_json))


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("Gemini Bridge Test (Remote Debugging)")
    print("=" * 60)
    
    print("\n[!] IMPORTANT: First run Brave with remote debugging:")
    print("    brave.exe --remote-debugging-port=9222")
    print()
    
    if not SELENIUM_AVAILABLE:
        print("Selenium not installed. Run: pip install selenium webdriver-manager")
        sys.exit(1)
    
    print("\n[1] Testing remote connection...")
    bridge = GeminiBridgeRemote()
    
    if bridge.connect():
        print("    Connected OK")
        
        print("\n[2] Testing query...")
        response = bridge.query("Say 'Gemini Bridge working' in exactly those words")
        
        if response:
            print(f"    Response: {response[:200]}...")
        else:
            print("    No response (timeout or no input found)")
        
        bridge.disconnect()
    else:
        print("    Remote connection failed")
        print("\n[2] Trying new session fallback...")
        
        response = query_new_session("Say 'Fallback working'")
        if response:
            print(f"    Fallback response: {response[:200]}...")
    
    print("\n" + "=" * 60)
    print("Gemini Bridge test complete")
    print("=" * 60)
