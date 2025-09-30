#!/usr/bin/env python3
"""
Continuous scraping script - runs multiple sessions until all accounts are complete
"""

import subprocess
import time
import json
import os
import logging
from datetime import datetime

# Configuration
DATA_DIR = "instagram_data"
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")

# Scraping parameters
ACCOUNTS_PER_SESSION = 25  # How many accounts to process per session (reduced from 50)
DELAY_BETWEEN_SESSIONS = 300  # Seconds to wait between sessions (5 minutes, increased from 60)
MAX_SESSIONS = 250  # Maximum number of sessions to run (increased to accommodate smaller batches)

# Quality thresholds (same as original script)
MIN_SCRAPE_RATIO = 0.1
MAX_ACCOUNT_SIZE = 2000

def setup_logging():
    """Set up logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"continuous_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

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

def get_progress_stats():
    """Get current progress statistics"""
    progress_data = load_json_data(PROGRESS_FILE, {})
    following_links = load_following_links()
    categories = categorize_accounts(progress_data, following_links)

    total = len(following_links)
    workable = total - len(categories['skipped'])
    complete = len(categories['complete'])
    remaining = len(categories['rate_limited']) + len(categories['incomplete']) + len(categories['unprocessed'])

    return {
        'total': total,
        'workable': workable,
        'complete': complete,
        'remaining': remaining,
        'categories': categories
    }

def print_progress_summary(stats, session_num=None):
    """Print a progress summary"""
    if session_num:
        logging.info(f"\n{'='*60}")
        logging.info(f"SESSION {session_num} COMPLETE")
        logging.info(f"{'='*60}")
    else:
        logging.info(f"\n{'='*60}")
        logging.info(f"PROGRESS SUMMARY")
        logging.info(f"{'='*60}")

    logging.info(f"Total accounts: {stats['total']:,}")
    logging.info(f"Workable accounts: {stats['workable']:,}")
    logging.info(f"✅ Complete: {stats['complete']:,} ({stats['complete']/stats['workable']*100:.1f}%)")
    logging.info(f"⏳ Remaining: {stats['remaining']:,} ({stats['remaining']/stats['workable']*100:.1f}%)")

    categories = stats['categories']
    logging.info(f"\nDetailed breakdown:")
    logging.info(f"  Complete: {len(categories['complete']):,}")
    logging.info(f"  Incomplete: {len(categories['incomplete']):,}")
    logging.info(f"  Rate-limited: {len(categories['rate_limited']):,}")
    logging.info(f"  Unprocessed: {len(categories['unprocessed']):,}")
    logging.info(f"  Skipped: {len(categories['skipped']):,}")
    logging.info(f"  Empty: {len(categories['empty']):,}")
    logging.info(f"{'='*60}\n")

def run_scraping_session():
    """Run a single scraping session"""
    try:
        result = subprocess.run(
            ['python3', 'scrape_with_instagrapi.py'],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per session
        )

        if result.returncode == 0:
            logging.info("Session completed successfully")
            return True
        else:
            logging.error(f"Session failed with return code {result.returncode}")
            logging.error(f"STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("Session timed out after 30 minutes")
        return False
    except Exception as e:
        logging.error(f"Error running session: {e}")
        return False

def main():
    setup_logging()

    logging.info("=" * 60)
    logging.info("CONTINUOUS INSTAGRAM SCRAPING")
    logging.info("=" * 60)
    logging.info(f"Configuration:")
    logging.info(f"  Accounts per session: {ACCOUNTS_PER_SESSION}")
    logging.info(f"  Delay between sessions: {DELAY_BETWEEN_SESSIONS} seconds")
    logging.info(f"  Max sessions: {MAX_SESSIONS}")
    logging.info("=" * 60)

    # Initial progress check
    initial_stats = get_progress_stats()
    print_progress_summary(initial_stats)

    if initial_stats['remaining'] == 0:
        logging.info("🎉 All accounts are already complete!")
        return

    logging.info(f"Starting continuous scraping...")
    logging.info(f"Estimated sessions needed: {(initial_stats['remaining'] + ACCOUNTS_PER_SESSION - 1) // ACCOUNTS_PER_SESSION}")

    session_count = 0
    total_success = 0
    total_failures = 0

    start_time = time.time()

    while session_count < MAX_SESSIONS:
        session_count += 1

        # Check if we're done
        current_stats = get_progress_stats()
        if current_stats['remaining'] == 0:
            logging.info("\n🎉 ALL ACCOUNTS COMPLETE! 🎉")
            break

        logging.info(f"\n{'='*60}")
        logging.info(f"STARTING SESSION {session_count}/{MAX_SESSIONS}")
        logging.info(f"Remaining accounts: {current_stats['remaining']:,}")
        logging.info(f"{'='*60}")

        # Run the session
        session_start = time.time()
        success = run_scraping_session()
        session_duration = time.time() - session_start

        if success:
            total_success += 1
            logging.info(f"✅ Session {session_count} completed in {session_duration:.1f} seconds")
        else:
            total_failures += 1
            logging.warning(f"❌ Session {session_count} failed")

        # Get updated stats
        updated_stats = get_progress_stats()
        accounts_processed = initial_stats['remaining'] - updated_stats['remaining']

        print_progress_summary(updated_stats, session_count)

        # Calculate time estimates
        elapsed_time = time.time() - start_time
        if accounts_processed > 0:
            time_per_account = elapsed_time / accounts_processed
            estimated_remaining_time = time_per_account * updated_stats['remaining']

            logging.info(f"⏱️  Time estimates:")
            logging.info(f"  Elapsed: {elapsed_time/60:.1f} minutes")
            logging.info(f"  Per account: {time_per_account:.1f} seconds")
            logging.info(f"  Estimated remaining: {estimated_remaining_time/60:.1f} minutes ({estimated_remaining_time/3600:.1f} hours)")

        # Check if we should continue
        if updated_stats['remaining'] == 0:
            logging.info("\n🎉 ALL ACCOUNTS COMPLETE! 🎉")
            break

        # Wait before next session (unless this is the last iteration)
        if session_count < MAX_SESSIONS and updated_stats['remaining'] > 0:
            logging.info(f"\n⏸️  Waiting {DELAY_BETWEEN_SESSIONS} seconds before next session...")
            time.sleep(DELAY_BETWEEN_SESSIONS)

    # Final summary
    total_time = time.time() - start_time
    final_stats = get_progress_stats()

    logging.info("\n" + "=" * 60)
    logging.info("CONTINUOUS SCRAPING COMPLETE")
    logging.info("=" * 60)
    logging.info(f"Total sessions run: {session_count}")
    logging.info(f"Successful sessions: {total_success}")
    logging.info(f"Failed sessions: {total_failures}")
    logging.info(f"Total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)")
    logging.info(f"Accounts processed: {initial_stats['remaining'] - final_stats['remaining']:,}")
    logging.info(f"Final completion: {final_stats['complete']}/{final_stats['workable']} ({final_stats['complete']/final_stats['workable']*100:.1f}%)")

    if final_stats['remaining'] > 0:
        logging.info(f"\n⚠️  {final_stats['remaining']:,} accounts still remaining")
        logging.info("You can run this script again to continue scraping")
    else:
        logging.info("\n🎉 ALL ACCOUNTS SUCCESSFULLY SCRAPED! 🎉")

    logging.info("=" * 60)

if __name__ == "__main__":
    main()
