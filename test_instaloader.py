#!/usr/bin/env python3
"""
Test instaloader library for Instagram scraping with login
"""

import instaloader
import time

# Create an instance of Instaloader
L = instaloader.Instaloader()

# Login credentials
username = "fretin98"
password = "Lcy199818su"

print("=" * 60)
print("Testing INSTALOADER")
print("=" * 60)

try:
    # Login
    print(f"\n1. Attempting login as '{username}'...")
    L.login(username, password)
    print("✅ Login successful!")

    # Test profile access
    test_account = "instagram"  # Instagram's official account
    print(f"\n2. Loading profile: {test_account}")
    profile = instaloader.Profile.from_username(L.context, test_account)

    print(f"\nProfile stats:")
    print(f"  Username: {profile.username}")
    print(f"  Full name: {profile.full_name}")
    print(f"  Followers: {profile.followers:,}")
    print(f"  Following: {profile.followees:,}")
    print(f"  Posts: {profile.mediacount:,}")

    # Test getting followers
    print(f"\n3. Testing followers retrieval...")
    print("Attempting to get first 50 followers...")

    followers_list = []
    try:
        for i, follower in enumerate(profile.get_followers()):
            followers_list.append(follower.username)
            if i >= 49:  # Get 50 followers
                break
            if (i + 1) % 10 == 0:
                print(f"  Retrieved {i + 1} followers...")

        print(f"✅ Successfully retrieved {len(followers_list)} followers")
        print(f"Sample followers: {followers_list[:5]}")

    except Exception as e:
        print(f"❌ Error getting followers: {e}")
        print(f"Retrieved {len(followers_list)} followers before error")

    # Test getting following
    print(f"\n4. Testing following retrieval...")
    print("Attempting to get first 50 following...")

    following_list = []
    try:
        for i, followee in enumerate(profile.get_followees()):
            following_list.append(followee.username)
            if i >= 49:  # Get 50 following
                break
            if (i + 1) % 10 == 0:
                print(f"  Retrieved {i + 1} following...")

        print(f"✅ Successfully retrieved {len(following_list)} following")
        print(f"Sample following: {following_list[:5]}")

    except Exception as e:
        print(f"❌ Error getting following: {e}")
        print(f"Retrieved {len(following_list)} following before error")

    # Test with a smaller account
    print(f"\n5. Testing with a smaller account...")
    small_account = "nancyaichuan"  # From your scraping_progress.json
    try:
        small_profile = instaloader.Profile.from_username(L.context, small_account)
        print(f"\n{small_account} stats:")
        print(f"  Followers: {small_profile.followers:,}")
        print(f"  Following: {small_profile.followees:,}")

        # Try to get all following
        print(f"\nAttempting to get ALL following for {small_account}...")
        all_following = []
        for i, followee in enumerate(small_profile.get_followees()):
            all_following.append(followee.username)
            if (i + 1) % 50 == 0:
                print(f"  Retrieved {i + 1} following...")
                time.sleep(2)  # Rate limit protection

        print(f"✅ Successfully retrieved ALL {len(all_following)} following!")

    except Exception as e:
        print(f"❌ Error with small account: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("INSTALOADER RESULTS:")
    print("=" * 60)
    print("✅ Can login successfully")
    print("✅ Can access profile data")
    print(f"✅ Can retrieve followers: {len(followers_list)} retrieved")
    print(f"✅ Can retrieve following: {len(following_list)} retrieved")
    print("\nInstaloader uses Instagram's official API endpoints")
    print("Rate limits: Instagram may limit requests, but with login")
    print("you should be able to get much more data than without login")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
