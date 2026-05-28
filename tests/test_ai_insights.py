"""
Test AI Insights - Gemini Integration

Test flow:
1. Login untuk dapat token
2. Test GET /insights/ai (should use cache or generate fresh)
3. Test POST /insights/ai/refresh (force refresh)
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000/api/v1"


async def test_ai_insights():
    """Test AI insights endpoint"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Login
        print("\n[1] Login...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123"
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            return
        
        token_data = login_response.json()
        access_token = token_data["access_token"]
        print(f"✓ Login successful! Token: {access_token[:20]}...")
        
        # Headers with auth
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Test GET /insights/ai
        print("\n[2] Testing GET /insights/ai...")
        ai_response = await client.get(
            f"{BASE_URL}/insights/ai",
            headers=headers
        )
        
        print(f"Status: {ai_response.status_code}")
        
        if ai_response.status_code == 200:
            data = ai_response.json()
            print(f"✓ AI Insights received!")
            print(f"  Source: {data.get('source', 'unknown')}")
            print(f"  Summary: {data.get('summary', 'N/A')[:100]}...")
            
            if "detailed_analysis" in data:
                analysis = data["detailed_analysis"]
                print(f"  Strengths: {len(analysis.get('strengths', []))} items")
                print(f"  Weaknesses: {len(analysis.get('weaknesses', []))} items")
                print(f"  Opportunities: {len(analysis.get('opportunities', []))} items")
                print(f"  Threats: {len(analysis.get('threats', []))} items")
            
            if "action_plan" in data:
                print(f"  Action Plan: {len(data['action_plan'])} steps")
        else:
            print(f"❌ Failed: {ai_response.status_code}")
            print(ai_response.text)
        
        # Step 3: Test POST /insights/ai/refresh (optional)
        print("\n[3] Testing POST /insights/ai/refresh...")
        refresh_response = await client.post(
            f"{BASE_URL}/insights/ai/refresh",
            headers=headers
        )
        
        print(f"Status: {refresh_response.status_code}")
        
        if refresh_response.status_code == 200:
            data = refresh_response.json()
            print(f"✓ AI Insights refreshed!")
            print(f"  Source: {data.get('source', 'unknown')}")
            print(f"  Summary: {data.get('summary', 'N/A')[:100]}...")
        else:
            print(f"❌ Failed: {refresh_response.status_code}")
            print(refresh_response.text)


if __name__ == "__main__":
    print("=" * 60)
    print("Testing AI Insights - Gemini Integration")
    print("=" * 60)
    asyncio.run(test_ai_insights())
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
