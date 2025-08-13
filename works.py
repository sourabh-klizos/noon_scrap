import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
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
# options.add_argument("--headless=new")  # Uncomment for headless mode

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

# --- Loop through URLs from MongoDB ---
for doc in source_collection.find().skip(10):
    url = doc.get("url")
    if not url:
        print("❌ Skipping document without 'url'")
        continue

    print(f"\n🔗 Opening URL: {url}")
    try:
        driver.get(url)
        time.sleep(10)  # Let page load fully

        sellers = driver.find_elements(By.CSS_SELECTOR, "a.CheckboxOption_container__ZOrNu")
        seller_data_list = []

        for s in sellers:
            try:
                # Try getting raw href directly from HTML (exact value, no normalization)
                href = driver.execute_script("return arguments[0].getAttribute('href');", s)

                # Extract partner ID from href if possible
                partner_match = re.search(r"p_\d+", href) if href else None
                partner_id = partner_match.group(0) if partner_match else None

                # If no href found, reconstruct manually
                if not href and partner_id:
                    base_url = driver.current_url.split("?")[0]
                    href = f"{base_url}?f[partner][]={partner_id}"

                # Extract seller ID from checkbox input
                label = s.find_element(By.CSS_SELECTOR, "label")
                checkbox_input = label.find_element(By.TAG_NAME, "input")
                seller_id = checkbox_input.get_attribute("id")  # facet-partner-p_XXXX
                secondary_id = seller_id.split("-")[-1] if seller_id else None
                seller_name = label.find_element(By.CSS_SELECTOR, ".MultiOptionFilter_text__Ysy2U").text

                seller_doc = {
                    "partner_id": partner_id,
                    "seller_id": seller_id,
                    "secondary_id": secondary_id,
                    "seller_name": seller_name,
                    "seller_link": href,
                    "source_url": url,
                    "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                seller_data_list.append(seller_doc)
                print(f"🛒 Partner: {partner_id} | SellerID: {seller_id} | SecondaryID: {secondary_id} | Name: {seller_name} | Link: {href}")

            except Exception as e:
                print(f"⚠️ Error extracting seller details: {e}")

        if seller_data_list:
            target_collection.insert_many(seller_data_list)
            print(f"💾 Inserted {len(seller_data_list)} sellers into MongoDB from {url}")
        else:
            print("⚠️ No seller data found.")

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

driver.quit()
print("\n✅ Scraping completed & browser closed.")
# /html/body/div[3]/div[1]/div[2]/div[1]/div[30]/div/div/div/button