#!/usr/bin/env python3
"""
Test script to verify the adjacency list append functionality
"""

import os
import json

# Constants
DATA_DIR = "instagram_data"
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")

# Make sure the directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Created directory: {DATA_DIR}")

def test_append_to_adj_list():
    """Test function to append to adjacency list"""
    # Create test data
    test_data = [
        "account1 follower1",  # Already exists from previous test
        "fretin98 pielet_",    # Original entry
        "account3 follower4",  # New entry
    ]
    
    # Check if file exists and load existing relationships
    existing_relations = set()
    if os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, "r") as file_h:
            for line in file_h:
                if line.strip():  # Skip empty lines
                    existing_relations.add(line.strip())
        
        print(f"Loaded {len(existing_relations)} existing relationships")
    
    # Count how many new relationships will be added
    new_relations = set(test_data) - existing_relations
    print(f"Will add {len(new_relations)} new relationships")
    
    # Open the file in write mode
    with open(ADJ_LIST_FILE, "w") as file_h:
        # Write existing relationships
        for relation in existing_relations:
            file_h.write(f"{relation}\n")
        
        # Add new relationships that don't already exist
        for relation in test_data:
            if relation not in existing_relations:
                file_h.write(f"{relation}\n")
    
    # Verify the file after the operation
    with open(ADJ_LIST_FILE, "r") as file_h:
        lines = file_h.readlines()
        unique_lines = set(line.strip() for line in lines if line.strip())
        print(f"File now contains {len(lines)} lines ({len(unique_lines)} unique relationships)")
    
    print("Test completed!")

if __name__ == "__main__":
    print("Testing adjacency list append functionality...")
    test_append_to_adj_list() 