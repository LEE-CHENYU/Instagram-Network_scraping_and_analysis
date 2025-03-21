#!/usr/bin/env python3
"""
Simple script to test adjacency list append functionality
"""
import os

DATA_DIR = "instagram_data"
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")

# Ensure directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def update_adj_list_file(username, following_list):
    """Update adjacency list file with user's following"""
    # Create list of relationships (one per line)
    new_adj_list = []
    for followed in following_list:
        new_adj_list.append(f"{username} {followed}")
    
    # Load existing relationships to avoid duplicates
    existing_relations = set()
    if os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, "r") as file_h:
            for line in file_h:
                if line.strip():  # Skip empty lines
                    existing_relations.add(line.strip())
    
    # Add new relationships without duplicates
    new_count = 0
    for relation in new_adj_list:
        if relation not in existing_relations:
            existing_relations.add(relation)
            new_count += 1
    
    # Write back all relationships
    with open(ADJ_LIST_FILE, "w") as file_h:
        for relation in existing_relations:
            file_h.write(f"{relation}\n")
    
    print(f"Updated adjacency list file: {ADJ_LIST_FILE}")
    print(f"Added {new_count} new relationships (total: {len(existing_relations)})")

# First run - initialize with a single relationship
print("First run - initializing with a single relationship")
update_adj_list_file("fretin98", ["pielet_"])

# Display current state
print("\nCurrent adjacency list:")
with open(ADJ_LIST_FILE, "r") as f:
    print(f.read())

# Second run - add more relationships
print("\nSecond run - adding more relationships")
update_adj_list_file("fretin98", ["pielet_", "user1", "user2"])

# Display final state
print("\nFinal adjacency list:")
with open(ADJ_LIST_FILE, "r") as f:
    print(f.read())

# Third run - add relationships for a different user
print("\nThird run - adding relationships for a different user")
update_adj_list_file("user1", ["fretin98", "user3"])

# Display final state
print("\nFinal adjacency list after third run:")
with open(ADJ_LIST_FILE, "r") as f:
    print(f.read()) 