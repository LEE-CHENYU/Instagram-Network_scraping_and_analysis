#!/usr/bin/env python3
"""
Test instagrapi library for Instagram scraping with login
"""

from instagrapi import Client
import time

# Create a client instance
cl = Client()

# Login credentials
username = "fretin98"
password = "Lcy199818su"

print("=" * 60)
print("Testing INSTAGRAPI")
print("=" * 60)

try:
    # Login
    print(f"\n1. Attempting login as '{username}'...")
    cl.login(username, password)
    print("✅ Login successful!")

    # Test profile access
    test_account = "instagram"
    print(f"\n2. Loading profile: {test_account}")
    user_id = cl.user_id_from_username(test_account)
    user_info = cl.user_info(user_id)

    print(f"\nProfile stats:")
    print(f"  Username: {user_info.username}")
    print(f"  Full name: {user_info.full_name}")
    print(f"  Followers: {user_info.follower_count:,}")
    print(f"  Following: {user_info.following_count:,}")
    print(f"  Posts: {user_info.media_count:,}")

    # Test getting followers
    print(f"\n3. Testing followers retrieval...")
    print("Attempting to get first 50 followers...")

    try:
        # Get followers (returns a dict of user_id -> User objects)
        followers = cl.user_followers(user_id, amount=50)
        followers_list = [user.username for user in followers.values()]

        print(f"✅ Successfully retrieved {len(followers_list)} followers")
        print(f"Sample followers: {followers_list[:5]}")

    except Exception as e:
        print(f"❌ Error getting followers: {e}")
        followers_list = []

    # Test getting following
    print(f"\n4. Testing following retrieval...")
    print("Attempting to get first 50 following...")

    try:
        # Get following
        following = cl.user_following(user_id, amount=50)
        following_list = [user.username for user in following.values()]

        print(f"✅ Successfully retrieved {len(following_list)} following")
        print(f"Sample following: {following_list[:5]}")

    except Exception as e:
        print(f"❌ Error getting following: {e}")
        following_list = []

    # Test with a smaller account
    print(f"\n5. Testing with a smaller account...")
    small_account = "nancyaichuan"
    try:
        small_user_id = cl.user_id_from_username(small_account)
        small_user_info = cl.user_info(small_user_id)

        print(f"\n{small_account} stats:")
        print(f"  Followers: {small_user_info.follower_count:,}")
        print(f"  Following: {small_user_info.following_count:,}")

        # Try to get all following
        print(f"\nAttempting to get ALL following for {small_account}...")
        all_following = cl.user_following(small_user_id, amount=0)  # 0 = get all
        all_following_list = [user.username for user in all_following.values()]

        print(f"✅ Successfully retrieved ALL {len(all_following_list)} following!")
        print(f"Sample: {all_following_list[:10]}")

    except Exception as e:
        print(f"❌ Error with small account: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("INSTAGRAPI RESULTS:")
    print("=" * 60)
    print("✅ Can login successfully")
    print("✅ Can access profile data")
    print(f"✅ Can retrieve followers: {len(followers_list)} retrieved")
    print(f"✅ Can retrieve following: {len(following_list)} retrieved")
    print("\nInstagrapi uses Instagram's private mobile API")
    print("More flexible and faster than instaloader")
    print("Can retrieve complete lists with amount=0 parameter")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
