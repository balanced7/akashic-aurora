"""
Gemini Bridge Monitor - Robust browser monitoring with vision feedback
===================================================================
Monitors the Gemini tab and detects crashes using Selenium + Vision Engine.
"""

import sys
import time
import traceback
sys.path.insert(0, r'E:\AI-Setup')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from vision_engine import capture_active_window, get_screen_context_for_analyst


CHROMEDRIVER_PATH = r"C:\Users\L5\.chromedriver-autoinstaller\chromedriver-win64\chromedriver.exe"
DEBUGGING_PORT = "127.0.0.1:9222"
DEFAULT_TIMEOUT = 5


class GeminiBridgeMonitor:
    """
    Robust Gemini bridge with crash detection and vision monitoring.
    """
    
    def __init__(self):
        self.driver = None
        self.gemini_handle = None
        self.crashed = False
    
    def connect(self) -> bool:
        """Connect to existing Brave via remote debugging"""
        try:
            options = Options()
            options.add_experimental_option("debuggerAddress", DEBUGGING_PORT)
            
            service = Service(executable_path=CHROMEDRIVER_PATH)
            self.driver = webdriver.Chrome(service=service, options=options)
            print("[monitor] Connected to Brave")
            return True
        except Exception as e:
            print(f"[monitor] Failed to connect: {e}")
            return False
    
    def find_or_create_gemini_tab(self) -> bool:
        """Find existing Gemini tab or create new one"""
        if not self.driver:
            return False
        
        try:
            handles = self.driver.window_handles
            for handle in handles:
                self.driver.switch_to.window(handle)
                if "gemini" in self.driver.current_url.lower():
                    self.gemini_handle = handle
                    print("[monitor] Found existing Gemini tab")
                    return True
            
            # Create new tab
            print("[monitor] Creating new Gemini tab...")
            self.driver.switch_to.new_window("tab")
            time.sleep(2)
            self.driver.get("https://gemini.google.com/app")
            time.sleep(5)
            self.gemini_handle = self.driver.current_window_handle
            print("[monitor] New Gemini tab created")
            return True
            
        except Exception as e:
            print(f"[monitor] Failed to find/create tab: {e}")
            return False
    
    def verify_page_loaded(self) -> bool:
        """Verify Gemini page is loaded using vision engine"""
        if not self.driver:
            return False
        
        try:
            # Check URL
            if "data:" in self.driver.current_url or self.driver.current_url == "http://data/":
                print("[monitor] Page crashed (URL is data:)")
                self.crashed = True
                return False
            
            # Try to find input box
            wait = WebDriverWait(self.driver, 10)
            input_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']"))
            )
            print("[monitor] Gemini page loaded successfully")
            return True
            
        except Exception as e:
            print(f"[monitor] Page verification failed: {e}")
            self.crashed = True
            return False
    
    def capture_state(self) -> dict:
        """Capture current browser state for diagnosis"""
        try:
            screenshot = capture_active_window()
            context = get_screen_context_for_analyst(screenshot)
            return context
        except Exception as e:
            print(f"[monitor] Failed to capture state: {e}")
            return {"error": str(e)}
    
    def query(self, prompt: str, timeout: int = 30) -> tuple:
        """
        Send query to Gemini with monitoring.
        
        Returns:
            tuple: (response_text or None, crash_detected: bool)
        """
        if not self.driver:
            if not self.connect():
                return None, False
        
        # Find or create Gemini tab
        if not self.find_or_create_gemini_tab():
            return None, False
        
        self.driver.switch_to.window(self.gemini_handle)
        
        # Check for crash before querying
        if "data:" in self.driver.current_url:
            print("[monitor] Tab crashed before query")
            self.crashed = True
            return None, True
        
        try:
            # Wait for input box
            wait = WebDriverWait(self.driver, 15)
            input_box = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='textbox']"))
            )
            
            # Clear and type prompt
            input_box.clear()
            input_box.send_keys(prompt)
            print("[monitor] Prompt sent")
            
            # Submit
            input_box.send_keys("\n")
            print("[monitor] Waiting for response...")
            
            # Poll for response
            start = time.time()
            while time.time() - start < timeout:
                # Check for crash
                if "data:" in self.driver.current_url:
                    print("[monitor] CRASH DETECTED during response wait!")
                    self.crashed = True
                    context = self.capture_state()
                    return None, True
                
                # Look for response
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "div.model-response-text")
                    if elements:
                        text = elements[-1].text
                        if len(text) > 10:
                            print(f"[monitor] Response received: {text[:50]}...")
                            return text, False
                except:
                    pass
                
                time.sleep(1)
            
            print("[monitor] Timeout waiting for response")
            return None, False
            
        except Exception as e:
            print(f"[monitor] Query failed: {e}")
            traceback.print_exc()
            self.crashed = True
            return None, True
    
    def is_alive(self) -> bool:
        """Check if the bridge is still responsive"""
        if not self.driver:
            return False
        
        try:
            # Simple check - can we get the window handles?
            _ = self.driver.window_handles
            return True
        except:
            return False
    
    def disconnect(self):
        """Disconnect from browser (don't close tabs)"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None


def test_gemini_bridge():
    """Test the Gemini bridge with monitoring"""
    print("=" * 60)
    print("Gemini Bridge Monitor Test")
    print("=" * 60)
    
    bridge = GeminiBridgeMonitor()
    
    try:
        if not bridge.connect():
            print("Failed to connect")
            return
        
        # Test query
        print("\n[Test 1] Sending test query...")
        response, crashed = bridge.query("Say 'Gemini Bridge working' in exactly those words", timeout=10)
        
        if crashed:
            print("Crash detected during query")
            context = bridge.capture_state()
            print("Captured state for diagnosis")
        elif response:
            print("SUCCESS:", response[:100])
        else:
            print("No response")
        
        print("\n[Test 2] Testing alive check...")
        alive = bridge.is_alive()
        print(f"Bridge alive: {alive}")
        
    finally:
        bridge.disconnect()


if __name__ == "__main__":
    test_gemini_bridge()
