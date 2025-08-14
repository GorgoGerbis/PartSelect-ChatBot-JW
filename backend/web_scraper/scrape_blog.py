"""
Blog scraper for PartSelect articles
Took forever to get the pagination working right
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

# add parent to path for config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import config

class BlogScraper:
    def __init__(self):
        self.driver = None
        self.scraped_articles = []
        self.interrupted = False
        self.progress_file = config.files.data_dir / "partselect_blogs_progress.csv"
        self.final_file = config.files.data_dir / "partselect_blogs.csv"
        self.interrupted_file = config.files.data_dir / "partselect_blogs_interrupted.csv"
        self.error_file = config.files.data_dir / "partselect_blogs_error.csv"
        
        # handle ctrl+c gracefully
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        # handle ctrl+c interruption
        print("\n\nInterruption detected! Saving current progress...")
        self.interrupted = True
        self._save_data(self.interrupted_file)
        if self.driver:
            self.driver.quit()
        print(f"Progress saved to {self.interrupted_file}")
        sys.exit(0)
    
    def setup_driver(self):
        """Setup Chrome driver for blog scraping."""
        print("Setting up Chrome driver...")
        
        # Create unique temporary directory for Chrome data
        temp_dir = tempfile.mkdtemp()
        print(f"Using temporary directory: {temp_dir}")
        
        try:
            # Using undetected chrome for better success rate
            chrome_options = uc.ChromeOptions()
            
            # Standard options to avoid detection
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
            self.driver = uc.Chrome(options=chrome_options, version_main=None)
            
            # Additional stealth: execute script to remove automation indicators
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            })
            
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(20)
            print("Chrome driver ready")
            return True
            
        except Exception as e:
            print(f"Chrome setup failed: {e}")
            print("Might be a version issue with undetected-chromedriver")
            print("Try: pip install --upgrade undetected-chromedriver")
            return False
    
    def safe_navigate(self, url, max_retries=3):
        """Safely navigate to URL with retry mechanism."""
        for attempt in range(max_retries):
            try:
                print(f"Navigating to {url} (attempt {attempt+1}/{max_retries})")
                self.driver.get(url)
                
                # Wait for page to load completely
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Check for access denied or bot detection
                page_source = self.driver.page_source.lower()
                title = self.driver.title.lower()
                
                if ("access denied" in title or "forbidden" in title or 
                    "blocked" in title or "captcha" in page_source or
                    "cloudflare" in page_source):
                    print("Bot detection/access denied detected, using longer delay...")
                    if attempt < max_retries - 1:
                        delay = random.uniform(15, 30)  # Much longer delay
                        print(f"Waiting {delay:.1f} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        print("Max retries reached for bot detection")
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
    
    def get_total_pages(self):
        """Figure out how many blog pages there are total."""
        try:
            # Try different pagination selectors
            pagination_selectors = [
                ".pagination a",
                ".page-numbers a", 
                "[class*='pagination'] a",
                "[class*='page'] a",
                "nav a",  # Generic navigation
                ".nav-links a"  # WordPress-style
            ]
            
            page_numbers = []
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"Found {len(elements)} pagination elements with selector: {selector}")
                    
                    for element in elements:
                        text = element.text.strip()
                        href = element.get_attribute('href')
                        
                        # Check for numeric text
                        if text.isdigit():
                            page_numbers.append(int(text))
                        
                        # Also check href for page numbers
                        if href and 'page/' in href:
                            try:
                                page_num = int(href.split('page/')[-1].split('/')[0])
                                page_numbers.append(page_num)
                            except:
                                pass
                    
                    if page_numbers:
                        break
                except Exception as e:
                    print(f"Selector {selector} failed: {e}")
                    continue
            
            if page_numbers:
                total_pages = max(page_numbers)
                print(f"Found {total_pages} total pages from pagination")
                return min(total_pages, 50)  # Cap at 50 pages for safety
            else:
                print("Could not determine total pages, trying content-based detection...")
                
                # Try to estimate based on content
                try:
                    articles = self.driver.find_elements(By.CSS_SELECTOR, "article, .post, [class*='post']")
                    if articles:
                        print(f"Found {len(articles)} articles on first page, estimating 20 pages")
                        return 20
                except:
                    pass
                
                print("Using default of 10 pages")
                return 10  # Final fallback
                
        except Exception as e:
            print(f"Error getting total pages: {e}")
            return 10  # Fallback
    
    def extract_articles_from_page(self):
        """Extract all articles from current page."""
        articles = []
        
        # Multiple selectors to try for articles
        article_selectors = [
            "article",
            ".post",
            ".blog-post",
            "[class*='post']",
            "[class*='article']",
            ".entry"
        ]
        
        for selector in article_selectors:
            try:
                article_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if article_elements:
                    print(f"Found {len(article_elements)} articles using selector: {selector}")
                    break
            except:
                continue
        
        if not article_elements:
            print("No articles found on this page")
            return articles
        
        for i, article in enumerate(article_elements):
            try:
                # Extract title
                title = ""
                title_selectors = ["h1", "h2", "h3", ".title", ".post-title", "[class*='title']"]
                for title_sel in title_selectors:
                    try:
                        title_elem = article.find_element(By.CSS_SELECTOR, title_sel)
                        title = title_elem.text.strip()
                        if title:
                            break
                    except:
                        continue
                
                # Extract URL
                url = ""
                url_selectors = ["a", ".read-more", "[href]"]
                for url_sel in url_selectors:
                    try:
                        url_elem = article.find_element(By.CSS_SELECTOR, url_sel)
                        url = url_elem.get_attribute("href")
                        if url:
                            url = urljoin(config.scraper.base_url, url)
                            break
                    except:
                        continue
                
                # Extract summary/content preview
                summary = ""
                summary_selectors = [".excerpt", ".summary", ".content", ".post-content", "p"]
                for summary_sel in summary_selectors:
                    try:
                        summary_elem = article.find_element(By.CSS_SELECTOR, summary_sel)
                        summary = summary_elem.text.strip()[:500]  # Limit to 500 chars
                        if summary:
                            break
                    except:
                        continue
                
                # Extract featured image
                featured_image = ""
                img_selectors = ["img", ".featured-image img", ".post-image img"]
                for img_sel in img_selectors:
                    try:
                        img_elem = article.find_element(By.CSS_SELECTOR, img_sel)
                        featured_image = img_elem.get_attribute("src")
                        if featured_image:
                            featured_image = urljoin(config.scraper.base_url, featured_image)
                            break
                    except:
                        continue
                
                # Extract metadata (author, date, category)
                author = ""
                publish_date = ""
                category = ""
                
                # Try to find author
                author_selectors = [".author", ".by-author", "[class*='author']"]
                for author_sel in author_selectors:
                    try:
                        author_elem = article.find_element(By.CSS_SELECTOR, author_sel)
                        author = author_elem.text.strip()
                        if author:
                            break
                    except:
                        continue
                
                # Try to find date
                date_selectors = [".date", ".published", "time", "[class*='date']"]
                for date_sel in date_selectors:
                    try:
                        date_elem = article.find_element(By.CSS_SELECTOR, date_sel)
                        publish_date = date_elem.text.strip()
                        if publish_date:
                            break
                    except:
                        continue
                
                # Try to find category
                cat_selectors = [".category", ".tag", "[class*='category']", "[class*='tag']"]
                for cat_sel in cat_selectors:
                    try:
                        cat_elem = article.find_element(By.CSS_SELECTOR, cat_sel)
                        category = cat_elem.text.strip()
                        if category:
                            break
                    except:
                        continue
                
                # Only add if we have at least title and URL
                if title and url:
                    article_data = {
                        'title': title,
                        'url': url,
                        'summary': summary,
                        'author': author,
                        'publish_date': publish_date,
                        'category': category,
                        'featured_image': featured_image,
                        'tags': '',  # Could be enhanced to extract tags
                        'content_preview': summary[:200]  # First 200 chars as preview
                    }
                    articles.append(article_data)
                    print(f"  Extracted article {i+1}: {title[:50]}...")
                
            except Exception as e:
                print(f"Error extracting article {i+1}: {e}")
                continue
        
        print(f"Successfully extracted {len(articles)} articles from page")
        return articles
    
    def _save_data(self, filename):
        """Save scraped data to CSV file."""
        if not self.scraped_articles:
            print("No data to save")
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'url', 'summary', 'author', 'publish_date', 
                            'category', 'featured_image', 'tags', 'content_preview']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.scraped_articles)
            print(f"Saved {len(self.scraped_articles)} articles to {filename}")
        except Exception as e:
            print(f"Error saving data to {filename}: {e}")
    
    def scrape_blogs(self):
        """Main method to scrape all blog articles."""
        try:
            print("Starting PartSelect blog scraping...")
            print(f"Target URL: {config.scraper.base_url}/blog")
            
            if not self.setup_driver():
                print("Failed to setup driver")
                return
            
            # Navigate to blog main page
            blog_url = f"{config.scraper.base_url}/blog"
            if not self.safe_navigate(blog_url):
                print("Failed to navigate to blog page")
                return
            
            # Get total pages
            total_pages = self.get_total_pages()
            print(f"Will scrape {total_pages} pages")
            
            # Scrape each page
            for page_num in range(1, total_pages + 1):
                if self.interrupted:
                    break
                
                print(f"\n--- Scraping page {page_num}/{total_pages} ---")
                
                # Navigate to specific page (if not first page)
                if page_num > 1:
                    page_url = f"{blog_url}/page/{page_num}"
                    if not self.safe_navigate(page_url):
                        print(f"Failed to navigate to page {page_num}, skipping...")
                        continue
                
                # Extract articles from current page
                page_articles = self.extract_articles_from_page()
                self.scraped_articles.extend(page_articles)
                
                print(f"Total articles scraped so far: {len(self.scraped_articles)}")
                
                # Save progress every 3 pages
                if page_num % 3 == 0:
                    self._save_data(self.progress_file)
                    print(f"Progress saved after page {page_num}")
                
                # Random delay between pages (5-12 seconds as per spec)
                if page_num < total_pages:
                    delay = random.uniform(5, 12)
                    print(f"Waiting {delay:.1f} seconds before next page...")
                    time.sleep(delay)
            
            # Save final results
            if self.scraped_articles and not self.interrupted:
                self._save_data(self.final_file)
                print(f"\n✅ Blog scraping completed successfully!")
                print(f"Total articles scraped: {len(self.scraped_articles)}")
                print(f"Final data saved to: {self.final_file}")
            
        except Exception as e:
            print(f"Critical error during blog scraping: {e}")
            if self.scraped_articles:
                self._save_data(self.error_file)
                print(f"Error recovery data saved to: {self.error_file}")
        
        finally:
            if self.driver:
                print("Closing browser...")
                self.driver.quit()


def main():
    """Run the blog scraper."""
    print("=" * 60)
    print("PartSelect Blog Scraper")
    print("=" * 60)
    
    scraper = BlogScraper()
    scraper.scrape_blogs()


if __name__ == "__main__":
    main()
