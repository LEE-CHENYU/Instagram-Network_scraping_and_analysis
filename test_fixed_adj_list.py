#!/usr/bin/env python3
"""
Test script to verify the fixed adjacency list functions
"""

import os
from essentialRoutines_fixed import dict_to_adjList, adjList_to_dict

# Constants
DATA_DIR = "instagram_data"
ADJ_LIST_FILE = os.path.join(DATA_DIR, "adjList.txt")

# Ensure directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def show_adj_list():
    """Display the contents of the adjacency list file"""
    if os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, 'r') as f:
            content = f.read()
        print(f"Current adjacency list ({ADJ_LIST_FILE}):")
        print("=" * 40)
        print(content)
        print("=" * 40)
    else:
        print(f"Adjacency list file does not exist yet: {ADJ_LIST_FILE}")

def load_adj_list():
    """Load adjacency list from file"""
    if os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, 'r') as f:
            lines = f.readlines()
        print(f"Loaded {len(lines)} relationships from adjacency list")
        return lines
    else:
        print("No existing adjacency list file")
        return []

def append_to_adj_list(new_relationships, existing_lines=None):
    """Append new relationships to the adjacency list without duplicates"""
    # Load existing relationships
    existing_relationships = set()
    
    if existing_lines:
        for line in existing_lines:
            existing_relationships.add(line.strip())
    elif os.path.exists(ADJ_LIST_FILE):
        with open(ADJ_LIST_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    existing_relationships.add(line.strip())
    
    print(f"Found {len(existing_relationships)} existing relationships")
    
    # Add new relationships that don't already exist
    new_count = 0
    for relationship in new_relationships:
        relationship = relationship.strip()
        if relationship and relationship not in existing_relationships:
            existing_relationships.add(relationship)
            new_count += 1
    
    print(f"Added {new_count} new relationships")
    
    # Write all relationships back to file
    with open(ADJ_LIST_FILE, 'w') as f:
        for relationship in existing_relationships:
            f.write(f"{relationship}\n")
    
    print(f"Total relationships in adjacency list: {len(existing_relationships)}")

def test_dict_to_adjList():
    """Test converting a dictionary to adjacency list format"""
    print("\nTesting dict_to_adjList function:")
    test_dict = {
        "user1": ["follow1", "follow2"],
        "user2": ["follow3"]
    }
    
    adj_list = dict_to_adjList(test_dict)
    print(f"Converted {len(test_dict)} users with relationships to {len(adj_list)} lines:")
    for line in adj_list:
        print(f"  {line.strip()}")
    
    return adj_list

def test_adjList_to_dict():
    """Test converting adjacency list to dictionary"""
    print("\nTesting adjList_to_dict function:")
    test_lines = [
        "user1 follow1\n",
        "user1 follow2\n",
        "user2 follow3\n"
    ]
    
    result_dict = adjList_to_dict(test_lines)
    print(f"Converted {len(test_lines)} lines to dictionary with {len(result_dict)} users:")
    for user, following in result_dict.items():
        print(f"  {user} follows {len(following)} users: {', '.join(following)}")
    
    return result_dict

def test_append_scenario():
    """Test appending to adjacency list in a typical usage scenario"""
    print("\nTesting append scenario:")
    
    # Create test data for first "scraping session"
    first_data = {
        "fretin98": ["user1", "user2", "user3"]
    }
    
    # Convert to adj list format
    first_adj_list = dict_to_adjList(first_data)
    first_adj_stripped = [line.strip() for line in first_adj_list]
    
    # Write to file (simulating first run)
    append_to_adj_list(first_adj_stripped)
    
    # Display result
    show_adj_list()
    
    # Create test data for second "scraping session"
    second_data = {
        "fretin98": ["user2", "user4", "user5"],  # Note user2 is duplicate
        "user3": ["user6"]  # New relationship chain
    }
    
    # Convert to adj list format
    second_adj_list = dict_to_adjList(second_data)
    second_adj_stripped = [line.strip() for line in second_adj_list]
    
    # Append to file (simulating second run)
    append_to_adj_list(second_adj_stripped)
    
    # Display final result
    show_adj_list()

if __name__ == "__main__":
    print("Testing fixed adjacency list functions")
    
    # Display current state
    show_adj_list()
    
    # Test basic functions
    test_adj_list = test_dict_to_adjList()
    test_dict = test_adjList_to_dict()
    
    # Test realistic append scenario
    test_append_scenario() 