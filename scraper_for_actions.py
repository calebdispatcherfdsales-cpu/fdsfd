# scraper_for_actions.py (Version 7.1 - Test Mode Enabled)

import time
import pandas as pd
import os
from selenium import webdriver
# ... (baaki tamam imports waisay hi)
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
OUTPUT_CSV_FILE = 'gmaps_leads.csv'
# === TEST MODE CONFIGURATION ===
MAX_BUSINESSES_TO_SCRAPE = 10 # <<< YEH LINE ADD KAREIN

# ... (scroll_to_load_all_results aur get_all_business_links mein koi tabdeeli nahi)

def get_all_business_links(driver):
    # ... (No change here)
    links = []
    try:
        business_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="https://www.google.com/maps/place/"]' )
        for elem in business_elements:
            link = elem.get_attribute('href')
            if link and 'search' not in link and 'reviews' not in link:
                links.append(link)
        unique_links = list(dict.fromkeys(links))
        print(f"  -> Found {len(unique_links)} unique business links.")
        return unique_links
    except Exception as e:
        print(f"  -> ERROR getting business links: {e}")
        return []

def scrape_individual_business_page(driver, url):
    # ... (No change here)
    driver.get(url)
    data = {}
    try:
        wait = WebDriverWait(driver, 10)
        title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1')))
        data['Business Name'] = title_element.text
    except TimeoutException:
        print(f"  - Page timed out or title not found for: {url}")
        return None
    try:
        rating_div = driver.find_element(By.CSS_SELECTOR, 'div.F7nice')
        data['Rating'] = rating_div.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]').text
        data['Reviews'] = rating_div.find_element(By.CSS_SELECTOR, 'span[aria-label*="reviews"]').text.replace('(', '').replace(')', '')
    except: data['Rating'], data['Reviews'] = 'N/A', 'N/A'
    try: data['Category'] = driver.find_element(By.CSS_SELECTOR, 'button.DkEaL').text
    except: data['Category'] = 'N/A'
    data['Address'], data['Website'], data['Phone Number'], data['Plus Code'] = 'N/A', 'No Website', 'N/A', 'N/A'
    try:
        detail_elements = driver.find_elements(By.CSS_SELECTOR, 'div.AeaXub')
        for element in detail_elements:
            try:
                icon_text = element.find_element(By.CSS_SELECTOR, 'span.google-symbols').text
                info_text = element.find_element(By.CSS_SELECTOR, 'div.Io6YTe').text
                if icon_text == '': data['Address'] = info_text
                elif icon_text == '': data['Phone Number'] = info_text
                elif icon_text == '': data['Website'] = info_text
                elif icon_text == '': data['Plus Code'] = info_text
            except: continue
    except: pass
    if data.get('Website') == 'No Website':
        try:
            data['Website'] = driver.find_element(By.XPATH, "//a[contains(@aria-label, 'Website:')]").get_attribute('href')
        except: pass
    return data

def main():
    # ... (main function ka shuru ka hissa waisa hi)
    search_query = os.environ.get('SEARCH_QUERY')
    if not search_query:
        print("Error: SEARCH_QUERY environment variable not set.")
        return
    print(f"Starting scraper for query: '{search_query}' in TEST MODE")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30) 
    except Exception as e:
        print(f"ERROR: Failed to start WebDriver. Error: {e}")
        return

    search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+' )}"
    driver.get(search_url)
    if not scroll_to_load_all_results(driver):
        driver.quit()
        return
    
    business_links = get_all_business_links(driver)
    if not business_links:
        print("No business links found. Exiting.")
        driver.quit()
        return
    
    # === TEST MODE IMPLEMENTATION ===
    # Ab hum poori list ke bajaye sirf pehle 10 links scrape karenge
    links_to_scrape = business_links[:MAX_BUSINESSES_TO_SCRAPE]
    # ==============================
    
    all_business_details = []
    total_links = len(links_to_scrape) # total_links ab 10 hoga
    print(f"\nStep 2/3: Scraping details for {total_links} businesses (Test Mode)...")

    for i, link in enumerate(links_to_scrape):
        print(f"  -> Scraping business {i+1}/{total_links}...")
        details = scrape_individual_business_page(driver, link)
        if details:
            all_business_details.append(details)
        time.sleep(0.5)
        
    driver.quit()

    if all_business_details:
        print(f"\nStep 3/3: Saving final report...")
        df = pd.DataFrame(all_business_details)
        column_order = ['Business Name', 'Website', 'Phone Number', 'Rating', 'Reviews', 'Category', 'Address', 'Plus Code']
        df = df.reindex(columns=column_order)

        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"\n--- SCRAPING COMPLETE! ---")
        print(f"Successfully scraped {len(all_business_details)} businesses.")
        print(f"Data has been saved to '{OUTPUT_CSV_FILE}'.")
    else:
        print("\nCould not scrape any detailed business information.")

if __name__ == "__main__":
    main()
