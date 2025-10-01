#!/usr/bin/env python3
"""
Instagram scraping using instagrapi - bypasses rate limits with mobile API
"""

import json
import os
import time
import logging
import datetime
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, PleaseWaitFewMinutes, UserNotFound

# Configuration
DATA_DIR = "instagram_data"
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")
DAILY_SESSIONS_FILE = os.path.join(DATA_DIR, "daily_sessions.json")

# Login credentials
USERNAME = "fretin98"
PASSWORD = "Lcy199818su"

# Quality thresholds (same as original script)
MIN_SCRAPE_RATIO = 0.1
MAX_ACCOUNT_SIZE = 2000

# Rate limiting (be conservative to avoid bans)
DELAY_BETWEEN_ACCOUNTS = 10  # seconds between accounts (increased from 5)
DELAY_AFTER_ERROR = 60  # seconds after error (increased from 30)
MAX_ACCOUNTS_PER_SESSION = 25  # Process max 25 accounts per run (reduced from 50)

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"instagrapi_scrape_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("=" * 60)
    logging.info("Instagram Scraper with Instagrapi Starting")
    logging.info("=" * 60)

def load_json_data(file_path, default=None):
    """Load data from a JSON file"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {file_path}")
            return default if default is not None else {}
    return default if default is not None else {}

def save_json_data(data, file_path):
    """Save data to a JSON file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    logging.info(f"Saved data to {file_path}")

def load_following_links():
    """Load the list of accounts to scrape"""
    if os.path.exists(FOLLOWING_LINKS_FILE):
        with open(FOLLOWING_LINKS_FILE, 'r') as f:
            links = [line.strip() for line in f.readlines() if line.strip()]
        return links
    return []

def categorize_accounts(progress_data, following_links):
    """Categorize accounts by their scraping status"""
    categories = {
        'unprocessed': [],
        'incomplete': [],
        'rate_limited': [],
        'complete': [],
        'skipped': [],
        'empty': []
    }

    for link in following_links:
        username = link.replace('https://www.instagram.com/', '').replace('/', '').strip()

        if username not in progress_data:
            categories['unprocessed'].append(username)
            continue

        data = progress_data[username]

        # Check if skipped due to size
        if data.get('skipped', False):
            categories['skipped'].append(username)
            continue

        # Check if empty
        following_count = data.get('following_count', 0)
        if following_count == 0 and data.get('processed', False):
            categories['empty'].append(username)
            continue

        # Check completion status
        following_retrieved = data.get('following_retrieved', 0)

        if following_count > 0:
            ratio = following_retrieved / following_count

            if ratio >= 0.95:  # 95% or more is complete
                categories['complete'].append(username)
            elif following_retrieved == 10:  # Rate limited
                categories['rate_limited'].append(username)
            elif data.get('processed', False):
                categories['incomplete'].append(username)
            else:
                categories['unprocessed'].append(username)
        else:
            categories['unprocessed'].append(username)

    return categories

def scrape_account(cl, username, progress_data):
    """Scrape a single account using instagrapi"""
    logging.info(f"\n{'='*60}")
    logging.info(f"Processing account: {username}")
    logging.info(f"{'='*60}")

    try:
        # Get user ID and info
        logging.info(f"Fetching user info for {username}...")
        try:
            user_id = cl.user_id_from_username(username)
            user_info = cl.user_info(user_id)
        except UserNotFound:
            logging.warning(f"User {username} not found - may be private or deleted")
            progress_data[username] = {
                'processed': True,
                'skipped': False,
                'followers_count': 0,
                'following_count': 0,
                'followers_retrieved': 0,
                'following_retrieved': 0,
                'timestamp': time.time(),
                'error': 'User not found'
            }
            return progress_data

        followers_count = user_info.follower_count
        following_count = user_info.following_count

        logging.info(f"Account stats: {followers_count:,} followers, {following_count:,} following")

        # Check if account is too large
        if following_count > MAX_ACCOUNT_SIZE:
            logging.info(f"Skipping {username} - following count ({following_count}) exceeds limit ({MAX_ACCOUNT_SIZE})")
            progress_data[username] = {
                'processed': True,
                'skipped': True,
                'followers_count': followers_count,
                'following_count': following_count,
                'followers_retrieved': 0,
                'following_retrieved': 0,
                'timestamp': time.time()
            }
            return progress_data

        # Get following list
        logging.info(f"Fetching following list for {username}...")
        try:
            following = cl.user_following(user_id, amount=0)  # 0 = get all
            following_usernames = [user.username for user in following.values()]
            following_retrieved = len(following_usernames)

            logging.info(f"✅ Successfully retrieved {following_retrieved} following accounts")

            # Save to adjacency list (append to adjList.txt)
            adj_list_file = os.path.join(DATA_DIR, "adjList.txt")
            with open(adj_list_file, 'a') as f:
                f.write(f"{username} {' '.join(following_usernames)}\n")

            # NOTE: We don't add discovered accounts to the queue
            # Only scrape the original following list, not following's following

        except PleaseWaitFewMinutes as e:
            logging.warning(f"Rate limit hit for {username}: {e}")
            following_retrieved = 0
        except Exception as e:
            logging.error(f"Error getting following for {username}: {e}")
            following_retrieved = 0

        # Update progress
        progress_data[username] = {
            'processed': True,
            'skipped': False,
            'followers_count': followers_count,
            'following_count': following_count,
            'followers_retrieved': 0,  # Not scraping followers for now
            'following_retrieved': following_retrieved,
            'timestamp': time.time()
        }

        # Save progress after each account
        save_json_data(progress_data, PROGRESS_FILE)

        return progress_data

    except Exception as e:
        logging.error(f"Unexpected error processing {username}: {e}")
        import traceback
        traceback.print_exc()

        # Still save some progress data
        if username not in progress_data:
            progress_data[username] = {
                'processed': False,
                'skipped': False,
                'error': str(e),
                'timestamp': time.time()
            }

        return progress_data

def main():
    setup_logging()

    # Load data
    logging.info("Loading existing data...")
    progress_data = load_json_data(PROGRESS_FILE, {})
    following_links = load_following_links()

    logging.info(f"Loaded {len(following_links)} accounts from queue")

    # Categorize accounts
    categories = categorize_accounts(progress_data, following_links)

    logging.info("\nAccount Categories:")
    for category, accounts in categories.items():
        percentage = (len(accounts) / len(following_links) * 100) if following_links else 0
        logging.info(f"  {category}: {len(accounts)} accounts ({percentage:.1f}%)")

    # Build queue: prioritize incomplete and rate_limited, then unprocessed
    queue = categories['rate_limited'] + categories['incomplete'] + categories['unprocessed']

    logging.info(f"\nTotal accounts to process: {len(queue)}")
    logging.info(f"Will process up to {MAX_ACCOUNTS_PER_SESSION} accounts this session")

    if not queue:
        logging.info("No accounts to process!")
        return

    # Login to Instagram
    logging.info(f"\nLogging in as {USERNAME}...")
    cl = Client()

    try:
        cl.login(USERNAME, PASSWORD)
        logging.info("✅ Login successful!")
    except Exception as e:
        logging.error(f"❌ Login failed: {e}")
        logging.error("⚠️  Login blocked - waiting 1-2 hours before next attempt to avoid triggering more protections")

        # Wait 1.5 hours (90 minutes) before allowing next attempt
        wait_time = 90 * 60  # 90 minutes in seconds
        logging.info(f"⏳ Sleeping for {wait_time/3600:.1f} hours...")
        time.sleep(wait_time)

        logging.info("⏰ Wait period complete. Script will exit - restart manually to try again.")
        return

    # Process accounts
    processed_count = 0
    success_count = 0
    error_count = 0

    for i, username in enumerate(queue[:MAX_ACCOUNTS_PER_SESSION]):
        logging.info(f"\n[{i+1}/{min(len(queue), MAX_ACCOUNTS_PER_SESSION)}] Processing {username}")

        try:
            progress_data = scrape_account(cl, username, progress_data)

            # Check if successful
            if username in progress_data and progress_data[username].get('following_retrieved', 0) > 0:
                success_count += 1
            else:
                error_count += 1

            processed_count += 1

            # Rate limiting delay
            if i < len(queue) - 1:  # Don't delay after last account
                logging.info(f"Waiting {DELAY_BETWEEN_ACCOUNTS} seconds before next account...")
                time.sleep(DELAY_BETWEEN_ACCOUNTS)

        except Exception as e:
            logging.error(f"Failed to process {username}: {e}")
            error_count += 1
            time.sleep(DELAY_AFTER_ERROR)

    # Update daily sessions
    daily_sessions = load_json_data(DAILY_SESSIONS_FILE, {})
    today = datetime.date.today().isoformat()

    if daily_sessions.get('date') == today:
        daily_sessions['count'] = daily_sessions.get('count', 0) + 1
    else:
        daily_sessions = {'date': today, 'count': 1}

    save_json_data(daily_sessions, DAILY_SESSIONS_FILE)

    # Final statistics
    logging.info("\n" + "=" * 60)
    logging.info("SCRAPING SESSION COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Processed: {processed_count} accounts")
    logging.info(f"Successful: {success_count} accounts")
    logging.info(f"Errors: {error_count} accounts")
    logging.info(f"Remaining in queue: {len(queue) - processed_count}")

    # Recategorize to show progress
    categories = categorize_accounts(progress_data, following_links)
    logging.info("\nUpdated Account Status:")
    for category, accounts in categories.items():
        percentage = (len(accounts) / len(following_links) * 100) if following_links else 0
        logging.info(f"  {category}: {len(accounts)} accounts ({percentage:.1f}%)")

    logging.info("\n" + "=" * 60)

if __name__ == "__main__":
    main()
