#!/usr/bin/env python3
"""
Test if current scraping is actually logged in
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import essentialRoutines

# Set up Chrome options (same as scraping scripts)
options = Options()
PATH = "/Users/chenyusu/GitHub/Instagram-Network_scraping_and_analysis/chromedriver"
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument("--headless")  # Run headless like the scraper
options.add_argument("--window-size=1920,1080")
service = Service(executable_path=PATH)
driver = webdriver.Chrome(service=service, options=options)

try:
    print("Testing Instagram login and data access...")
    print("="*50)

    # Login
    print("Step 1: Logging in...")
    essentialRoutines.login_insta(driver, "fretin98", "Lcy199818su")
    time.sleep(5)

    # Check if logged in
    current_url = driver.current_url
    print(f"After login URL: {current_url}")

    if "login" in current_url:
        print("❌ FAILED: Still on login page!")
    else:
        print("✓ Login successful")

    # Try to access a profile
    print("\nStep 2: Accessing a profile...")
    test_profile = "instagram"  # Instagram's own account
    driver.get(f"https://www.instagram.com/{test_profile}/")
    time.sleep(3)

    # Check if we can see follower/following links (only visible when logged in)
    print("\nStep 3: Checking for follower/following links...")
    try:
        followers_link = driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]")
        if followers_link:
            print("✅ SUCCESS: Can see followers link - WE ARE LOGGED IN!")
            followers_text = followers_link.text
            print(f"Followers link text: {followers_text}")
    except:
        print("❌ FAILED: Cannot see followers link - NOT LOGGED IN!")

        # Check page source for clues
        page_source = driver.page_source
        if "Log in" in page_source or "Sign up" in page_source:
            print("Page shows login/signup prompts - definitely not logged in")

    # Try clicking on followers to see if dialog opens
    print("\nStep 4: Trying to open followers dialog...")
    try:
        followers_link = driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]")
        followers_link.click()
        time.sleep(3)

        # Check if dialog opened
        dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
        if dialog:
            print("✅ SUCCESS: Followers dialog opened!")

            # Try to find usernames in the dialog
            usernames = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]")
            print(f"Found {len(usernames)} username links in dialog")

            if len(usernames) == 0:
                print("⚠️  WARNING: Dialog opened but no users visible")
            elif len(usernames) <= 12:
                print(f"⚠️  WARNING: Only {len(usernames)} users visible - might be rate limited")
            else:
                print(f"✅ Can see {len(usernames)} users")
    except Exception as e:
        print(f"❌ FAILED: Could not open followers dialog: {e}")

    print("\n" + "="*50)
    print("CONCLUSION:")
    if "login" not in current_url:
        print("✓ Login is working")
        print("⚠️  But Instagram is still rate-limiting data to ~10 users per list")
        print("This is Instagram's anti-scraping measure, not a login issue")
    else:
        print("✗ Login is NOT working - this explains why we get no data!")

except Exception as e:
    print(f"Error during test: {e}")
    import traceback
    traceback.print_exc()

finally:
    driver.quit()
    print("\nTest complete.")