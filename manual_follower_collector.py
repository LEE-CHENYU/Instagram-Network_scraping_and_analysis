import time
import json
import os
import sys
import argparse
import tkinter as tk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constants
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers_manual.json")

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
    return default if default is not None else []

def save_data(data, file_path):
    """Save data to a file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved data to {file_path}")

def login_insta(driver, username, password):
    """Log in to Instagram"""
    driver.get("https://www.instagram.com/")
    time.sleep(3)
    
    try:
        # Handle cookie dialog if it appears
        try:
            cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Allow')]"))
            )
            cookie_button.click()
            time.sleep(1)
        except:
            pass
        
        # Find username and password fields
        username_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']"))
        )
        password_field = driver.find_element(By.CSS_SELECTOR, "input[name='password']")
        
        # Enter credentials
        username_field.clear()
        username_field.send_keys(username)
        password_field.clear()
        password_field.send_keys(password)
        
        # Click login button
        login_button = driver.find_element(By.XPATH, "//button[contains(.,'Log in')]")
        login_button.click()
        time.sleep(5)
        
        # Handle "Save Login Info" dialog if it appears
        try:
            not_now_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now_button.click()
        except:
            pass
            
        # Handle notifications dialog if it appears
        try:
            not_now_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]"))
            )
            not_now_button.click()
        except:
            pass
            
        print(f"Logged in as {username}")
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False

def extract_usernames(driver):
    """Extract usernames from the followers modal"""
    usernames = []
    
    # Try multiple methods to extract usernames
    try:
        # Method 1: Modern profile layout (most common)
        elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href, '/')]")
        
        # Filter to only username links (not hashtags, etc.)
        for element in elements:
            href = element.get_attribute('href')
            if href and '/p/' not in href and '/explore/' not in href and '/stories/' not in href:
                try:
                    username = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                    if username and username != "":
                        usernames.append(username)
                except:
                    pass
    except:
        pass
        
    # Method 2: Alternative structure
    if len(usernames) == 0:
        try:
            # Look for elements with username class
            elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[contains(@class, 'notranslate')]")
            for element in elements:
                try:
                    username = element.text
                    if username and username != "":
                        usernames.append(username)
                except:
                    pass
        except:
            pass
    
    # Method 3: Last resort - any link with short text
    if len(usernames) == 0:
        try:
            elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//a")
            for element in elements:
                try:
                    username = element.text
                    if username and len(username) > 2 and len(username) < 30:
                        usernames.append(username)
                except:
                    pass
        except:
            pass
    
    # Remove duplicates while preserving order
    unique_usernames = []
    seen = set()
    for username in usernames:
        if username not in seen:
            seen.add(username)
            unique_usernames.append(username)
    
    return unique_usernames

def create_control_window(driver, username):
    """Create a control window with buttons to collect followers"""
    window = tk.Tk()
    window.title("Instagram Manual Follower Collector")
    window.geometry("500x300")
    
    # Load existing followers
    existing_followers = load_saved_data(FOLLOWERS_FILE, [])
    existing_count = len(existing_followers)
    
    # Status label
    status_var = tk.StringVar()
    status_var.set(f"Ready. {existing_count} followers already collected.")
    status_label = tk.Label(window, textvariable=status_var, pady=10)
    status_label.pack(fill='x')
    
    # Instructions
    instructions = tk.Label(window, text="1. Scroll through your followers list manually\n2. Click 'Collect Followers' when ready\n3. Click 'Save & Exit' when finished", pady=10)
    instructions.pack()
    
    # Create a function to collect followers
    def collect_followers():
        try:
            usernames = extract_usernames(driver)
            existing_followers = load_saved_data(FOLLOWERS_FILE, [])
            
            # Count new followers
            existing_set = set(existing_followers)
            new_count = 0
            for username in usernames:
                if username not in existing_set:
                    existing_followers.append(username)
                    existing_set.add(username)
                    new_count += 1
            
            # Remove duplicates
            existing_followers = list(dict.fromkeys(existing_followers))
            
            # Update status
            status_var.set(f"Collected {len(usernames)} visible followers ({new_count} new). Total: {len(existing_followers)}")
            print(f"Collected {len(usernames)} followers from view ({new_count} new)")
            
            # Save data
            save_data(existing_followers, FOLLOWERS_FILE)
            messagebox.showinfo("Collection Complete", f"Collected {new_count} new followers\nTotal: {len(existing_followers)}")
        except Exception as e:
            status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to collect followers: {str(e)}")
    
    # Function to save and exit
    def save_and_exit():
        driver.quit()
        window.destroy()
        sys.exit(0)
    
    # Collect button
    collect_button = tk.Button(window, text="Collect Followers", command=collect_followers, padx=20, pady=10, bg="#4CAF50", fg="white")
    collect_button.pack(pady=20)
    
    # Save & exit button
    exit_button = tk.Button(window, text="Save & Exit", command=save_and_exit, padx=20, pady=10, bg="#f44336", fg="white")
    exit_button.pack(pady=10)
    
    # Shortcut labels
    shortcuts_label = tk.Label(window, text="Note: Keep this window open while you scroll in the browser window.")
    shortcuts_label.pack(pady=10)
    
    return window

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Manual Instagram Follower Collector')
    parser.add_argument('--username', default="fretin98", help='Instagram username')
    parser.add_argument('--password', default="Lcy199818su!", help='Instagram password')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (not recommended for manual scrolling)')
    args = parser.parse_args()
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Set up Chrome options
    options = Options()
    PATH = "/Users/chenyusu/Documents/GitHub/Instagram-Network_scraping_and_analysis/chromedriver"  # Chromedriver path
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    service = Service(executable_path=PATH)
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Login to Instagram
        login_success = login_insta(driver, args.username, args.password)
        if not login_success:
            print("Failed to log in. Exiting.")
            driver.quit()
            return
        
        # Navigate to the user's profile
        profile_url = f"https://www.instagram.com/{args.username}/"
        driver.get(profile_url)
        time.sleep(3)
        
        # Open followers modal
        try:
            # Try standard link first
            followers_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]"))
            )
            followers_button.click()
        except:
            # If that fails, try alternate methods
            try:
                followers_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'followers')]"))
                )
                followers_button.click()
            except:
                try:
                    # Try the list item approach
                    followers_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//ul/li[contains(., 'follower')]"))
                    )
                    followers_button.click()
                except Exception as e:
                    print(f"Could not click on followers: {e}")
                    driver.quit()
                    return
        
        # Wait for the modal to load
        time.sleep(3)
        
        # Create control window
        print("Followers modal opened. You can now scroll manually.")
        print("Use the control window to collect followers when ready.")
        window = create_control_window(driver, args.username)
        
        # Start the main loop for the control window
        window.mainloop()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    main()