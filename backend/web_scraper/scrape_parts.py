"""
Scraper for PartSelect refrigerator parts.
Started this a while back, finally got it working properly.
"""
import csv
import time
import random
import os
import sys
import signal
import re
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
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

class PartsScraper:
    def __init__(self):
        self.scraped_parts = []
        self.interrupted = False
        self.progress_file = config.files.data_dir / "refrigerator_parts_progress.csv"
        self.final_file = config.files.data_dir / "refrigerator_parts.csv"
        self.interrupted_file = config.files.data_dir / "refrigerator_parts_interrupted.csv"
        self.error_file = config.files.data_dir / "refrigerator_parts_error.csv"
        
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C interruption gracefully."""
        print("\n\nInterruption detected! Saving current progress...")
        self.interrupted = True
        self._save_data(self.interrupted_file)
        print(f"Progress saved to {self.interrupted_file}")
        sys.exit(0)
    
    def setup_driver(self):
        """Setup Chrome driver with some anti-detection stuff."""
        print("Setting up Chrome driver...")
        
        # Create unique temporary directory for Chrome data
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Using undetected chrome - found this works better than regular selenium
            chrome_options = uc.ChromeOptions()
            
            # Bunch of options to avoid detection - collected these over time
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
            
            # Some performance tweaks
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows") 
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--window-size=1920,1080")  # standard size
            
            # User agent - copied from my regular browser
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            # Set user data directory
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            # Create driver with stealth patches
            driver = uc.Chrome(options=chrome_options, version_main=None)
            
            # Hide webdriver property - found this trick online
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            # Override user agent just to be sure
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            })
            
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(20)
            print("Chrome driver setup successful")
            return driver
            
        except Exception as e:
            print(f"Chrome setup failed: {e}")
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
                
                # Wait for dynamic content
                time.sleep(3)
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
    
    def discover_brands(self, driver):
        """Get list of refrigerator brands to scrape."""
        print("Getting refrigerator brands...")
        
        brands = []
        
        # Try to load brand data from JSON file if it exists
        try:
            import json
            suffix_file = config.files.web_scraper_dir / "suffix" / "Refrigerator.json"
            if suffix_file.exists():
                with open(suffix_file, "r", encoding="utf-8") as f:
                    brand_suffixes = json.load(f)
                
                print(f"Loaded {len(brand_suffixes)} brands from file")
                
                for brand_name, brand_suffix in brand_suffixes.items():
                    # Build the URL for each brand
                    if brand_suffix.startswith('/'):
                        url = f"{config.scraper.base_url.rstrip('/')}{brand_suffix}"
                    else:
                        url = f"{config.scraper.base_url.rstrip('/')}/{brand_suffix}"
                    
                    brands.append({
                        'name': brand_name,
                        'url': url
                    })
                
                print(f"Built {len(brands)} brand URLs from file")
                return brands[:10]  # TODO: remove this limit later
                
        except Exception as e:
            print(f"Could not load brand suffixes: {e}")
        
        # Backup list of major brands if file loading fails
        print("Using hardcoded brand list...")
        fallback_brands = [
            ("Whirlpool", "whirlpool-refrigerator-parts"),
            ("GE", "ge-refrigerator-parts"), 
            ("Frigidaire", "frigidaire-refrigerator-parts"),
            ("Kenmore", "kenmore-refrigerator-parts"),  # most popular ones
            ("Maytag", "maytag-refrigerator-parts"),
            ("Samsung", "samsung-refrigerator-parts"),
            ("LG", "lg-refrigerator-parts"),
            ("KitchenAid", "kitchenaid-refrigerator-parts")
        ]
        
        for brand_name, brand_suffix in fallback_brands:
            url = f"{config.scraper.base_url}/{brand_suffix}"
            brands.append({
                'name': brand_name,
                'url': url
            })
        
        print(f"Set up {len(brands)} brand URLs")
        return brands
    
    def extract_parts_from_page(self, driver, brand_name):
        """Extract parts from the current page."""
        parts = []
        
        # Try the specific selector that works for PartSelect
        try:
            # This selector usually works for their part listings
            part_elements = driver.find_elements(By.CLASS_NAME, "nf__part")
            if part_elements:
                print(f"Found {len(part_elements)} parts using .nf__part selector")
                return self._scrape_parts_with_partselect_logic(part_elements, brand_name)
        except Exception as e:
            print(f"Main selector failed: {e}")
        
        # Try some backup selectors if main one doesn't work
        part_selectors = [
            ".part-item",
            ".product-item", 
            "[class*='part']",  # anything with 'part' in class name
            "[class*='product']",
            ".listing-item"
        ]
        
        part_elements = []
        for selector in part_selectors:
            try:
                part_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if part_elements:
                    print(f"Found {len(part_elements)} parts using backup selector: {selector}")
                    break
            except:
                continue
        
        if not part_elements:
            print("No parts found on this page")
            return parts
        
        for i, part in enumerate(part_elements):
            try:
                # Get part name first
                name = ""
                name_selectors = ["h3", "h4", ".part-name", ".product-name", "[class*='title']"]
                for name_sel in name_selectors:
                    try:
                        name_elem = part.find_element(By.CSS_SELECTOR, name_sel)
                        name = name_elem.text.strip()
                        if name:
                            break
                    except:
                        continue
                
                # Extract part URL
                url = ""
                url_selectors = ["a", ".part-link", ".product-link"]
                for url_sel in url_selectors:
                    try:
                        url_elem = part.find_element(By.CSS_SELECTOR, url_sel)
                        url = url_elem.get_attribute("href")
                        if url:
                            url = urljoin(config.scraper.base_url, url)
                            break
                    except:
                        continue
                
                # Extract description
                description = ""
                desc_selectors = [".description", ".part-desc", "p", ".summary"]
                for desc_sel in desc_selectors:
                    try:
                        desc_elem = part.find_element(By.CSS_SELECTOR, desc_sel)
                        description = desc_elem.text.strip()
                        if description:
                            break
                    except:
                        continue
                
                # Extract part numbers
                partselect_number = ""
                manufacturer_number = ""
                
                # Try to find part numbers in text
                part_num_selectors = [".part-number", ".model-number", "[class*='number']"]
                for num_sel in part_num_selectors:
                    try:
                        num_elem = part.find_element(By.CSS_SELECTOR, num_sel)
                        num_text = num_elem.text.strip()
                        if "PS" in num_text:
                            partselect_number = num_text
                        else:
                            manufacturer_number = num_text
                    except:
                        continue
                
                # Extract price
                price = ""
                price_selectors = [".price", ".cost", "[class*='price']", ".amount"]
                for price_sel in price_selectors:
                    try:
                        price_elem = part.find_element(By.CSS_SELECTOR, price_sel)
                        price = price_elem.text.strip()
                        if price:
                            break
                    except:
                        continue
                
                # Extract stock status
                stock_status = ""
                stock_selectors = [".stock", ".availability", "[class*='stock']", ".in-stock", ".out-stock"]
                for stock_sel in stock_selectors:
                    try:
                        stock_elem = part.find_element(By.CSS_SELECTOR, stock_sel)
                        stock_status = stock_elem.text.strip()
                        if stock_status:
                            break
                    except:
                        continue
                
                # Extract rating and reviews
                rating = ""
                reviews_count = ""
                
                rating_selectors = [".rating", ".stars", "[class*='rating']"]
                for rating_sel in rating_selectors:
                    try:
                        rating_elem = part.find_element(By.CSS_SELECTOR, rating_sel)
                        rating = rating_elem.text.strip()
                        if rating:
                            break
                    except:
                        continue
                
                review_selectors = [".reviews", ".review-count", "[class*='review']"]
                for review_sel in review_selectors:
                    try:
                        review_elem = part.find_element(By.CSS_SELECTOR, review_sel)
                        reviews_count = review_elem.text.strip()
                        if reviews_count:
                            break
                    except:
                        continue
                
                # Extract image URL
                image_url = ""
                img_selectors = ["img", ".part-image img", ".product-image img"]
                for img_sel in img_selectors:
                    try:
                        img_elem = part.find_element(By.CSS_SELECTOR, img_sel)
                        image_url = img_elem.get_attribute("src")
                        if image_url:
                            image_url = urljoin(config.scraper.base_url, image_url)
                            break
                    except:
                        continue
                
                # Only add if we have the basic info we need
                if name and url:
                    part_data = {
                        'name': name,
                        'url': url,
                        'description': description,
                        'partselect_number': partselect_number,
                        'manufacturer_number': manufacturer_number,
                        'price': price,
                        'stock_status': stock_status,
                        'rating': rating,
                        'reviews_count': reviews_count,
                        'image_url': image_url,
                        'brand': brand_name,
                        'category': 'Refrigerator'  # hardcoded for now
                    }
                    parts.append(part_data)
                    if i % 20 == 0:  # don't spam the console too much
                        print(f"  Extracted part {i+1}: {name[:50]}...")
                
            except Exception as e:
                print(f"Error extracting part {i+1}: {e}")
                continue
        
        print(f"Successfully extracted {len(parts)} parts from page")
        return parts
    
    def _scrape_parts_with_partselect_logic(self, part_elements, brand_name):
        """Extract parts using the specific PartSelect page structure."""
        parts = []
        
        for i, part_div in enumerate(part_elements):
            try:
                part_data = {
                    'brand': brand_name,
                    'category': 'Refrigerator'
                }
                
                # Get the part URL
                try:
                    part_link_elem = part_div.find_element(By.CSS_SELECTOR, ".nf__part__left-col__img a")
                    if part_link_elem:
                        part_data["url"] = part_link_elem.get_attribute("href")
                except Exception as e:
                    print(f"Part {i+1}: Can't get URL: {e}")

                # Get image URL - this handles their lazy loading
                img_url = self._extract_image_url(part_div)
                if img_url:
                    part_data["image_url"] = img_url
                    
                # Extract title and part numbers
                try:
                    title_elem = part_div.find_element(By.CSS_SELECTOR, ".nf__part__detail__title span")
                    if title_elem:
                        part_data["name"] = title_elem.text.strip()

                    ps_number_elem = part_div.find_element(By.XPATH, ".//div[contains(text(), 'PartSelect Number')]/strong")
                    if ps_number_elem:
                        part_data["partselect_number"] = ps_number_elem.text.strip()

                    mfr_number_elem = part_div.find_element(By.XPATH, ".//div[contains(text(), 'Manufacturer Part Number')]/strong")
                    if mfr_number_elem:
                        part_data["manufacturer_number"] = mfr_number_elem.text.strip()
                except Exception as e:
                    print(f"Part {i+1}: Title/part number extraction error: {e}")

                # Extract description and clean it up
                try:
                    detail_div = part_div.find_element(By.CLASS_NAME, "nf__part__detail")
                    full_text = detail_div.text
                    
                    # Remove the title from description if it's there
                    if part_data.get("name"):
                        full_text = full_text.replace(part_data["name"], "")
                    
                    # Clean out part number lines - they're redundant
                    import re  # TODO: move this to top of file
                    full_text = re.sub(r"PartSelect Number.*\n", "", full_text)
                    full_text = re.sub(r"Manufacturer Part Number.*\n", "", full_text)
                    
                    # Cut off extra sections we don't need
                    if "Fixes these symptoms" in full_text:
                        full_text = full_text.split("Fixes these symptoms")[0].strip()
                    
                    if "Installation Instructions" in full_text:
                        full_text = full_text.split("Installation Instructions")[0].strip()
                    
                    if full_text:
                        part_data["description"] = full_text.strip()
                except Exception as e:
                    print(f"Part {i+1}: Description extraction error: {e}")

                # Get price info
                try:
                    price_elem = part_div.find_element(By.CSS_SELECTOR, ".price")
                    if price_elem:
                        # They separate currency symbol from amount
                        currency_elem = price_elem.find_element(By.CSS_SELECTOR, ".price__currency")
                        currency = currency_elem.text if currency_elem else "$"
                        price_text = price_elem.text.replace(currency, "").strip()
                        part_data["price"] = f"{currency}{price_text}"
                except Exception as e:
                    # print(f"Part {i+1}: Price extraction error: {e}")  # too noisy
                    pass

                # Get stock status
                try:
                    stock_elem = part_div.find_element(By.CSS_SELECTOR, ".nf__part__left-col__basic-info__stock span")
                    if stock_elem:
                        part_data["stock_status"] = stock_elem.text.strip()
                except Exception as e:
                    print(f"Part {i+1}: Stock status extraction error: {e}")

                # Extract rating info (PartSelect-specific)
                try:
                    rating_elem = part_div.find_element(By.CSS_SELECTOR, ".nf__part__detail__rating")
                    if rating_elem:
                        alt_text = rating_elem.get_attribute("alt")
                        if alt_text and "out of 5" in alt_text:
                            part_data["rating"] = alt_text

                    review_count_elem = part_div.find_element(By.CSS_SELECTOR, ".rating__count")
                    if review_count_elem:
                        match = re.search(r'\d+', review_count_elem.text)
                        if match:
                            part_data["reviews_count"] = int(match.group(0))
                except Exception as e:
                    print(f"Part {i+1}: Rating extraction error: {e}")
                
                # Add to list if we got something useful
                if part_data.get("name") or part_data.get("url"):
                    parts.append(part_data)
                    if i % 10 == 0 and i > 0:  # progress update
                        print(f"Processed {i+1} parts so far...")
                        
            except Exception as e:
                print(f"Part {i+1}: Error: {e}")

        print(f"Got {len(parts)} parts total")
        return parts
    
    def _extract_image_url(self, part_div):
        """Extract image URL handling their lazy loading setup."""
        try:
            picture_elem = part_div.find_element(By.CSS_SELECTOR, "picture")
            if not picture_elem:
                return None
                
            img_elem = picture_elem.find_element(By.TAG_NAME, "img")
            if not img_elem:
                return None
                
            # Check if image is loaded already
            img_class = img_elem.get_attribute("class") or ""
            if "b-loaded" in img_class:
                image_url = img_elem.get_attribute("src")
                if image_url and not image_url.startswith("data:"):
                    return image_url
                    
            # Check data-src attribute for lazy loaded images
            data_src = img_elem.get_attribute("data-src")
            if data_src and not data_src.startswith("data:"):
                return data_src
                
            # Try source elements
            source_elems = picture_elem.find_elements(By.TAG_NAME, "source")
            for source in source_elems:
                srcset = source.get_attribute("srcset")
                if srcset:
                    urls = srcset.split(",")
                    if urls:
                        url = urls[0].strip().split(" ")[0].strip()
                        if url:
                            return url
                            
                data_srcset = source.get_attribute("data-srcset")
                if data_srcset:
                    urls = data_srcset.split(",")
                    if urls:
                        url = urls[0].strip().split(" ")[0].strip()
                        if url:
                            return url
            
            return None
        except Exception as e:
            print(f"Error extracting image URL: {e}")
            return None
    
    def scrape_detailed_part_info(self, driver, part_data):
        """Scrape detailed information from individual part page."""
        part_url = part_data.get('url')
        if not part_url:
            return part_data
        
        print(f"Scraping detailed info for: {part_data.get('name', 'Unknown')}")
        
        if not self.safe_navigate(driver, part_url):
            print(f"Failed to navigate to part page: {part_url}")
            return part_data
        
        try:
            # Extract install difficulty and time (from repair stories section)
            difficulty = ""
            install_time = ""
            try:
                repair_stories = driver.find_elements(By.CSS_SELECTOR, ".repair-story, [class*='repair'], [class*='story']")
                if repair_stories:
                    for story in repair_stories[:3]:  # Check first few stories
                        story_text = story.text.lower()
                        
                        # Extract difficulty
                        if "difficulty level:" in story_text:
                            difficulty_match = re.search(r"difficulty level:\s*([^\\n]+)", story_text)
                            if difficulty_match and not difficulty:
                                difficulty = difficulty_match.group(1).strip()
                        
                        # Extract time
                        if "total repair time:" in story_text:
                            time_match = re.search(r"total repair time:\s*([^\\n]+)", story_text)
                            if time_match and not install_time:
                                install_time = time_match.group(1).strip()
                        
                        if difficulty and install_time:
                            break
            except Exception as e:
                print(f"Error extracting difficulty/time: {e}")
            
            # Extract symptoms (what this part fixes)
            symptoms = ""
            try:
                # Look for symptoms section
                symptom_selectors = [
                    "[class*='symptom']",
                    "[class*='fixes']", 
                    ".product-symptoms",
                    ".part-symptoms"
                ]
                
                for selector in symptom_selectors:
                    symptom_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if symptom_elements:
                        symptom_texts = []
                        for elem in symptom_elements[:5]:  # Limit to first 5
                            text = elem.text.strip()
                            if text and len(text) > 5:
                                symptom_texts.append(text)
                        
                        if symptom_texts:
                            symptoms = " | ".join(symptom_texts)
                            break
                
                # Alternative: look for "Fixes these symptoms" text
                if not symptoms:
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    if "fixes these symptoms" in page_text.lower():
                        symptoms_match = re.search(r"fixes these symptoms[:\\s]*([^\\n\\r]+)", page_text, re.IGNORECASE)
                        if symptoms_match:
                            symptoms = symptoms_match.group(1).strip()
                            
            except Exception as e:
                print(f"Error extracting symptoms: {e}")
            
            # Extract replacement parts (also replaces)
            replace_parts = ""
            try:
                replace_selectors = [
                    "[class*='replace']",
                    "[class*='also']",
                    ".replacement-parts",
                    ".also-replaces"
                ]
                
                for selector in replace_selectors:
                    replace_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if replace_elements:
                        replace_texts = []
                        for elem in replace_elements:
                            text = elem.text.strip()
                            # Look for part numbers (typically alphanumeric with dashes/underscores)
                            part_numbers = re.findall(r'\\b[A-Z0-9][A-Z0-9\\-_]{3,}\\b', text)
                            replace_texts.extend(part_numbers)
                        
                        if replace_texts:
                            replace_parts = ", ".join(replace_texts[:10])  # Limit to 10 part numbers
                            break
                            
            except Exception as e:
                print(f"Error extracting replacement parts: {e}")
            
            # Extract installation video URL
            video_url = ""
            try:
                # Look for YouTube video links
                video_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='youtube.com'], a[href*='youtu.be']")
                if video_links:
                    video_url = video_links[0].get_attribute('href')
                
                # Alternative: look for embedded videos
                if not video_url:
                    video_embeds = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='youtube.com']")
                    if video_embeds:
                        embed_src = video_embeds[0].get_attribute('src')
                        # Convert embed URL to watch URL
                        if 'embed/' in embed_src:
                            video_id = embed_src.split('embed/')[-1].split('?')[0]
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            
            except Exception as e:
                print(f"Error extracting video URL: {e}")
            
            # Update part data with detailed info
            if difficulty:
                part_data['install_difficulty'] = difficulty
            if install_time:
                part_data['install_time'] = install_time
            if symptoms:
                part_data['symptoms'] = symptoms
            if replace_parts:
                part_data['replace_parts'] = replace_parts
            if video_url:
                part_data['install_video_url'] = video_url
                
            print(f"Extracted detailed info: difficulty={difficulty}, time={install_time}, symptoms={bool(symptoms)}, video={bool(video_url)}")
            
        except Exception as e:
            print(f"Error scraping detailed part info: {e}")
        
        return part_data
    
    def scrape_brand_parts(self, brand):
        """Scrape all parts for a specific brand."""
        print(f"\n--- Scraping parts for {brand['name']} ---")
        
        driver = self.setup_driver()
        if not driver:
            print(f"Failed to setup driver for {brand['name']}")
            return []
        
        brand_parts = []
        
        try:
            # Navigate to brand page
            if not self.safe_navigate(driver, brand['url']):
                print(f"Failed to navigate to {brand['name']} page")
                return brand_parts
            
            # Get parts from main brand page
            page_parts = self.extract_parts_from_page(driver, brand['name'])
            
            # Scrape detailed info for each part (this makes it much slower but complete)
            if page_parts:
                print(f"Scraping detailed info for {len(page_parts)} parts...")
                detailed_parts = []
                for i, part in enumerate(page_parts):
                    try:
                        print(f"Getting detailed info for part {i+1}/{len(page_parts)}: {part.get('name', 'Unknown')}")
                        detailed_part = self.scrape_detailed_part_info(driver, part)
                        detailed_parts.append(detailed_part)
                        
                        # Small delay between detailed scrapes to be respectful
                        time.sleep(random.uniform(3, 6))
                        
                    except Exception as e:
                        print(f"Error getting detailed info for {part.get('name', 'Unknown')}: {e}")
                        detailed_parts.append(part)  # Add original part data
                
                brand_parts.extend(detailed_parts)
            else:
                brand_parts.extend(page_parts)
            
            # Try to find pagination or related category pages
            # This could be enhanced to handle multiple pages per brand
            
            print(f"Scraped {len(brand_parts)} parts for {brand['name']}")
            
        except Exception as e:
            print(f"Error scraping {brand['name']}: {e}")
        
        finally:
            driver.quit()
        
        return brand_parts
    
    def _save_data(self, filename):
        """Save scraped data to CSV file in the exact format as parts_dataset.csv."""
        if not self.scraped_parts:
            print("No data to save")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Define exact fieldnames to match parts_dataset.csv structure
                fieldnames = [
                    'part_name',
                    'part_id', 
                    'mpn_id',
                    'part_price',
                    'install_difficulty',
                    'install_time', 
                    'symptoms',
                    'appliance_types',
                    'replace_parts',
                    'brand',
                    'availability',
                    'install_video_url',
                    'product_url'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Transform each part to match the expected format
                for part in self.scraped_parts:
                    # Clean price field
                    price = part.get('price', '')
                    if price:
                        price = price.replace('$\n', '').replace('$', '').strip()
                    
                    csv_row = {
                        'part_name': part.get('name', ''),
                        'part_id': part.get('partselect_number', ''),
                        'mpn_id': part.get('manufacturer_number', ''),
                        'part_price': price,
                        'install_difficulty': part.get('install_difficulty', ''),  # Now available from detailed scraping
                        'install_time': part.get('install_time', ''),  # Now available from detailed scraping
                        'symptoms': part.get('symptoms', ''),  # Now available from detailed scraping
                        'appliance_types': part.get('category', 'Refrigerator') + '.',
                        'replace_parts': part.get('replace_parts', ''),  # Now available from detailed scraping
                        'brand': part.get('brand', ''),
                        'availability': part.get('stock_status', ''),
                        'install_video_url': part.get('install_video_url', ''),  # Now available from detailed scraping
                        'product_url': part.get('url', '')
                    }
                    writer.writerow(csv_row)
                    
            print(f"Saved {len(self.scraped_parts)} parts to {filename}")
        except Exception as e:
            print(f"Error saving data to {filename}: {e}")
    
    def scrape_parts(self):
        """Main method to scrape all refrigerator parts."""
        try:
            print("Starting PartSelect refrigerator parts scraping...")
            print(f"Target URL: {config.scraper.base_url}/refrigerator-parts")
            
            # First, discover all brands
            discovery_driver = self.setup_driver()
            if not discovery_driver:
                print("Failed to setup discovery driver")
                return
            
            brands = self.discover_brands(discovery_driver)
            discovery_driver.quit()
            
            if not brands:
                print("No brands discovered, exiting...")
                return
            
            print(f"Will scrape {len(brands)} brands")
            
            # Use ThreadPoolExecutor for parallel brand processing (max 5 as per spec)
            max_workers = min(5, len(brands))
            brands_processed = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all brand scraping tasks
                future_to_brand = {executor.submit(self.scrape_brand_parts, brand): brand 
                                 for brand in brands}
                
                for future in as_completed(future_to_brand):
                    if self.interrupted:
                        break
                    
                    brand = future_to_brand[future]
                    try:
                        brand_parts = future.result()
                        self.scraped_parts.extend(brand_parts)
                        brands_processed += 1
                        
                        print(f"Completed {brand['name']}: {len(brand_parts)} parts")
                        print(f"Progress: {brands_processed}/{len(brands)} brands, "
                              f"{len(self.scraped_parts)} total parts")
                        
                        # Save progress every 2 brands as per spec
                        if brands_processed % 2 == 0:
                            self._save_data(self.progress_file)
                            print(f"Progress saved after {brands_processed} brands")
                        
                    except Exception as e:
                        print(f"Error processing {brand['name']}: {e}")
            
            # Save final results
            if self.scraped_parts and not self.interrupted:
                self._save_data(self.final_file)
                print(f"\n✅ Parts scraping completed successfully!")
                print(f"Total parts scraped: {len(self.scraped_parts)}")
                print(f"Brands processed: {brands_processed}/{len(brands)}")
                print(f"Final data saved to: {self.final_file}")
            
        except Exception as e:
            print(f"Critical error during parts scraping: {e}")
            if self.scraped_parts:
                self._save_data(self.error_file)
                print(f"Error recovery data saved to: {self.error_file}")


def main():
    """Run the parts scraper."""
    print("=" * 60)
    print("PartSelect Refrigerator Parts Scraper")
    print("=" * 60)
    
    scraper = PartsScraper()
    scraper.scrape_parts()


if __name__ == "__main__":
    main()
