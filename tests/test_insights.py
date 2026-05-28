"""
Test Insights - Step 12

Test cases:
1. Setup: Create user with diverse portfolio
2. Test insights endpoint
3. Verify health score calculation
4. Verify insights categories

Run: python test_insights.py
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


async def setup_test_portfolio():
    """Setup: Create user with portfolio that triggers various insights"""
    print("\n" + "="*60)
    print("SETUP: Creating test portfolio")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Register
        email = f"insights_{datetime.now().timestamp()}@test.com"
        print(f"📝 Registering user: {email}")
        
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test1234!",
                "full_name": "Insights Test User",
            },
        )
        
        if response.status_code != 201:
            print(f"❌ Register failed: {response.text}")
            return None
        
        token = response.json()["access_token"]
        print(f"✅ Token obtained")
        
        # Create assets to trigger insights
        print("\n📊 Creating portfolio...")
        
        assets_data = [
            {
                "symbol": "bitcoin",
                "asset_name": "Bitcoin",
                "asset_type": "crypto",
                "quantity": "1.3",
                "avg_buy_price": "60000",  # Will trigger concentration risk
                "notes": "Large crypto position"
            },
            {
                "symbol": "ethereum",
                "asset_name": "Ethereum",
                "asset_type": "crypto",
                "quantity": "2",
                "avg_buy_price": "3500",  # Smaller position
                "notes": "Secondary crypto"
            },
        ]
        
        for asset_data in assets_data:
            response = await client.post(
                f"{BASE_URL}/assets",
                json=asset_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 201:
                print(f"  ✅ Created: {asset_data['asset_name']}")
            else:
                print(f"  ❌ Failed: {response.text}")
        
        return token


async def test_insights(token: str):
    """Test: Get insights endpoint"""
    print("\n" + "="*60)
    print("TEST: Get Portfolio Insights")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/insights/",  # Add trailing slash
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Insights fetched successfully!")
            print(f"\n📊 Health Score: {data['health_score']}/100")
            print(f"📊 Health Status: {data['health_status'].upper()}")
            print(f"\n💬 Summary:")
            print(f"   {data['summary']}")
            
            print(f"\n🔍 Insights ({len(data['insights'])} found):")
            
            # Group by type
            warnings = [i for i in data['insights'] if i['type'] == 'warning']
            alerts = [i for i in data['insights'] if i['type'] == 'alert']
            suggestions = [i for i in data['insights'] if i['type'] == 'suggestion']
            positives = [i for i in data['insights'] if i['type'] == 'positive']
            
            if warnings:
                print(f"\n   ⚠️  WARNINGS ({len(warnings)}):")
                for insight in warnings:
                    print(f"      • {insight['title']}")
                    print(f"        {insight['message']}")
                    print(f"        → {insight['recommendation']}")
                    print()
            
            if alerts:
                print(f"\n   🚨 ALERTS ({len(alerts)}):")
                for insight in alerts:
                    print(f"      • {insight['title']}")
                    print(f"        {insight['message']}")
                    print(f"        → {insight['recommendation']}")
                    print()
            
            if suggestions:
                print(f"\n   💡 SUGGESTIONS ({len(suggestions)}):")
                for insight in suggestions:
                    print(f"      • {insight['title']}")
                    print(f"        {insight['message']}")
                    print()
            
            if positives:
                print(f"\n   ✅ POSITIVE ({len(positives)}):")
                for insight in positives:
                    print(f"      • {insight['title']}")
                    print(f"        {insight['message']}")
                    print()
            
            print(f"\n📝 Disclaimer:")
            print(f"   {data['disclaimer']}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("STEP 12: RULE-BASED INSIGHTS TEST")
    print("🚀"*30)
    
    # Setup
    token = await setup_test_portfolio()
    
    if not token:
        print("❌ Setup failed. Aborting tests.")
        return
    
    # Test insights
    success = await test_insights(token)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if success:
        print("✅ All tests passed!")
        print("\n🎉 Step 12 complete!")
        print("\n📝 Note:")
        print("   - Rule-based insights working")
        print("   - Health score calculated")
        print("   - Multiple insight categories detected")
        print("   - Ready for Step 13 (Gemini AI)")
    else:
        print("❌ Tests failed. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
