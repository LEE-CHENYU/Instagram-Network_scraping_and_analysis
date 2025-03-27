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

#%% Constants and helper functions
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers.json")
FOLLOWING_FILE = os.path.join(DATA_DIR, "following.json")
CURSOR_FILE = os.path.join(DATA_DIR, "next_cursor.json")
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")
RATE_LIMIT_THRESHOLD = 10  # Instagram typically limits to 10 users per request

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

def sanitize_and_save_links(links, file_path):
    """Sanitize, deduplicate and save links to a file"""
    if DEBUG:
        print(f"DEBUG: Sanitizing and saving {len(links)} links")
    
    # Normalize and sanitize links
    clean_links = []
    seen = set()
    
    for link in links:
        # Strip whitespace and ensure it's a string
        link = str(link).strip()
        
        # Skip empty links
        if not link:
            if DEBUG:
                print("DEBUG: Skipping empty link")
            continue
        
        # Ensure proper URL format
        if not (link.startswith('http') and 'instagram.com' in link):
            if DEBUG:
                print(f"DEBUG: Skipping invalid link format: {link}")
            continue
        
        # Skip duplicates
        if link in seen:
            if DEBUG:
                print(f"DEBUG: Skipping duplicate link: {link}")
            continue
        
        seen.add(link)
        clean_links.append(link + '\n')  # Ensure newline at end
    
    if DEBUG:
        print(f"DEBUG: After sanitization: {len(clean_links)} links (removed {len(links) - len(clean_links)})")
    
    # Save to file
    try:
        with open(file_path, 'w') as file_h:
            file_h.writelines(clean_links)
        if DEBUG:
            print(f"DEBUG: Successfully saved {len(clean_links)} links to {file_path}")
    except Exception as e:
        print(f"ERROR: Failed to save links: {e}")
    
    return clean_links

#%% Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Instagram Following Accounts Scraper')
    parser.add_argument('--username', default="fretin98", help='Instagram username')
    parser.add_argument('--password', default="Lcy199818su!", help='Instagram password')
    parser.add_argument('--batch-size', type=int, default=3, help='Number of accounts to scrape in this session')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

#%% Setup and login
args = parse_arguments()

# Set debug flag
DEBUG = args.debug
if DEBUG:
    print("DEBUG MODE ENABLED")

ensure_data_directory()

# Load existing data
progress_data = load_saved_data(PROGRESS_FILE, {})
print(f"Loaded scraping progress: {len(progress_data)} accounts processed")

# Use command line arguments instead of input
username = args.username
password = args.password
batch_size = args.batch_size

print(f"Will process {batch_size} accounts in this session")

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

# Login
essentialRoutines.login_insta(driver, username, password)
time.sleep(5)

#%% Scraping functions
def load_links_and_adj_list():
    """Load the links and adjacency list from files"""
    # Load links
    try:
        with open(FOLLOWING_LINKS_FILE, "r") as links_file:
            links = links_file.readlines()
        print(f"Loaded {len(links)} links from {FOLLOWING_LINKS_FILE}")
    except FileNotFoundError:
        print(f"Warning: {FOLLOWING_LINKS_FILE} not found. Starting with empty links list.")
        links = []
    
    # Load adjacency list
    try:
        with open(ADJ_LIST_FILE, "r") as adj_file:
            adj_list = adj_file.readlines()
        print(f"Loaded adjacency list from {ADJ_LIST_FILE}")
        all_nodes = essentialRoutines.adjList_to_dict(adj_list)
    except FileNotFoundError:
        print(f"Warning: {ADJ_LIST_FILE} not found. Starting with empty adjacency list.")
        all_nodes = {}
    
    return links, all_nodes

def get_processed_accounts():
    """Extract list of accounts that have already been processed from adjList.txt"""
    processed_accounts = set()
    
    if os.path.exists(ADJ_LIST_FILE):
        try:
            with open(ADJ_LIST_FILE, "r") as adj_file:
                for line in adj_file:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        # The first part is the account that has been processed
                        processed_accounts.add(parts[0])
        except Exception as e:
            print(f"Error reading adjList.txt: {e}")
    
    if DEBUG:
        print(f"DEBUG: Found {len(processed_accounts)} already processed accounts in adjList.txt")
    
    return processed_accounts

def deduplicate_adj_list():
    """Remove duplicate entries from the adjacency list file"""
    if not os.path.exists(ADJ_LIST_FILE):
        print(f"Warning: {ADJ_LIST_FILE} not found. No deduplication needed.")
        return
    
    try:
        # Read existing relations
        with open(ADJ_LIST_FILE, "r") as adj_file:
            relations = adj_file.readlines()
        
        # Normalize and deduplicate
        unique_relations = set()
        for relation in relations:
            relation = relation.strip()
            if relation:  # Skip empty lines
                unique_relations.add(relation)
        
        # Check if any duplicates were found
        if len(relations) != len(unique_relations):
            print(f"Found {len(relations) - len(unique_relations)} duplicate relations in adjList.txt")
            
            # Write back unique relations
            with open(ADJ_LIST_FILE, "w") as adj_file:
                for relation in sorted(unique_relations):
                    adj_file.write(f"{relation}\n")
            
            print(f"Deduplicated adjList.txt now contains {len(unique_relations)} unique relationships")
        else:
            print("No duplicates found in adjList.txt")
    
    except Exception as e:
        print(f"Error deduplicating adjList.txt: {e}")

def save_relations_to_adj_list(new_relations):
    """Save new relations to adjList.txt with deduplication"""
    # Load existing adjacency list to avoid duplicates
    existing_relations = set()
    if os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, "r") as adj_file:
            for line in adj_file:
                if line.strip():  # Skip empty lines
                    existing_relations.add(line.strip())
    
    # Count new relationships
    new_count = 0
    for relation in new_relations:
        if relation not in existing_relations:
            existing_relations.add(relation)
            new_count += 1
    
    # Write all relationships back to the file
    with open(ADJ_LIST_FILE, "w") as adj_file:
        for relation in sorted(existing_relations):
            adj_file.write(f"{relation}\n")
    
    print(f"Added {new_count} new relationships to adjacency list (total: {len(existing_relations)})")
    return new_count

def scrape_account(account_link, all_nodes):
    """Scrape a single Instagram account"""
    print(f"Processing: {account_link}")
    account_username = account_link.rstrip('/').split('/')[-1].strip()
    
    # Check if we've already processed this account
    if account_username in progress_data:
        # If it was previously rate-limited, don't skip but re-scrape
        if progress_data[account_username].get("rate_limited", False):
            print(f"Account {account_username} was previously rate-limited. Re-attempting scrape.")
        else:
            print(f"Account {account_username} already processed. Skipping.")
            return True, all_nodes
    
    # Navigate to the account
    driver.get(account_link)
    time.sleep(3)
    
    # Try to get the username from the page
    try:
        # Try multiple selectors for username
        try:
            curr_username = driver.find_element(By.TAG_NAME, "h2").text
        except:
            try:
                curr_username = driver.find_element(By.XPATH, "//section//h2").text
            except:
                try:
                    # Try getting from URL
                    current_url = driver.current_url
                    curr_username = current_url.split("/")[3]
                except:
                    # Last resort - use the link
                    curr_username = account_username
    except Exception as e:
        print(f"Error getting username: {e}")
        curr_username = account_username
    
    print(f"Scraping {curr_username}")
    
    # Define limits for reasonable scraping
    follower_limit = 2000
    following_limit = 2000
    
    # Get follower and following counts - use fastest method first
    try:
        # Try JavaScript approach first (fastest)
        js_script = """
        const followerText = document.querySelector('a[href*="followers"] span')?.textContent || 
                          document.evaluate('//span[contains(text(), "follower")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue?.textContent;
        const followingText = document.querySelector('a[href*="following"] span')?.textContent || 
                           document.evaluate('//span[contains(text(), "following")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue?.textContent;
        
        let followers = 0;
        let following = 0;
        
        if (followerText) {
            followers = parseInt(followerText.replace(/,/g, '').match(/\\d+/)[0]);
        }
        if (followingText) {
            following = parseInt(followingText.replace(/,/g, '').match(/\\d+/)[0]);
        }
        
        return [followers, following];
        """
        counts = driver.execute_script(js_script)
        
        if counts and len(counts) == 2:
            curr_Followers = counts[0]
            curr_Following = counts[1]
            
            # Early check if the account exceeds limits
            if curr_Followers > follower_limit or curr_Following > following_limit:
                print(f"Early detection: Account has too many followers ({curr_Followers}) or following ({curr_Following}). Skipping detailed scraping.")
                # Record that we processed this account
                progress_data[curr_username] = {
                    "processed": True,
                    "skipped": True,
                    "followers_count": curr_Followers,
                    "following_count": curr_Following,
                    "timestamp": time.time()
                }
                save_data(progress_data, PROGRESS_FILE)
                return True, all_nodes
        else:
            # If JS approach failed, set to None to try other methods
            curr_Followers = None
            curr_Following = None
    except:
        # If JS approach failed, set to None to try other methods
        curr_Followers = None
        curr_Following = None
    
    # If JavaScript approach failed, try other methods
    if curr_Followers is None or curr_Following is None:
        try:
            # Strategy 1: Classic selectors (old UI)
            try:
                curr_Followers = int("".join((driver.find_element(By.XPATH, "//a[text()=' followers']/span[@class='g47SY ']").text).split(",")))
                curr_Following = int("".join((driver.find_element(By.XPATH, "//a[text()=' following']/span[@class='g47SY ']").text).split(",")))
            except:
                pass
                
            # Strategy 2: New UI with href attribute
            if curr_Followers is None or curr_Following is None:
                try:
                    follower_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/followers/')]/span")
                    following_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/following/')]/span")
                    
                    if follower_elements and following_elements:
                        curr_Followers = int("".join(follower_elements[0].text.split(",")))
                        curr_Following = int("".join(following_elements[0].text.split(",")))
                except:
                    pass
                    
            # Strategy 3: Section-based approach (newer UI)
            if curr_Followers is None or curr_Following is None:
                try:
                    sections = driver.find_elements(By.XPATH, "//section/ul/li")
                    if len(sections) >= 3:
                        curr_Followers = int("".join(sections[1].text.split(" ")[0].replace(",", "")))
                        curr_Following = int("".join(sections[2].text.split(" ")[0].replace(",", "")))
                except:
                    pass
                    
            # Strategy 4: Header-based approach for newest UI
            if curr_Followers is None or curr_Following is None:
                try:
                    header_stats = driver.find_elements(By.XPATH, "//header//ul/li")
                    if len(header_stats) >= 2:
                        for stat in header_stats:
                            stat_text = stat.text.lower()
                            if 'follower' in stat_text:
                                curr_Followers = int("".join(stat_text.split(" ")[0].replace(",", "")))
                            elif 'following' in stat_text:
                                curr_Following = int("".join(stat_text.split(" ")[0].replace(",", "")))
                except:
                    pass
                    
            # Strategy 5: API approach
            if curr_Followers is None or curr_Following is None:
                try:
                    # Execute JavaScript to get the data from window._sharedData
                    js_script = """
                    return window._sharedData && window._sharedData.entry_data && 
                           window._sharedData.entry_data.ProfilePage && 
                           window._sharedData.entry_data.ProfilePage[0].graphql.user;
                    """
                    user_data = driver.execute_script(js_script)
                    if user_data:
                        curr_Followers = user_data.get('edge_followed_by', {}).get('count', 0)
                        curr_Following = user_data.get('edge_follow', {}).get('count', 0)
                except:
                    pass
            
            # If we still couldn't get the counts, set default values
            if curr_Followers is None:
                print("WARNING: Could not determine follower count. Skipping.")
                curr_Followers = 0
            if curr_Following is None:
                print("WARNING: Could not determine following count. Skipping.")
                curr_Following = 0
                
        except Exception as e:
            print(f"Error getting follower/following counts: {e}")
            curr_Followers = 0
            curr_Following = 0
    
    print(f"{curr_username}: Followers: {curr_Followers}, Following: {curr_Following}")
    
    # Only scrape if counts are reasonable (below limit)
    success = False
    
    if curr_Followers > follower_limit or curr_Following > following_limit:
        print(f"Account has too many followers ({curr_Followers}) or following ({curr_Following}). Skipping detailed scraping.")
        # Just record that we processed this account
        progress_data[curr_username] = {
            "processed": True,
            "skipped": True,
            "followers_count": curr_Followers,
            "following_count": curr_Following,
            "timestamp": time.time()
        }
        success = True
    else:
        followers = []
        following = []
        
        # Scrape followers if count is reasonable
        if curr_Followers > 0 and curr_Followers <= follower_limit:
            try:
                # Try to get followers using the API approach
                print(f"Scraping {curr_Followers} followers for {curr_username}...")
                followers_data = essentialRoutines.scrape_whole_list("followers", driver, account_link)
                
                # Handle the case where scrape_whole_list returns a tuple (followers, cursor)
                if isinstance(followers_data, tuple) and len(followers_data) >= 1:
                    followers = followers_data[0]  # Extract just the followers list
                else:
                    followers = followers_data  # Use as is if not a tuple
                    
                print(f"Retrieved {len(followers)} followers")
                
                # Add to adjacency list
                for follower in followers:
                    try:
                        # Ensure follower is a string, not a list
                        if isinstance(follower, str):
                            if follower not in all_nodes:
                                all_nodes[follower] = []
                            all_nodes[follower].append(curr_username)
                        else:
                            print(f"Skipping non-string follower: {follower}")
                    except Exception as e:
                        print(f"Error adding follower {follower} to adjacency list: {e}")
            except Exception as e:
                print(f"Error scraping followers: {e}")
        
        # Scrape following if count is reasonable
        if curr_Following > 0 and curr_Following <= following_limit:
            try:
                # Try to get following using the API approach
                print(f"Scraping {curr_Following} following for {curr_username}...")
                following_data = essentialRoutines.scrape_whole_list("following", driver, account_link)
                
                # Handle the case where scrape_whole_list returns a tuple (following, cursor)
                if isinstance(following_data, tuple) and len(following_data) >= 1:
                    following = following_data[0]  # Extract just the following list
                else:
                    following = following_data  # Use as is if not a tuple
                    
                print(f"Retrieved {len(following)} following")
                
                # Add to adjacency list
                all_nodes[curr_username] = following
            except Exception as e:
                print(f"Error scraping following: {e}")
        
        # Check if we've hit Instagram's rate limit (exactly RATE_LIMIT_THRESHOLD followers or following)
        rate_limited = False
        # Check if much fewer followers were retrieved than expected (rate limited to fewer than 10 or even just 1)
        if len(followers) > 0 and len(followers) <= RATE_LIMIT_THRESHOLD and curr_Followers > RATE_LIMIT_THRESHOLD * 2:
            print(f"RATE LIMIT DETECTED: Retrieved only {len(followers)} followers when account has {curr_Followers}")
            rate_limited = True
        
        if len(following) > 0 and len(following) <= RATE_LIMIT_THRESHOLD and curr_Following > RATE_LIMIT_THRESHOLD * 2:
            print(f"RATE LIMIT DETECTED: Retrieved only {len(following)} following when account has {curr_Following}")
            rate_limited = True
            
        # Record progress
        progress_data[curr_username] = {
            "processed": not rate_limited,  # Mark as not processed if rate-limited
            "rate_limited": rate_limited,   # Flag to indicate rate limit was hit
            "skipped": False,
            "followers_count": curr_Followers,
            "following_count": curr_Following,
            "followers_retrieved": len(followers),
            "following_retrieved": len(following),
            "timestamp": time.time()
        }
        
        success = True
    
    # Save the updated progress
    save_data(progress_data, PROGRESS_FILE)
    
    return success, all_nodes

#%% Main scraping loop
try:
    links, all_nodes = load_links_and_adj_list()
    
    # Deduplicate adjacency list at startup
    print("Deduplicating adjacency list...")
    deduplicate_adj_list()
    
    # Get accounts that have already been processed
    processed_accounts = get_processed_accounts()
    print(f"Found {len(processed_accounts)} accounts that have already been processed")
    
    # Filter out links to accounts that are already processed
    if processed_accounts:
        filtered_links = []
        skipped_count = 0
        
        for link in links:
            # Extract username from link
            username = link.rstrip('/').split('/')[-1].strip()
            if username in processed_accounts:
                if DEBUG:
                    print(f"DEBUG: Skipping already processed account: {username}")
                skipped_count += 1
                continue
            filtered_links.append(link)
        
        if skipped_count > 0:
            print(f"Skipped {skipped_count} already processed accounts")
            links = filtered_links
            
            # Save the filtered list
            sanitize_and_save_links(links, FOLLOWING_LINKS_FILE)
            print(f"Saved filtered list with {len(links)} remaining accounts")
    
    if not links:
        print("No links to process. Run scrapeMyAccount.py first to generate links.")
    else:
        print(f"Starting batch processing of {min(batch_size, len(links))} accounts")
        processed_count = 0
        rate_limited_count = 0
        
        # First, prioritize accounts by checking if they are suitable for processing
        if batch_size > 1 and len(links) > batch_size:
            print("Pre-checking accounts to prioritize ones with reasonable follower/following counts...")
            
            # Track accounts that are good candidates (have reasonable counts)
            good_candidates = []
            bad_candidates = []
            
            # Use lower limits for prioritization
            pre_check_follower_limit = 1000  # Lower than the main limit for prioritization
            pre_check_following_limit = 1000
            
            # Check the first N+3 accounts (where N is batch size) to find good candidates
            max_check = min(len(links), batch_size + 3)
            for i in range(max_check):
                try:
                    current_link = links[i].strip()
                    account_username = current_link.rstrip('/').split('/')[-1].strip()
                    
                    # Skip if already processed
                    if account_username in processed_accounts:
                        continue
                    
                    # Do a quick check of follower/following counts
                    driver.get(current_link)
                    time.sleep(2)
                    
                    # Try to get follower/following counts quickly
                    try:
                        # Javascript approach for faster extraction
                        js_script = """
                        const followerText = document.querySelector('a[href*="followers"] span')?.textContent || 
                                          document.evaluate('//span[contains(text(), "follower")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue?.textContent;
                        const followingText = document.querySelector('a[href*="following"] span')?.textContent || 
                                           document.evaluate('//span[contains(text(), "following")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue?.textContent;
                        
                        let followers = 0;
                        let following = 0;
                        
                        if (followerText) {
                            followers = parseInt(followerText.replace(/,/g, '').match(/\\d+/)[0]);
                        }
                        if (followingText) {
                            following = parseInt(followingText.replace(/,/g, '').match(/\\d+/)[0]);
                        }
                        
                        return [followers, following];
                        """
                        counts = driver.execute_script(js_script)
                        
                        if counts and len(counts) == 2:
                            follower_count = counts[0]
                            following_count = counts[1]
                            
                            if follower_count <= pre_check_follower_limit and following_count <= pre_check_following_limit:
                                good_candidates.append(i)
                                print(f"✓ {account_username}: Good candidate with {follower_count} followers, {following_count} following")
                            else:
                                bad_candidates.append(i)
                                print(f"✗ {account_username}: Too many connections ({follower_count} followers, {following_count} following)")
                    except Exception as e:
                        print(f"Could not pre-check {account_username}: {e}")
                        # If we can't check, assume it's a good candidate
                        good_candidates.append(i)
                except Exception as e:
                    print(f"Error pre-checking account {i}: {e}")
        
        # Reorder links to prioritize good candidates
        if good_candidates:
            print(f"Found {len(good_candidates)} accounts with reasonable follower/following counts")
            
            # Create a new ordered list
            new_links = []
            
            # First add good candidates
            for i in good_candidates:
                if i < len(links):
                    new_links.append(links[i])
            
            # Then add all other links that weren't checked
            for i in range(len(links)):
                if i not in good_candidates and i not in bad_candidates:
                    new_links.append(links[i])
            
            # Finally add bad candidates at the end
            for i in bad_candidates:
                if i < len(links):
                    new_links.append(links[i])
            
            # Replace the original links list
            links = new_links
            
            # Save the reordered list
            sanitize_and_save_links(links, FOLLOWING_LINKS_FILE)
            
            print("Links reordered to prioritize accounts with reasonable follower/following counts")

        for i in range(min(batch_size, len(links))):
            if i >= len(links):
                break
                
            current_link = links[0].strip()  # Get the first link
            
            try:
                if DEBUG:
                    print(f"DEBUG: Processing link #{i+1}/{batch_size}: {current_link}")
                    print(f"DEBUG: Before processing - {len(links)} links in queue")
                
                # Extract username to check if already processed
                account_username = current_link.rstrip('/').split('/')[-1].strip()
                if account_username in processed_accounts:
                    if DEBUG:
                        print(f"DEBUG: Skipping already processed account: {account_username}")
                    # Remove from queue since it's already processed
                    removed_link = links.pop(0)
                    sanitize_and_save_links(links, FOLLOWING_LINKS_FILE)
                    continue
                
                success, all_nodes = scrape_account(current_link, all_nodes)
                if success:
                    processed_count += 1
                    # Check if the account was rate-limited
                    if account_username in progress_data and progress_data[account_username].get("rate_limited", False):
                        rate_limited_count += 1
                        # Don't add to processed_accounts set if rate-limited, so we can retry later
                        print(f"Account {account_username} was rate-limited. Will retry in a future session.")
                    else:
                        # Add to processed accounts set only if not rate-limited
                        processed_accounts.add(account_username)
                    
                # Remove the processed link
                if DEBUG:
                    print(f"DEBUG: Removing link from queue: {current_link}")
                    
                removed_link = links.pop(0)
                if DEBUG:
                    print(f"DEBUG: Link removed. Queue size now: {len(links)}")
                
            except Exception as e:
                print(f"Error processing {current_link}: {e}")
                traceback.print_exc()
                
                if DEBUG:
                    print(f"DEBUG: Moving failed link to end of queue: {current_link}")
                
                # Move to the end of the list to try again later
                # Check if the link still exists in list before appending
                if links and links[0].strip() == current_link:
                    links.append(links.pop(0))
                    if DEBUG:
                        print(f"DEBUG: Link moved to end. Queue size: {len(links)}")
                else:
                    print(f"WARNING: Failed link {current_link} not found at position 0, might have been removed already")
            
            # Save updated links and adjacency list after each account
            sanitize_and_save_links(links, FOLLOWING_LINKS_FILE)
            
            if DEBUG:
                print(f"DEBUG: Links saved")
            
            # Create proper formatted adjacency list entries (one relationship per line)
            new_relations = []
            
            # Add relationships from all_nodes dictionary
            for follower, following_list in all_nodes.items():
                for followed in following_list:
                    new_relations.append(f"{follower} {followed}")
            
            # Save relations with deduplication
            save_relations_to_adj_list(new_relations)
            
            print(f"Completed {processed_count}/{batch_size} accounts. {len(links)} remaining in queue.")
            print(f"Waiting 5 seconds before next account...")
            time.sleep(5)
        
        print(f"\nBatch complete! Processed {processed_count} accounts ({rate_limited_count} were rate-limited and will be retried later).")
        print(f"{len(links)} links remaining for future sessions.")

except Exception as e:
    print(f"Error during batch processing: {e}")
    traceback.print_exc()
finally:
    # Close the driver
    driver.close()
    print("Browser closed. Script complete.")
