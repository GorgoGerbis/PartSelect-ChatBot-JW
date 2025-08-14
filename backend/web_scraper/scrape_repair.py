"""
Repair guide scraper for PartSelect.
Gets troubleshooting info and repair instructions.
"""
import csv
import time
import random
import os
import sys
import signal
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException
import undetected_chromedriver as uc
import tempfile

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import config

class RepairScraper:
    def __init__(self):
        self.scraped_repairs = []
        self.interrupted = False
        
        # Set up signal handler for graceful interruption
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C interruption gracefully."""
        print("\n\nInterruption detected! Saving current progress...")
        self.interrupted = True
        self._save_all_data()
        print("Progress saved")
        sys.exit(0)
    
    def setup_driver(self):
        """Setup Chrome for scraping repair guides."""
        print("Setting up Chrome driver...")
        
        # Create unique temporary directory for Chrome data
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Use undetected Chrome with FULL stealth options
            chrome_options = uc.ChromeOptions()
            
            # Essential stealth options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            chrome_options.add_argument("--disable-site-isolation-trials")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-gpu-logging")
            chrome_options.add_argument("--silent")
            chrome_options.add_argument("--log-level=3")
            
            # Performance and stealth
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Realistic user agent for Windows
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            # Set user data directory
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            # Create driver with stealth patches
            driver = uc.Chrome(options=chrome_options, version_main=None)
            
            # Additional stealth: execute script to remove automation indicators
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            })
            
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(20)
            print("Stealth Chrome WebDriver setup successful")
            return driver
            
        except Exception as e:
            print(f"Stealth Chrome setup failed: {e}")
            return None
    
    def safe_navigate(self, driver, url, max_retries=3):
        """Safely navigate to URL with retry mechanism."""
        for attempt in range(max_retries):
            try:
                print(f"Navigating to {url} (attempt {attempt+1}/{max_retries})")
                driver.get(url)
                
                # Wait for page to load completely
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Check for access denied
                if "Access Denied" in driver.title or "Forbidden" in driver.title:
                    print("Access denied detected, retrying...")
                    if attempt < max_retries - 1:
                        delay = random.uniform(5, 10)
                        print(f"Waiting {delay:.1f} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Max retries reached for access denied")
                        return False
                
                # Wait for dynamic content to load
                time.sleep(5)  # Longer wait for JavaScript content
                print(f"Successfully navigated to {url}")
                return True
                
            except TimeoutException:
                print(f"Timeout on attempt {attempt+1}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    print("Max retries reached for timeout")
                    return False
            except Exception as e:
                print(f"Error navigating to {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                else:
                    return False
        
        return False
    
    def discover_repair_symptoms(self, driver, appliance_type):
        """Discover all repair symptoms for a specific appliance type using PartSelect patterns."""
        print(f"Discovering {appliance_type} repair symptoms...")
        
        symptoms = []
        repair_url = f"{config.scraper.base_url}/{appliance_type.lower()}-repair"
        
        if not self.safe_navigate(driver, repair_url):
            print(f"Failed to navigate to {appliance_type} repair page")
            return symptoms
        
        # PartSelect-specific selectors (more targeted based on their structure)
        symptom_selectors = [
            # PartSelect likely uses specific classes for repair links
            ".nf__links a",  # Similar to parts navigation
            "a[href*='repair']",
            "a[href*='symptom']",
            "a[href*='problem']",
            ".repair-symptom a",
            ".symptom-list a",
            "[class*='symptom'] a",
            "[class*='repair'] a",
            "[class*='problem'] a",
            # Generic fallbacks
            ".content a[href*='repair']",
            "main a[href*='repair']"
        ]
        
        symptom_elements = []
        for selector in symptom_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Found {len(elements)} potential symptom links using selector: {selector}")
                    
                    # Filter for repair-related links
                    filtered_elements = []
                    for elem in elements:
                        href = elem.get_attribute('href')
                        text = elem.text.strip()
                        
                        if (href and ('repair' in href.lower() or 'symptom' in href.lower() or 'problem' in href.lower()) 
                            and text and len(text) > 5):
                            filtered_elements.append(elem)
                    
                    if filtered_elements:
                        symptom_elements = filtered_elements
                        print(f"Filtered to {len(symptom_elements)} actual repair links")
                        break
            except Exception as e:
                print(f"Selector {selector} failed: {e}")
                continue
        
        if not symptom_elements:
            print(f"No symptom links found for {appliance_type}, trying fallback approach...")
            
            # Fallback: Look for any links that might be repair-related
            try:
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links[:50]:  # Check first 50 links
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if (href and text and 
                        any(keyword in href.lower() for keyword in ['repair', 'fix', 'symptom', 'problem']) and
                        len(text) > 10):  # Longer text likely indicates actual repair topics
                        symptom_elements.append(link)
                
                if symptom_elements:
                    print(f"Found {len(symptom_elements)} repair links using fallback method")
            except Exception as e:
                print(f"Fallback approach failed: {e}")
                return symptoms
        
        # Extract symptom information
        for element in symptom_elements[:50]:  # Limit to first 50 symptoms
            try:
                symptom_url = element.get_attribute('href')
                symptom_text = element.text.strip()
                
                # Filter for repair-specific URLs and meaningful text
                if (symptom_url and 'repair' in symptom_url.lower() and 
                    symptom_text and len(symptom_text) > 5):
                    symptoms.append({
                        'symptom': symptom_text,
                        'url': symptom_url,
                        'appliance_type': appliance_type
                    })
            except:
                continue
        
        # Remove duplicates
        unique_symptoms = []
        seen_urls = set()
        for symptom in symptoms:
            if symptom['url'] not in seen_urls:
                unique_symptoms.append(symptom)
                seen_urls.add(symptom['url'])
        
        print(f"Discovered {len(unique_symptoms)} unique {appliance_type} repair symptoms")
        return unique_symptoms
    
    def extract_repair_details(self, driver, symptom_info):
        """Extract detailed repair information from a symptom page."""
        print(f"Extracting details for: {symptom_info['symptom'][:50]}...")
        
        if not self.safe_navigate(driver, symptom_info['url']):
            print("Failed to navigate to repair details page")
            return None
        
        # Extract description
        description = ""
        desc_selectors = [
            ".repair-description",
            ".symptom-description", 
            ".problem-description",
            "[class*='description']",
            ".content p"
        ]
        
        for desc_sel in desc_selectors:
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, desc_sel)
                description = desc_elem.text.strip()
                if description and len(description) > 20:
                    break
            except:
                continue
        
        # Extract difficulty rating
        difficulty = ""
        difficulty_selectors = [
            ".difficulty",
            ".repair-difficulty",
            "[class*='difficulty']",
            ".rating",
            "[data-difficulty]"
        ]
        
        for diff_sel in difficulty_selectors:
            try:
                diff_elem = driver.find_element(By.CSS_SELECTOR, diff_sel)
                difficulty = diff_elem.text.strip()
                if difficulty:
                    break
                # Try data attribute
                difficulty = diff_elem.get_attribute('data-difficulty')
                if difficulty:
                    break
            except:
                continue
        
        # Extract video URL
        repair_video_url = ""
        video_selectors = [
            "iframe[src*='youtube']",
            "iframe[src*='vimeo']",
            ".video-container iframe",
            "[class*='video'] iframe",
            "a[href*='youtube']"
        ]
        
        for video_sel in video_selectors:
            try:
                video_elem = driver.find_element(By.CSS_SELECTOR, video_sel)
                video_url = video_elem.get_attribute('src') or video_elem.get_attribute('href')
                if video_url:
                    # Extract YouTube video ID if it's a YouTube URL
                    if 'youtube.com' in video_url or 'youtu.be' in video_url:
                        repair_video_url = video_url
                        break
                    elif 'vimeo.com' in video_url:
                        repair_video_url = video_url
                        break
            except:
                continue
        
        # Extract parts needed
        parts_needed = ""
        parts_selectors = [
            ".parts-list",
            ".required-parts",
            "[class*='parts'] ul",
            "[class*='parts'] li",
            ".tools-parts"
        ]
        
        parts_list = []
        for parts_sel in parts_selectors:
            try:
                parts_elements = driver.find_elements(By.CSS_SELECTOR, parts_sel)
                for parts_elem in parts_elements:
                    part_text = parts_elem.text.strip()
                    if part_text and len(part_text) > 3:
                        parts_list.append(part_text)
            except:
                continue
        
        if parts_list:
            parts_needed = "; ".join(parts_list[:5])  # Limit to first 5 parts
        
        # Extract estimated time
        estimated_time = ""
        time_selectors = [
            ".repair-time",
            ".estimated-time",
            "[class*='time']",
            ".duration"
        ]
        
        for time_sel in time_selectors:
            try:
                time_elem = driver.find_element(By.CSS_SELECTOR, time_sel)
                estimated_time = time_elem.text.strip()
                if estimated_time:
                    break
            except:
                continue
        
        # Extract model compatibility
        model_compatibility = ""
        model_selectors = [
            ".compatible-models",
            ".model-list",
            "[class*='model'] ul",
            "[class*='compatible']"
        ]
        
        model_list = []
        for model_sel in model_selectors:
            try:
                model_elements = driver.find_elements(By.CSS_SELECTOR, model_sel)
                for model_elem in model_elements:
                    model_text = model_elem.text.strip()
                    if model_text and len(model_text) > 3:
                        model_list.append(model_text)
            except:
                continue
        
        if model_list:
            model_compatibility = "; ".join(model_list[:10])  # Limit to first 10 models
        
        # Create repair data object
        repair_data = {
            'appliance_type': symptom_info['appliance_type'],
            'symptom': symptom_info['symptom'],
            'description': description,
            'difficulty': difficulty,
            'repair_video_url': repair_video_url,
            'parts_needed': parts_needed,
            'estimated_time': estimated_time,
            'model_compatibility': model_compatibility
        }
        
        return repair_data
    
    def scrape_appliance_repairs(self, appliance_type):
        """Scrape all repairs for a specific appliance type."""
        print(f"\n--- Scraping {appliance_type} repairs ---")
        
        driver = self.setup_driver()
        if not driver:
            print(f"Failed to setup driver for {appliance_type}")
            return []
        
        appliance_repairs = []
        
        try:
            # Discover all symptoms for this appliance
            symptoms = self.discover_repair_symptoms(driver, appliance_type)
            
            if not symptoms:
                print(f"No symptoms found for {appliance_type}")
                return appliance_repairs
            
            print(f"Processing {len(symptoms)} {appliance_type} repair symptoms...")
            
            # Extract details for each symptom
            for i, symptom_info in enumerate(symptoms):
                if self.interrupted:
                    break
                
                print(f"Processing symptom {i+1}/{len(symptoms)}: {symptom_info['symptom'][:30]}...")
                
                repair_details = self.extract_repair_details(driver, symptom_info)
                if repair_details:
                    appliance_repairs.append(repair_details)
                    print(f"  ✅ Extracted repair details")
                else:
                    print(f"  ❌ Failed to extract repair details")
                
                # Random delay between repairs to avoid detection
                if i < len(symptoms) - 1:
                    delay = random.uniform(3, 7)
                    print(f"  Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
            
            print(f"Scraped {len(appliance_repairs)} {appliance_type} repairs")
            
        except Exception as e:
            print(f"Error scraping {appliance_type} repairs: {e}")
        
        finally:
            driver.quit()
        
        return appliance_repairs
    
    def _save_data(self, repairs, appliance_type):
        """Save scraped repair data to CSV file."""
        if not repairs:
            print(f"No {appliance_type} repair data to save")
            return
        
        filename = config.files.data_dir / f"{appliance_type.lower()}_repairs.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['appliance_type', 'symptom', 'description', 'difficulty', 
                            'repair_video_url', 'parts_needed', 'estimated_time', 'model_compatibility']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(repairs)
            print(f"Saved {len(repairs)} {appliance_type} repairs to {filename}")
        except Exception as e:
            print(f"Error saving {appliance_type} repair data: {e}")
    
    def _save_all_data(self):
        """Save all scraped data (used for interruption handling)."""
        # Group repairs by appliance type
        dishwasher_repairs = [r for r in self.scraped_repairs if r['appliance_type'] == 'Dishwasher']
        refrigerator_repairs = [r for r in self.scraped_repairs if r['appliance_type'] == 'Refrigerator']
        
        if dishwasher_repairs:
            self._save_data(dishwasher_repairs, 'Dishwasher')
        if refrigerator_repairs:
            self._save_data(refrigerator_repairs, 'Refrigerator')
    
    def scrape_repairs(self):
        """Main method to scrape all appliance repairs."""
        try:
            print("Starting PartSelect repair guides scraping...")
            print(f"Target appliances: {config.scraper.categories}")
            
            # Scrape repairs for each appliance type
            for appliance_type in config.scraper.categories:
                if self.interrupted:
                    break
                
                appliance_repairs = self.scrape_appliance_repairs(appliance_type)
                self.scraped_repairs.extend(appliance_repairs)
                
                # Save data for this appliance type immediately
                self._save_data(appliance_repairs, appliance_type)
                
                print(f"Completed {appliance_type}: {len(appliance_repairs)} repairs")
                print(f"Total repairs scraped: {len(self.scraped_repairs)}")
                
                # Delay between appliance types
                if appliance_type != config.scraper.categories[-1]:
                    delay = random.uniform(10, 20)
                    print(f"Waiting {delay:.1f} seconds before next appliance type...")
                    time.sleep(delay)
            
            # Final summary
            if not self.interrupted:
                print(f"\n✅ Repair scraping completed successfully!")
                print(f"Total repairs scraped: {len(self.scraped_repairs)}")
                
                # Group and display results by appliance type
                for appliance_type in config.scraper.categories:
                    count = len([r for r in self.scraped_repairs if r['appliance_type'] == appliance_type])
                    print(f"  {appliance_type}: {count} repairs")
            
        except Exception as e:
            print(f"Critical error during repair scraping: {e}")
            self._save_all_data()


def main():
    """Run the repair scraper."""
    print("=" * 60)
    print("PartSelect Repair Guides Scraper")
    print("=" * 60)
    
    scraper = RepairScraper()
    scraper.scrape_repairs()


if __name__ == "__main__":
    main()
