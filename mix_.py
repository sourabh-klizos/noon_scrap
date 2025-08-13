import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pymongo import MongoClient

# --- MongoDB Setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["noon_scrap"]
source_collection = db["noon_seller_db"]  # URLs to scrape
target_collection = db["noon_seller_full_details"]

# --- Chrome Options ---
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
# options.add_argument("--headless=new")  # Uncomment for headless

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

# --- Loop through URLs ---
for doc in source_collection.find():
    url = doc.get("url")
    if not url:
        print("❌ Skipping document without 'url'")
        continue

    print(f"\n🔗 Opening URL: {url}")
    try:
        driver.get(url)
        time.sleep(5)  # Let page load fully

        # --- Get full HTML from Selenium ---
        html = driver.page_source

        # --- Parse with BeautifulSoup ---
        soup = BeautifulSoup(html, "html.parser")

        seller_data_list = []
        seller_ids = set()

        # Find all hrefs that contain p_xxx
        for a in soup.find_all("a", href=True):
            matches = re.findall(r"p_\d+", a["href"])
            for m in matches:
                if m not in seller_ids:
                    seller_ids.add(m)
                    seller_doc = {
                        "partner_id": m,
                        "source_url": url,
                        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    seller_data_list.append(seller_doc)
                    print(f"🛒 Found Seller Partner ID: {m}")

        if seller_data_list:
            target_collection.insert_many(seller_data_list)
            print(f"💾 Inserted {len(seller_data_list)} seller IDs into MongoDB from {url}")
        else:
            print("⚠️ No seller data found.")

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

driver.quit()
print("\n✅ Scraping completed & browser closed.")
