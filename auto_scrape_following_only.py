#!/usr/bin/env python3
"""
Instagram Following Accounts Auto Scraper (Focused Version)

This script automates the scraping of following accounts ONLY.
It intelligently handles incomplete scraping and prioritizes accounts
that haven't been properly scraped yet.

Key Features:
- Smart categorization of accounts (unprocessed, incomplete, complete)
- Intelligent retry logic for partially scraped accounts
- Clear progress tracking showing real completion rates
- Adaptive batch sizing and timing to avoid detection
"""

import os
import json
import time
import random
import logging
import subprocess
import traceback
import datetime
from collections import Counter

# Constants
DATA_DIR = "instagram_data"
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")

# Instagram account credentials
USERNAME = "cheneyli7"
PASSWORD = "Lcy199818"

# Scraping settings
MIN_INTERVAL_MINUTES = 20  # Minimum time between sessions
MAX_INTERVAL_MINUTES = 40  # Maximum time between sessions
MAX_SESSIONS_PER_DAY = 20  # Maximum sessions per day
NATURAL_BREAK_LENGTH_MINUTES = 120  # 2-hour natural break
RANDOM_SKIP_CHANCE = 0.1  # 10% chance to skip a session
PAUSE_HOURS = [2, 3, 4, 5]  # Hours to pause scraping (2am-5am)

# Quality thresholds
MIN_SCRAPE_RATIO = 0.1  # Minimum ratio of retrieved/total to consider complete
MAX_ACCOUNT_SIZE = 2000  # Skip accounts with more followers/following than this

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"auto_scrape_following_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("=" * 60)
    logging.info("Instagram Following Accounts Auto Scraper Starting")
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
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        logging.info(f"Saved data to {file_path}")
    except Exception as e:
        logging.error(f"Error saving data to {file_path}: {e}")

def categorize_accounts():
    """
    Categorize all accounts based on their scraping status.
    Returns a dictionary with categories and their account lists.
    """
    categories = {
        'unprocessed': [],
        'incomplete': [],
        'rate_limited': [],
        'complete': [],
        'skipped': [],
        'empty': []
    }

    # Load progress data
    progress_data = load_json_data(PROGRESS_FILE, {})

    # Load all links
    all_accounts = []
    if os.path.exists(FOLLOWING_LINKS_FILE):
        with open(FOLLOWING_LINKS_FILE, 'r') as f:
            links = f.readlines()
            for link in links:
                link = link.strip()
                if link:
                    username = link.rstrip('/').split('/')[-1]
                    all_accounts.append(username)

    # Categorize based on progress data
    for username in all_accounts:
        if username not in progress_data:
            categories['unprocessed'].append(username)
        else:
            data = progress_data[username]

            # Check various conditions
            if data.get('rate_limited', False):
                categories['rate_limited'].append(username)
            elif data.get('skipped', False):
                categories['skipped'].append(username)
            elif is_account_incomplete(data):
                categories['incomplete'].append(username)
            elif data.get('followers_retrieved', 0) == 0 and data.get('following_retrieved', 0) == 0:
                categories['empty'].append(username)
            else:
                categories['complete'].append(username)

    # Log category summary
    logging.info("Account Categories:")
    total = len(all_accounts)
    for category, accounts in categories.items():
        percentage = (len(accounts) / max(1, total)) * 100
        logging.info(f"  {category}: {len(accounts)} accounts ({percentage:.1f}%)")

    return categories

def is_account_incomplete(data):
    """
    Check if an account was incompletely scraped.
    An account is incomplete if it retrieved less than 10% of its connections.
    """
    # If it's marked as skipped, it's not incomplete - it was intentionally skipped
    if data.get('skipped', False):
        return False

    followers_count = data.get('followers_count', 0)
    following_count = data.get('following_count', 0)
    followers_retrieved = data.get('followers_retrieved', 0)
    following_retrieved = data.get('following_retrieved', 0)

    # Skip if account has too many connections (these are intentionally skipped)
    if followers_count > MAX_ACCOUNT_SIZE or following_count > MAX_ACCOUNT_SIZE:
        return False

    # Check retrieval ratios
    if followers_count > 10:
        followers_ratio = followers_retrieved / followers_count
        if followers_ratio < MIN_SCRAPE_RATIO:
            return True

    if following_count > 10:
        following_ratio = following_retrieved / following_count
        if following_ratio < MIN_SCRAPE_RATIO:
            return True

    return False

def build_prioritized_queue(categories, max_queue_size=100):
    """
    Build a prioritized queue of accounts to scrape.
    Priority order: unprocessed > incomplete > rate_limited > empty
    Note: Skipped accounts are NOT included as they're too large to scrape
    """
    queue = []

    # 1. Add unprocessed accounts (highest priority)
    unprocessed = categories['unprocessed']
    if unprocessed:
        # Randomize to avoid patterns
        random.shuffle(unprocessed)
        queue.extend(unprocessed[:max_queue_size])

    # 2. Add incomplete accounts if room (but NOT skipped accounts)
    if len(queue) < max_queue_size:
        incomplete = categories['incomplete']
        if incomplete:
            random.shuffle(incomplete)
            remaining_slots = max_queue_size - len(queue)
            queue.extend(incomplete[:remaining_slots])

    # 3. Occasionally retry rate-limited accounts
    if len(queue) < max_queue_size and random.random() < 0.2:  # 20% chance
        rate_limited = categories['rate_limited']
        if rate_limited:
            logging.info("Including rate-limited accounts for retry")
            remaining_slots = max_queue_size - len(queue)
            queue.extend(rate_limited[:remaining_slots])

    # 4. Add empty accounts if still room
    if len(queue) < max_queue_size:
        empty = categories['empty']
        if empty:
            random.shuffle(empty)
            remaining_slots = max_queue_size - len(queue)
            queue.extend(empty[:remaining_slots])

    # Note: We NEVER add 'skipped' accounts to the queue as they're too large

    logging.info(f"Built queue with {len(queue)} accounts (excluding skipped)")
    if queue:
        logging.info(f"Queue composition: {queue[:5]}... (showing first 5)")

    return queue

def calculate_batch_size(categories):
    """
    Calculate appropriate batch size based on current state.
    """
    unprocessed = len(categories['unprocessed'])
    incomplete = len(categories['incomplete'])

    # If many unprocessed accounts, use larger batches
    if unprocessed > 100:
        batch_size = random.randint(8, 12)
    elif unprocessed > 50:
        batch_size = random.randint(6, 10)
    elif incomplete > 100:
        batch_size = random.randint(4, 8)
    else:
        batch_size = random.randint(3, 6)

    logging.info(f"Calculated batch size: {batch_size}")
    return batch_size

def safe_to_run():
    """Check if it's safe to run a scraping session"""
    current_hour = datetime.datetime.now().hour
    current_minute = datetime.datetime.now().minute

    # Random skip for human-like behavior
    if random.random() < RANDOM_SKIP_CHANCE:
        skip_minutes = random.randint(30, 60)
        logging.info(f"Randomly skipping session for human-like pattern")
        logging.info(f"Will check again in {skip_minutes} minutes")
        time.sleep(skip_minutes * 60)
        return False

    # Don't scrape during pause hours
    if current_hour in PAUSE_HOURS:
        logging.info(f"It's {current_hour}:{current_minute:02d}, during pause hours")
        return False

    # Check session count for the day
    session_file = os.path.join(DATA_DIR, "daily_sessions.json")
    sessions_data = load_json_data(session_file, {"date": "", "count": 0})

    today = datetime.date.today().isoformat()
    if sessions_data["date"] != today:
        sessions_data = {"date": today, "count": 0}

    if sessions_data["count"] >= MAX_SESSIONS_PER_DAY:
        logging.info(f"Reached maximum {MAX_SESSIONS_PER_DAY} sessions today")
        return False

    # Update session count
    sessions_data["count"] += 1
    save_json_data(sessions_data, session_file)

    return True

def run_following_scraping_session(batch_size):
    """
    Run a session to scrape following accounts.
    """
    logging.info(f"Starting following scraping session with batch size {batch_size}")

    try:
        # Build command - using Instagrapi API instead of Selenium
        command = [
            "python3", "scrape_with_instagrapi.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--batch-size", str(batch_size)
        ]

        # Execute the command
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # Read output in real-time
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                logging.info(f"SCRAPER: {line}")

        # Wait for completion
        process.wait()

        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Scraping failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return False

        return True

    except Exception as e:
        logging.error(f"Error running scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def wait_for_next_session():
    """Wait a random amount of time before the next session"""
    # Add variation for human-like behavior
    if random.random() < 0.2:  # 20% chance for longer break
        wait_minutes = random.randint(MAX_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES + 30)
        logging.info(f"Taking a longer break ({wait_minutes} minutes)")
    else:
        wait_minutes = random.randint(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)

    next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=wait_minutes)
    logging.info(f"Waiting {wait_minutes} minutes until {next_run_time.strftime('%H:%M:%S')}")

    # Sleep with periodic updates
    elapsed = 0
    wait_seconds = wait_minutes * 60
    update_interval = 600  # 10 minutes

    while elapsed < wait_seconds:
        sleep_time = min(60, wait_seconds - elapsed)
        time.sleep(sleep_time)
        elapsed += sleep_time

        if elapsed % update_interval == 0 and elapsed < wait_seconds:
            minutes_left = (wait_seconds - elapsed) // 60
            logging.info(f"{minutes_left} minutes remaining until next session")

def display_progress_summary():
    """Display a detailed progress summary"""
    categories = categorize_accounts()

    # Calculate totals
    total_accounts = sum(len(accounts) for accounts in categories.values())
    complete = len(categories['complete'])
    incomplete = len(categories['incomplete'])
    unprocessed = len(categories['unprocessed'])
    skipped = len(categories['skipped'])
    rate_limited = len(categories['rate_limited'])
    empty = len(categories['empty'])

    # Calculate real work that needs to be done (exclude skipped accounts)
    workable_accounts = total_accounts - skipped
    real_completion = (complete / max(1, workable_accounts)) * 100

    logging.info("\n" + "=" * 60)
    logging.info("PROGRESS SUMMARY")
    logging.info("=" * 60)
    logging.info(f"Total accounts in list: {total_accounts}")
    logging.info(f"Accounts to actually scrape: {workable_accounts} (excluding {skipped} skipped)")
    logging.info(f"✓ Fully completed: {complete} ({(complete/max(1,workable_accounts))*100:.1f}% of workable)")
    logging.info(f"⚠ Partially scraped: {incomplete} ({(incomplete/max(1,workable_accounts))*100:.1f}% of workable)")
    logging.info(f"✗ Not attempted: {unprocessed} ({(unprocessed/max(1,workable_accounts))*100:.1f}% of workable)")
    logging.info(f"⊘ Skipped (too large): {skipped}")
    logging.info(f"⟲ Rate limited: {rate_limited}")
    logging.info(f"∅ Empty accounts: {empty}")

    # Estimate time to completion (only count incomplete and unprocessed, not skipped)
    remaining = unprocessed + incomplete
    if remaining > 0:
        # Assume average of 8 accounts per session, accounting for skips
        estimated_sessions = remaining // 6  # Reduced because many will be skipped
        estimated_days = estimated_sessions / MAX_SESSIONS_PER_DAY
        logging.info(f"\nEstimated to complete: ~{estimated_sessions} sessions (~{estimated_days:.1f} days)")
    else:
        logging.info("\n✅ All workable accounts have been processed!")

    logging.info("=" * 60 + "\n")

def main():
    """Main execution loop"""
    setup_logging()
    logging.info("Starting Instagram Following Accounts Auto Scraper")

    try:
        # Initial progress display
        display_progress_summary()

        while True:
            # 1. Categorize all accounts
            categories = categorize_accounts()

            # 2. Check if we're done
            if len(categories['unprocessed']) == 0 and len(categories['incomplete']) == 0:
                logging.info("🎉 All accounts have been processed!")
                logging.info("Checking for any rate-limited accounts to retry...")

                if len(categories['rate_limited']) > 0:
                    logging.info(f"Found {len(categories['rate_limited'])} rate-limited accounts to retry")
                else:
                    logging.info("No more accounts to process. Exiting.")
                    break

            # 3. Check if safe to run
            if not safe_to_run():
                time.sleep(3600)  # Wait an hour
                continue

            # 4. Calculate batch size
            batch_size = calculate_batch_size(categories)

            # 5. Run scraping session
            success = run_following_scraping_session(batch_size)

            if success:
                logging.info("Session completed successfully")
            else:
                logging.error("Session failed")

            # 6. Display updated progress
            display_progress_summary()

            # 7. Wait for next session
            wait_for_next_session()

    except KeyboardInterrupt:
        logging.info("Script interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        logging.error(traceback.format_exc())
    finally:
        logging.info("Auto scraper ended")

if __name__ == "__main__":
    main()