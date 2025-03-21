#%% Loading libraries
import time
import traceback
import os
import json
import argparse
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import essentialRoutines

#%% Define constants for file paths
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers.json")
FOLLOWING_FILE = os.path.join(DATA_DIR, "following.json")
CURSOR_FILE = os.path.join(DATA_DIR, "next_cursor.json")
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")

#%% Helper functions
def ensure_data_directory():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created data directory: {DATA_DIR}")

def load_saved_data(file_path, default=None):
    """Load saved data from a file"""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return default if default is not None else {}

def save_data(data, file_path):
    """Save data to a file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {file_path}")

def dict_to_adj_list(following_dict):
    """Convert dictionary of following to adjacency list format"""
    adj_list = []
    for follower, followings in following_dict.items():
        for followed in followings:
            adj_list.append(f"{follower} {followed}\n")
    return adj_list

def update_adj_list_file(my_username, my_following):
    """Update adjacency list file with user's following"""
    following_dict = {my_username: my_following}
    adj_list = dict_to_adj_list(following_dict)
    
    with open(ADJ_LIST_FILE, "w") as file_h:
        file_h.writelines(adj_list)
    print(f"Updated adjacency list file: {ADJ_LIST_FILE}")

def update_following_links_file(my_following_links):
    """Update file containing links to following accounts"""
    with open(FOLLOWING_LINKS_FILE, "w") as file_h:
        file_h.writelines([f"{link}\n" for link in my_following_links])
    print(f"Updated following links file: {FOLLOWING_LINKS_FILE}")

#%% Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Account Scraper')
    parser.add_argument('--username', default="fretin98", help='Instagram username')
    parser.add_argument('--password', default="Lcy199818su!", help='Instagram password')
    parser.add_argument('--no-followers', action='store_true', help='Skip scraping followers')
    parser.add_argument('--no-following', action='store_true', help='Skip scraping following')
    parser.add_argument('--resume', action='store_true', help='Resume previous scraping session')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum number of pages to scrape (default: 10)')
    return parser.parse_args()

#%% Main execution
if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Set up Chrome options
    options = Options()
    PATH = "/Users/chenyusu/Documents/GitHub/Instagram-Network_scraping_and_analysis/chromedriver"  # Chromedriver path
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    if args.headless:
        options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    service = Service(executable_path=PATH)
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Login to Instagram
        essentialRoutines.login_insta(driver, args.username, args.password)
        print(f"Logged in as {args.username}")
        time.sleep(5)  # Wait for login to complete
        
        # Check for previous session data
        saved_followers = load_saved_data(FOLLOWERS_FILE, [])
        saved_following = load_saved_data(FOLLOWING_FILE, [])
        saved_cursor = load_saved_data(CURSOR_FILE, {})
        
        # Initialize variables for this session
        my_followers = []
        my_following = []
        next_cursor = {"followers": None, "following": None}
        
        if args.resume and (saved_followers or saved_following or saved_cursor):
            print("Resuming previous session...")
            my_followers = saved_followers
            my_following = saved_following
            next_cursor = saved_cursor
            print(f"Loaded {len(my_followers)} followers and {len(my_following)} following from previous session")
        
        # Navigate to user's profile
        driver.get(f"https://www.instagram.com/{args.username}/")
        time.sleep(3)
        
        # Get account information
        profile_stats = essentialRoutines.get_profile_stats(driver)
        follower_count = profile_stats.get('followers', 0)
        following_count = profile_stats.get('following', 0)
        
        print(f"\nProfile Stats: {profile_stats}")
        print(f"Followers: {follower_count}, Following: {following_count}")
        
        # Scrape followers if requested
        if not args.no_followers:
            print("\nScraping followers...")
            try:
                new_followers, next_cursor['followers'] = essentialRoutines.scrape_whole_list(
                    "followers", 
                    driver, 
                    f"https://www.instagram.com/{args.username}/",
                    max_pages=args.max_pages,
                    next_cursor=next_cursor.get('followers')
                )
                
                # Merge with existing followers, remove duplicates
                my_followers.extend(new_followers)
                my_followers = list(dict.fromkeys(my_followers))  # Remove duplicates
                
                print(f"Total followers retrieved: {len(my_followers)}/{follower_count}")
                
                # Save followers data
                save_data(my_followers, FOLLOWERS_FILE)
                save_data(next_cursor, CURSOR_FILE)
            except Exception as e:
                print(f"Error scraping followers: {e}")
                traceback.print_exc()
        
        # Scrape following if requested
        if not args.no_following:
            print("\nScraping following...")
            try:
                new_following, next_cursor['following'] = essentialRoutines.scrape_whole_list(
                    "following", 
                    driver, 
                    f"https://www.instagram.com/{args.username}/",
                    max_pages=args.max_pages,
                    next_cursor=next_cursor.get('following')
                )
                
                # Merge with existing following, remove duplicates
                my_following.extend(new_following)
                my_following = list(dict.fromkeys(my_following))  # Remove duplicates
                
                print(f"Total following retrieved: {len(my_following)}/{following_count}")
                
                # Save following data
                save_data(my_following, FOLLOWING_FILE)
                save_data(next_cursor, CURSOR_FILE)
            except Exception as e:
                print(f"Error scraping following: {e}")
                traceback.print_exc()
        
        # Get links to following accounts
        if my_following:
            print("\nGetting links to following accounts...")
            try:
                # Get following profile links
                my_following_links = essentialRoutines.get_following_links(driver, following_usernames=my_following)
                update_following_links_file(my_following_links)
                
                # Update adjacency list
                update_adj_list_file(args.username, my_following)
                
                print(f"Retrieved {len(my_following_links)} following links")
            except Exception as e:
                print(f"Error getting following links: {e}")
                traceback.print_exc()
        
        print("\nSession completed successfully!")
    
    except Exception as e:
        print(f"Error occurred: {e}")
        traceback.print_exc()
    
    finally:
        # Close the driver
        driver.close()
        print("Browser closed.")
