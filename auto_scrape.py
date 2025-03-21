#!/usr/bin/env python3
"""
Instagram Auto Scraper

This script automates the process of collecting Instagram followers/following data
over multiple sessions with safe time intervals to avoid detection.
It's designed to run in the background (e.g., overnight) until all
following accounts are collected.
"""

import os
import json
import time
import random
import logging
import subprocess
import traceback
import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"auto_scrape_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Constants
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers.json")
FOLLOWING_FILE = os.path.join(DATA_DIR, "following.json")
CURSOR_FILE = os.path.join(DATA_DIR, "next_cursor.json")
STATUS_FILE = os.path.join(DATA_DIR, "auto_scrape_status.json")
FOLLOWING_LINKS_FILE = os.path.join(DATA_DIR, "followingLinks.txt")
PROGRESS_FILE = os.path.join(DATA_DIR, "scraping_progress.json")

# Instagram account credentials
USERNAME = "fretin98"  # Replace with your username if different
PASSWORD = "Lcy199818su!"  # Replace with your password if different

# Settings for safe scraping
MIN_INTERVAL_MINUTES = 20  # Minimum time between sessions (was 45)
MAX_INTERVAL_MINUTES = 40  # Maximum time between sessions (was 90)
MAX_SESSIONS_PER_DAY = 18  # Maximum number of sessions per day (was 12)
HEADLESS_MODE = True  # Run without visible browser window
FOLLOWINGS_BATCH_SIZE = None  # Will be randomized each session
NATURAL_BREAK_LENGTH_MINUTES = 120  # 2-hour natural break once per day
NATURAL_BREAK_HOUR_MIN = 13  # Natural break starts between 1 PM
NATURAL_BREAK_HOUR_MAX = 15  # and 3 PM
RANDOM_SKIP_CHANCE = 0.1  # 10% chance to randomly skip a session for more human-like behavior

# Safety settings
PAUSE_HOURS = [2, 3, 4, 5]  # Hours to pause scraping (2am-5am) to seem human

def ensure_dir_exists(directory):
    """Ensure a directory exists, creating it if necessary"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.info(f"Created directory: {directory}")

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

def get_progress():
    """Get current scraping progress"""
    following_data = load_json_data(FOLLOWING_FILE, [])
    status_data = load_json_data(STATUS_FILE, {"total_following": 0, "sessions": 0, "last_run": None})
    
    # If we don't have a total count yet, estimate it
    if status_data["total_following"] == 0 and following_data:
        status_data["total_following"] = 1861  # Use the known total from previous logs
        save_json_data(status_data, STATUS_FILE)
    
    return {
        "collected": len(following_data),
        "total": status_data["total_following"],
        "sessions": status_data["sessions"],
        "last_run": status_data["last_run"]
    }

def get_following_accounts_progress():
    """Get progress on scraping following accounts"""
    progress_data = load_json_data(PROGRESS_FILE, {})
    links = []
    
    try:
        if os.path.exists(FOLLOWING_LINKS_FILE):
            with open(FOLLOWING_LINKS_FILE, "r") as f:
                links = f.readlines()
    except Exception as e:
        logging.error(f"Error reading following links: {e}")
        
    return {
        "accounts_processed": len(progress_data),
        "accounts_remaining": len(links)
    }

def update_status(session_completed=True, total_following=None):
    """Update the status file with latest information"""
    status_data = load_json_data(STATUS_FILE, {
        "total_following": 0,
        "sessions": 0,
        "last_run": None
    })
    
    if session_completed:
        status_data["sessions"] += 1
        status_data["last_run"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if total_following is not None:
        status_data["total_following"] = total_following
    
    save_json_data(status_data, STATUS_FILE)

def safe_to_run():
    """Check if it's safe to run a scraping session"""
    current_hour = datetime.datetime.now().hour
    current_minute = datetime.datetime.now().minute
    
    # Randomly skip a session (10% chance) to create more human-like patterns
    if random.random() < RANDOM_SKIP_CHANCE:
        skip_minutes = random.randint(30, 60)
        logging.info(f"Randomly skipping this session to create a more human-like pattern")
        logging.info(f"Will check again in {skip_minutes} minutes")
        time.sleep(skip_minutes * 60)
        return False
    
    # Don't scrape during pause hours
    if current_hour in PAUSE_HOURS:
        logging.info(f"It's {current_hour}:{current_minute:02d}, during pause hours. Waiting until morning.")
        return False
    
    # Check if it's time for a natural break - use a random hour in the specified range
    # But only take the break once per day by setting a flag in the status file
    status_data = load_json_data(STATUS_FILE, {"sessions": 0, "last_run": None, "natural_break_taken": False})
    
    # Reset natural break flag for a new day
    if status_data.get("last_run"):
        last_run = datetime.datetime.strptime(status_data["last_run"], '%Y-%m-%d %H:%M:%S')
        now = datetime.datetime.now()
        if last_run.date() != now.date():
            status_data["natural_break_taken"] = False
            save_json_data(status_data, STATUS_FILE)
    
    # Take a natural break if within the time range and we haven't taken one today
    if (NATURAL_BREAK_HOUR_MIN <= current_hour <= NATURAL_BREAK_HOUR_MAX and 
            not status_data.get("natural_break_taken", False)):
        # Add some randomness to the break length
        break_length = random.randint(
            NATURAL_BREAK_LENGTH_MINUTES - 30, 
            NATURAL_BREAK_LENGTH_MINUTES + 30
        )
        logging.info(f"It's {current_hour}:{current_minute:02d}, taking a natural break to appear more human-like.")
        next_check_time = datetime.datetime.now() + datetime.timedelta(minutes=break_length)
        logging.info(f"Will take a {break_length} minute break and resume at approximately {next_check_time.strftime('%H:%M')}")
        
        # Mark that we've taken our natural break for today
        status_data["natural_break_taken"] = True
        save_json_data(status_data, STATUS_FILE)
        
        # Actually wait here for the break time
        time.sleep(break_length * 60)
        logging.info("Natural break complete, resuming operations")
        return True  # Return true to indicate we can proceed after waiting
        
    # Check if we've reached the maximum sessions per day
    if status_data.get("last_run"):
        last_run = datetime.datetime.strptime(status_data["last_run"], '%Y-%m-%d %H:%M:%S')
        now = datetime.datetime.now()
        
        # If last run was on a different day, reset session count
        if last_run.date() != now.date():
            status_data["sessions"] = 0
            save_json_data(status_data, STATUS_FILE)
        elif status_data.get("sessions", 0) >= MAX_SESSIONS_PER_DAY:
            logging.info(f"Reached maximum {MAX_SESSIONS_PER_DAY} sessions today. Waiting until tomorrow.")
            return False
        
        # Check if we've waited long enough since the last run
        minutes_since_last_run = (now - last_run).total_seconds() / 60
        if minutes_since_last_run < MIN_INTERVAL_MINUTES:
            logging.info(f"Only {minutes_since_last_run:.1f} minutes since last run. " 
                       f"Waiting at least {MIN_INTERVAL_MINUTES} minutes between runs.")
            return False
    
    return True

def run_scraping_session():
    """Run a single scraping session using the main script"""
    logging.info("Starting new scraping session")
    
    try:
        # Randomize max_pages each session for more human-like behavior
        max_pages = random.randint(3, 7)  # Vary between 3-7 pages per session
        logging.info(f"Using {max_pages} max pages for this session")
        
        # Run the scraping script with command line arguments instead of input files
        command = [
            "python3", "scrapeMyAccount.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--resume",
            "--headless",
            "--max-pages", str(max_pages)  # Use randomized value
        ]
        
        # Execute the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Read and log output in real-time
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                logging.info(f"SCRAPER: {line}")
                
                # Extract the following count if available
                if "Following:" in line and "," in line:
                    try:
                        total_following = int(line.split("Following:")[1].split(",")[0].strip())
                        update_status(session_completed=False, total_following=total_following)
                    except:
                        pass
        
        # Wait for process to complete
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Scraping script failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return False
        
        # Update status
        update_status(session_completed=True)
        return True
        
    except Exception as e:
        logging.error(f"Error running scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def run_following_scraping_session():
    """Run a session to scrape data from following accounts"""
    logging.info("Starting following accounts scraping session")
    
    # Randomize batch size for each session for more human-like behavior
    batch_size = random.randint(2, 5)
    logging.info(f"Using random batch size of {batch_size} accounts for this session")
    
    try:
        # Run the scrapingFollowing script with command line arguments
        command = [
            "python3", "scrapingFollowing.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--batch-size", str(batch_size),
            "--headless"
        ]
        
        # Execute the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Read and log output in real-time
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                logging.info(f"FOLLOWING SCRAPER: {line}")
        
        # Wait for process to complete
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Following scraping failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"Error running following scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def wait_for_next_session():
    """Wait a random amount of time before the next session"""
    # Choose a random interval between min and max
    # Add a bit more randomness by sometimes having slightly longer intervals
    if random.random() < 0.2:  # 20% chance for a longer break
        wait_minutes = random.randint(MAX_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES + 20)
        logging.info(f"Taking a slightly longer break this time ({wait_minutes} minutes)")
    else:
        wait_minutes = random.randint(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)
    
    wait_seconds = wait_minutes * 60
    
    next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=wait_minutes)
    logging.info(f"Waiting {wait_minutes} minutes until next session at {next_run_time.strftime('%H:%M:%S')}")
    
    # Wait with periodic status updates - less predictable intervals
    update_intervals = [600, 900, 1200]  # 10, 15, or 20 minutes
    next_update = random.choice(update_intervals)
    elapsed = 0
    
    while elapsed < wait_seconds:
        sleep_time = min(60, wait_seconds - elapsed)  # Sleep in 1-minute chunks
        time.sleep(sleep_time)
        elapsed += sleep_time
        
        if elapsed >= next_update:
            minutes_left = (wait_seconds - elapsed) // 60
            logging.info(f"{minutes_left} minutes remaining until next session")
            next_update = elapsed + random.choice(update_intervals)

def check_completion():
    """Check if we've collected all the following accounts"""
    progress = get_progress()
    if progress["collected"] >= progress["total"]:
        logging.info(f"All following accounts collected! {progress['collected']}/{progress['total']}")
        return True
    return False

def main():
    """Main function to run the auto-scraper"""
    logging.info("=" * 60)
    logging.info("Instagram Auto Scraper Starting")
    logging.info("=" * 60)
    
    # Create necessary directories
    ensure_dir_exists(DATA_DIR)
    
    # Initialize status if needed
    if not os.path.exists(STATUS_FILE):
        update_status(session_completed=False)
    
    try:
        while True:
            # Check if we've collected everything
            main_collection_complete = check_completion()
            following_progress = get_following_accounts_progress()
            
            if main_collection_complete and following_progress["accounts_remaining"] == 0:
                logging.info("Data collection complete! All following accounts and their data collected.")
                break
            
            # Check if it's safe to run now
            if not safe_to_run():
                # Wait an hour before checking again
                logging.info("Waiting 60 minutes before checking again")
                time.sleep(3600)
                continue
            
            # Run a main account scraping session if we need more following accounts
            if not main_collection_complete:
                logging.info("Running main account scraping to get more following accounts")
                success = run_scraping_session()
                
                progress = get_progress()
                logging.info(f"Main scraping completed. Progress: {progress['collected']}/{progress['total']} "
                          f"following accounts ({(progress['collected']/progress['total']*100):.1f}%)")
                
                # After each successful main scraping session, also process some following accounts
                if success and following_progress["accounts_remaining"] > 0:
                    # Wait a bit before starting the following scraping
                    intermediate_wait = random.randint(10, 20)
                    logging.info(f"Waiting {intermediate_wait} minutes before processing following accounts")
                    time.sleep(intermediate_wait * 60)
                    
                    following_success = run_following_scraping_session()
                    
                    # Get updated progress
                    following_progress = get_following_accounts_progress()
                    logging.info(f"Following scraping completed. {following_progress['accounts_processed']} accounts "
                              f"processed, {following_progress['accounts_remaining']} remaining.")
            
            # If main collection is complete but we still have following accounts to process
            elif following_progress["accounts_remaining"] > 0:
                logging.info("Main collection complete. Focusing on processing following accounts.")
                following_success = run_following_scraping_session()
                
                # Get updated progress
                following_progress = get_following_accounts_progress()
                logging.info(f"Following scraping completed. {following_progress['accounts_processed']} accounts "
                          f"processed, {following_progress['accounts_remaining']} remaining.")
            
            # Wait before next session
            wait_for_next_session()
            
    except KeyboardInterrupt:
        logging.info("Auto scraper stopped by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        logging.error(traceback.format_exc())
    finally:
        logging.info("Auto scraper shutting down")

if __name__ == "__main__":
    main() 