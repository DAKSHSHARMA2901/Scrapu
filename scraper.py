import re
import time
import random
import pandas as pd
import streamlit as st
import traceback
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller


# Setup Selenium driver
def setup_driver():
    chromedriver_autoinstaller.install()  # auto-download matching chromedriver

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")

    driver = webdriver.Chrome(options=options)

    # Stealth mode: hide webdriver flag
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


# Extract emails from a website
def extract_emails_from_website(driver, website_url):
    if not website_url or website_url == "N/A":
        return "N/A"
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    found_emails = set()

    try:
        driver.get(website_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        found_emails.update(email_pattern.findall(soup.get_text()))

        for link in ["contact", "about", "support"]:
            try:
                driver.get(urljoin(website_url, link))
                time.sleep(1.5)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                found_emails.update(email_pattern.findall(soup.get_text()))
            except:
                pass

        return list(found_emails)[0] if found_emails else "N/A"
    except:
        return "N/A"


# Main scraping function
def scrape_google_maps(query, num_pages=1):
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        st.write(f"🔎 Opening: {search_url}")
        driver.get(search_url)
        time.sleep(5)

        for page in range(num_pages):
            scrollable_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            for _ in range(5):
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(random.uniform(1, 2))

            cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            cards = list({card.get_attribute("href"): card for card in cards}.values())

            for card in cards:
                try:
                    href = card.get_attribute("href")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(2)

                    try:
                        name = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text.strip()
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

                    # Try to extract email directly or via website
                    try:
                        email = driver.find_element(By.CSS_SELECTOR, 'a[href^="mailto:"]').get_attribute("href").replace("mailto:", "")
                    except:
                        email = "N/A"
                    if email == "N/A" and website != "N/A":
                        email = extract_emails_from_website(driver, website)

                    if email != "N/A":
                        scraped_data.append({
                            "Name": name,
                            "Address": address,
                            "Phone": phone,
                            "Website": website,
                            "Email": email,
                            "Rating": rating
                        })

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                except Exception:
                    st.error("⚠️ Error scraping a business card")
                    st.text(traceback.format_exc())
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

    except Exception:
        st.error("❌ Scraping failed")
        st.text(traceback.format_exc())
    finally:
        driver.quit()

    return scraped_data


# Streamlit UI
st.title("Google Maps Lead Scraper")
st.write("Enter a search query and number of pages to scrape. Only results with emails are collected.")

query = st.text_input("Search query", "IT services in Delhi")
pages = st.number_input("Pages to scrape", min_value=1, max_value=5, value=1)
start_btn = st.button("Start Scraping")

if start_btn:
    with st.spinner("Scraping in progress..."):
        data = scrape_google_maps(query, pages)

    if data:
        df = pd.DataFrame(data)
        st.success(f"Scraping complete! {len(df)} results found.")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="scraped_leads.csv",
            mime="text/csv"
        )
    else:
        st.warning("No results found with emails.")
