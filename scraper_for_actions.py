# scraper_for_actions.py (Version 7.0 - GitHub Actions Ready)
# Yeh script ab search query 'input()' ke bajaye environment variable se leta hai.

import time
import pandas as pd
import os # <<< YEH IMPORT ADD KAREIN
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
# Output file ka naam ab keyword ke hisab se banega
OUTPUT_CSV_FILE = 'gmaps_leads.csv' 

# (Baaki tamam scraping functions bilkul waisay hi rahenge)
def scroll_to_load_all_results(driver):
    # ... (No change here)
    try:
        wait = WebDriverWait(driver, 15)
        scrollable_list = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]')))
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_list)
        scroll_attempts = 0
        print("Step 1/3: Scrolling Google Maps to load all results...")
        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_list)
            time.sleep(3)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_list)
            if new_height == last_height:
                print("  -> Scrolling complete. All results loaded.")
                return True
            last_height = new_height
            scroll_attempts += 1
            if scroll_attempts > 100:
                print("  -> Max scroll limit (100) reached.")
                return True
    except TimeoutException:
        print("  -> ERROR: Could not find the results panel to scroll.")
        return False

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
    # === YEH HISSA BADAL DIYA GAYA HAI ===
    # Ab hum input() ke bajaye environment variable se query lenge
    search_query = os.environ.get('SEARCH_QUERY')
    if not search_query:
        print("Error: SEARCH_QUERY environment variable not set.")
        return
    print(f"Starting scraper for query: '{search_query}'")
    # ======================================

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox") # <<< YEH LINUX SERVER KE LIYE ZAROORI HAI
    options.add_argument("--disable-dev-shm-usage") # <<< YEH BHI LINUX SERVER KE LIYE ZAROORI HAI
    
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
    
    all_business_details = []
    total_links = len(business_links)
    print(f"\nStep 2/3: Scraping details for {total_links} businesses...")

    for i, link in enumerate(business_links):
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

        # File ka naam ab hamesha 'gmaps_final_leads.csv' hoga
        df.to_csv(OUTPUT_CSV_FILE, index=False, encoding='utf-8-sig')
        print(f"\n--- SCRAPING COMPLETE! ---")
        print(f"Successfully scraped {len(all_business_details)} businesses.")
        print(f"Data has been saved to '{OUTPUT_CSV_FILE}'.")
    else:
        print("\nCould not scrape any detailed business information.")

if __name__ == "__main__":
    main()
