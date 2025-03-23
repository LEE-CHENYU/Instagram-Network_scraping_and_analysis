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
    
    # Updated selectors based on actual HTML structure
    # Each follower is contained in a div with class x1dm5mii
    follower_elements = soup.select('div.x1dm5mii')
    
    followers = []
    for element in follower_elements:
        try:
            # Find the username - it's in a span with class _ap3a _aaco _aacw _aacx _aad7 _aade
            username_element = element.select_one('span._ap3a._aaco._aacw._aacx._aad7._aade')
            if username_element:
                username = username_element.text.strip()
            else:
                continue
            
            # Find the full name - it's in a span with classes that include x1lliihq x193iq5w x6ikm8r x10wlt62 xlyipyv xuxw1ft
            name_element = element.select_one('span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft')
            name = name_element.text.strip() if name_element else ""
            
            # Find the profile pic - it's in an img tag with class that includes xpdipgo
            profile_pic_element = element.select_one('img.xpdipgo')
            profile_pic = profile_pic_element.get('src') if profile_pic_element else ""
            
            followers.append({
                'username': username,
                'name': name,
                'profile_pic': profile_pic
            })
        except AttributeError as e:
            # Skip if any element couldn't be found
            print(f"Error processing element: {e}")
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