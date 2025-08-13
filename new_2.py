from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import time

# --- Chrome Options ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--headless=new")  # Comment this if you want to see browser

# --- Init Driver ---
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- Apply Stealth ---
stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
        )

urls = [
    "https://www.noon.com/uae-en/samsung-galaxy-ai/",
    "https://www.noon.com/uae-en/apple-mobiles/?sort%5Bby%5D=popularity&sort%5Bdir%5D=desc"
]

for url in urls:
    print(f"Opening URL: {url}")
    try:
        driver.get(url)
        time.sleep(5)  # Let page load fully

        sellers = driver.find_elements(By.CSS_SELECTOR, "a.CheckboxOption_container__ZOrNu")

        for s in sellers:
            href = s.get_attribute("href")
            label = s.find_element(By.CSS_SELECTOR, "label")
            checkbox_input = label.find_element(By.TAG_NAME, "input")
            seller_id = checkbox_input.get_attribute("id")
            seller_name = label.find_element(By.CSS_SELECTOR, ".MultiOptionFilter_text__Ysy2U").text.strip()

            print(seller_id, seller_name, href)

    except Exception as e:
        print(f"Error scraping {url}: {e}")

driver.quit()
