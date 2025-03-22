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
MIN_INTERVAL_MINUTES = 20  # Minimum time between sessions (was 45)
MAX_INTERVAL_MINUTES = 40  # Maximum time between sessions (was 90)
MAX_SESSIONS_PER_DAY = 18  # Maximum number of sessions per day (was 12)
HEADLESS_MODE = True  # Run without visible browser window
FOLLOWINGS_BATCH_SIZE = None  # Will be randomized each session
NATURAL_BREAK_LENGTH_MINUTES = 120  # 2-hour natural break once per day
RANDOM_SKIP_CHANCE = 0.1  # 10% chance to randomly skip a session for more human-like behavior
WAIT_TIME = 3600  # Base wait time in seconds (1 hour)

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
    
    # If we don't have a total count yet, estimate it
    if status_data["total_following"] == 0 and following_data:
        status_data["total_following"] = 1861  # Use the known total from previous logs
        save_json_data(status_data, STATUS_FILE)
    
    # If we don't have a total followers count yet or it's incorrect, update it
    if status_data["total_followers"] == 0 or status_data["total_followers"] == 232:  # 232 is the incorrect value
        status_data["total_followers"] = 877  # Update to the correct value from the profile
        save_json_data(status_data, STATUS_FILE)
        logging.info(f"Updated total followers count to the correct value: 877")
    
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
        # Randomize max_pages each session for more human-like behavior
        max_pages = random.randint(3, 7)  # Vary between 3-7 pages per session
        logging.info(f"Using {max_pages} max pages for this session")
        
        # Build command line options
        command = [
            "python3", "scrapeMyAccount.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--resume",
            "--headless",
            "--max-pages", str(max_pages)  # Use randomized value
        ]
        
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
                
                # Extract the following count if available
                if "Following:" in line and "," in line:
                    try:
                        total_following = int(line.split("Following:")[1].split(",")[0].strip())
                    except:
                        pass
                
                # Extract the followers count if available
                if "Followers:" in line and "," in line:
                    try:
                        total_followers = int(line.split("Followers:")[1].split(",")[0].strip())
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
        update_status(session_completed=True, total_following=total_following, total_followers=total_followers)
        return True
        
    except Exception as e:
        logging.error(f"Error running scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def run_following_scraping_session():
    """Run a session to scrape data from following accounts"""
    logging.info("Starting following accounts scraping session")
    
    # Check if there are any following accounts left to process
    following_progress = get_following_accounts_progress()
    if following_progress["accounts_remaining"] <= 0:
        logging.info("No following accounts left to process. Skipping following scraping session.")
        return True
    
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

def main():
    # Set up logging
    setup_logging()
    logging.info("Auto-scraper script started")
    
    try:
        # Initial check - will update status file if it doesn't exist
        check_completion()
        
        while True:
            # Check if collection is complete
            if check_completion():
                logging.info("Collection is complete. Waiting for next check...")
                # Sleep for a longer time since we're done (6 hours)
                time.sleep(WAIT_TIME * 12)
                continue
            
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
            
            # Regular collection session
            session_result = run_scraping_session()
            
            # Determine wait time between sessions (3-6 hours normally)
            random_wait = random.randint(WAIT_TIME, WAIT_TIME * 2)
            hours = random_wait // 3600
            minutes = (random_wait % 3600) // 60
            logging.info(f"Session completed with result: {session_result}. Waiting {hours} hours and {minutes} minutes before next session...")
            
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