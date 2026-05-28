"""
Test Google OAuth - Manual Testing Script

Flow:
1. Generate Google OAuth URL
2. User manually login via browser
3. Copy authorization code dari URL redirect
4. Exchange code → tokens via backend API
5. Verify tokens work

Note: Requires GOOGLE_CLIENT_ID configured in .env
"""

import asyncio
import httpx
from app.config import settings


BASE_URL = "http://localhost:8000/api/v1"


def generate_google_oauth_url():
    """Generate Google OAuth consent screen URL"""
    
    if not settings.GOOGLE_CLIENT_ID:
        print("❌ GOOGLE_CLIENT_ID not configured in .env")
        return None
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    
    # Build URL
    url = "https://accounts.google.com/o/oauth2/v2/auth?"
    url += "&".join([f"{k}={v}" for k, v in params.items()])
    
    return url


async def test_google_oauth():
    """Test Google OAuth flow"""
    
    print("=" * 70)
    print("Google OAuth Testing")
    print("=" * 70)
    
    # Step 1: Generate OAuth URL
    print("\n[STEP 1] Generate Google OAuth URL")
    oauth_url = generate_google_oauth_url()
    
    if not oauth_url:
        print("\n❌ Cannot generate OAuth URL. Check .env configuration:")
        print("   - GOOGLE_CLIENT_ID")
        print("   - GOOGLE_REDIRECT_URI")
        return
    
    print(f"\n✓ OAuth URL generated!")
    print(f"\n{oauth_url}\n")
    
    # Step 2: Manual login
    print("[STEP 2] Manual Login")
    print("1. Copy URL di atas")
    print("2. Paste di browser")
    print("3. Login dengan Google account")
    print("4. Approve consent screen")
    print("5. Copy 'code' parameter dari URL redirect")
    print("   Example: http://localhost:8000/...?code=4/0AY0e-g7xxx...")
    
    code = input("\n[STEP 3] Paste authorization code di sini: ").strip()
    
    if not code:
        print("\n❌ No code provided. Exiting.")
        return
    
    # Step 4: Exchange code → tokens
    print("\n[STEP 4] Exchange code → tokens")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/auth/google",
                json={"code": code}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                print("\n✅ Login berhasil!")
                print(f"\nAccess Token: {data['access_token'][:50]}...")
                print(f"Refresh Token: {data['refresh_token'][:50]}...")
                print(f"Token Type: {data['token_type']}")
                
                # Step 5: Verify token works
                print("\n[STEP 5] Verify token works")
                
                headers = {"Authorization": f"Bearer {data['access_token']}"}
                
                # Test: Get current user
                me_response = await client.get(
                    f"{BASE_URL}/users/me",
                    headers=headers
                )
                
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    
                    print("\n✅ Token valid! User info:")
                    print(f"   Email: {user_data.get('email')}")
                    print(f"   Name: {user_data.get('full_name')}")
                    print(f"   Avatar: {user_data.get('avatar_url', 'N/A')}")
                    print(f"   User ID: {user_data.get('id')}")
                else:
                    print(f"\n❌ Token verification failed: {me_response.status_code}")
                    print(me_response.text)
            
            else:
                print(f"\n❌ Login failed: {response.status_code}")
                print(f"\nError: {response.text}")
                
                if response.status_code == 400:
                    print("\nPossible causes:")
                    print("- Authorization code expired (codes expire in ~10 minutes)")
                    print("- Authorization code already used (can only use once)")
                    print("- Invalid code format")
                    print("\nSolution: Generate new code (repeat Step 1-3)")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_google_oauth())
