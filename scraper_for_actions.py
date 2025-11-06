# batch_scraper_for_actions.py (Version 2.0 - GitHub Actions Ready)
# Ismein Linux server ke liye zaroori options add kiye gaye hain.

import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
KEYWORDS_FILE = 'keywords.txt'
OUTPUT_FOLDER = 'BATCH_SCRAPING_RESULTS' 

# (Baaki tamam scraping functions bilkul waisay hi rahenge)
def scroll_to_load_all_results(driver):
    # ... (No change here)
    try:
        wait = WebDriverWait(driver, 15)
        scrollable_list = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]')))
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_list)
        scroll_attempts = 0
        print("  -> Scrolling to load all results...")
        while True:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_list)
            time.sleep(3)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_list)
            if new_height == last_height:
                print("    + Scrolling complete.")
                return True
            last_height = new_height
            scroll_attempts += 1
            if scroll_attempts > 100:
                print("    ! Max scroll limit (100) reached.")
                return True
    except TimeoutException:
        print("    - ERROR: Could not find the results panel to scroll.")
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
        return None
    try:
        rating_div = driver.find_element(By.CSS_SELECTOR, 'div.F7nice')
        data['Rating'] = rating_div.find_element(By.CSS_SELECTOR, 'span[aria-hidden="true"]').text
        data['Reviews'] = rating_div.find_element(By.CSS_SELECTOR, 'span[aria-label*="reviews"]').text.replace('(', '').replace(')', '')
    except: data['Rating'], data['Reviews'] = 'N/A', 'N/A'
    try: data['Category'] = driver.find_element(By.CSS_SELECTOR, 'button.DkEaL').text
    except: data['Category'] = 'N/A'
    data['Address'], data['Website'], data['Phone Number'] = 'N/A', 'No Website', 'N/A'
    try:
        detail_elements = driver.find_elements(By.CSS_SELECTOR, 'div.AeaXub')
        for element in detail_elements:
            try:
                icon_text = element.find_element(By.CSS_SELECTOR, 'span.google-symbols').text
                info_text = element.find_element(By.CSS_SELECTOR, 'div.Io6YTe').text
                if icon_text == '': data['Address'] = info_text
                elif icon_text == '': data['Phone Number'] = info_text
                elif icon_text == '': data['Website'] = info_text
            except: continue
    except: pass
    if data.get('Website') == 'No Website':
        try:
            data['Website'] = driver.find_element(By.XPATH, "//a[contains(@aria-label, 'Website:')]").get_attribute('href')
        except: pass
    return data

def main():
    try:
        with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
        if not keywords:
            print(f"Error: '{KEYWORDS_FILE}' is empty.")
            return
    except FileNotFoundError:
        print(f"Error: '{KEYWORDS_FILE}' not found.")
        return

    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    print(f"Found {len(keywords)} keywords. Starting batch process...")

    # === YEH HISSA BADAL DIYA GAYA HAI ===
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox") # Zaroori for Linux servers
    options.add_argument("--disable-dev-shm-usage") # Zaroori for Linux servers
    # ======================================
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(45) 
    except Exception as e:
        print(f"FATAL ERROR: Failed to start WebDriver. Error: {e}")
        return

    for i, keyword in enumerate(keywords):
        print(f"\n--- Processing Keyword {i+1}/{len(keywords)}: '{keyword}' ---")
        
        search_url = f"https://www.google.com/maps/search/{keyword.replace(' ', '+' )}"
        driver.get(search_url)
        
        if not scroll_to_load_all_results(driver):
            print(f"  ! Skipping keyword '{keyword}' due to scrolling error.")
            continue
        
        business_links = get_all_business_links(driver)
        if not business_links:
            print(f"  ! No businesses found for '{keyword}'. Skipping.")
            continue
        
        all_business_details = []
        total_links = len(business_links)
        print(f"  -> Scraping details for {total_links} businesses...")

        for j, link in enumerate(business_links):
            print(f"    - Scraping business {j+1}/{total_links}...")
            details = scrape_individual_business_page(driver, link)
            if details:
                all_business_details.append(details)
            time.sleep(0.2)
            
        if all_business_details:
            df = pd.DataFrame(all_business_details)
            column_order = ['Business Name', 'Website', 'Phone Number', 'Rating', 'Reviews', 'Category', 'Address']
            df = df.reindex(columns=column_order)
            
            safe_filename = "".join(c for c in keyword if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
            output_path = os.path.join(OUTPUT_FOLDER, f"leads_{safe_filename}.csv")
            
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"  -> SUCCESS: Saved {len(all_business_details)} leads to '{output_path}'")
        else:
            print(f"  ! Could not scrape any details for keyword '{keyword}'.")

        print("  -> Taking a short break before the next keyword...")
        time.sleep(15)

    driver.quit()
    print(f"\n\n--- BATCH PROCESS COMPLETE! All files are in '{OUTPUT_FOLDER}' folder. ---")

if __name__ == "__main__":
    main()
