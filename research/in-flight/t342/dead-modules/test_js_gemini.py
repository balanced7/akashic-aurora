import sys
sys.path.insert(0, r'E:\AI-Setup')
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

chromedriver_path = r"C:\Users\L5\.chromedriver-autoinstaller\chromedriver-win64\chromedriver.exe"

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
options.add_argument("--disable-blink-features=AutomationControlled")

service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

try:
    print("[1] Connected")
    
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        if "gemini" in driver.current_url.lower():
            driver.get("https://gemini.google.com/app")
            time.sleep(3)
            print("[2] URL:", driver.current_url)
            
            ready = driver.execute_script("return document.readyState")
            print("[3] Ready state:", ready)
            
            result = driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.focus(); return \"input_found\"; }"
                "return \"input_not_found\";"
            )
            print("[4] JS result:", result)
            
            driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.innerText = \"Hello, what is 2+2?\"; }"
            )
            print("[5] Typed via JS")
            
            time.sleep(1)
            
            driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.dispatchEvent(new KeyboardEvent(\"keydown\", {key: \"Enter\", keyCode: 13})); }"
            )
            print("[6] Submitted via JS")
            
            time.sleep(8)
            print("[7] URL after wait:", driver.current_url)
            print("[8] Title:", driver.title)
            
            response = driver.execute_script(
                "var els = document.querySelectorAll(\"div.model-response-text\");"
                "if (els.length > 0) { return els[els.length-1].innerText; }"
                "return \"no_response\";"
            )
            print("[9] Response:", response[:100] if len(response) > 100 else response)
            
            break
    
    driver.quit()
    print("[10] Done")
except Exception as e:
    print("Error:", str(e)[:300])
    try:
        driver.quit()
    except:
        pass
