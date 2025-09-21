#!/usr/bin/env python3
"""
Login to Instagram manually and save cookies for reuse
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def save_instagram_cookies():
    """Login manually and save cookies"""

    async with async_playwright() as p:
        # Launch browser in non-headless mode for manual login
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        print("Opening Instagram login page...")
        await page.goto('https://www.instagram.com/accounts/login/')

        print("\n" + "="*60)
        print("MANUAL LOGIN REQUIRED")
        print("="*60)
        print("1. Login manually in the browser window")
        print("2. Complete any CAPTCHA or 2FA if required")
        print("3. Wait until you see your Instagram feed")
        print("4. Press Enter here when done...")
        print("="*60)

        input("\nPress Enter after successful login...")

        # Check if logged in
        current_url = page.url
        if "login" in current_url:
            print("❌ Still on login page. Please complete login first.")
            input("Press Enter after login...")

        # Save cookies
        cookies = await context.cookies()
        with open('instagram_cookies.json', 'w') as f:
            json.dump(cookies, f, indent=2)

        print(f"✅ Saved {len(cookies)} cookies to instagram_cookies.json")

        # Test access
        await page.goto('https://www.instagram.com/fretin98/')
        await page.wait_for_timeout(2000)

        followers_link = await page.query_selector('a[href*="/followers/"]')
        if followers_link:
            print("✅ Successfully logged in and can access follower data!")
        else:
            print("⚠️  Warning: Cannot see followers link")

        await browser.close()

if __name__ == "__main__":
    print("Instagram Cookie Saver")
    print("This will save your login session for automated scraping")
    asyncio.run(save_instagram_cookies())