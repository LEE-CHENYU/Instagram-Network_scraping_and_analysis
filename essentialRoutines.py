import time
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import random
import json
from selenium.webdriver import ActionChains
import os
import datetime

# Add global variables to track cursors
_last_cursors = {
    'followers': None,
    'following': None
}

# Add rate limit tracking
_rate_limit_info = {
    'followers': {
        'last_hit': None,
        'retry_count': 0
    },
    'following': {
        'last_hit': None,
        'retry_count': 0
    }
}

# Rate limit constants
RATE_LIMIT_THRESHOLD = 10  # Instagram typically limits to 10 users per request
RATE_LIMIT_WAIT_TIME = 600  # 10 minutes in seconds - base wait time
MAX_RATE_LIMIT_RETRIES = 5  # Maximum number of retries before giving up

def get_last_cursor(list_type):
    """Get the last cursor for the specified list type"""
    return _last_cursors.get(list_type)

def dict_to_adjList(allNodes):
    adjList = []
    for person,following in allNodes.items():
        f = " ".join(following)
        adjList.append(person +" "+ f + "\n")
        
    return adjList

def adjList_to_dict(adjList):
    allNodes = {}
    for line in adjList:
        list_of_persons = line.strip('\n').split(" ")
        person = list_of_persons[0]
        following = list_of_persons[1:]
        allNodes[person] = following
        
    return allNodes


def check_if_stuck(prev_scrape_sizes, new_scrape_size):
    occurences = Counter(prev_scrape_sizes)
    for v in occurences.values():
        if v > 38:
            return (True,prev_scrape_sizes)
        
    if len(prev_scrape_sizes) >= 40:
        del prev_scrape_sizes[0]
    prev_scrape_sizes.append(new_scrape_size)
        
    return (False, prev_scrape_sizes)


def login_insta(driver,username,password):
    driver.get("https://www.instagram.com/accounts/login")
    time.sleep(5)  # Increased wait time
    
    # Input username and password
    try:
        # Try different username input selectors
        username_selectors = [
            "//input[@name='username']",
            "//input[@aria-label='Phone number, username, or email']",
            "//input[contains(@aria-label, 'username')]"
        ]
        
        for selector in username_selectors:
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                ).send_keys(username)
                break
            except:
                continue
                
        # Try different password input selectors
        password_selectors = [
            "//input[@name='password']",
            "//input[@aria-label='Password']",
            "//input[contains(@aria-label, 'password')]",
            "//input[@type='password']"
        ]
        
        for selector in password_selectors:
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                ).send_keys(password)
                break
            except:
                continue
        
        # Try different possible login button selectors
        login_buttons = [
            "//button[contains(.,'Log In')]",
            "//button[contains(.,'Log in')]",
            "//button[@type='submit']",
            "//button[contains(@class,'_acan _acap')]",
            "//div[contains(text(), 'Log In')]/parent::button",
            "//div[contains(text(), 'Log in')]/parent::button"
        ]
        
        for button_xpath in login_buttons:
            try:
                login_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath))
                )
                login_button.click()
                print(f"Logged in using button: {button_xpath}")
                break
            except:
                continue
        
        # Wait for login to complete
        time.sleep(5)
        
        # Handle "Save Your Login Info" dialog if it appears
        try:
            save_info_buttons = [
                "//button[contains(text(), 'Not Now')]", 
                "//button[contains(text(), 'Not now')]",
                "//div[contains(text(), 'Not Now')]"
            ]
            
            for button in save_info_buttons:
                try:
                    WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, button))
                    ).click()
                    break
                except:
                    continue
        except:
            pass
        
        # Check if login was successful
        if "instagram.com/accounts/login" in driver.current_url:
            print("Login might have failed. Current URL still shows login page.")
        else:
            print("Logged in successfully!")
            
    except Exception as e:
        print(f"Login error: {e}")
        driver.save_screenshot('login_error.png')
        raise

        
def get_following_links(driver, following_usernames=None):
    """Get links to following users' profiles
    
    Args:
        driver: Selenium webdriver instance
        following_usernames: Optional list of usernames to create links from (bypassing UI scraping)
    
    Returns:
        List of profile URLs
    """
    # If we already have usernames from API, just construct the links directly
    if following_usernames and len(following_usernames) > 0:
        links = [f"https://www.instagram.com/{username}/" for username in following_usernames]
        print(f"Created {len(links)} following links from usernames")
        return links
    
    # Otherwise, try to extract from UI
    try:
        # Try multiple selectors for getting following links
        selectors = [
            "li.wo9IH span a",  # Old UI
            "div[role='dialog'] li a",  # Generic dialog selector
            "div[role='dialog'] a[href^='/']",  # More generic
            "//div[contains(@role,'dialog')]//li//a[contains(@href,'/')]",  # XPATH version
            "//div[contains(@role,'dialog')]//a[contains(@href,'/') and not(contains(@href, 'explore'))]"  # Exclude non-profile links
        ]
        
        links = []
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    followList = driver.find_elements(By.XPATH, selector)
                else:
                    followList = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for item in followList:
                    try:
                        href = item.get_attribute("href")
                        if href and href.startswith("https://www.instagram.com/") and not "/p/" in href and href not in links:
                            links.append(href)
                    except Exception as e:
                        print(f"Error getting href: {e}")
                
                if links:
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"Error finding following links: {e}")
        driver.save_screenshot('following_links_error.png')
        links = []
    
    # If UI approach failed, try JavaScript
    if not links:
        try:
            js_script = """
            const links = Array.from(document.querySelectorAll('a'))
                .filter(a => a.href && a.href.startsWith('https://www.instagram.com/') && 
                        !a.href.includes('/p/') && !a.href.includes('/explore/'))
                .map(a => a.href);
            return [...new Set(links)];  // Remove duplicates
            """
            js_links = driver.execute_script(js_script)
            if js_links and len(js_links) > 0:
                links = js_links
        except Exception as e:
            print(f"JavaScript link extraction failed: {e}")
    
    print(f"Found {len(links)} following links")
    return links


def scrape_whole_list(list_type, driver, profile_link, next_cursor=None, resume_from_saved=None, max_pages=10, aggressive_resume=False):
    """Scrape followers or following list from a profile"""
    # Get to profile
    driver.get(profile_link)
    time.sleep(3)
    
    # First click the right button (followers or following)
    if list_type == "followers":
        # Click on the followers button
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
                    return [], None
    else:  # following
        # Click on the following button
        try:
            # Try standard link first
            following_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following/')]"))
            )
            following_button.click()
        except:
            # If that fails, try alternate methods
            try:
                following_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'following')]"))
                )
                following_button.click()
            except:
                try:
                    # Try the list item approach
                    following_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//ul/li[contains(., 'following')]"))
                    )
                    following_button.click()
                except Exception as e:
                    print(f"Could not click on following: {e}")
                    return [], None
    
    # Wait for the modal to appear
    time.sleep(3)
    
    # Initialize our containers
    usernames = []
    resuming_with_existing = False
    existing_count = 0
    
    if resume_from_saved:
        usernames = list(resume_from_saved)  # Make a copy of the existing data
        resuming_with_existing = len(usernames) > 0
        existing_count = len(usernames)
        print(f"Resuming with {len(usernames)} existing {list_type}")

    # Find the scrollable div in the modal
    scroll_div = None
    try:
        # First try to find by dialog role
        scroll_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@style, 'overflow')]"))
        )
    except:
        try:
            # Fallback to any scrollable div in the popup
            scroll_div = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@class, 'scroll')]"))
            )
        except:
            try:
                # Last resort: just use the dialog itself
                scroll_div = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
                )
            except Exception as e:
                print(f"Could not find scrollable area: {e}")
                return usernames, None
    
    # If we're resuming with a lot of existing users, perform initial scrolls to get past them
    if (resuming_with_existing and existing_count > 20) or aggressive_resume:
        # Determine how many scrolls based on existing count and if aggressive mode is enabled
        if aggressive_resume:
            print(f"AGGRESSIVE RESUME MODE: Performing extra aggressive scrolling to get past {existing_count} existing users")
            # In aggressive mode, do more scrolls and use a different approach
            initial_scrolls_needed = min(80, max(50, existing_count // 8))  # More scrolls in aggressive mode
            
            # Do different types of scrolling to try and get past the existing users
            print(f"Performing {initial_scrolls_needed} aggressive initial scrolls")
            
            # First, try rapid scrolling to get to the bottom
            for i in range(initial_scrolls_needed // 2):
                if i % 5 == 0:
                    print(f"Aggressive initial scroll {i+1}/{initial_scrolls_needed}")
                
                if i % 3 == 0:
                    # Scroll to bottom
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
                else:
                    # Scroll a fixed large amount
                    driver.execute_script("arguments[0].scrollTop += 5000;", scroll_div)
                
                # Very short pauses for rapid scrolling
                time.sleep(0.2)
            
            # Then do some slower, more thorough scrolls
            for i in range(initial_scrolls_needed // 2, initial_scrolls_needed):
                if i % 5 == 0:
                    print(f"Aggressive initial scroll {i+1}/{initial_scrolls_needed}")
                
                # Mix of scrolling approaches
                if i % 2 == 0:
                    # Normal scroll
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
                else:
                    # Scroll to specific position (estimate)
                    scroll_position = (i / initial_scrolls_needed) * 10000  # Approximate large value
                    driver.execute_script(f"arguments[0].scrollTop = {scroll_position};", scroll_div)
                
                # Medium pauses to let content load
                time.sleep(0.7)
        else:
            # Standard approach for non-aggressive mode
            print(f"Performing initial scrolls to get past {existing_count} existing users")
            # Calculate how many initial scrolls might be needed (rough estimate - about 10-12 users per scroll)
            initial_scrolls_needed = min(50, existing_count // 10)  # Cap at 50 to prevent excessive scrolling
            
            for i in range(initial_scrolls_needed):
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
                # Shorter pauses between these initial scrolls
                time.sleep(0.3)
                if i % 5 == 0:  # Log progress every 5 scrolls
                    print(f"Initial scroll {i+1}/{initial_scrolls_needed} to get past existing users")
        
        # Final longer pause to ensure content loads after bulk scrolling
        time.sleep(3)
        print("Finished initial scrolling, now looking for new users")

    # Scroll through the list to load more items
    last_height = driver.execute_script("return arguments[0].scrollHeight", scroll_div)
    current_page = 1
    consecutive_no_new = 0
    
    # Adjust max consecutive no-new threshold based on whether we're resuming
    # If resuming with many users, be more persistent in scrolling
    if aggressive_resume:
        max_consecutive_no_new = 10  # Most persistent in aggressive mode
        print(f"Using highest persistence threshold ({max_consecutive_no_new}) due to aggressive resume mode")
    elif resuming_with_existing and existing_count > 100:
        max_consecutive_no_new = 8  # More persistent when resuming with many existing users
        print(f"Using higher persistence threshold ({max_consecutive_no_new}) since resuming with {existing_count} users")
    else:
        max_consecutive_no_new = 3  # Standard value for fresh scraping or few existing users
    
    # Increase scroll timeout to let more items load
    scroll_timeout = 3.0  # Increased from default 2.0 seconds
    if aggressive_resume:
        scroll_timeout = 4.0  # Even longer timeout for aggressive mode
    
    # Track if we've found any new users since resuming
    found_new_since_resuming = False
    
    # With aggressive resume, we'll try multiple scrolling strategies if we get stuck
    scroll_strategies = [
        # Strategy 1: Normal scrolling (default)
        lambda: driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div),
        # Strategy 2: Fixed amount scrolling
        lambda: driver.execute_script("arguments[0].scrollTop += 3000;", scroll_div),
        # Strategy 3: Percentage-based scrolling
        lambda: driver.execute_script(f"arguments[0].scrollTop = arguments[0].scrollHeight * 0.{random.randint(5, 9)};", scroll_div),
        # Strategy 4: Scroll to random position
        lambda: driver.execute_script(f"arguments[0].scrollTop = {random.randint(5000, 20000)};", scroll_div)
    ]
    current_strategy = 0
    
    # Rate limit variables
    rate_limit_hit = False
    rate_limit_retry_count = 0
    consecutive_rate_limits = 0
    
    while current_page <= max_pages:
        print(f"Scrolling page {current_page}/{max_pages} for {list_type}")
        
        # Get current usernames
        prev_count = len(usernames)
        
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
                        if username and username not in usernames and username != "":
                            usernames.append(username)
                            found_new_since_resuming = True
                    except:
                        pass
        except:
            pass
            
        # Method 2: Alternative structure
        if len(usernames) == prev_count:  # If Method 1 didn't find any new users
            try:
                # Look for elements with username class
                elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//div[contains(@class, 'notranslate')]")
                for element in elements:
                    try:
                        username = element.text
                        if username and username not in usernames and username != "":
                            usernames.append(username)
                            found_new_since_resuming = True
                    except:
                        pass
            except:
                pass
        
        # Method 3: Last resort - any link with short text
        if len(usernames) == prev_count:  # If Methods 1 & 2 didn't find any new users
            try:
                elements = driver.find_elements(By.XPATH, "//div[@role='dialog']//a")
                for element in elements:
                    try:
                        username = element.text
                        if username and len(username) > 2 and len(username) < 30 and username not in usernames:
                            usernames.append(username)
                            found_new_since_resuming = True
                    except:
                        pass
            except:
                pass
        
        # Check if we found any new users
        new_users = len(usernames) - prev_count
        filtered_count = len(elements) - new_users if 'elements' in locals() else "unknown"
        print(f"Added {new_users} new users (filtered {filtered_count} duplicates)")
        
        # Check if we've hit Instagram's rate limit (exactly 10 new users)
        if new_users == RATE_LIMIT_THRESHOLD:
            consecutive_rate_limits += 1
            
            if consecutive_rate_limits >= 2:
                print(f"RATE LIMIT DETECTED: Exactly {RATE_LIMIT_THRESHOLD} users retrieved for {consecutive_rate_limits} consecutive pages")
                rate_limit_hit = True
                
                # Update rate limit information
                _rate_limit_info[list_type]['last_hit'] = datetime.datetime.now()
                _rate_limit_info[list_type]['retry_count'] += 1
                
                # Calculate wait time with exponential backoff
                backoff_factor = min(4, _rate_limit_info[list_type]['retry_count'])
                wait_time = RATE_LIMIT_WAIT_TIME * (1.5 ** backoff_factor)
                
                print(f"Rate limit hit {_rate_limit_info[list_type]['retry_count']} times. Waiting {wait_time/60:.1f} minutes before retrying...")
                
                # Close the modal to prevent session timeout
                try:
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.ESCAPE).perform()
                    time.sleep(1)
                except:
                    pass
                
                # Wait for the rate limit to refresh
                wait_start = datetime.datetime.now()
                wait_end = wait_start + datetime.timedelta(seconds=wait_time)
                
                print(f"Rate limit wait started at {wait_start.strftime('%H:%M:%S')}, will continue at {wait_end.strftime('%H:%M:%S')}")
                
                # Wait with periodic updates
                elapsed = 0
                update_interval = min(300, wait_time / 5)  # Update every 5 minutes or 1/5 of wait time, whichever is smaller
                
                while elapsed < wait_time:
                    sleep_chunk = min(60, wait_time - elapsed)  # Sleep in 1-minute chunks
                    time.sleep(sleep_chunk)
                    elapsed += sleep_chunk
                    
                    if elapsed % update_interval < 60:  # Show update near the interval points
                        remaining = wait_time - elapsed
                        print(f"Rate limit wait: {elapsed/60:.1f} minutes elapsed, {remaining/60:.1f} minutes remaining")
                
                print("Rate limit wait completed. Resuming scraping...")
                
                # Re-navigate to profile and re-open the dialog
                driver.get(profile_link)
                time.sleep(3)
                
                # Re-click the appropriate button
                try:
                    if list_type == "followers":
                        followers_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]"))
                        )
                        followers_button.click()
                    else:  # following
                        following_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following/')]"))
                        )
                        following_button.click()
                    
                    time.sleep(3)
                    
                    # Re-find the scrollable div
                    try:
                        scroll_div = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@style, 'overflow')]"))
                        )
                    except:
                        try:
                            scroll_div = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@class, 'scroll')]"))
                            )
                        except:
                            scroll_div = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
                            )
                    
                    # Reset the rate limit flag and continue scraping
                    rate_limit_hit = False
                    consecutive_rate_limits = 0
                    continue
                    
                except Exception as e:
                    print(f"Error re-opening dialog after rate limit wait: {e}")
                    return usernames, None
            
        else:
            consecutive_rate_limits = 0  # Reset counter if we didn't get exactly 10 users
            
        # Handle consecutive no-new counter with special logic when resuming
        if new_users == 0:
            consecutive_no_new += 1
            
            # If we're resuming and haven't found any new users yet, be more persistent
            if resuming_with_existing and not found_new_since_resuming:
                # Only increment halfway to be more persistent in finding that first new user
                consecutive_no_new = consecutive_no_new * 0.5
                print(f"Still looking for first new user beyond existing {existing_count} users")
                
            # Try changing scrolling strategy if we're getting stuck with aggressive resume
            if aggressive_resume and consecutive_no_new > 2 and not found_new_since_resuming:
                current_strategy = (current_strategy + 1) % len(scroll_strategies)
                print(f"Changing to scroll strategy {current_strategy+1} to find new users")
                consecutive_no_new -= 0.5  # Reduce counter when switching strategies
                
            # Check if we should stop scrolling
            if consecutive_no_new >= max_consecutive_no_new:
                if resuming_with_existing and not found_new_since_resuming:
                    # If we haven't found any new users yet, force continue a few more times
                    if current_page < max_pages * 0.75:  # Continue until 75% of max pages
                        print(f"Forcing continued scrolling to find new users beyond existing {existing_count}")
                        consecutive_no_new = max_consecutive_no_new - 1  # Reset just below threshold
                    else:
                        print(f"No new users found after persistent scrolling. Ending pagination.")
                        break
                else:
                    print(f"No new users found after {max_consecutive_no_new} consecutive scrolls. Ending pagination.")
                    break
        else:
            consecutive_no_new = 0  # Reset counter if we found new users
            
            # If this is our first batch of new users after resuming, log it
            if resuming_with_existing and not found_new_since_resuming and new_users > 0:
                print(f"SUCCESS! Found first {new_users} new users beyond previously collected ones.")
                found_new_since_resuming = True
        
        # Skip further scrolling if we hit the rate limit
        if rate_limit_hit:
            continue
            
        # Scroll down within the div for the next page
        # Use more aggressive scrolling - scroll multiple times before checking results
        num_scrolls = 4
        if aggressive_resume:
            num_scrolls = 6  # Even more scrolls in aggressive mode
            
        for _ in range(num_scrolls):
            # Use the current scroll strategy
            if aggressive_resume and not found_new_since_resuming:
                try:
                    scroll_strategies[current_strategy]()
                except:
                    # Fall back to default if the strategy fails
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
            else:
                # Normal scrolling
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div)
                
            time.sleep(0.5)  # Short pause between scrolls
        
        # Wait longer after the multiple scrolls to ensure content loads
        time.sleep(scroll_timeout)
        
        # Check if we've reached the bottom
        new_height = driver.execute_script("return arguments[0].scrollHeight", scroll_div)
        if new_height == last_height:
            consecutive_no_new += 1
            
            # Try a more aggressive scroll by scrolling a fixed amount
            try:
                # Try scrolling a fixed amount (3000px) in addition to normal scrolling
                driver.execute_script("arguments[0].scrollTop += 3000;", scroll_div)
                time.sleep(1)
                print("Attempted fixed-distance scroll to bypass potential UI limitations")
                
                # In aggressive mode, try even more radical approaches if we're stuck
                if aggressive_resume and not found_new_since_resuming:
                    # Try scrolling to different positions
                    positions = [0, 5000, 10000, 15000, 20000]
                    position = positions[current_page % len(positions)]
                    print(f"Trying scroll to position {position}px")
                    driver.execute_script(f"arguments[0].scrollTop = {position};", scroll_div)
                    time.sleep(1)
            except Exception as e:
                print(f"Fixed scroll error: {e}")
                
            if consecutive_no_new >= max_consecutive_no_new:
                print("Reached the end of the list or no new content loading. Ending pagination.")
                break
        else:
            last_height = new_height
            consecutive_no_new = 0  # Reset if the height changed
        
        current_page += 1
    
    # Close the modal by clicking outside of it
    try:
        actions = ActionChains(driver)
        actions.send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
    except:
        pass
    
    # Count how many new users we found during this session
    new_users_this_session = len(usernames) - existing_count
    print(f"Total {list_type} retrieved: {len(usernames)} ({new_users_this_session} new in this session)")
    
    # Return the collected usernames and the cursor for potential future pagination
    return usernames, None  # We don't track cursors in this version

def get_profile_stats(driver):
    """
    Extract profile statistics (followers, following, posts) from an Instagram profile page.
    
    Args:
        driver: Selenium webdriver instance on a profile page
        
    Returns:
        Dictionary with keys 'followers', 'following', and 'posts'
    """
    stats = {
        'followers': 0,
        'following': 0,
        'posts': 0
    }
    
    try:
        # Strategy 1: Classic selectors (old UI)
        try:
            followers_text = driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]/span").text.replace(',', '')
            following_text = driver.find_element(By.XPATH, "//a[contains(@href, '/following/')]/span").text.replace(',', '')
            posts_text = driver.find_element(By.XPATH, "//span[contains(@class, 'g47SY')][1]").text.replace(',', '')
            
            stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
            stats['following'] = int(following_text) if following_text.isdigit() else 0
            stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
            
            if stats['followers'] > 0 or stats['following'] > 0:
                return stats
        except:
            pass
            
        # Strategy 2: Section-based approach (newer UI)
        try:
            sections = driver.find_elements(By.XPATH, "//section/ul/li")
            if len(sections) >= 3:
                posts_text = sections[0].text.split(" ")[0].replace(",", "")
                followers_text = sections[1].text.split(" ")[0].replace(",", "")
                following_text = sections[2].text.split(" ")[0].replace(",", "")
                
                stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
                stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
                stats['following'] = int(following_text) if following_text.isdigit() else 0
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 3: Header-based approach for newest UI
        try:
            header_stats = driver.find_elements(By.XPATH, "//header//ul/li")
            if len(header_stats) >= 2:
                for stat in header_stats:
                    stat_text = stat.text.lower()
                    if 'post' in stat_text:
                        posts_text = stat_text.split(" ")[0].replace(",", "")
                        stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
                    elif 'follower' in stat_text:
                        followers_text = stat_text.split(" ")[0].replace(",", "")
                        stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
                    elif 'following' in stat_text:
                        following_text = stat_text.split(" ")[0].replace(",", "")
                        stats['following'] = int(following_text) if following_text.isdigit() else 0
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 4: JavaScript approach
        try:
            js_script = """
            return {
                followers: parseInt((document.querySelector('a[href*="followers"] span')?.textContent || '0').replace(/,/g, '')),
                following: parseInt((document.querySelector('a[href*="following"] span')?.textContent || '0').replace(/,/g, '')),
                posts: parseInt((document.querySelector('span[class*="g47SY"]:first-child')?.textContent || '0').replace(/,/g, ''))
            };
            """
            js_stats = driver.execute_script(js_script)
            if js_stats:
                stats['followers'] = js_stats.get('followers', 0)
                stats['following'] = js_stats.get('following', 0)
                stats['posts'] = js_stats.get('posts', 0)
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 5: API approach
        try:
            js_script = """
            return window._sharedData && window._sharedData.entry_data && 
                   window._sharedData.entry_data.ProfilePage && 
                   window._sharedData.entry_data.ProfilePage[0].graphql.user;
            """
            user_data = driver.execute_script(js_script)
            if user_data:
                stats['followers'] = user_data.get('edge_followed_by', {}).get('count', 0)
                stats['following'] = user_data.get('edge_follow', {}).get('count', 0)
                stats['posts'] = user_data.get('edge_owner_to_timeline_media', {}).get('count', 0)
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
    
    except Exception as e:
        print(f"Error getting profile stats: {e}")
        driver.save_screenshot('profile_stats_error.png')
    
    return stats