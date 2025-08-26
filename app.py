import re
import time
import random
import pandas as pd
import streamlit as st
import requests
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import asyncio
from database import DatabaseManager

# ------------------------------
# Setup Selenium Chrome driver
# ------------------------------
def setup_driver():
    chromedriver_autoinstaller.install()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.images": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        },
    )

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """
        },
    )
    return driver

# ------------------------------
# Email extractor from website
# ------------------------------
def extract_emails_from_website(driver, website_url):
    if not website_url or website_url == "N/A":
        return "N/A"
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    found_emails = set()

    try:
        driver.get(website_url)
        time.sleep(1)  # Reduced to save time
        soup = BeautifulSoup(driver.page_source, "html.parser")
        found_emails.update(email_pattern.findall(soup.get_text()))

        for link in ["contact"]:  # Limited to one page to save time
            try:
                driver.get(urljoin(website_url, link))
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                found_emails.update(email_pattern.findall(soup.get_text()))
            except:
                pass

        return list(found_emails)[0] if found_emails else "N/A"
    except:
        return "N/A"

# ------------------------------
# ScrapingBee Fallback
# ------------------------------
def scrape_with_scrapingbee(query):
    scraped_data = []
    api_key = "YOUR_SCRAPINGBEE_API_KEY"  # Replace with your ScrapingBee API key
    search_url = f"https://www.google.com/maps/search/{quote(query)}"
    
    try:
        start_time = time.time()
        response = requests.get(
            "https://app.scrapingbee.com/api/v1/",
            params={
                "api_key": api_key,
                "url": search_url,
                "render_js": "true",
                "premium_proxy": "true",
                "timeout": 30  # 30 seconds max
            },
            timeout=30
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select('a[href*="/maps/place/"]')
        for card in cards[:5]:  # Limit to 5 for speed
            scraped_data.append({
                "Name": card.get_text() or "N/A",
                "Address": "N/A",
                "Phone": "N/A",
                "Website": "N/A",
                "Email": "N/A",
                "Rating": "N/A"
            })
        st.write(f"ScrapingBee completed in {time.time() - start_time:.2f} seconds")
    except Exception as e:
        st.error(f"ScrapingBee failed: {str(e)}")
    return scraped_data

# ------------------------------
# Google Maps Scraper with 1-minute timeout
# ------------------------------
def scrape_google_maps(query, logger=print):
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()
    start_time = time.time()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        logger(f"🔎 Opening: {search_url}")
        driver.get(search_url)
        time.sleep(5)  # Reduced to save time

        scrollable_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )

        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
        while time.time() - start_time < 50:  # Leave 10 seconds for processing
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(random.uniform(1, 2))
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                break
            last_height = new_height

        cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/maps/place/"]'))
        )
        cards = list({card.get_attribute("href"): card for card in cards}.values())[:10]  # Limit to 10 for speed

        for i, card in enumerate(cards):
            if time.time() - start_time >= 60:
                logger("⏰ 1-minute timeout reached, stopping scrape")
                break

            try:
                href = card.get_attribute("href")
                driver.execute_script("window.open(arguments[0]);", href)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(1)  # Reduced to save time

                try:
                    name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text.strip()
                except:
                    name = "N/A"

                try:
                    address = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Address"]').text.strip()
                except:
                    address = "N/A"

                if (name, address) in seen_businesses:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue
                seen_businesses.add((name, address))

                try:
                    phone = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Phone"]').text.strip()
                except:
                    phone = "N/A"

                try:
                    website = driver.find_element(By.CSS_SELECTOR, 'a[data-tooltip="Open website"]').get_attribute("href")
                except:
                    website = "N/A"

                try:
                    rating = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="star rating"]').text.strip()
                except:
                    rating = "N/A"

                try:
                    email = driver.find_element(By.CSS_SELECTOR, 'a[href^="mailto:"]').get_attribute("href").replace("mailto:", "")
                except:
                    email = "N/A"

                if email == "N/A" and website != "N/A":
                    email = extract_emails_from_website(driver, website)

                if email != "N/A" and phone != "N/A":
                    scraped_data.append({
                        "Name": name,
                        "Address": address,
                        "Phone": phone,
                        "Website": website,
                        "Email": email,
                        "Rating": rating
                    })
                    logger(f"✅ Found: {name} (Email: {email}, Phone: {phone})")

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                logger(f"⚠️ Error scraping business card {i+1}: {str(e)}")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                continue

    except Exception as e:
        logger(f"❌ Scraping failed: {str(e)}")
    finally:
        driver.quit()

    logger(f"Scrape completed in {time.time() - start_time:.2f} seconds")
    return scraped_data

# ------------------------------
# Streamlit UI
# ------------------------------
async def main():
    db = DatabaseManager(db_path="/app/leads.db")  # Persistent storage on Render Disk
    await db.initialize()

    st.title("Google Maps Lead Scraper")
    st.write("Enter a search query. Scrape limited to 1 page and 1 minute.")
    
    query = st.text_input("Search query", "IT services in Delhi", key="query")
    start_btn = st.button("Start Scraping", key="start_btn")

    if start_btn:
        with st.spinner("Scraping in progress... (max 1 minute)"):
            session_id = await db.create_session(query, 1)
            data = scrape_google_maps(query, logger=st.write)
            if not data:
                st.warning("Selenium scraper found no data, trying ScrapingBee...")
                data = scrape_with_scrapingbee(query)
            
            # Filter data for entries with both email and phone
            valid_data = [entry for entry in data if entry["Email"] != "N/A" and entry["Phone"] != "N/A"]
            for i, business in enumerate(valid_data):
                business["query"] = query
                business["page_number"] = 1
                business["position"] = i + 1
                await db.insert_business(business, session_id)
            
            await db.update_session(session_id, total_businesses=len(valid_data), successful_scrapes=len(valid_data), failed_scrapes=0, status="completed")

        if valid_data:
            df = pd.DataFrame(valid_data)
            st.success(f"Scraping complete! {len(df)} results found with email and phone.")
            st.table(df)  # Display as table

            csv_filename = "scraped_leads.csv"
            await db.export_to_csv(session_id, csv_filename)
            st.download_button(
                label="Download CSV",
                data=open(csv_filename, "rb").read(),
                file_name=csv_filename,
                mime="text/csv",
            )
        else:
            st.warning("No results found with both email and phone.")
            stored_data = await db.get_businesses_by_query(query)
            valid_stored = [entry for entry in stored_data if entry["email"] != "N/A" and entry["phone"] != "N/A"]
            if valid_stored:
                st.write("Showing previously stored results with email and phone:")
                st.table(pd.DataFrame(valid_stored))

if __name__ == "__main__":
    asyncio.run(main())
