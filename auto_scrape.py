#!/usr/bin/env python3
"""
Instagram Auto Scraper

This script automates the process of collecting Instagram followers/following data
over multiple sessions with safe time intervals to avoid detection.
It's designed to run in the background (e.g., overnight) until all
following accounts are collected.
"""

"""
Performance Settings:
- The script is configured to scrape approximately 600 accounts per day
- This is achieved through:
  - 30 scraping sessions per day (MAX_SESSIONS_PER_DAY)
  - 40-60 accounts per batch (in run_following_scraping_session)
  - 15-30 minute intervals between sessions (MIN/MAX_INTERVAL_MINUTES)
- Adjust these values carefully if needed, as too aggressive scraping may trigger Instagram's rate limits

Debug Information:
- Added duplicate link detection and removal (debug_check_duplicates function)
- Added file locking mechanism to prevent race conditions (save_links_with_lock function)
- Added detailed logging to track queue sizes before and after processing
- Added --debug flag to scrapingFollowing.py to enable additional debugging
- Added link file format inspection (debug_inspect_links_file function)

Bug Fixes:
- Fixed issue where the number of remaining accounts could increase instead of decrease
- Fixed potential race condition when writing to followingLinks.txt
- Added proper error handling when moving failed links to the end of the queue
- Improved sanitization of links before saving to prevent format issues

How to Use This Fix:
1. Run this script normally: python3 auto_scrape.py
2. The script will automatically check for and fix duplicates in the followingLinks.txt file
3. Each time it processes a batch of accounts, it will check for and report any issues
4. If the number of accounts still increases, check the logs for detailed diagnostics

Tip: To quickly fix the issue without running a full session, you can also run:
     python3 -c "import auto_scrape; auto_scrape.debug_check_duplicates(); auto_scrape.debug_inspect_links_file()"
"""

import os
import json
import time
import random
import logging
import subprocess
import traceback
import datetime
import fcntl
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_logging():
    """Set up logging configuration"""
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
    logging.info("=" * 60)
    logging.info("Instagram Auto Scraper Starting")
    logging.info("=" * 60)

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
MIN_INTERVAL_MINUTES = 15  # Minimum time between sessions (was 20)
MAX_INTERVAL_MINUTES = 30  # Maximum time between sessions (was 40)
MAX_SESSIONS_PER_DAY = 30  # Maximum number of sessions per day (was 18)
HEADLESS_MODE = True  # Run without visible browser window
FOLLOWINGS_BATCH_SIZE = None  # Will be randomized each session
NATURAL_BREAK_LENGTH_MINUTES = 120  # 2-hour natural break once per day
RANDOM_SKIP_CHANCE = 0.1  # 10% chance to randomly skip a session for more human-like behavior
WAIT_TIME = 1200  # 20 minutes instead of 1 hour

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
    followers_data = load_json_data(FOLLOWERS_FILE, [])
    status_data = load_json_data(STATUS_FILE, {"total_following": 0, "total_followers": 0, "sessions": 0, "last_run": None})
    
    # Handle case where total_followers might not exist in older status files
    if "total_followers" not in status_data:
        status_data["total_followers"] = 0
    
    # If we don't have total counts and we have some data, set counts based on collected data
    # until we can get the actual counts from the profile
    if status_data["total_following"] == 0 and following_data:
        # Use collected count as a temporary baseline
        status_data["total_following"] = len(following_data)
        logging.info(f"Setting temporary total following count to {len(following_data)} until profile is loaded")
        save_json_data(status_data, STATUS_FILE)
    
    if status_data["total_followers"] == 0 and followers_data:
        # Use collected count as a temporary baseline
        status_data["total_followers"] = len(followers_data)
        logging.info(f"Setting temporary total followers count to {len(followers_data)} until profile is loaded")
        save_json_data(status_data, STATUS_FILE)
    
    # Log current counts from status file
    logging.info(f"Current counts in status file - Followers: {status_data['total_followers']}, Following: {status_data['total_following']}")
    
    return {
        "following_collected": len(following_data),
        "following_total": status_data["total_following"],
        "followers_collected": len(followers_data),
        "followers_total": status_data["total_followers"],
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

def update_status(session_completed=True, total_following=None, total_followers=None):
    """Update the status file with latest information"""
    status_data = load_json_data(STATUS_FILE, {
        "total_following": 0,
        "total_followers": 0,
        "sessions": 0,
        "last_run": None
    })
    
    # Ensure required keys exist
    for key in ["total_following", "total_followers", "sessions", "last_run"]:
        if key not in status_data:
            if key == "sessions":
                status_data[key] = 0
            elif key == "last_run":
                status_data[key] = None
            else:
                status_data[key] = 0
    
    if session_completed:
        status_data["sessions"] += 1
        status_data["last_run"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if total_following is not None:
        status_data["total_following"] = total_following
    
    if total_followers is not None:
        status_data["total_followers"] = total_followers
    
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
    
    # Reset natural break flag and set random break hours for a new day
    if status_data.get("last_run"):
        last_run = datetime.datetime.strptime(status_data["last_run"], '%Y-%m-%d %H:%M:%S')
        now = datetime.datetime.now()
        if last_run.date() != now.date():
            status_data["natural_break_taken"] = False
            # Set random break hours for today
            # Choose a random 2-hour window between 11 AM and 6 PM
            break_start = random.randint(11, 16)  # 11 AM to 4 PM start time (to end by 6 PM)
            status_data["break_hour_min"] = break_start
            status_data["break_hour_max"] = break_start + 2
            logging.info(f"Set today's natural break window to {break_start}:00-{break_start+2}:00")
            save_json_data(status_data, STATUS_FILE)
    
    # If break hours aren't set yet (first run of the day), set them now
    if "break_hour_min" not in status_data or "break_hour_max" not in status_data:
        break_start = random.randint(11, 16)  # 11 AM to 4 PM start time
        status_data["break_hour_min"] = break_start
        status_data["break_hour_max"] = break_start + 2
        logging.info(f"Set today's natural break window to {break_start}:00-{break_start+2}:00")
        save_json_data(status_data, STATUS_FILE)
    
    # Take a natural break if within the time range and we haven't taken one today
    break_hour_min = status_data.get("break_hour_min")
    break_hour_max = status_data.get("break_hour_max")
    
    if (break_hour_min <= current_hour <= break_hour_max and 
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
    
    # Check collection progress
    progress = get_progress()
    
    # Only skip if both are complete
    if progress["following_collected"] >= progress["following_total"] and progress["followers_collected"] >= progress["followers_total"]:
        logging.info(f"Already collected all following accounts ({progress['following_collected']}/{progress['following_total']}) and followers ({progress['followers_collected']}/{progress['followers_total']}). Skipping main scraping session.")
        return True
    
    # Log which collection still needs work
    if progress["following_collected"] < progress["following_total"]:
        logging.info(f"Need to collect more following accounts: {progress['following_collected']}/{progress['following_total']}")
    if progress["followers_collected"] < progress["followers_total"]:
        logging.info(f"Need to collect more followers: {progress['followers_collected']}/{progress['followers_total']}")
    
    try:
        # Calculate how many followers we still need to collect
        followers_remaining = max(0, progress["followers_total"] - progress["followers_collected"])
        following_remaining = max(0, progress["following_total"] - progress["following_collected"])
        
        # Adjust max_pages based on how many items we still need to collect
        # Use higher value for followers since that's what we're concerned about
        if followers_remaining > 500:
            max_pages = random.randint(15, 20)  # Much more aggressive for large gaps
            logging.info(f"Large follower gap detected ({followers_remaining} remaining). Using higher max_pages: {max_pages}")
        elif followers_remaining > 200:
            max_pages = random.randint(10, 15)  # More aggressive for medium gaps
            logging.info(f"Medium follower gap detected ({followers_remaining} remaining). Using higher max_pages: {max_pages}")
        elif followers_remaining > 50:
            max_pages = random.randint(8, 12)  # Slightly more aggressive for smaller gaps
            logging.info(f"Small follower gap detected ({followers_remaining} remaining). Using higher max_pages: {max_pages}")
        else:
            max_pages = random.randint(5, 8)  # Standard range for minimal remaining
            logging.info(f"Using {max_pages} max pages for this session")
        
        # Build command line options
        command = [
            "python3", "scrapeMyAccount.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--resume",
            "--headless",
            "--max-pages", str(max_pages)
        ]
        
        # If we have a lot of existing followers that we need to scroll past,
        # add a special flag to use a more aggressive scrolling approach
        if progress["followers_collected"] > 100 and followers_remaining > 100:
            command.append("--aggressive-resume")
            logging.info(f"Using aggressive resume mode to get past {progress['followers_collected']} existing followers")
        
        # If following is complete, only scrape followers
        if progress["following_collected"] >= progress["following_total"]:
            command.append("--no-following")
            logging.info("Following collection is complete. Only scraping followers in this session.")
        
        # If followers is complete, only scrape following
        if progress["followers_collected"] >= progress["followers_total"]:
            command.append("--no-followers")
            logging.info("Followers collection is complete. Only scraping following in this session.")
        
        # Execute the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Read and log output in real-time
        total_following = None
        total_followers = None
        
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                logging.info(f"SCRAPER: {line}")
                
                # Check for the profile stats line
                if "Profile Stats:" in line:
                    logging.info("Found profile stats line")
                
                # Check for the specific followers/following count line
                if "Followers:" in line and "Following:" in line:
                    try:
                        # Parse the line: "Followers: X, Following: Y"
                        parts = line.split(",")
                        if len(parts) >= 2:
                            followers_part = parts[0].strip()
                            following_part = parts[1].strip()
                            
                            # Extract numbers
                            if "Followers:" in followers_part:
                                total_followers = int(followers_part.split("Followers:")[1].strip())
                                logging.info(f"Extracted total followers: {total_followers}")
                            
                            if "Following:" in following_part:
                                total_following = int(following_part.split("Following:")[1].strip())
                                logging.info(f"Extracted total following: {total_following}")
                    except Exception as e:
                        logging.error(f"Error parsing followers/following counts: {e}")
                
                # Alternative method to extract counts from individual lines
                elif "Following:" in line and "," in line:
                    try:
                        total_following = int(line.split("Following:")[1].split(",")[0].strip())
                        logging.info(f"Extracted total following: {total_following}")
                    except Exception as e:
                        logging.error(f"Error parsing following count: {e}")
                
                elif "Followers:" in line and "," in line:
                    try:
                        total_followers = int(line.split("Followers:")[1].split(",")[0].strip())
                        logging.info(f"Extracted total followers: {total_followers}")
                    except Exception as e:
                        logging.error(f"Error parsing followers count: {e}")
        
        # Wait for process to complete
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Scraping script failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return False
        
        # Update status with the actual counts from the profile
        if total_following is not None or total_followers is not None:
            logging.info(f"Updating status with dynamic counts - Followers: {total_followers}, Following: {total_following}")
            update_status(session_completed=True, total_following=total_following, total_followers=total_followers)
        else:
            # If we couldn't extract the counts, just update session completed
            logging.warning("Could not extract follower/following counts from output")
            update_status(session_completed=True)
        
        return True
        
    except Exception as e:
        logging.error(f"Error running scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def run_following_scraping_session():
    """Run a session to scrape data from following accounts"""
    logging.info("Starting following accounts scraping session")
    
    # Debug: Check for duplicates before processing
    logging.info("DEBUG: Checking for duplicates before processing")
    debug_check_duplicates()
    
    # Log the number of accounts before processing
    before_count = 0
    try:
        with open(FOLLOWING_LINKS_FILE, "r") as f:
            links = f.readlines()
            before_count = len(links)
        logging.info(f"DEBUG: Before processing - {before_count} accounts in queue")
    except Exception as e:
        logging.error(f"Error counting accounts before processing: {e}")
    
    # Check if there are any following accounts left to process
    following_progress = get_following_accounts_progress()
    if following_progress["accounts_remaining"] <= 0:
        logging.info("No following accounts left to process. Skipping following scraping session.")
        return True
    
    # Randomize batch size for each session for more human-like behavior
    # Increased batch size to reach approximately 600 accounts per day
    batch_size = random.randint(40, 60)
    logging.info(f"Using random batch size of {batch_size} accounts for this session")
    
    try:
        # Run the scrapingFollowing script with command line arguments
        command = [
            "python3", "scrapingFollowing.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--batch-size", str(batch_size),
            "--headless",
            "--debug"  # Add debug flag to enable debugging in scrapingFollowing.py
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
            result = False
        else:
            result = True
        
        # After processing, check the number of accounts again
        try:
            with open(FOLLOWING_LINKS_FILE, "r") as f:
                links = f.readlines()
                after_count = len(links)
            
            diff = after_count - before_count
            if diff >= 0:
                logging.error(f"DEBUG: ISSUE DETECTED - Queue size didn't decrease. Before: {before_count}, After: {after_count}, Diff: {diff}")
            else:
                logging.info(f"DEBUG: After processing - {after_count} accounts in queue (removed {abs(diff)})")
            
            # Debug: Check for duplicates after processing
            logging.info("DEBUG: Checking for duplicates after processing")
            debug_check_duplicates()
        except Exception as e:
            logging.error(f"Error counting accounts after processing: {e}")
        
        return result
        
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
    """Check if we've collected all the followers and following accounts"""
    progress = get_progress()
    following_complete = progress["following_collected"] >= progress["following_total"] if progress["following_total"] > 0 else False
    followers_complete = progress["followers_collected"] >= progress["followers_total"] if progress["followers_total"] > 0 else False
    
    # Calculate safe percentages
    following_percent = (progress["following_collected"] / max(1, progress["following_total"])) * 100
    followers_percent = (progress["followers_collected"] / max(1, progress["followers_total"])) * 100
    
    if following_complete:
        logging.info(f"All following accounts collected! {progress['following_collected']}/{progress['following_total']}")
    else:
        logging.info(f"Following collection progress: {progress['following_collected']}/{progress['following_total']} ({following_percent:.1f}%)")
    
    if followers_complete:
        logging.info(f"All followers collected! {progress['followers_collected']}/{progress['followers_total']}")
    else:
        logging.info(f"Followers collection progress: {progress['followers_collected']}/{progress['followers_total']} ({followers_percent:.1f}%)")
    
    # Return True only if both are complete
    return following_complete and followers_complete

def check_status():
    """Get the current status percentages"""
    progress = get_progress()
    following_percent = (progress["following_collected"] / max(1, progress["following_total"])) * 100
    followers_percent = (progress["followers_collected"] / max(1, progress["followers_total"])) * 100
    return {
        "following_percent": following_percent,
        "follower_percent": followers_percent
    }

def fetch_profile_counts():
    """Fetch current follower and following counts directly from the profile"""
    logging.info("Fetching current follower and following counts from profile...")
    
    try:
        # Run scrapeMyAccount.py with minimal options just to get the counts
        command = [
            "python3", "scrapeMyAccount.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--headless",
            "--no-followers",  # Don't scrape followers
            "--no-following",  # Don't scrape following
            "--max-pages", "1"  # Minimal scraping
        ]
        
        # Execute the command and capture output
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        total_following = None
        total_followers = None
        
        # Process the output to extract counts
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if line:
                logging.info(f"PROFILE CHECK: {line}")
                
                # Check for the profile stats line
                if "Profile Stats:" in line:
                    logging.info("Found profile stats")
                
                # Check for the specific followers/following count line
                if "Followers:" in line and "Following:" in line:
                    try:
                        # Parse the line: "Followers: X, Following: Y"
                        parts = line.split(",")
                        if len(parts) >= 2:
                            followers_part = parts[0].strip()
                            following_part = parts[1].strip()
                            
                            # Extract numbers
                            if "Followers:" in followers_part:
                                total_followers = int(followers_part.split("Followers:")[1].strip())
                                logging.info(f"Extracted total followers: {total_followers}")
                            
                            if "Following:" in following_part:
                                total_following = int(following_part.split("Following:")[1].strip())
                                logging.info(f"Extracted total following: {total_following}")
                    except Exception as e:
                        logging.error(f"Error parsing followers/following counts: {e}")
                
                # Alternative method to extract counts from individual lines
                elif "Following:" in line and "," in line:
                    try:
                        total_following = int(line.split("Following:")[1].split(",")[0].strip())
                        logging.info(f"Extracted total following: {total_following}")
                    except Exception as e:
                        logging.error(f"Error parsing following count: {e}")
                
                elif "Followers:" in line and "," in line:
                    try:
                        total_followers = int(line.split("Followers:")[1].split(",")[0].strip())
                        logging.info(f"Extracted total followers: {total_followers}")
                    except Exception as e:
                        logging.error(f"Error parsing followers count: {e}")
        
        # Wait for process to complete
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Profile check failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return None, None
        
        # Return the counts if found
        if total_following is not None or total_followers is not None:
            return total_followers, total_following
        else:
            logging.warning("Could not extract follower/following counts from profile check")
            return None, None
        
    except Exception as e:
        logging.error(f"Error checking profile counts: {e}")
        logging.error(traceback.format_exc())
        return None, None

def debug_check_duplicates():
    """Check for duplicate links in the followingLinks.txt file and remove them"""
    try:
        if not os.path.exists(FOLLOWING_LINKS_FILE):
            logging.warning(f"Links file {FOLLOWING_LINKS_FILE} does not exist yet")
            return
            
        with open(FOLLOWING_LINKS_FILE, "r") as f:
            links = f.readlines()
        
        # Strip whitespace and normalize links
        normalized_links = [link.strip() for link in links]
        unique_links = []
        seen = set()
        
        # Preserve order while removing duplicates
        for link in normalized_links:
            if link and link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        if len(normalized_links) != len(unique_links):
            logging.error(f"DUPLICATE LINKS DETECTED: {len(normalized_links)} total, {len(unique_links)} unique")
            
            # Count occurrences of each link
            link_counts = Counter(normalized_links)
            duplicates = {link: count for link, count in link_counts.items() if count > 1}
            
            logging.error(f"Duplicated links: {duplicates}")
            
            # Fix by removing duplicates and writing back
            save_links_with_lock(unique_links, FOLLOWING_LINKS_FILE)
            
            logging.info(f"Fixed duplicate links. Removed {len(normalized_links) - len(unique_links)} duplicates.")
        else:
            logging.info(f"No duplicate links found in {FOLLOWING_LINKS_FILE}")
    except Exception as e:
        logging.error(f"Error checking for duplicates: {e}")

def debug_inspect_links_file():
    """Inspect the links file for format issues"""
    try:
        if not os.path.exists(FOLLOWING_LINKS_FILE):
            logging.warning(f"Links file {FOLLOWING_LINKS_FILE} does not exist yet")
            return
            
        with open(FOLLOWING_LINKS_FILE, "r") as f:
            links = f.readlines()
        
        logging.info(f"Links file contains {len(links)} lines")
        
        # Check for empty lines
        empty_lines = [i for i, link in enumerate(links) if not link.strip()]
        if empty_lines:
            logging.error(f"Empty lines found at positions: {empty_lines}")
        
        # Check for lines without proper URL format
        invalid_format = [i for i, link in enumerate(links) 
                         if link.strip() and not (link.strip().startswith('http') and 'instagram.com' in link)]
        if invalid_format:
            logging.error(f"Lines with invalid format found at positions: {invalid_format}")
            logging.error(f"Examples of invalid lines: {[links[i] for i in invalid_format[:5]]}")
        
        # Check for lines without newline at the end
        missing_newline = [i for i, link in enumerate(links) if link and not link.endswith('\n')]
        if missing_newline:
            logging.error(f"Lines missing newline character found at positions: {missing_newline}")
        
        # Check first and last few links
        if links:
            logging.info(f"First 3 links: {[links[i].strip() for i in range(min(3, len(links)))]}")
            logging.info(f"Last 3 links: {[links[i].strip() for i in range(max(0, len(links)-3), len(links))]}")
        
        # Fix any format issues
        fixed_links = []
        has_issues = False
        
        for link in links:
            link = link.strip()
            if not link:
                has_issues = True
                continue  # Skip empty lines
                
            if not (link.startswith('http') and 'instagram.com' in link):
                logging.error(f"Invalid link format: {link}")
                has_issues = True
                continue  # Skip invalid links
            
            fixed_links.append(link)
        
        if has_issues:
            logging.info(f"Fixed {len(links) - len(fixed_links)} formatting issues in links file")
            save_links_with_lock(fixed_links, FOLLOWING_LINKS_FILE)
        
    except Exception as e:
        logging.error(f"Error inspecting links file: {e}")

def remove_processed_links():
    """
    Remove links from followingLinks.txt that have already been processed 
    (first item in adjacency list)
    """
    try:
        if not os.path.exists(FOLLOWING_LINKS_FILE):
            logging.warning(f"Links file {FOLLOWING_LINKS_FILE} does not exist yet")
            return
            
        if not os.path.exists(os.path.join(DATA_DIR, "adjList.txt")):
            logging.info("No adjList.txt file found yet. No links to remove.")
            return
        
        # Get processed accounts from adjList.txt (first item in each line)
        processed_accounts = set()
        with open(os.path.join(DATA_DIR, "adjList.txt"), "r") as adj_file:
            for line in adj_file:
                parts = line.strip().split()
                if len(parts) >= 1:
                    processed_accounts.add(parts[0])
        
        logging.info(f"Found {len(processed_accounts)} processed accounts in adjList.txt")
        
        # Read links from followingLinks.txt
        with open(FOLLOWING_LINKS_FILE, "r") as f:
            links = f.readlines()
        
        initial_count = len(links)
        logging.info(f"Found {initial_count} links in followingLinks.txt")
        
        # Filter out links for accounts that have already been processed
        filtered_links = []
        removed_links = []
        
        for link in links:
            link_stripped = link.strip()
            if not link_stripped:
                continue
                
            # Extract username from the link
            username = link_stripped.rstrip('/').split('/')[-1]
            
            if username in processed_accounts:
                removed_links.append(username)
            else:
                filtered_links.append(link_stripped)
        
        # Save the filtered links back to the file
        if len(filtered_links) < initial_count:
            save_links_with_lock(filtered_links, FOLLOWING_LINKS_FILE)
            logging.info(f"Removed {initial_count - len(filtered_links)} already processed links from followingLinks.txt")
            if len(removed_links) > 0:
                logging.info(f"Examples of removed accounts: {removed_links[:5]}")
        else:
            logging.info("No processed links found in followingLinks.txt")
        
    except Exception as e:
        logging.error(f"Error removing processed links: {e}")
        logging.error(traceback.format_exc())

def save_links_with_lock(links, file_path):
    """Save links with file locking to prevent race conditions"""
    try:
        with open(file_path, "w") as file_h:
            fcntl.flock(file_h, fcntl.LOCK_EX)  # Exclusive lock
            for link in links:
                file_h.write(f"{link}\n")
            fcntl.flock(file_h, fcntl.LOCK_UN)  # Release lock
        logging.info(f"Saved {len(links)} links to {file_path} with lock")
    except Exception as e:
        logging.error(f"Error saving links with lock: {e}")

def main():
    # Set up logging
    setup_logging()
    logging.info("Auto-scraper script started")
    
    try:
        # Ensure data directory exists
        ensure_dir_exists(DATA_DIR)
        
        # First, debug file format issues
        logging.info("Inspecting links file for format issues")
        debug_inspect_links_file()
        
        # Then, check for and fix duplicates 
        logging.info("Performing initial duplicate check on following links")
        debug_check_duplicates()
        
        # Finally, remove links that have already been processed
        # This should run last to ensure processed links are removed
        logging.info("Checking and removing already processed links")
        remove_processed_links()
        
        # Get current profile counts to ensure we have accurate totals
        total_followers, total_following = fetch_profile_counts()
        
        # If we got valid counts, update the status file
        if total_followers is not None or total_following is not None:
            logging.info(f"Updating status with initial profile counts - Followers: {total_followers}, Following: {total_following}")
            update_status(session_completed=False, total_followers=total_followers, total_following=total_following)
        
        # Initial check - will update status file if it doesn't exist
        check_completion()
        
        while True:
            # Check if collection is complete
            # if check_completion():
            #     logging.info("Collection is complete. Waiting for next check...")
            #     # Sleep for a longer time since we're done (6 hours)
            #     time.sleep(WAIT_TIME * 12)
            #     continue
            
            # Get current progress to check for discrepancies
            progress = get_progress()
            status = check_status()
            
            # Determine the session duration based on collection status
            if progress["followers_total"] > 0 and progress["followers_collected"] < progress["followers_total"]:
                # Calculate what percentage of followers we've collected
                followers_percent = (progress["followers_collected"] / progress["followers_total"]) * 100
                
                # If we have a significant discrepancy (collected <70% but status >90%), run longer sessions
                if followers_percent < 70 and status["follower_percent"] > 90:
                    logging.info(f"Detected follower collection discrepancy: {followers_percent:.1f}% actual vs {status['follower_percent']:.1f}% reported")
                    logging.info("Running an extended collection session...")
                    
                    # Run session
                    session_result = run_scraping_session()
                    
                    # Wait for a shorter time before continuing (1-2 hours)
                    random_wait = random.randint(WAIT_TIME//2, WAIT_TIME)
                    logging.info(f"Session completed with result: {session_result}. Waiting {random_wait//60} minutes before next session...")
                    time.sleep(random_wait)
                    continue
            
            # Check if it's safe to run now
            if not safe_to_run():
                # Wait an hour before checking again
                logging.info("Not safe to run right now. Waiting 60 minutes before checking again")
                time.sleep(WAIT_TIME)
                continue
                
            # Regular collection session
            session_result = run_scraping_session()
            
            # Now run a following accounts scraping session to collect network data
            # This will scrape data from 10-20 following accounts per session
            logging.info("Now running a session to scrape following accounts network data...")
            following_result = run_following_scraping_session()
            logging.info(f"Following accounts scraping session completed with result: {following_result}")
            
            # Determine wait time between sessions (3-6 hours normally)
            random_wait = random.randint(WAIT_TIME, WAIT_TIME * 2)
            hours = random_wait // 3600
            minutes = (random_wait % 3600) // 60
            logging.info(f"Sessions completed. Waiting {hours} hours and {minutes} minutes before next sessions...")
            
            # Sleep for the random time period
            time.sleep(random_wait)
            
    except KeyboardInterrupt:
        logging.info("Scraper interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        logging.error(traceback.format_exc())
    finally:
        logging.info("Auto-scraper script ended")

if __name__ == "__main__":
    main() 