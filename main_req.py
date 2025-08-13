# import requests

# def fetch_sellers_from_api():
#     url = "https://www.noon.com/_svc/catalog/api/v3/search"
#     params = {
#         "q": "samsung galaxy ai",
#         "filters": "",
#         "limit": 50,
#     }
#     headers = {
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
#         "accept": "application/json",
#     }

#     r = requests.get(url, params=params, headers=headers)
#     r.raise_for_status()
#     data = r.json()
#     print(data,"======="*10)

#     sellers = []
#     for f in data.get("filters", []):
#         if f.get("name") == "partner":
#             for option in f.get("options", []):
#                 sellers.append({
#                     "partner_id": option.get("value"),
#                     "seller_name": option.get("label"),
#                 })
#     return sellers

# print(fetch_sellers_from_api())

import re
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time

# --- MongoDB Setup ---
client = MongoClient("mongodb://localhost:27017/")
db = client["noon_scrap"]
source_collection = db["noon_seller_db"]       # Collection with URLs
target_collection = db["noon_seller_full_details"]  # Where we save sellers

def fetch_sellers_from_html(url):
    headers = {
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0.0.0 Safari/537.36"
        ),
        "accept-language": "en-US,en;q=0.9",
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    sellers = []

    for label in soup.select("a.CheckboxOption_container__ZOrNu label"):
        seller_id_full = label.get("for")  # e.g. facet-partner-p_832
        partner_id = seller_id_full.split("-")[-1] if seller_id_full else None

        name_tag = label.select_one(".MultiOptionFilter_text__Ysy2U")
        seller_name = name_tag.get_text(strip=True) if name_tag else None

        sellers.append({
            "partner_id": partner_id,
            "seller_id": seller_id_full,
            "seller_name": seller_name,
            "source_url": url,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    return sellers


if __name__ == "__main__":
    for doc in source_collection.find():
        url = doc.get("url")
        if not url:
            print("❌ Skipping document without 'url'")
            continue

        print(f"\n🔗 Scraping URL: {url}")
        try:
            seller_data_list = fetch_sellers_from_html(url)

            if seller_data_list:
                target_collection.insert_many(seller_data_list)
                print(f"💾 Inserted {len(seller_data_list)} sellers from {url}")
            else:
                print("⚠️ No seller data found.")

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
