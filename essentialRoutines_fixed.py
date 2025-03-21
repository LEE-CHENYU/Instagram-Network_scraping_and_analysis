import time
from collections import Counter
import os

# Add global variables to track cursors
_last_cursors = {
    'followers': None,
    'following': None
}

def get_last_cursor(list_type):
    """Get the last cursor for the specified list type"""
    return _last_cursors.get(list_type)

def dict_to_adjList(allNodes):
    """
    Convert dictionary of following to adjacency list format
    One line per relationship in format: "follower followed"
    """
    adjList = []
    for person, following in allNodes.items():
        # Create one line per relationship
        for followed in following:
            adjList.append(f"{person} {followed}\n")
    return adjList

def adjList_to_dict(adjList):
    """
    Convert adjacency list to dictionary
    Input: list of strings in format "follower followed"
    Output: dict with follower as key and list of followed as value
    """
    allNodes = {}
    for line in adjList:
        list_of_persons = line.strip('\n').split(" ")
        if len(list_of_persons) >= 2:  # Ensure there's at least follower and followed
            person = list_of_persons[0]
            followed = list_of_persons[1]
            
            if person not in allNodes:
                allNodes[person] = []
            
            if followed not in allNodes[person]:
                allNodes[person].append(followed)
        
    return allNodes 