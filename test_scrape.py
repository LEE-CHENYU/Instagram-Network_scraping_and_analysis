#!/usr/bin/env python3
"""
Simple test script to verify the Instagram scraper functionality
"""

import os
import json
import time
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import essentialRoutines

# Constants
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers.json")
FOLLOWING_FILE = os.path.join(DATA_DIR, "following.json")
CURSOR_FILE = os.path.join(DATA_DIR, "next_cursor.json")
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")

# Instagram credentials
USERNAME = "fretin98"
PASSWORD = "Lcy199818su!"
MAX_PAGES = 2

# Ensure the data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Created directory: {DATA_DIR}")

# Set up Chrome options
options = Options()
PATH = "/Users/chenyusu/Documents/GitHub/Instagram-Network_scraping_and_analysis/chromedriver"
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
options.add_argument("--headless")
options.add_argument("--window-size=1920,1080")
service = Service(executable_path=PATH)

# Save data helper function
def save_data(data, file_path):
    """Save data to a file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {file_path}")

try:
    print("Starting test scrape...")
    driver = webdriver.Chrome(service=service, options=options)
    
    # Login to Instagram
    essentialRoutines.login_insta(driver, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")
    time.sleep(5)
    
    # Go to profile
    driver.get(f"https://www.instagram.com/{USERNAME}/")
    time.sleep(3)
    
    # Get account stats
    profile_stats = essentialRoutines.get_profile_stats(driver)
    follower_count = profile_stats.get('followers', 0)
    following_count = profile_stats.get('following', 0)
    
    print(f"Profile Stats: {profile_stats}")
    print(f"Followers: {follower_count}, Following: {following_count}")
    
    # Try to scrape just followers as a test
    print("\nScraping followers (limited to 2 pages)...")
    try:
        # Initialize
        my_followers = []
        next_cursor = {"followers": None}
        
        # Call the scrape function with explicit parameters
        followers, cursor = essentialRoutines.scrape_whole_list(
            list_to_scrape="followers",
            driver=driver,
            link=f"https://www.instagram.com/{USERNAME}/",
            next_cursor=None,
            resume_from_saved=my_followers,
            max_pages=MAX_PAGES
        )
        
        print(f"Successfully scraped {len(followers)} followers")
        print(f"Next cursor: {cursor}")
        
        # Save the data
        next_cursor["followers"] = cursor
        my_followers.extend(followers)
        
        save_data(my_followers, FOLLOWERS_FILE)
        save_data(next_cursor, CURSOR_FILE)
        
        print(f"Total followers retrieved: {len(my_followers)}/{follower_count}")
        
    except Exception as e:
        print(f"Error scraping followers: {e}")
        traceback.print_exc()
    
    print("\nTest completed!")
    
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

finally:
    if 'driver' in locals():
        driver.close()
        print("Browser closed.") 