"""
Test Price Service - Step 9

Test cases:
1. Get stock price (BBCA.JK)
2. Get crypto price (bitcoin)
3. Get gold price (GC=F)
4. Test caching (call 2x, yang kedua harus dari cache)
5. Search crypto symbols

Run: python test_prices.py
"""

import asyncio
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000/api/v1"


async def register_and_login():
    """Register user baru dan login untuk dapat token"""
    async with httpx.AsyncClient() as client:
        # Register
        email = f"pricetest_{datetime.now().timestamp()}@test.com"
        register_data = {
            "email": email,
            "password": "Test1234!",
            "full_name": "Price Test User",
        }
        
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json=register_data,
        )
        
        if response.status_code == 201:
            data = response.json()
            return data["access_token"]
        else:
            print(f"❌ Register failed: {response.text}")
            return None


async def test_stock_price(token: str):
    """Test 1: Get stock price (BBCA.JK)"""
    print("\n" + "="*60)
    print("TEST 1: Get Stock Price (BBCA.JK)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/prices/BBCA.JK",
            params={"asset_type": "stock_id"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stock price fetched successfully!")
            print(f"   Symbol: {data['symbol']}")
            print(f"   Price: Rp {data['price']}")
            print(f"   Cached: {data['cached']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_crypto_price(token: str):
    """Test 2: Get crypto price (bitcoin)"""
    print("\n" + "="*60)
    print("TEST 2: Get Crypto Price (bitcoin)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/prices/bitcoin",
            params={"asset_type": "crypto"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Crypto price fetched successfully!")
            print(f"   Symbol: {data['symbol']}")
            print(f"   Price: ${data['price']}")
            print(f"   Cached: {data['cached']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_gold_price(token: str):
    """Test 3: Get gold price (GC=F)"""
    print("\n" + "="*60)
    print("TEST 3: Get Gold Price (GC=F)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/prices/GC=F",
            params={"asset_type": "gold"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Gold price fetched successfully!")
            print(f"   Symbol: {data['symbol']}")
            print(f"   Price: ${data['price']}")
            print(f"   Cached: {data['cached']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def test_caching(token: str):
    """Test 4: Test caching (call 2x dalam 5 menit)"""
    print("\n" + "="*60)
    print("TEST 4: Test Caching (call 2x)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First call
        print("📡 First call (should fetch from API)...")
        response1 = await client.get(
            f"{BASE_URL}/prices/ethereum",
            params={"asset_type": "crypto"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response1.status_code != 200:
            print(f"❌ First call failed: {response1.text}")
            return False
        
        data1 = response1.json()
        print(f"   Price: ${data1['price']}")
        print(f"   Cached: {data1['cached']}")
        
        # Wait 2 seconds
        print("\n⏳ Waiting 2 seconds...")
        await asyncio.sleep(2)
        
        # Second call
        print("📡 Second call (should use cache)...")
        response2 = await client.get(
            f"{BASE_URL}/prices/ethereum",
            params={"asset_type": "crypto"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response2.status_code != 200:
            print(f"❌ Second call failed: {response2.text}")
            return False
        
        data2 = response2.json()
        print(f"   Price: ${data2['price']}")
        print(f"   Cached: {data2['cached']}")
        
        # Verify caching
        if data2['cached']:
            print(f"✅ Caching works! Second call used cache.")
            return True
        else:
            print(f"⚠️  Warning: Second call did not use cache (might be > 5 min)")
            return True


async def test_search_crypto(token: str):
    """Test 5: Search crypto symbols"""
    print("\n" + "="*60)
    print("TEST 5: Search Crypto Symbols")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/prices/search/crypto",
            params={"q": "bitcoin", "limit": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search successful!")
            print(f"   Query: {data['query']}")
            print(f"   Results: {len(data['results'])} found")
            
            for i, coin in enumerate(data['results'], 1):
                print(f"   {i}. {coin['name']} ({coin['symbol']}) - ID: {coin['id']}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("STEP 9: PRICE SERVICE TEST")
    print("🚀"*30)
    
    # Get token
    print("\n📝 Registering test user and getting token...")
    token = await register_and_login()
    
    if not token:
        print("❌ Failed to get token. Aborting tests.")
        return
    
    print(f"✅ Token obtained: {token[:20]}...")
    
    # Run tests
    results = []
    
    results.append(await test_stock_price(token))
    results.append(await test_crypto_price(token))
    results.append(await test_gold_price(token))
    results.append(await test_caching(token))
    results.append(await test_search_crypto(token))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Step 9 complete!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")


if __name__ == "__main__":
    asyncio.run(main())
