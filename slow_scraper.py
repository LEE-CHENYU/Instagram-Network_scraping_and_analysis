#!/usr/bin/env python3
"""
Slow, careful Instagram scraper that mimics human behavior
to avoid rate limits
"""

import time
import random
import subprocess
import datetime
import json
import os

DATA_DIR = "instagram_data"
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")

def run_single_account():
    """Run scraping for just ONE account with human-like behavior"""

    # Random wait before starting (30-120 seconds)
    wait_time = random.randint(30, 120)
    print(f"Waiting {wait_time} seconds before starting (human-like delay)...")
    time.sleep(wait_time)

    # Run scraping for just 1 account
    command = [
        "python3", "scrapingFollowing.py",
        "--username", "cheneyli7",
        "--password", "Lcy199818",
        "--batch-size", "1",  # Only 1 account at a time
        "--headless"
    ]

    print(f"Starting scrape at {datetime.datetime.now()}")
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ Scraping completed successfully")
    else:
        print("✗ Scraping failed")
        print(result.stderr)

    return result.returncode == 0

def count_rate_limited():
    """Count how many accounts are rate-limited"""
    if not os.path.exists(PROGRESS_FILE):
        return 0

    with open(PROGRESS_FILE, 'r') as f:
        data = json.load(f)

    rate_limited = sum(1 for v in data.values() if v.get('rate_limited', False))
    return rate_limited

def main():
    """Main loop - very slow and careful"""

    print("="*60)
    print("SLOW INSTAGRAM SCRAPER")
    print("This will scrape VERY slowly to avoid rate limits")
    print("="*60)

    session_count = 0
    max_sessions = 20  # Max accounts per run

    while session_count < max_sessions:
        session_count += 1
        print(f"\n--- Session {session_count}/{max_sessions} ---")

        # Check rate limit status
        rate_limited_count = count_rate_limited()
        print(f"Currently {rate_limited_count} accounts are rate-limited")

        # Run single account scrape
        success = run_single_account()

        if not success:
            print("Scraping failed. Waiting longer before retry...")
            time.sleep(300)  # 5 minutes on failure
            continue

        # Random wait between accounts (2-5 minutes)
        wait_minutes = random.uniform(2, 5)
        wait_seconds = int(wait_minutes * 60)

        print(f"Waiting {wait_minutes:.1f} minutes before next account...")
        print(f"Next scrape at {(datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)).strftime('%H:%M:%S')}")

        # Add occasional longer breaks
        if session_count % 5 == 0:
            print("Taking a longer break (10-15 minutes)...")
            wait_seconds = random.randint(600, 900)

        time.sleep(wait_seconds)

    print("\n" + "="*60)
    print(f"Completed {session_count} scraping sessions")
    print(f"Final rate-limited count: {count_rate_limited()}")
    print("="*60)

if __name__ == "__main__":
    main()