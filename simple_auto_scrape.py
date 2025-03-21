#!/usr/bin/env python3
"""
Simplified Auto Scraper to test the Instagram scraper functionality
"""

import os
import json
import time
import logging
import subprocess
import traceback
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
DATA_DIR = "instagram_data"
FOLLOWERS_FILE = os.path.join(DATA_DIR, "followers.json")
FOLLOWING_FILE = os.path.join(DATA_DIR, "following.json")
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")

# Instagram credentials
USERNAME = "fretin98"
PASSWORD = "Lcy199818su!"

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logging.info(f"Created directory: {DATA_DIR}")

# Copy adjList.txt to instagram_data if it exists
if os.path.exists("adjList.txt") and not os.path.exists(ADJ_LIST_FILE):
    try:
        import shutil
        shutil.copy("adjList.txt", ADJ_LIST_FILE)
        logging.info(f"Copied adjList.txt to {ADJ_LIST_FILE}")
    except Exception as e:
        logging.error(f"Error copying adjList.txt: {e}")

def run_scraping_session():
    """Run a single scraping session"""
    logging.info("Starting scraping session")
    
    try:
        # Run the scraping script with command line arguments
        command = [
            "python3", "scrapeMyAccount.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--resume",
            "--headless",
            "--max-pages", "2"  # Limit pages for testing
        ]
        
        # Execute the command and capture output
        logging.info(f"Executing: {' '.join(command)}")
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
        
        # Wait for process to complete
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            error_output = process.stderr.read()
            logging.error(f"Scraping script failed with return code {process.returncode}")
            logging.error(f"Error output: {error_output}")
            return False
        
        logging.info("Scraping session completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error running scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

def run_following_scraping_session():
    """Run a session to scrape data from following accounts"""
    logging.info("Starting following accounts scraping session")
    
    try:
        # Run the scrapingFollowing script with command line arguments
        command = [
            "python3", "scrapingFollowing.py",
            "--username", USERNAME,
            "--password", PASSWORD,
            "--batch-size", "1",  # Just 1 account for testing
            "--headless"
        ]
        
        # Execute the command and capture output
        logging.info(f"Executing: {' '.join(command)}")
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
        
        logging.info("Following scraping session completed successfully")
        return True
        
    except Exception as e:
        logging.error(f"Error running following scraping session: {e}")
        logging.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("Instagram Simplified Auto Scraper Starting")
    logging.info("=" * 60)
    
    # Run a main account scraping session
    logging.info("Running main account scraping session")
    main_success = run_scraping_session()
    
    if main_success:
        logging.info("Main scraping successful. Now trying following scraping.")
        following_success = run_following_scraping_session()
        if following_success:
            logging.info("Following scraping successful.")
        else:
            logging.error("Following scraping failed.")
    else:
        logging.error("Main scraping failed. Not attempting following scraping.")
    
    logging.info("=" * 60)
    logging.info("Auto scraper completed")
    logging.info("=" * 60) 