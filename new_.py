from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import time

# --- MongoDB Setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["noon_scrap"]
source_collection = db["noon_seller_db"]  # original URLs
target_collection = db["noon_seller_details"]  # seller details

# --- Selenium Setup ---
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")  # avoids maximize_window issue
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

try:
    for doc in source_collection.find():
        url = doc.get("url")
        if not url:
            print("❌ Skipping document without 'url'")
            continue

        print(f"\n🔗 Opening URL: {url}")
        driver.get(url)

        try:
            seller_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@href, '/seller/')]"))
            )

            seller_data = []
            print(f"✅ Found {len(seller_elements)} seller link elements on page")

            for idx, elem in enumerate(seller_elements, start=1):
                name = elem.text.strip()
                href = elem.get_attribute("href")
                print(f"   {idx}. Seller Name: {name} | Link: {href}")

                if name and href:
                    seller_data.append({"name": name, "href": href, "source_url": url})

            if seller_data:
                target_collection.insert_many(seller_data)
                print(f"💾 Inserted {len(seller_data)} sellers from {url} into MongoDB")
            else:
                print(f"⚠️ No valid seller data found for {url}")

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")

        time.sleep(2)

        break

finally:
    driver.quit()
    print("\n🚀 Scraping completed and browser closed.")
