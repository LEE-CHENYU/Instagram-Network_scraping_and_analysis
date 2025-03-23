import json
from bs4 import BeautifulSoup
import os

def extract_followers(html_path):
    # Check if file exists
    if not os.path.exists(html_path):
        print(f"Error: File {html_path} not found.")
        return None
    
    # Read the HTML file
    with open(html_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # This is a placeholder for the actual selector logic
    # You'll need to inspect the HTML to find the correct selectors
    follower_elements = soup.select('div.follower-item')  # Update this selector
    
    followers = []
    for element in follower_elements:
        try:
            # These selectors need to be updated based on actual HTML structure
            username = element.select_one('div.username').text.strip()
            name = element.select_one('div.name').text.strip()
            profile_pic = element.select_one('img.profile-pic').get('src')
            
            followers.append({
                'username': username,
                'name': name,
                'profile_pic': profile_pic
            })
        except AttributeError:
            # Skip if any element couldn't be found
            continue
    
    return followers

def save_to_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
    print(f"Successfully saved {len(data)} followers to {output_path}")

if __name__ == "__main__":
    html_path = "/Users/chenyusu/Documents/GitHub/Instagram-Network_scraping_and_analysis/follower_list.html"
    output_path = "extracted_followers.json"
    
    followers = extract_followers(html_path)
    if followers:
        save_to_json(followers, output_path)
    else:
        print("No followers were extracted.")