import time
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import random
import json
from selenium.webdriver import ActionChains
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
    adjList = []
    for person,following in allNodes.items():
        f = " ".join(following)
        adjList.append(person +" "+ f + "\n")
        
    return adjList

def adjList_to_dict(adjList):
    allNodes = {}
    for line in adjList:
        list_of_persons = line.strip('\n').split(" ")
        person = list_of_persons[0]
        following = list_of_persons[1:]
        allNodes[person] = following
        
    return allNodes


def check_if_stuck(prev_scrape_sizes, new_scrape_size):
    occurences = Counter(prev_scrape_sizes)
    for v in occurences.values():
        if v > 38:
            return (True,prev_scrape_sizes)
        
    if len(prev_scrape_sizes) >= 40:
        del prev_scrape_sizes[0]
    prev_scrape_sizes.append(new_scrape_size)
        
    return (False, prev_scrape_sizes)


def login_insta(driver,username,password):
    driver.get("https://www.instagram.com/accounts/login")
    time.sleep(5)  # Increased wait time
    
    # Input username and password
    try:
        # Try different username input selectors
        username_selectors = [
            "//input[@name='username']",
            "//input[@aria-label='Phone number, username, or email']",
            "//input[contains(@aria-label, 'username')]"
        ]
        
        for selector in username_selectors:
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                ).send_keys(username)
                break
            except:
                continue
                
        # Try different password input selectors
        password_selectors = [
            "//input[@name='password']",
            "//input[@aria-label='Password']",
            "//input[contains(@aria-label, 'password')]",
            "//input[@type='password']"
        ]
        
        for selector in password_selectors:
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                ).send_keys(password)
                break
            except:
                continue
        
        # Try different possible login button selectors
        login_buttons = [
            "//button[contains(.,'Log In')]",
            "//button[contains(.,'Log in')]",
            "//button[@type='submit']",
            "//button[contains(@class,'_acan _acap')]",
            "//div[contains(text(), 'Log In')]/parent::button",
            "//div[contains(text(), 'Log in')]/parent::button"
        ]
        
        for button_xpath in login_buttons:
            try:
                login_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath))
                )
                login_button.click()
                print(f"Logged in using button: {button_xpath}")
                break
            except:
                continue
        
        # Wait for login to complete
        time.sleep(5)
        
        # Handle "Save Your Login Info" dialog if it appears
        try:
            save_info_buttons = [
                "//button[contains(text(), 'Not Now')]", 
                "//button[contains(text(), 'Not now')]",
                "//div[contains(text(), 'Not Now')]"
            ]
            
            for button in save_info_buttons:
                try:
                    WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, button))
                    ).click()
                    break
                except:
                    continue
        except:
            pass
        
        # Check if login was successful
        if "instagram.com/accounts/login" in driver.current_url:
            print("Login might have failed. Current URL still shows login page.")
        else:
            print("Logged in successfully!")
            
    except Exception as e:
        print(f"Login error: {e}")
        driver.save_screenshot('login_error.png')
        raise

        
def get_following_links(driver, following_usernames=None):
    """Get links to following users' profiles
    
    Args:
        driver: Selenium webdriver instance
        following_usernames: Optional list of usernames to create links from (bypassing UI scraping)
    
    Returns:
        List of profile URLs
    """
    # If we already have usernames from API, just construct the links directly
    if following_usernames and len(following_usernames) > 0:
        links = [f"https://www.instagram.com/{username}/" for username in following_usernames]
        print(f"Created {len(links)} following links from usernames")
        return links
    
    # Otherwise, try to extract from UI
    try:
        # Try multiple selectors for getting following links
        selectors = [
            "li.wo9IH span a",  # Old UI
            "div[role='dialog'] li a",  # Generic dialog selector
            "div[role='dialog'] a[href^='/']",  # More generic
            "//div[contains(@role,'dialog')]//li//a[contains(@href,'/')]",  # XPATH version
            "//div[contains(@role,'dialog')]//a[contains(@href,'/') and not(contains(@href, 'explore'))]"  # Exclude non-profile links
        ]
        
        links = []
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    followList = driver.find_elements(By.XPATH, selector)
                else:
                    followList = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for item in followList:
                    try:
                        href = item.get_attribute("href")
                        if href and href.startswith("https://www.instagram.com/") and not "/p/" in href and href not in links:
                            links.append(href)
                    except Exception as e:
                        print(f"Error getting href: {e}")
                
                if links:
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"Error finding following links: {e}")
        driver.save_screenshot('following_links_error.png')
        links = []
    
    # If UI approach failed, try JavaScript
    if not links:
        try:
            js_script = """
            const links = Array.from(document.querySelectorAll('a'))
                .filter(a => a.href && a.href.startsWith('https://www.instagram.com/') && 
                        !a.href.includes('/p/') && !a.href.includes('/explore/'))
                .map(a => a.href);
            return [...new Set(links)];  // Remove duplicates
            """
            js_links = driver.execute_script(js_script)
            if js_links and len(js_links) > 0:
                links = js_links
        except Exception as e:
            print(f"JavaScript link extraction failed: {e}")
    
    print(f"Found {len(links)} following links")
    return links


def scrape_whole_list(list_to_scrape, driver, link, next_cursor=None, resume_from_saved=None, max_pages=10):
    """
    Scrape a list of followers or following users
    
    Args:
        list_to_scrape: Either "followers" or "following"
        driver: Selenium webdriver instance
        link: Profile URL
        next_cursor: Pagination cursor to resume from
        resume_from_saved: List of already saved usernames to avoid duplicates
        max_pages: Maximum number of pages to fetch (default: 10)
        
    Returns:
        Tuple of (list of usernames, next_cursor)
    """
    global _last_cursors
    
    driver.get(link)
    driver.implicitly_wait(5)
    
    # Reset cursor for this list type if not resuming
    if next_cursor is None:
        _last_cursors[list_to_scrape] = None
    
    # Initialize already fetched usernames
    already_fetched = set(resume_from_saved if resume_from_saved else [])
    print(f"Resuming with {len(already_fetched)} already fetched {list_to_scrape}")
    
    # Try multiple approaches to get the follower/following count
    length_of_list = None
    
    # Strategy 1: Classic approach
    try:
        length_of_list = int("".join((driver.find_element(By.XPATH, "//a[text()=' {}']/span[@class='g47SY ']".format(list_to_scrape)).text).split(",")))
    except:
        pass
    
    # Strategy 2: New UI
    if length_of_list is None:
        try:
            elements = driver.find_elements(By.XPATH, f"//a[contains(@href, '/{list_to_scrape}/')]/span")
            if elements:
                length_of_list = int("".join(elements[0].text.split(",")))
        except:
            pass
            
    # Strategy 3: Section approach
    if length_of_list is None:
        try:
                sections = driver.find_elements(By.XPATH, "//section/ul/li")
                length_index = 1 if list_to_scrape == "followers" else 2
                if len(sections) >= max(2, length_index):
                    length_of_list = int("".join(sections[length_index].text.split(" ")[0].replace(",", "")))
        except:
            pass
    
    # Strategy 4: Header approach
    if length_of_list is None:
        try:
            header_stats = driver.find_elements(By.XPATH, "//header//ul/li")
            if header_stats:
                for stat in header_stats:
                    stat_text = stat.text.lower()
                    if list_to_scrape == "followers" and "follower" in stat_text:
                        length_of_list = int("".join(stat_text.split(" ")[0].replace(",", "")))
                    elif list_to_scrape == "following" and "following" in stat_text:
                        length_of_list = int("".join(stat_text.split(" ")[0].replace(",", "")))
        except:
            pass
    
    # Strategy 5: JavaScript approach
    if length_of_list is None:
        try:
            js_script = """
            return window._sharedData && window._sharedData.entry_data && 
                window._sharedData.entry_data.ProfilePage && 
                window._sharedData.entry_data.ProfilePage[0].graphql.user;
            """
            user_data = driver.execute_script(js_script)
            if user_data:
                if list_to_scrape == "followers":
                    length_of_list = user_data.get('edge_followed_by', {}).get('count', 0)
                else:
                    length_of_list = user_data.get('edge_follow', {}).get('count', 0)
        except:
            pass
            
    # Strategy 6: Text-based approach for new 2024 UI
    if length_of_list is None:
        try:
            # Look for elements containing text with followers/following
            text_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{list_to_scrape}')]")
            for element in text_elements:
                try:
                    text = element.text.strip().lower()
                    if list_to_scrape in text:
                        # Extract numbers from text like "878 followers" or "1861 following"
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            # Join multi-part numbers (e.g., "1,234" -> "1234")
                            length_of_list = int("".join(numbers))
                            break
                except:
                    continue
        except:
            pass
    
    # Default fallback
    if length_of_list is None:
        print(f"WARNING: Could not determine exact {list_to_scrape} count. Using default value.")
        length_of_list = 100  # Default value

    # Try API-based approach first - it's more reliable with new Instagram UI
    # This approach doesn't require opening dialogs and handles pagination behind the scenes
    username = link.rstrip('/').split('/')[-1]
    api_result = []
    
    try:
        print(f"Attempting API-based approach for {list_to_scrape}...")
        
        # First, try to get the user ID from the username
        user_id = None
        try:
            # Method 1: From page source
            js_script = """
            try {
                for (const script of document.querySelectorAll('script')) {
                    const text = script.textContent;
                    if (text && text.includes('"user_id":"') && text.includes('"username":"')) {
                        const match = text.match(/"user_id":"([0-9]+)"/);
                        if (match) return match[1];
                    }
                }
                return null;
            } catch (e) {
                return null;
            }
            """
            user_id = driver.execute_script(js_script)
            print(f"Found user_id: {user_id}")
        except:
            pass
            
        if not user_id:
            # Method 2: Direct URL with username
            try:
                driver.get(f"https://www.instagram.com/{username}/")
                time.sleep(2)
                js_script = """
                try {
                    for (const script of document.querySelectorAll('script')) {
                        const text = script.textContent;
                        if (text && text.includes('"user_id":"') && text.includes('"username":"')) {
                            const match = text.match(/"user_id":"([0-9]+)"/);
                            if (match) return match[1];
                        }
                    }
                    // Fallback to window._sharedData
                    if (window._sharedData && window._sharedData.entry_data && 
                        window._sharedData.entry_data.ProfilePage) {
                        return window._sharedData.entry_data.ProfilePage[0].graphql.user.id;
                    }
                    return null;
                } catch (e) {
                    return null;
                }
                """
                user_id = driver.execute_script(js_script)
                print(f"Found user_id (method 2): {user_id}")
            except:
                pass
                
        if user_id:
            # Now fetch the followers/following using the user ID
            # Add the needed headers to make the request look like it's coming from the Instagram web app
            driver.execute_script("""
            window.instaHeaders = {
                'x-ig-app-id': '936619743392459',
                'x-asbd-id': '198387',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-mode': 'cors',
                'sec-fetch-dest': 'empty',
                'accept': '*/*',
                'referer': 'https://www.instagram.com/'
            };
            """)
            
            # Determine the endpoint based on whether we're fetching followers or following
            endpoint = f"https://www.instagram.com/api/v1/friendships/{user_id}/{'followers' if list_to_scrape == 'followers' else 'following'}/"
            
            # Fetch the first page
            js_script = """
            return (async function() {
                try {
                    const headers = window.instaHeaders;
                    const endpoint = arguments[0];
                    let response = await fetch(endpoint + '?count=50', { headers });
                    if (!response.ok) return { error: `HTTP error! status: ${response.status}` };
                    
                    const data = await response.json();
                    let users = data.users || [];
                    let has_more = data.big_list || false;
                    let next_max_id = data.next_max_id;
                    
                    // Only fetch up to 10 pages (500 users) to avoid overloading
                    let page_count = 1;
                    const max_pages = arguments[1] || 10;
                    
                    while (has_more && next_max_id && page_count < max_pages) {
                        let nextUrl = `${endpoint}?count=50&max_id=${next_max_id}`;
                        response = await fetch(nextUrl, { headers });
                        if (!response.ok) break;
                        
                        const nextData = await response.json();
                        if (nextData.users && nextData.users.length > 0) {
                            users = users.concat(nextData.users);
                            has_more = nextData.big_list || false;
                            next_max_id = nextData.next_max_id;
                            page_count++;
                        } else {
                            break;
                        }
                    }
                    
                    return { 
                        success: true, 
                        users: users.map(u => u.username),
                        has_more
                    };
                } catch (e) {
                    return { error: e.toString() };
                }
            })();
            """
            
            result = driver.execute_script(js_script, endpoint, max_pages)
            
            if result and 'success' in result and result['success']:
                api_result = result.get('users', [])
                print(f"Successfully fetched {len(api_result)} {list_to_scrape} via API approach")
                print(f"Has more: {result.get('has_more', False)}")
                
                # If we got a good result from the API, return it
                if api_result and len(api_result) > 0:
                    return (api_result, result.get('has_more', False))
            elif result and 'error' in result:
                print(f"API approach error: {result['error']}")
    except Exception as e:
        print(f"Error in API-based approach: {e}")
    
    # If API approach failed or didn't return any results, continue with the UI-based approach
    
    # Try an enhanced direct API approach first
    try:
        print("Attempting enhanced API approach...")
        # Navigate to the profile page first to ensure we're on the correct page
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(3)
        
        # Use JavaScript to extract csrf token
        csrf_token = driver.execute_script("return document.cookie.match(/csrftoken=([^;]+)/)[1]")
        print(f"Got CSRF token: {csrf_token}")
        
        # Set up headers for API request
        headers = {
            'x-ig-app-id': '936619743392459',
            'x-csrftoken': csrf_token,
            'x-requested-with': 'XMLHttpRequest',
            'x-asbd-id': '198387',
            'referer': f'https://www.instagram.com/{username}/',
            'content-type': 'application/json'
        }
        
        # Make API call using JavaScript for better reliability
        js_script = """
        async function fetchData(apiUrl, headers) {
            try {
                const response = await fetch(apiUrl, {
                    method: 'GET',
                    headers: headers,
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    return { error: `HTTP error! status: ${response.status}` };
                }
                
                const data = await response.json();
                return { success: true, data: data };
            } catch (e) {
                return { error: e.toString() };
            }
        }
        
        const username = arguments[0];
        const headers = arguments[1];
        const endpointType = arguments[2];
        const maxId = arguments[3];  // Pagination cursor
        
        // First get user ID
        const userInfoUrl = `https://www.instagram.com/api/v1/users/web_profile_info/?username=${username}`;
        
        return (async () => {
            try {
                const userInfoResult = await fetchData(userInfoUrl, headers);
                if (!userInfoResult.success) {
                    return { error: userInfoResult.error };
                }
                
                const userId = userInfoResult.data.data.user.id;
                console.log(`User ID: ${userId}`);
                
                // Now get followers/following with pagination
                let apiUrl = `https://www.instagram.com/api/v1/friendships/${userId}/${endpointType}/?count=200`;
                
                // Add max_id for pagination if provided
                if (maxId) {
                    apiUrl += `&max_id=${maxId}`;
                    console.log(`Using pagination cursor: ${maxId}`);
                }
                
                const result = await fetchData(apiUrl, headers);
                
                if (!result.success) {
                    return { error: result.error };
                }
                
                // Extract usernames
                const usernames = result.data.users.map(user => user.username);
                
                // Return next_max_id for pagination
                return { 
                    success: true, 
                    usernames: usernames,
                    total: usernames.length,
                    hasMore: result.data.big_list === true,
                    nextMaxId: result.data.next_max_id || null
                };
            } catch (e) {
                return { error: e.toString() };
            }
        })();
        """
        
        endpoint_type = 'followers' if list_to_scrape == 'followers' else 'following'
        result = driver.execute_script(js_script, username, headers, endpoint_type, next_cursor)
        
        if result and 'success' in result and result['success']:
            api_users = result.get('usernames', [])
            has_more = result.get('hasMore', False)
            next_cursor = result.get('nextMaxId')
            
            print(f"Enhanced API approach succeeded! Found {len(api_users)} {list_to_scrape}")
            print(f"Has more: {has_more}")
            
            if next_cursor:
                print(f"Next cursor: {next_cursor}")
                # Store the cursor for next run
                _last_cursors[list_to_scrape] = next_cursor
            
            # Filter out already fetched users
            new_users = [user for user in api_users if user not in already_fetched]
            print(f"Added {len(new_users)} new users (filtered {len(api_users) - len(new_users)} duplicates)")
            
            if api_users and len(api_users) > 0:
                return (api_users, next_cursor)
        elif result and 'error' in result:
            print(f"Enhanced API approach error: {result['error']}")
    except Exception as e:
        print(f"Error in enhanced API approach: {e}")
    
    # If both API approaches failed, try UI approach
    # But modify the scrolling mechanism

    # Try multiple approaches to click on followers/following link
    click_successful = False
    
    # Try approach 1: Classic selector
    try:
        driver.find_element(By.XPATH, "//a[text() = ' {}']".format(list_to_scrape)).click()
        click_successful = True
    except:
        pass
        
    # Try approach 2: href attribute
    if not click_successful:
        try:
            elements = driver.find_elements(By.XPATH, f"//a[contains(@href, '/{list_to_scrape}/')]")
            if elements:
                elements[0].click()
                click_successful = True
        except:
            pass
    
    # Try approach 3: text content
    if not click_successful:
        try:
            # Try different text-based selectors
            text_selectors = [
                f"//div[contains(text(), '{list_to_scrape}')]",
                f"//span[contains(text(), '{list_to_scrape}')]",
                f"//*[contains(text(), '{list_to_scrape}')]"
            ]
            
            for selector in text_selectors:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        # Check if this is actually a count element and not some other text
                        text = element.text.lower()
                        if list_to_scrape in text and any(char.isdigit() for char in text):
                            driver.execute_script("arguments[0].click();", element)
                            click_successful = True
                            break
                    except:
                        continue
                if click_successful:
                    break
        except:
            pass
            
    # Try approach 4: direct navigation
    if not click_successful and list_to_scrape in ["followers", "following"]:
        try:
            username = link.rstrip('/').split('/')[-1]
            driver.get(f"{link}/{list_to_scrape}/")
            click_successful = True
        except:
            pass
            
    if not click_successful:
        print(f"WARNING: Could not click on {list_to_scrape} link or navigate to list page.")
    
    # Wait for the dialog to appear
    driver.implicitly_wait(5)
    
    # Check if we got a "Remove follower?" confirmation dialog instead of the followers list
    try:
        remove_dialog_selectors = [
            "//div[text()='Remove follower?']",
            "//*[contains(text(), 'Remove follower?')]",
            "//div[@role='dialog']//*[contains(text(), 'Remove')]"
        ]
        
        for selector in remove_dialog_selectors:
            try:
                remove_dialog = driver.find_element(By.XPATH, selector)
                if remove_dialog:
                    print("Detected 'Remove follower?' dialog. Clicking Cancel...")
                    
                    # Try to find and click the Cancel button
                    cancel_button_selectors = [
                        "//button[text()='Cancel']",
                        "//div[@role='dialog']//button[contains(text(), 'Cancel')]",
                        "//div[@role='presentation']//button[contains(text(), 'Cancel')]",
                        "//div[@role='dialog']//*[contains(text(), 'Cancel')]"
                    ]
                    
                    for cancel_selector in cancel_button_selectors:
                        try:
                            cancel_button = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, cancel_selector))
                            )
                            cancel_button.click()
                            print("Clicked Cancel on remove dialog")
                            time.sleep(2)  # Wait for dialog to close
                            break
                        except:
                            continue
                    
                    # Try again with direct URL approach
                    print("Trying direct URL navigation for followers/following")
                    username = link.rstrip('/').split('/')[-1]
                    driver.get(f"{link}/{list_to_scrape}/")
                    time.sleep(3)
                    break
            except:
                continue
    except Exception as e:
        print(f"Error checking for removal dialog: {e}")
    
    # Wait for the followers/following list
    FList = None
    dialog_selectors = [
        'div[role=\'dialog\'] ul',  # CSS
        "//div[contains(@role,'dialog')]//ul",  # XPATH
        "//div[contains(@class, 'isgrP')]",  # Old UI
        "//div[contains(@class, '_aano')]",  # New UI
        "//div[contains(@role, 'dialog')]",  # Generic dialog
        "//div[contains(@role, 'presentation')]//ul",  # Another possible dialog type
        "//div[contains(@class, 'ReactModal__Content')]//ul"  # React modal
    ]
    
    for selector in dialog_selectors:
        try:
            if selector.startswith("//"):
                FList = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
            else:
                FList = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            print(f"Found dialog using selector: {selector}")
            break
        except:
            continue
            
    if not FList:
        print(f"Error locating {list_to_scrape} dialog")
        driver.save_screenshot(f'{list_to_scrape}_dialog_error.png')
        
        # One last attempt - try using JavaScript to detect modal dialogs
        try:
            js_script = """
            return document.querySelector('div[role="dialog"]') || 
                   document.querySelector('div[role="presentation"]') ||
                   document.querySelector('.ReactModal__Content');
            """
            dialog = driver.execute_script(js_script)
            if dialog:
                print("Found dialog using JavaScript")
                FList = dialog
            else:
                return ([], False)
        except:
            return ([], False)
    
    # Get initial count of items
    numberInList = 0
    try:
        numberInList = len(FList.find_elements(By.CSS_SELECTOR, 'li'))
    except:
        try:
            numberInList = len(FList.find_elements(By.XPATH, './/li'))
        except:
            try:
                numberInList = len(driver.find_elements(By.XPATH, "//div[contains(@role,'dialog')]//li"))
            except:
                try:
                    # Try to find any list items with generic approach
                    numberInList = len(driver.find_elements(By.XPATH, "//div[contains(@role,'dialog') or contains(@role,'presentation')]//li"))
                except:
                    new_numberInList = numberInList  # No change
            
    # Find the scrollable area
    frame = None
    frame2 = None
    
    # Try to find scrollable area with multiple selectors
    scroll_selectors = [
        "//div[@class='isgrP']", 
        "//div[@class='PZuss']",
        "//div[contains(@class, '_aano')]",
        "//div[contains(@role,'dialog')]//div[contains(@style,'overflow') or contains(@style,'auto')]",
        "//div[contains(@role,'dialog')]//div[contains(@class, 'scroll')]",
        "//div[contains(@role,'dialog')]//ul",
        "//div[contains(@role,'dialog')]//div[contains(@style, 'overflow-y') or contains(@style, 'scroll')]",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//div[contains(@style, 'height') and contains(@style, 'overflow')]",
        "//div[contains(@role,'dialog')]"
    ]
    
    for selector in scroll_selectors:
        try:
            frame = driver.find_element(By.XPATH, selector)
            frame2 = frame  # Use same element as both frames
            print(f"Found scrollable area using selector: {selector}")
            break
        except:
            continue
            
    if not frame:
        # Last resort - just use the dialog
        try:
            dialog = driver.find_element(By.XPATH, "//div[contains(@role,'dialog') or contains(@role,'presentation')]")
            frame = dialog
            frame2 = dialog
            print("Using dialog as scrollable area")
        except Exception as e:
            print(f"Error finding scrollable area: {e}")
            driver.save_screenshot(f'{list_to_scrape}_scroll_error.png')
            
            # Try using JavaScript to find scrollable elements
            try:
                js_script = """
                return Array.from(document.querySelectorAll('*')).find(el => {
                    const style = window.getComputedStyle(el);
                    return (style.overflowY === 'scroll' || style.overflowY === 'auto') && 
                           el.clientHeight > 100 && 
                           el.scrollHeight > el.clientHeight;
                });
                """
                scrollable = driver.execute_script(js_script)
                if scrollable:
                    print("Found scrollable area using JavaScript")
                    frame = scrollable
                    frame2 = scrollable
            except Exception as e:
                print(f"JavaScript scrollable detection failed: {e}")
            
    # Rest of the scrolling logic
    scrape_sizes = []
    driver.implicitly_wait(1)
    
    # If we found a frame and have items to load
    if frame and length_of_list > 10:
        try:
            # Try to scroll using different methods
            
            # Method 1: ActionChains
            try:
                size_of_list = frame.size
                w = size_of_list['width']
                ActionChains(driver).move_to_element(frame).perform()
                ActionChains(driver).move_by_offset(0.25*(w),0).click().perform()
                ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
                ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()
                time.sleep(1)
            except Exception as e:
                print(f"Initial ActionChains scrolling failed: {e}")
                
            # Method 2: JavaScript scrolling
            try:
                driver.execute_script("arguments[0].scrollTop = 100;", frame)
                time.sleep(0.5)
                driver.execute_script("arguments[0].scrollTop += 100;", frame)
                time.sleep(0.5)
            except Exception as e:
                print(f"Initial JavaScript scrolling failed: {e}")
        except Exception as e:
            print(f"Error during initial scrolling: {e}")
    
    # Scroll until we load all items or hit a stop condition
    max_scroll_attempts = 50  # Prevent infinite loops
    scroll_attempts = 0
    
    while frame and (numberInList < length_of_list) and scroll_attempts < max_scroll_attempts:
        try:
            driver.implicitly_wait(1)
            
            # Use multiple scrolling techniques to improve reliability
            
            # Technique 1: Direct JavaScript scroll (most reliable)
            try:
                current_height = driver.execute_script("return arguments[0].scrollHeight", frame)
                current_scroll = driver.execute_script("return arguments[0].scrollTop", frame)
                
                # Random scroll amount between 500-1000px to simulate human behavior
                scroll_amount = random.randint(500, 1000)
                new_position = min(current_scroll + scroll_amount, current_height)
                
                # Smooth scroll with animation for better loading
                js_script = """
                let start = arguments[0].scrollTop;
                let end = arguments[1];
                let step = 20;
                let duration = 30; // ms
                let steps = Math.abs(Math.floor((end - start) / step));
                
                function scrollStep(i) {
                    if (i >= steps) {
                        arguments[0].scrollTop = end;
                        return;
                    }
                    let progress = i / steps;
                    let current = start + (end - start) * progress;
                    arguments[0].scrollTop = current;
                    setTimeout(function() { scrollStep(i + 1); }, duration);
                }
                
                scrollStep(0);
                """
                driver.execute_script(js_script, frame, new_position)
                
                # Wait for content to load
                time.sleep(2)
                
                print(f"Scrolled from {current_scroll} to {new_position} (height: {current_height})")
            except Exception as e:
                print(f"JavaScript smooth scroll failed: {e}")
                
                # Fallback to simple scroll
                try:
                    driver.execute_script("arguments[0].scrollTop += 800;", frame)
                    time.sleep(1.5)
                except Exception as e2:
                    print(f"Simple scroll failed: {e2}")
            
            # Technique 2: Click and drag approach (simulate touch)
            if scroll_attempts % 3 == 0:  # Try every third attempt
                try:
                    action = ActionChains(driver)
                    # Move to middle of scrollable area
                    action.move_to_element(frame)
                    # Click and hold
                    action.click_and_hold()
                    # Move up (drag down effect)
                    action.move_by_offset(0, -400)
                    # Release and perform
                    action.release().perform()
                    
                    time.sleep(1.5)
                    print("Used click and drag scrolling")
                except Exception as e:
                    print(f"Click and drag failed: {e}")
            
            # Technique 3: Try a touch-based scroll if all else fails
            if scroll_attempts % 5 == 0:  # Try every fifth attempt
                try:
                    # Simulate touch scroll with JavaScript
                    js_touch_script = """
                    function simulateTouchScroll(element) {
                        const rect = element.getBoundingClientRect();
                        const centerX = rect.left + rect.width / 2;
                        const startY = rect.top + rect.height * 0.8;
                        const endY = rect.top + rect.height * 0.2;
                        
                        // Touch start event
                        const touchStartEvent = new TouchEvent('touchstart', {
                            bubbles: true,
                            touches: [new Touch({
                                identifier: Date.now(),
                                target: element,
                                clientX: centerX,
                                clientY: startY
                            })]
                        });
                        element.dispatchEvent(touchStartEvent);
                        
                        // Touch move event
                        const touchMoveEvent = new TouchEvent('touchmove', {
                            bubbles: true,
                            touches: [new Touch({
                                identifier: Date.now(),
                                target: element,
                                clientX: centerX,
                                clientY: endY
                            })]
                        });
                        element.dispatchEvent(touchMoveEvent);
                        
                        // Touch end event
                        const touchEndEvent = new TouchEvent('touchend', {
                            bubbles: true,
                            touches: []
                        });
                        element.dispatchEvent(touchEndEvent);
                        
                        return true;
                    }
                    
                    try {
                        return simulateTouchScroll(arguments[0]);
                    } catch(e) {
                        console.error('Touch simulation error:', e);
                        return false;
                    }
                    """
                    touch_result = driver.execute_script(js_touch_script, frame)
                    if touch_result:
                        print("Used touch-based scrolling")
                        time.sleep(2)
                except Exception as e:
                    print(f"Touch scroll failed: {e}")
            
            # Get updated count with multiple selectors
            new_numberInList = 0
            
            # Try a different approach to find list items
            try:
                # Direct JavaScript approach to count items
                js_count_script = """
                // Find all potential user items in dialogs
                function findUserItems() {
                    const dialog = document.querySelector('div[role="dialog"]') || 
                                 document.querySelector('div[role="presentation"]');
                    if (!dialog) return [];
                    
                    // Look for list items
                    const listItems = dialog.querySelectorAll('li');
                    if (listItems.length > 0) return Array.from(listItems);
                    
                    // Look for anchor tags that could be users
                    const anchorTags = dialog.querySelectorAll('a[href^="/"]');
                    const userAnchors = Array.from(anchorTags).filter(a => {
                        const href = a.getAttribute('href');
                        // Filter out non-user links
                        return href && !href.includes('/p/') && !href.includes('/explore/') && 
                               !href.includes('/direct/') && href.split('/').filter(p => p).length === 1;
                    });
                    
                    if (userAnchors.length > 0) return userAnchors;
                    
                    // Last resort - look for elements containing usernames
                    return Array.from(dialog.querySelectorAll('div[class*="user"], span[class*="user"]'));
                }
                
                return findUserItems().length;
                """
                new_numberInList = driver.execute_script(js_count_script)
                print(f"JS count found {new_numberInList} items")
            except Exception as e:
                print(f"JS item counting failed: {e}")
                # Fall back to previous methods
            try:
                new_numberInList = len(FList.find_elements(By.CSS_SELECTOR, 'li'))
            except:
                try:
                    new_numberInList = len(FList.find_elements(By.XPATH, './/li'))
                except:
                    try:
                        new_numberInList = len(driver.find_elements(By.XPATH, "//div[contains(@role,'dialog') or contains(@role,'presentation')]//li"))
                    except:
                        new_numberInList = numberInList  # No change
            
            print(f"Current items loaded: {new_numberInList}/{length_of_list} (attempt {scroll_attempts+1})")
            
            # If we've loaded items, reset the stuck counter
            if new_numberInList > numberInList:
                print(f"Progress made! Found {new_numberInList - numberInList} new items")
                scrape_sizes = []  # Reset stuck counter
            
            # Check if we're stuck
            stop, scrape_sizes = check_if_stuck(scrape_sizes, new_numberInList)
            
            # Update our count
            numberInList = new_numberInList
            scroll_attempts += 1
            
            # If we're stuck or close enough to target, break
            if stop:
                if new_numberInList >= (length_of_list - 5) or new_numberInList > (0.8 * length_of_list):
                    print(f"Close enough to target ({new_numberInList}/{length_of_list}), stopping scroll")
                    break
                else:
                    # Try a page refresh approach if stuck
                    print(f"Stuck at {new_numberInList}/{length_of_list}. Trying refresh approach...")
                    driver.get(f"https://www.instagram.com/{username}/{list_to_scrape}/")
                    time.sleep(3)
                    # We'll exit this loop and extract what we can
                    break
            
            # Break early if we're not making progress after multiple attempts
            if scroll_attempts > 10 and new_numberInList == 0:
                print(f"No progress after {scroll_attempts} attempts. Trying direct API as fallback.")
                
                # Try the direct graphql API as a last resort
                try:
                    # Build request
                    if list_to_scrape == "followers":
                        variables = {
                            "id": username, 
                            "include_reel": True,
                            "fetch_mutual": False,
                            "first": 50
                        }
                        query_hash = "c76146de99bb02f6415203be841dd25a" # Followers query hash
                    else:
                        variables = {
                            "id": username,
                            "include_reel": True,
                            "fetch_mutual": False,
                            "first": 50
                        }
                        query_hash = "d04b0a864b4b54837c0d870b0e77e076" # Following query hash
                    
                    gql_url = f"https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={json.dumps(variables)}"
                    
                    # Execute using JavaScript
                    js_script = """
                    async function fetchGraphQL(url) {
                        const response = await fetch(url);
                        if (!response.ok) return null;
                        return await response.json();
                    }
                    
                    return fetchGraphQL(arguments[0]);
                    """
                    
                    gql_result = driver.execute_script(js_script, gql_url)
                    if gql_result:
                        # Process results
                        if list_to_scrape == "followers":
                            edges = gql_result.get("data", {}).get("user", {}).get("edge_followed_by", {}).get("edges", [])
                        else:
                            edges = gql_result.get("data", {}).get("user", {}).get("edge_follow", {}).get("edges", [])
                            
                        graphql_users = [edge["node"]["username"] for edge in edges if "username" in edge["node"]]
                        if graphql_users:
                            print(f"GraphQL API returned {len(graphql_users)} users")
                            return (graphql_users, False)
                except Exception as e:
                    print(f"GraphQL API approach failed: {e}")
                
                break
            
        except Exception as e:
            print(f"Error during scrolling: {e}")
            scroll_attempts += 1
    
    # Extract username list using multiple selectors
    result = []
    
    # Try multiple selector approaches for usernames
    username_selectors = [
        ".notranslate._0imsa", # Old selector
        ".notranslate",
        "span > a.notranslate",
        "a.notranslate",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//div[@class='notranslate']",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//a[contains(@href,'/') and not(contains(@href, 'explore'))]",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//a[contains(@href,'/')]",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//span[contains(@class, 'username')]",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//li//div[contains(@class, 'user')]",
        "//div[contains(@role,'dialog') or contains(@role,'presentation')]//li//a"
    ]
    
    for selector in username_selectors:
        try:
            if selector.startswith("//"):
                username_elements = driver.find_elements(By.XPATH, selector)
            else:
                username_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
            # Extract usernames
            for element in username_elements:
                try:
                    if element.get_attribute("href"):
                        # If it's an anchor, extract from the href
                        href = element.get_attribute("href")
                        username = href.rstrip('/').split('/')[-1]
                        if username and username not in result and not username.startswith("explore"):
                            result.append(username)
                    else:
                        # Otherwise get the text
                        username = element.text
                        if username and username not in result:
                            result.append(username)
                except:
                    continue
                    
            if result:
                break
        except:
            continue
    
    # Try extracting usernames with JavaScript if we haven't found any yet
    if not result or len(result) == 0:
        try:
            # More robust JavaScript-based username extraction
            js_username_script = """
            function extractUsernames() {
                const dialog = document.querySelector('div[role="dialog"]') || 
                               document.querySelector('div[role="presentation"]');
                if (!dialog) return [];
                
                // First try to get usernames from links
                const anchors = Array.from(dialog.querySelectorAll('a[href^="/"]'));
                const usernames = anchors
                    .filter(a => {
                        const href = a.getAttribute('href');
                        // Only include links that look like user profiles
                        return href && !href.includes('/p/') && !href.includes('/explore/') && 
                               !href.includes('/direct/') && href.split('/').filter(p => p).length === 1;
                    })
                    .map(a => {
                        const href = a.getAttribute('href');
                        const username = href.replace(/\\//g, '').trim();
                        return username;
                    })
                    .filter(u => u && u.length > 0);
                
                // Remove duplicates
                return [...new Set(usernames)];
            }
            
            return extractUsernames();
            """
            
            js_users = driver.execute_script(js_username_script)
            if js_users and len(js_users) > 0:
                print(f"JavaScript extraction found {len(js_users)} usernames")
                result = js_users
        except Exception as e:
            print(f"Enhanced JavaScript username extraction failed: {e}")
    
    # If we still don't have results but have API results, use those
    if (not result or len(result) == 0) and api_result and len(api_result) > 0:
        result = api_result
    
    # Filter out already fetched users
    new_users = [user for user in result if user not in already_fetched]
    print(f"Added {len(new_users)} new users via UI approach (filtered {len(result) - len(new_users)} duplicates)")
    
    print(f"Scraped {len(new_users)} new {list_to_scrape}")
    return (new_users, _last_cursors[list_to_scrape])

def get_profile_stats(driver):
    """
    Extract profile statistics (followers, following, posts) from an Instagram profile page.
    
    Args:
        driver: Selenium webdriver instance on a profile page
        
    Returns:
        Dictionary with keys 'followers', 'following', and 'posts'
    """
    stats = {
        'followers': 0,
        'following': 0,
        'posts': 0
    }
    
    try:
        # Strategy 1: Classic selectors (old UI)
        try:
            followers_text = driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]/span").text.replace(',', '')
            following_text = driver.find_element(By.XPATH, "//a[contains(@href, '/following/')]/span").text.replace(',', '')
            posts_text = driver.find_element(By.XPATH, "//span[contains(@class, 'g47SY')][1]").text.replace(',', '')
            
            stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
            stats['following'] = int(following_text) if following_text.isdigit() else 0
            stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
            
            if stats['followers'] > 0 or stats['following'] > 0:
                return stats
        except:
            pass
            
        # Strategy 2: Section-based approach (newer UI)
        try:
            sections = driver.find_elements(By.XPATH, "//section/ul/li")
            if len(sections) >= 3:
                posts_text = sections[0].text.split(" ")[0].replace(",", "")
                followers_text = sections[1].text.split(" ")[0].replace(",", "")
                following_text = sections[2].text.split(" ")[0].replace(",", "")
                
                stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
                stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
                stats['following'] = int(following_text) if following_text.isdigit() else 0
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 3: Header-based approach for newest UI
        try:
            header_stats = driver.find_elements(By.XPATH, "//header//ul/li")
            if len(header_stats) >= 2:
                for stat in header_stats:
                    stat_text = stat.text.lower()
                    if 'post' in stat_text:
                        posts_text = stat_text.split(" ")[0].replace(",", "")
                        stats['posts'] = int(posts_text) if posts_text.isdigit() else 0
                    elif 'follower' in stat_text:
                        followers_text = stat_text.split(" ")[0].replace(",", "")
                        stats['followers'] = int(followers_text) if followers_text.isdigit() else 0
                    elif 'following' in stat_text:
                        following_text = stat_text.split(" ")[0].replace(",", "")
                        stats['following'] = int(following_text) if following_text.isdigit() else 0
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 4: JavaScript approach
        try:
            js_script = """
            return {
                followers: parseInt((document.querySelector('a[href*="followers"] span')?.textContent || '0').replace(/,/g, '')),
                following: parseInt((document.querySelector('a[href*="following"] span')?.textContent || '0').replace(/,/g, '')),
                posts: parseInt((document.querySelector('span[class*="g47SY"]:first-child')?.textContent || '0').replace(/,/g, ''))
            };
            """
            js_stats = driver.execute_script(js_script)
            if js_stats:
                stats['followers'] = js_stats.get('followers', 0)
                stats['following'] = js_stats.get('following', 0)
                stats['posts'] = js_stats.get('posts', 0)
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
            
        # Strategy 5: API approach
        try:
            js_script = """
            return window._sharedData && window._sharedData.entry_data && 
                   window._sharedData.entry_data.ProfilePage && 
                   window._sharedData.entry_data.ProfilePage[0].graphql.user;
            """
            user_data = driver.execute_script(js_script)
            if user_data:
                stats['followers'] = user_data.get('edge_followed_by', {}).get('count', 0)
                stats['following'] = user_data.get('edge_follow', {}).get('count', 0)
                stats['posts'] = user_data.get('edge_owner_to_timeline_media', {}).get('count', 0)
                
                if stats['followers'] > 0 or stats['following'] > 0:
                    return stats
        except:
            pass
    
    except Exception as e:
        print(f"Error getting profile stats: {e}")
        driver.save_screenshot('profile_stats_error.png')
    
    return stats