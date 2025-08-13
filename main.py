import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException, NoSuchElementException, TimeoutException
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from pymongo import MongoClient

# --- MongoDB Setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["noon_scrap"]
source_collection = db["noon_seller_db"]
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

# --- Helper function: safe click with retry ---
def safe_click_with_retry(driver, xpath, max_retries=5, wait_between=1, skip_if_missing=False):
    for attempt in range(1, max_retries + 1):
        try:
            el = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            el.click()
            print(f"✅ Clicked element on attempt {attempt}: {xpath}")
            return True
        except TimeoutException:
            if skip_if_missing and attempt == 1:
                print(f"⚠️ Skipping, element not found: {xpath}")
                return False
        except (ElementClickInterceptedException, NoSuchElementException) as e:
            print(f"⚠️ Attempt {attempt} failed to click: {e}")
        time.sleep(wait_between)
    print(f"❌ Failed to click after {max_retries} attempts: {xpath}")
    return False

# --- Function to close overlays/popups ---
def close_overlays(driver):
    try:
        cookie_close = driver.find_element(By.CSS_SELECTOR, ".cookie-banner-close")
        cookie_close.click()
        print("✅ Closed cookie banner.")
    except NoSuchElementException:
        pass
    try:
        signin_popup = driver.find_element(By.CSS_SELECTOR, ".modal__close")
        signin_popup.click()
        print("✅ Closed sign-in popup.")
    except NoSuchElementException:
        pass

# --- Main scraping loop ---
# for idx, doc in enumerate(source_collection.find().skip(200).limit(250)):  # Adjust skip/limit
for idx, doc in enumerate(source_collection.find().skip(250).limit(280)):  # Adjust skip/limit
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print("Index -> ", idx)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    url = doc.get("url")
    if not url:
        print("❌ Skipping document without 'url'")
        continue
    if "?" in url:
        url = url.split("?")[0]

    print(f"\n🔗 Opening URL: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        close_overlays(driver)  # Close popups if any

        # --- Step 1: Click first filter/category element (if exists) ---
        # first_xpath = "//div[contains(@class,'FilterOption')]"
        first_xpath = "/html/body/div[3]/div/div[2]/div[1]/div[24]"
        safe_click_with_retry(driver, first_xpath, max_retries=3, wait_between=1, skip_if_missing=True)

        # --- Step 2: Click expand button (if exists, with retries) ---
        # expand_button_xpath = "//button[contains(@class,'FilterOption_moreButton')]"
        second_xpath = "/html/body/div[3]/div/div[2]/div[1]/div[24]/div/div/div/button"
        safe_click_with_retry(driver, second_xpath, max_retries=5, wait_between=1, skip_if_missing=True)

        time.sleep(2)  # allow sellers to load
        sellers = driver.find_elements(By.CSS_SELECTOR, "a.CheckboxOption_container__ZOrNu")
        seller_data_list = []

        for s in sellers:
            try:
                href = driver.execute_script("return arguments[0].getAttribute('href');", s)
                partner_match = re.search(r"p_\d+", href) if href else None
                partner_id = partner_match.group(0) if partner_match else None

                label = s.find_element(By.CSS_SELECTOR, "label")
                checkbox_input = label.find_element(By.TAG_NAME, "input")
                seller_id = checkbox_input.get_attribute("id")
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
                if not partner_id:
                    continue
                seller_data_list.append(seller_doc)
                print(f"🛒 Partner: {partner_id} | SellerID: {seller_id} | Name: {seller_name} | Link: {href}")

            except Exception as e:
                print(f"⚠️ Error extracting seller details: {e}")

        # --- Insert data into MongoDB ---
        if seller_data_list:
            target_collection.insert_many(seller_data_list)
            source_collection.update_one(
                {"_id": doc.get("_id")},
                {"$set": {"called": True}}
            )
            print(f"💾 Inserted {len(seller_data_list)} sellers into MongoDB from {url}")
        else:
            print("⚠️ No seller data found.")

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")

    finally:
        driver.quit()

print("\n✅ Scraping completed & browser closed.")
