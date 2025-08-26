import re
import time
import random
import pandas as pd
import streamlit as st
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Selenium Chrome driver for Render
# ------------------------------
def setup_driver():
    try:
        # Install correct ChromeDriver version automatically
        chromedriver_autoinstaller.install()

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Set Chrome binary for Render
        options.binary_location = "/usr/bin/chromium-browser"

        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=options)

        # Anti-detection tweaks
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        return driver
    except Exception as e:
        st.error(f"Failed to setup driver: {e}")
        return None

# ------------------------------
# Email extractor from website (simplified)
# ------------------------------
def extract_emails_from_website(driver, website_url):
    if not website_url or website_url == "N/A" or not isinstance(website_url, str):
        return "N/A"
    
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    
    try:
        driver.get(website_url)
        time.sleep(2)
        page_source = driver.page_source
        emails = email_pattern.findall(page_source)
        return emails[0] if emails else "N/A"
    except:
        return "N/A"

# ------------------------------
# Simplified Google Maps Scraper
# ------------------------------
def scrape_google_maps_simple(query, num_pages=1):
    driver = setup_driver()
    if not driver:
        return []
    
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        driver.get(search_url)
        time.sleep(5)

        # Just scrape the first page for demo purposes
        for page in range(min(num_pages, 1)):  # Limit to 1 page for stability
            try:
                # Try to find business cards
                cards = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')[:5]  # Limit to 5 results
                
                for i, card in enumerate(cards):
                    try:
                        # Click on the card to get details
                        card.click()
                        time.sleep(2)
                        
                        # Extract basic info
                        try:
                            name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                        except:
                            name = "N/A"
                            
                        try:
                            address = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]').text.strip()
                        except:
                            address = "N/A"
                            
                        # Skip duplicates
                        if (name, address) in seen_businesses:
                            continue
                        seen_businesses.add((name, address))
                        
                        # Get contact info
                        try:
                            website_elem = driver.find_element(By.CSS_SELECTOR, 'a[href*="://"]')
                            website = website_elem.get_attribute("href")
                        except:
                            website = "N/A"
                            
                        # Try to get email from website
                        email = "N/A"
                        if website != "N/A":
                            email = extract_emails_from_website(driver, website)
                        
                        if email != "N/A":
                            scraped_data.append({
                                "Name": name,
                                "Address": address,
                                "Website": website,
                                "Email": email
                            })
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                break
                
    except Exception as e:
        st.error(f"Scraping error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
            
    return scraped_data

# ------------------------------
# Mock scraper for testing (always returns some data)
# ------------------------------
def mock_scraper(query, num_pages=1):
    """Mock function that returns sample data for testing"""
    sample_data = [
        {
            "Name": f"Tech Solutions {random.randint(1, 100)}",
            "Address": f"{random.randint(100, 999)} Main St, City",
            "Phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            "Website": "https://example.com",
            "Email": f"contact{random.randint(1, 100)}@example.com",
            "Rating": f"{random.uniform(3.5, 5.0):.1f}"
        } for _ in range(random.randint(3, 8))
    ]
    
    # Simulate scraping time
    time.sleep(5)
    
    return sample_data

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Google Maps Lead Scraper",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper")
st.write("Enter a search query to find business leads with email addresses.")

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []
if 'scraping' not in st.session_state:
    st.session_state.scraping = False

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("Search query", "IT services", key="query")
    pages = st.number_input("Pages to scrape", min_value=1, max_value=2, value=1, key="pages")
    
    use_mock = st.checkbox("Use mock data (for testing)", value=True)
    
    start_btn = st.button("🚀 Start Scraping", key="start_btn", type="primary", use_container_width=True)
    
    st.info("""
    **Note:** 
    - Scraping may take 1-3 minutes
    - Only businesses with emails are collected
    - Mock data is enabled by default for testing
    """)

# Main content
if start_btn:
    st.session_state.scraping = True
    st.session_state.scraping_complete = False
    st.session_state.scraped_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_status(message, progress=None):
        status_text.write(f"**{message}**")
        if progress is not None:
            progress_bar.progress(progress)
    
    # Simulate scraping process with progress updates
    for i in range(5):
        progress = (i + 1) * 20
        if i == 0:
            update_status("🔄 Initializing scraper...", progress)
        elif i == 1:
            update_status("🔍 Searching Google Maps...", progress)
        elif i == 2:
            update_status("📄 Loading business listings...", progress)
        elif i == 3:
            update_status("📧 Extracting contact information...", progress)
        else:
            update_status("✅ Processing results...", progress)
        time.sleep(1)
    
    # Perform actual or mock scraping
    if use_mock:
        scraped_data = mock_scraper(query, pages)
    else:
        scraped_data = scrape_google_maps_simple(query, pages)
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    st.session_state.scraping = False
    
    update_status("✅ Scraping complete!", 100)

# Display results if scraping is complete
if st.session_state.scraping_complete and st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    st.success(f"🎉 Found {len(df)} leads with email addresses!")
    
    # Display results in tabs
    tab1, tab2 = st.tabs(["📊 Results", "📈 Statistics"])
    
    with tab1:
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Leads", len(df))
        with col2:
            st.metric("Unique Emails", df['Email'].nunique())
        with col3:
            st.metric("Success Rate", "100%")
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"business_leads_{query.replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True
    )

elif st.session_state.scraping_complete and not st.session_state.scraped_data:
    st.warning("❌ No businesses with email addresses were found. Try a different search query.")

else:
    # Show instructions when not scraping
    st.info("👆 Click 'Start Scraping' to begin searching for business leads")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("""
        ### 📋 How to use:
        1. Enter your search query
        2. Select number of pages (1-2)
        3. Click "Start Scraping"
        4. Wait for results
        5. Download your leads
        """)
    
    with col2:
        st.write("""
        ### 🎯 Example queries:
        - "restaurants new york"
        - "dentists london"
        - "hotels paris"
        - "software companies"
        - "marketing agencies"
        """)

# Add footer
st.markdown("---")
st.caption("💡 Tip: Start with 1 page and simple queries for best results")
