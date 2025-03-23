#!/usr/bin/env python3
import json
import os

def merge_followers():
    # Paths to the JSON files
    main_followers_path = 'followers.json'
    manual_followers_path = 'instagram_data/followers_manual.json'
    output_path = 'followers.json'  # Same as input to overwrite

    # Load the existing followers
    with open(main_followers_path, 'r', encoding='utf-8') as f:
        existing_followers = set(json.load(f))
    
    print(f"Loaded {len(existing_followers)} existing followers")
    
    # Load the manual followers
    with open(manual_followers_path, 'r', encoding='utf-8') as f:
        manual_followers = json.load(f)
    
    print(f"Loaded {len(manual_followers)} manual followers")
    
    # Merge followers (deduplication happens automatically with sets)
    for follower in manual_followers:
        existing_followers.add(follower)
    
    # Convert back to list
    merged_followers = list(existing_followers)
    
    # Save the merged followers
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_followers, f, indent=2)
    
    print(f"Merged followers saved to {output_path}")
    print(f"Total unique followers: {len(merged_followers)}")
    print(f"Added {len(merged_followers) - len(existing_followers) + len(manual_followers) - len(merged_followers)} new followers")

if __name__ == "__main__":
    merge_followers() 