"""
Test Background Jobs - Step 11

Test cases:
1. Manual trigger wealth snapshot job
2. Manual trigger price updater job
3. Test wealth history endpoint (after snapshot)

Run: python test_background_jobs.py
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


async def setup_test_user():
    """Setup: Register user dan buat aset"""
    print("\n" + "="*60)
    print("SETUP: Creating test user with assets")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Register
        email = f"jobs_{datetime.now().timestamp()}@test.com"
        print(f"📝 Registering user: {email}")
        
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test1234!",
                "full_name": "Jobs Test User",
            },
        )
        
        if response.status_code != 201:
            print(f"❌ Register failed: {response.text}")
            return None
        
        token = response.json()["access_token"]
        print(f"✅ Token obtained")
        
        # Create asset
        print("\n📊 Creating asset...")
        response = await client.post(
            f"{BASE_URL}/assets",
            json={
                "symbol": "bitcoin",
                "asset_name": "Bitcoin",
                "asset_type": "crypto",
                "quantity": "1",
                "avg_buy_price": "75000",
                "notes": "Test asset for jobs"
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 201:
            print(f"  ✅ Created Bitcoin asset")
        else:
            print(f"  ❌ Failed: {response.text}")
            return None
        
        return token


async def test_wealth_snapshot():
    """Test 1: Manual trigger wealth snapshot job"""
    print("\n" + "="*60)
    print("TEST 1: Wealth Snapshot Job")
    print("="*60)
    
    try:
        from app.tasks.wealth_snapshot import wealth_snapshot_job
        
        print("📸 Running wealth snapshot job...")
        await wealth_snapshot_job()
        print("✅ Wealth snapshot job completed!")
        return True
    
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_price_updater():
    """Test 2: Manual trigger price updater job"""
    print("\n" + "="*60)
    print("TEST 2: Price Updater Job")
    print("="*60)
    
    try:
        from app.tasks.price_updater import price_updater_job
        
        print("💰 Running price updater job...")
        await price_updater_job()
        print("✅ Price updater job completed!")
        return True
    
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_wealth_history(token: str):
    """Test 3: Get wealth history endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Wealth History Endpoint")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test different periods
        periods = ["7d", "30d", "all"]
        
        for period in periods:
            print(f"\n📊 Testing period: {period}")
            
            response = await client.get(
                f"{BASE_URL}/dashboard/wealth-history",
                params={"period": period},
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Success!")
                print(f"     Period: {data['period']}")
                print(f"     Data points: {len(data['data'])}")
                
                if len(data['data']) > 0:
                    print(f"     Start value: Rp {data['start_value']}")
                    print(f"     End value: Rp {data['end_value']}")
                    print(f"     Change: Rp {data['change']} ({data['change_percentage']}%)")
                    
                    # Show first few data points
                    print(f"     Sample data:")
                    for record in data['data'][:3]:
                        print(f"       - {record['date']}: Rp {record['total_value']}")
                else:
                    print(f"     No historical data yet (run wealth snapshot job first)")
            else:
                print(f"  ❌ Failed: {response.status_code} - {response.text}")
                return False
        
        return True


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("STEP 11: BACKGROUND JOBS TEST")
    print("🚀"*30)
    
    # Setup
    token = await setup_test_user()
    
    if not token:
        print("❌ Setup failed. Aborting tests.")
        return
    
    # Run tests
    results = []
    
    # Test 1: Wealth snapshot (will create snapshot for all users)
    results.append(await test_wealth_snapshot())
    
    # Test 2: Price updater (will update all prices)
    results.append(await test_price_updater())
    
    # Test 3: Wealth history endpoint
    results.append(await test_wealth_history(token))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Step 11 complete!")
        print("\n📝 Note:")
        print("   - Background jobs are now running automatically")
        print("   - Wealth snapshot: Daily at 00:00")
        print("   - Price updater: Every 5 minutes")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
