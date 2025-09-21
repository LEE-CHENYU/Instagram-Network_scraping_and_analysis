#!/usr/bin/env python3
"""
Test Instagram login in headless mode to diagnose issues
"""

import asyncio
from playwright.async_api import async_playwright

async def test_instagram_login():
    """Test Instagram login and diagnose issues"""

    username = "fretin98"
    password = "Lcy199818su"  # Removed the ! at the end

    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Create context with realistic settings
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        try:
            print("Navigating to Instagram login...")
            await page.goto('https://www.instagram.com/accounts/login/')
            await page.wait_for_timeout(3000)

            print(f"Current URL: {page.url}")

            # Try to fill login form
            print("Attempting to fill login form...")

            # Check if username field exists
            username_field = await page.query_selector('input[name="username"]')
            if username_field:
                await username_field.fill(username)
                print("✓ Username entered")
            else:
                print("✗ Username field not found")
                return

            # Check if password field exists
            password_field = await page.query_selector('input[name="password"], input[type="password"]')
            if password_field:
                await password_field.fill(password)
                print("✓ Password entered")
            else:
                print("✗ Password field not found")
                return

            # Check if login button exists and is enabled
            login_button = await page.query_selector('button[type="submit"]')
            if login_button:
                is_disabled = await login_button.get_attribute('disabled')
                if is_disabled:
                    print("✗ Login button is disabled")
                else:
                    print("✓ Login button is enabled")
                    await login_button.click()
                    print("Clicked login button")
            else:
                print("✗ Login button not found")
                return

            # Wait for response
            print("Waiting for login response...")
            await page.wait_for_timeout(5000)

            new_url = page.url
            print(f"After login URL: {new_url}")

            # Check results
            if "login" in new_url:
                print("\n❌ LOGIN FAILED - Still on login page")

                # Check for error messages
                page_content = await page.content()
                if "incorrect" in page_content.lower():
                    print("⚠️  Possible incorrect password")
                if "suspicious" in page_content.lower():
                    print("⚠️  Suspicious activity detected")
                if "captcha" in page_content.lower() or "recaptcha" in page_content.lower():
                    print("⚠️  CAPTCHA required")

            elif "challenge" in new_url:
                print("\n⚠️  Security challenge required")
            elif "two_factor" in new_url or "checkpoint" in new_url:
                print("\n⚠️  Two-factor authentication required")
            else:
                print("\n✅ Login successful or redirected")

            # Try to check if we can access the profile
            print("\nTrying to access profile...")
            await page.goto(f'https://www.instagram.com/{username}/')
            await page.wait_for_timeout(3000)

            profile_url = page.url
            if username in profile_url:
                print(f"✅ Profile accessible: {profile_url}")

                # Check for followers link
                followers_link = await page.query_selector('a[href*="/followers/"]')
                if followers_link:
                    print("✅ Can see followers link - logged in successfully")
                else:
                    print("❌ Cannot see followers link - not logged in")
            else:
                print(f"❌ Cannot access profile, redirected to: {profile_url}")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")

        finally:
            await browser.close()

if __name__ == "__main__":
    print("Instagram Login Test (Headless)")
    print("=" * 50)
    asyncio.run(test_instagram_login())