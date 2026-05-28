"""
Test Dashboard Service - Step 10

Test cases:
1. Setup: Register user, create assets, create transactions
2. Test net worth endpoint
3. Test allocation endpoint
4. Test performance endpoint
5. Test summary endpoint (all-in-one)

Run: python test_dashboard.py
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


async def setup_test_data():
    """Setup: Register user dan buat beberapa aset + transaksi"""
    print("\n" + "="*60)
    print("SETUP: Creating test data")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register user
        email = f"dashboard_{datetime.now().timestamp()}@test.com"
        print(f"📝 Registering user: {email}")
        
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test1234!",
                "full_name": "Dashboard Test User",
            },
        )
        
        if response.status_code != 201:
            print(f"❌ Register failed: {response.text}")
            return None
        
        token = response.json()["access_token"]
        print(f"✅ Token obtained")
        
        # 2. Create assets
        print("\n📊 Creating assets...")
        
        assets_data = [
            {
                "symbol": "bitcoin",
                "asset_name": "Bitcoin",
                "asset_type": "crypto",
                "quantity": "0.5",
                "avg_buy_price": "70000",
                "notes": "Test crypto asset"
            },
            {
                "symbol": "ethereum",
                "asset_name": "Ethereum",
                "asset_type": "crypto",
                "quantity": "5",
                "avg_buy_price": "3000",
                "notes": "Test crypto asset 2"
            },
        ]
        
        created_assets = []
        for asset_data in assets_data:
            response = await client.post(
                f"{BASE_URL}/assets",
                json=asset_data,
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code == 201:
                asset = response.json()
                created_assets.append(asset)
                print(f"  ✅ Created: {asset['asset_name']} ({asset['symbol']})")
            else:
                print(f"  ❌ Failed to create {asset_data['asset_name']}: {response.text}")
        
        print(f"\n✅ Setup complete! Created {len(created_assets)} assets")
        
        return {
            "token": token,
            "assets": created_assets,
        }


async def test_net_worth(token: str):
    """Test 1: Get net worth"""
    print("\n" + "="*60)
    print("TEST 1: Get Net Worth")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/dashboard/net-worth",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Net worth fetched successfully!")
            print(f"   Total: Rp {data['total']}")
            print(f"   Breakdown:")
            for asset_type, value in data['breakdown'].items():
                print(f"     - {asset_type}: Rp {value}")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_allocation(token: str):
    """Test 2: Get allocation"""
    print("\n" + "="*60)
    print("TEST 2: Get Allocation")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/dashboard/allocation",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Allocation fetched successfully!")
            print(f"   Total: Rp {data['total']}")
            print(f"   Allocations:")
            for alloc in data['allocations']:
                print(f"     - {alloc['asset_type']}: {alloc['percentage']}% (Rp {alloc['value']})")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_performance(token: str):
    """Test 3: Get performance"""
    print("\n" + "="*60)
    print("TEST 3: Get Performance")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/dashboard/performance",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Performance fetched successfully!")
            print(f"\n📊 Assets:")
            for asset in data['assets']:
                print(f"   • {asset['asset_name']} ({asset['symbol']})")
                print(f"     Quantity: {asset['quantity']}")
                print(f"     Avg Buy: Rp {asset['avg_buy_price']}")
                print(f"     Current: Rp {asset['current_price']}")
                print(f"     Invested: Rp {asset['total_invested']}")
                print(f"     Value: Rp {asset['current_value']}")
                print(f"     P&L: Rp {asset['unrealized_pnl']}")
                print(f"     ROI: {asset['roi']}%")
                print()
            
            print(f"📈 Summary:")
            print(f"   Total Invested: Rp {data['summary']['total_invested']}")
            print(f"   Current Value: Rp {data['summary']['current_value']}")
            print(f"   Total P&L: Rp {data['summary']['total_unrealized_pnl']}")
            print(f"   Average ROI: {data['summary']['average_roi']}%")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_summary(token: str):
    """Test 4: Get summary (all-in-one)"""
    print("\n" + "="*60)
    print("TEST 4: Get Summary (All-in-One)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summary fetched successfully!")
            print(f"\n💰 Net Worth: Rp {data['net_worth']['total']}")
            print(f"📊 Allocations: {len(data['allocation']['allocations'])} types")
            print(f"📈 Assets: {len(data['performance']['assets'])} assets")
            print(f"🎯 Average ROI: {data['performance']['summary']['average_roi']}%")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("STEP 10: DASHBOARD SERVICE TEST")
    print("🚀"*30)
    
    # Setup test data
    setup_data = await setup_test_data()
    
    if not setup_data:
        print("❌ Setup failed. Aborting tests.")
        return
    
    token = setup_data["token"]
    
    # Run tests
    results = []
    
    results.append(await test_net_worth(token))
    results.append(await test_allocation(token))
    results.append(await test_performance(token))
    results.append(await test_summary(token))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Step 10 complete!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
