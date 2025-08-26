import re
import time
import pandas as pd
import streamlit as st
from urllib.parse import quote
from playwright.sync_api import sync_playwright
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Playwright browser
# ------------------------------
def setup_browser():
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--disable-blink-features=AutomationControlled',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        return playwright, browser
    except Exception as e:
        st.error(f"Failed to setup browser: {e}")
        return None, None

# ------------------------------
# Email extractor
# ------------------------------
def extract_emails_from_text(text):
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    emails = email_pattern.findall(text)
    return emails[0] if emails else "N/A"

# ------------------------------
# Playwright Google Maps Scraper
# ------------------------------
def scrape_google_maps_playwright(query, progress_callback=None):
    playwright, browser = setup_browser()
    if not browser:
        if progress_callback:
            progress_callback("❌ Failed to initialize browser")
        return []
    
    scraped_data = []
    
    try:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        if progress_callback:
            progress_callback(f"🔍 Searching: {query}")
        
        page.goto(search_url, timeout=30000)
        page.wait_for_timeout(5000)
        
        if progress_callback:
            progress_callback("📊 Loading business listings...")
        
        # Wait for results to load
        page.wait_for_selector('[role="feed"], .section-result, .searchbox', timeout=15000)
        
        # Scroll to load more results
        for i in range(3):
            page.evaluate('''() => {
                const feed = document.querySelector('[role="feed"]');
                if (feed) feed.scrollTop = feed.scrollHeight;
            }''')
            page.wait_for_timeout(2000)
            if progress_callback:
                progress_callback(f"⬇️ Scrolling ({i + 1}/3)")
        
        # Get business listings
        listings = page.query_selector_all('[role="article"], .section-result, .Nv2PK')
        
        if progress_callback:
            progress_callback(f"✅ Found {len(listings)} businesses")
        
        for i, listing in enumerate(listings[:8]):  # Limit to 8
            try:
                # Click on the listing
                listing.click()
                page.wait_for_timeout(3000)
                
                # Extract information
                business_data = {}
                
                # Name
                name_elem = page.query_selector('h1, .fontHeadlineLarge, [aria-hidden="true"]')
                business_data["Name"] = name_elem.inner_text().strip() if name_elem else "N/A"
                
                # Address
                address_btn = page.query_selector('button[data-item-id*="address"], [aria-label*="ddress"]')
                business_data["Address"] = address_btn.inner_text().strip() if address_btn else "N/A"
                
                # Phone
                phone_btn = page.query_selector('button[data-item-id*="phone"], [aria-label*="hone"]')
                business_data["Phone"] = phone_btn.inner_text().strip() if phone_btn else "N/A"
                
                # Website
                website_link = page.query_selector('a[href*="://"]:not([href*="google"])')
                business_data["Website"] = website_link.get_attribute('href') if website_link else "N/A"
                
                # Extract email from page
                page_content = page.content()
                business_data["Email"] = extract_emails_from_text(page_content)
                
                # Only add if we have a valid name
                if business_data["Name"] != "N/A" and business_data["Name"].strip():
                    scraped_data.append(business_data)
                    if progress_callback:
                        progress_callback(f"📝 Added: {business_data['Name'][:20]}...")
                
                # Go back to results
                page.go_back()
                page.wait_for_timeout(2000)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ Skipping business {i+1}")
                continue
                
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Error during scraping")
    finally:
        try:
            browser.close()
            playwright.stop()
        except:
            pass
            
    return scraped_data

# ------------------------------
# Alternative: Direct HTML parsing approach
# ------------------------------
def scrape_google_maps_simple(query, progress_callback=None):
    """Fallback method using direct requests and HTML parsing"""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        if progress_callback:
            progress_callback(f"🔍 Trying alternative method for: {query}")
        
        # This is a simplified approach that might work better
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        response = requests.get(search_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to extract basic info
            businesses = []
            
            # This is a very basic extraction - Google Maps makes this difficult
            name_elements = soup.find_all(['h1', 'h2', 'h3'], class_=lambda x: x and any(keyword in str(x) for keyword in ['title', 'name', 'headline']))
            
            for name_elem in name_elements[:5]:
                business_data = {
                    "Name": name_elem.get_text().strip(),
                    "Address": "N/A",
                    "Phone": "N/A",
                    "Website": "N/A",
                    "Email": "N/A"
                }
                businesses.append(business_data)
            
            return businesses
        else:
            return []
            
    except Exception as e:
        if progress_callback:
            progress_callback("❌ Alternative method failed")
        return []

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Google Maps Lead Scraper",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper")
st.write("Get real business leads with contact information from Google Maps")

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("Search query", "restaurants in mumbai", key="query")
    
    method = st.selectbox("Scraping Method", ["Playwright (Recommended)", "Alternative"])
    
    start_btn = st.button("🚀 Start Scraping", key="start_btn", type="primary", use_container_width=True)
    
    st.info("""
    **Recommended Queries:** 
    - "restaurants mumbai"
    - "hotels delhi" 
    - "cafe bangalore"
    - "it companies pune"
    """)

# Main content
if start_btn:
    st.session_state.scraping_complete = False
    st.session_state.scraped_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(message, progress=None):
        status_text.write(f"**{message}**")
        if progress is not None:
            progress_bar.progress(progress)
    
    # Start scraping based on selected method
    if method == "Playwright (Recommended)":
        scraped_data = scrape_google_maps_playwright(
            query, 
            progress_callback=update_progress
        )
    else:
        scraped_data = scrape_google_maps_simple(
            query,
            progress_callback=update_progress
        )
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    
    update_progress("✅ Scraping complete!", 100)

# Display results
if st.session_state.scraping_complete:
    if st.session_state.scraped_data:
        df = pd.DataFrame(st.session_state.scraped_data)
        
        st.success(f"🎉 Successfully scraped {len(df)} businesses!")
        
        # Display results
        st.dataframe(df, use_container_width=True, height=400)
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"business_leads_{query.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("""
        ❌ No businesses found. This could be because:
        
        1. **Google detected scraping** - Try again in a few minutes
        2. **Query too broad** - Use specific queries like "restaurants mumbai"
        3. **Location issues** - Try different cities: delhi, mumbai, bangalore
        
        💡 **Try these exact queries:**
        - "restaurants in mumbai"
        - "hotels in delhi"
        - "cafe in bangalore"
        - "it companies in pune"
        """)

else:
    st.info("👆 Enter a search query and click 'Start Scraping'")
    
    # Quick action buttons
    st.write("### 🚀 Quick Search:")
    quick_queries = [
        "restaurants in mumbai",
        "hotels in delhi", 
        "cafe in bangalore",
        "it companies in pune"
    ]
    
    cols = st.columns(2)
    for i, q in enumerate(quick_queries):
        with cols[i % 2]:
            if st.button(f"🔍 {q}", key=f"quick_{i}"):
                st.session_state.query = q
                st.rerun()

st.markdown("---")
st.caption("Google Maps Lead Scraper - Now with Playwright for better reliability")
