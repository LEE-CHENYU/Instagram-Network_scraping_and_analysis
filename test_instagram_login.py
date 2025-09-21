#!/usr/bin/env python3
"""
Test Instagram login using Playwright to diagnose login issues
"""

import asyncio
from playwright.async_api import async_playwright
import time

async def test_instagram_login():
    """Test Instagram login and diagnose issues"""

    username = "fretin98"
    password = "Lcy199818su!"

    async with async_playwright() as p:
        # Launch browser in non-headless mode to see what's happening
        browser = await p.chromium.launch(
            headless=False,  # Set to False to see the browser
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        # Create context with realistic viewport and user agent
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Create a new page
        page = await context.new_page()

        try:
            print("Step 1: Navigating to Instagram login page...")
            await page.goto('https://www.instagram.com/accounts/login/', wait_until='networkidle')
            await page.wait_for_timeout(3000)

            # Check if we're on the login page
            current_url = page.url
            print(f"Current URL: {current_url}")

            # Take a screenshot for debugging
            await page.screenshot(path='login_page.png')
            print("Screenshot saved as login_page.png")

            # Handle cookie banner if present
            try:
                print("Step 2: Checking for cookie banner...")
                cookie_button = await page.wait_for_selector('button:has-text("Allow essential and optional cookies")', timeout=2000)
                if cookie_button:
                    await cookie_button.click()
                    print("Dismissed cookie banner")
            except:
                print("No cookie banner found")

            # Find and fill username field
            print("Step 3: Looking for username input field...")
            username_input = await page.wait_for_selector('input[name="username"]', timeout=10000)
            if username_input:
                print("Found username field, entering username...")
                await username_input.click()
                await page.keyboard.type(username, delay=100)  # Type with delay to appear human
                await page.wait_for_timeout(1000)
            else:
                print("ERROR: Could not find username field!")
                return

            # Find and fill password field
            print("Step 4: Looking for password input field...")
            password_input = await page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
            if password_input:
                print("Found password field, entering password...")
                await password_input.click()
                await page.keyboard.type(password, delay=100)
                await page.wait_for_timeout(1000)
            else:
                print("ERROR: Could not find password field!")
                return

            # Take screenshot before clicking login
            await page.screenshot(path='before_login.png')
            print("Screenshot saved as before_login.png")

            # Find and click login button
            print("Step 5: Looking for login button...")
            login_button = await page.wait_for_selector('button[type="submit"], button:has-text("Log In"), button:has-text("Log in")', timeout=10000)
            if login_button:
                # Check if button is enabled
                is_disabled = await login_button.get_attribute('disabled')
                if is_disabled:
                    print("Login button is disabled. Waiting...")
                    await page.wait_for_timeout(2000)

                print("Clicking login button...")
                await login_button.click()
            else:
                print("ERROR: Could not find login button!")
                return

            # Wait for navigation or error
            print("Step 6: Waiting for login response...")
            await page.wait_for_timeout(5000)

            # Check the result
            new_url = page.url
            print(f"After login URL: {new_url}")

            # Take screenshot after login attempt
            await page.screenshot(path='after_login.png')
            print("Screenshot saved as after_login.png")

            # Check for various possible outcomes
            if "login" in new_url:
                print("\n⚠️  ISSUE: Still on login page!")

                # Check for error messages
                error_messages = await page.query_selector_all('[role="alert"], .eiCW-, .O4QwN')
                for error in error_messages:
                    error_text = await error.text_content()
                    print(f"Error message found: {error_text}")

                # Check for CAPTCHA
                captcha = await page.query_selector('iframe[title*="recaptcha"], iframe[src*="captcha"]')
                if captcha:
                    print("⚠️  CAPTCHA detected! Manual intervention required.")

                # Check for 2FA
                two_fa = await page.query_selector('input[name="verificationCode"]')
                if two_fa:
                    print("⚠️  Two-factor authentication required!")

            elif "challenge" in new_url:
                print("\n⚠️  ISSUE: Instagram security challenge detected!")
                print("This might be a suspicious login attempt verification.")

            elif "onetap" in new_url or "save" in new_url:
                print("\n✓ Login appears successful! On save login info page.")

                # Try to click "Not Now"
                try:
                    not_now = await page.wait_for_selector('button:has-text("Not Now")', timeout=3000)
                    if not_now:
                        await not_now.click()
                        print("Clicked 'Not Now' on save info dialog")
                except:
                    pass

            else:
                print("\n✓ Login appears successful!")
                print(f"Redirected to: {new_url}")

            # Final check - try to access profile
            print("\nStep 7: Testing profile access...")
            await page.goto(f'https://www.instagram.com/{username}/', wait_until='networkidle')
            await page.wait_for_timeout(3000)

            profile_url = page.url
            print(f"Profile URL: {profile_url}")

            if username in profile_url:
                print("✓ Successfully accessed profile!")

                # Check if we can see followers/following
                followers_link = await page.query_selector('a[href*="/followers/"]')
                if followers_link:
                    followers_text = await followers_link.text_content()
                    print(f"Can see followers link: {followers_text}")
                else:
                    print("⚠️  Cannot see followers link - might not be logged in properly")

            else:
                print("⚠️  Could not access profile - login may have failed")

            await page.screenshot(path='final_state.png')
            print("\nFinal screenshot saved as final_state.png")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            await page.screenshot(path='error_state.png')
            print("Error screenshot saved as error_state.png")

        finally:
            # Keep browser open for manual inspection
            print("\nPress Enter to close the browser...")
            input()
            await browser.close()

if __name__ == "__main__":
    print("Instagram Login Test using Playwright")
    print("=" * 50)
    asyncio.run(test_instagram_login())