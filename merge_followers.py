#!/usr/bin/env python3
import json
import os

def merge_followers():
    # Paths to the JSON files
    main_followers_path = 'followers.json'
    manual_followers_path = 'instagram_data/followers_manual.json'
    output_path = 'followers.json'  # Same as input to overwrite

    # Load existing followers from followers.json if it exists
    try:
        with open(main_followers_path, 'r', encoding='utf-8') as f:
            existing_followers = set(json.load(f))
        print(f"Loaded {len(existing_followers)} existing followers")
    except FileNotFoundError:
        existing_followers = set()
        print("No existing followers.json found, creating new file")

    # Load extracted followers data
    try:
        with open('extracted_followers.json', 'r') as f:
            extracted_data = json.load(f)
        print(f"Loaded {len(extracted_data)} entries from extracted_followers.json")
    except FileNotFoundError:
        print("Error: extracted_followers.json not found")
        exit(1)

    # Extract usernames from extracted_followers.json
    new_followers = set()
    for entry in extracted_data:
        if 'username' in entry and entry['username']:
            new_followers.add(entry['username'])

    print(f"Extracted {len(new_followers)} usernames")

    # Merge and deduplicate
    all_followers = existing_followers.union(new_followers)
    print(f"Total unique followers after merging: {len(all_followers)}")
    print(f"Added {len(all_followers) - len(existing_followers)} new followers")

    # Save to followers.json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(all_followers)), f, indent=2)

    print(f"Saved deduplicated followers to {output_path}")

if __name__ == "__main__":
    merge_followers() 