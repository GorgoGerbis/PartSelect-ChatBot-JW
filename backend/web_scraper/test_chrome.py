"""
Quick test to check Chrome WebDriver compatibility.
"""
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_undetected_chrome():
    """Test undetected Chrome setup."""
    print("Testing undetected Chrome...")
    try:
        import undetected_chromedriver as uc
        
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = uc.Chrome(options=chrome_options)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Undetected Chrome works! Page title: {title}")
        return True
        
    except Exception as e:
        print(f"❌ Undetected Chrome failed: {e}")
        return False

def test_standard_chrome():
    """Test standard Chrome setup."""
    print("Testing standard Chrome...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.google.com")
        title = driver.title
        driver.quit()
        
        print(f"✅ Standard Chrome works! Page title: {title}")
        return True
        
    except Exception as e:
        print(f"❌ Standard Chrome failed: {e}")
        return False

def main():
    """Test Chrome WebDriver setups."""
    print("Chrome WebDriver Compatibility Test")
    print("=" * 50)
    
    # Test both approaches
    undetected_works = test_undetected_chrome()
    standard_works = test_standard_chrome()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Undetected Chrome: {'✅ Works' if undetected_works else '❌ Failed'}")
    print(f"Standard Chrome: {'✅ Works' if standard_works else '❌ Failed'}")
    
    if undetected_works or standard_works:
        print("\n🎉 At least one Chrome setup works! Scrapers should run.")
    else:
        print("\n😞 Both Chrome setups failed. Check Chrome/ChromeDriver installation.")

if __name__ == "__main__":
    main()
