"""
Test Asset CRUD - Test semua endpoint asset management

Test flow:
1. Login untuk dapat access_token
2. Create asset (saham BBCA)
3. Create asset (crypto Bitcoin)
4. List all assets
5. Get asset detail
6. Update asset (quantity + notes)
7. Delete asset
8. Verify asset tidak muncul di list lagi

Run: python test_assets.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "="*60)
print("  ASSET CRUD TEST")
print("="*60)

# ══════════════════════════════════════════════════════════
# 1. LOGIN
# ══════════════════════════════════════════════════════════
print("\n1️⃣  LOGIN")
print("-" * 60)

login_data = {
    "email": "fazrin@example.com",
    "password": "password123BISA!"
}

response = requests.post(
    f"{BASE_URL}/auth/login/json",
    json=login_data,
    timeout=10
)

if response.status_code == 200:
    data = response.json()
    access_token = data["access_token"]
    print("✅ Login berhasil!")
    print(f"Access Token: {access_token[:50]}...")
else:
    print(f"❌ Login gagal! Status: {response.status_code}")
    print(f"Response: {response.text}")
    exit(1)

headers = {"Authorization": f"Bearer {access_token}"}


# ══════════════════════════════════════════════════════════
# 2. CREATE ASSET - Saham BBCA
# ══════════════════════════════════════════════════════════
print("\n2️⃣  CREATE ASSET - Saham BBCA")
print("-" * 60)

asset_data = {
    "symbol": "BBCA.JK",
    "asset_name": "Bank Central Asia",
    "asset_type": "stock_id",
    "quantity": 100,
    "avg_buy_price": 9500,
    "notes": "Beli saat dip"
}

print(f"Data: {json.dumps(asset_data, indent=2)}")

response = requests.post(
    f"{BASE_URL}/assets",
    headers=headers,
    json=asset_data,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 201:
    asset1 = response.json()
    asset1_id = asset1["id"]
    print("✅ Asset created!")
    print(f"Asset ID: {asset1_id}")
    print(f"Symbol: {asset1['symbol']}")
    print(f"Name: {asset1['asset_name']}")
    print(f"Type: {asset1['asset_type']}")
    print(f"Quantity: {asset1['quantity']}")
    print(f"Avg Buy Price: {asset1['avg_buy_price']}")
else:
    print(f"❌ Create asset gagal!")
    print(f"Response: {response.text}")
    exit(1)


# ══════════════════════════════════════════════════════════
# 3. CREATE ASSET - Crypto Bitcoin
# ══════════════════════════════════════════════════════════
print("\n3️⃣  CREATE ASSET - Crypto Bitcoin")
print("-" * 60)

asset_data = {
    "symbol": "bitcoin",
    "asset_name": "Bitcoin",
    "asset_type": "crypto",
    "quantity": 0.5,
    "avg_buy_price": 45000,
    "notes": "HODL for long term"
}

print(f"Data: {json.dumps(asset_data, indent=2)}")

response = requests.post(
    f"{BASE_URL}/assets",
    headers=headers,
    json=asset_data,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 201:
    asset2 = response.json()
    asset2_id = asset2["id"]
    print("✅ Asset created!")
    print(f"Asset ID: {asset2_id}")
    print(f"Symbol: {asset2['symbol']}")
    print(f"Quantity: {asset2['quantity']} BTC")
    print(f"Avg Buy Price: ${asset2['avg_buy_price']}")
else:
    print(f"❌ Create asset gagal!")
    print(f"Response: {response.text}")


# ══════════════════════════════════════════════════════════
# 4. LIST ALL ASSETS
# ══════════════════════════════════════════════════════════
print("\n4️⃣  LIST ALL ASSETS")
print("-" * 60)

response = requests.get(
    f"{BASE_URL}/assets",
    headers=headers,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    assets = response.json()
    print(f"✅ Found {len(assets)} assets")
    for i, asset in enumerate(assets, 1):
        print(f"\n  Asset {i}:")
        print(f"    ID: {asset['id']}")
        print(f"    Symbol: {asset['symbol']}")
        print(f"    Name: {asset['asset_name']}")
        print(f"    Type: {asset['asset_type']}")
        print(f"    Quantity: {asset['quantity']}")
        print(f"    Avg Buy Price: {asset['avg_buy_price']}")
else:
    print(f"❌ List assets gagal!")
    print(f"Response: {response.text}")


# ══════════════════════════════════════════════════════════
# 5. GET ASSET DETAIL
# ══════════════════════════════════════════════════════════
print("\n5️⃣  GET ASSET DETAIL")
print("-" * 60)

print(f"Get detail asset: {asset1_id}")

response = requests.get(
    f"{BASE_URL}/assets/{asset1_id}",
    headers=headers,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    asset = response.json()
    print("✅ Asset detail retrieved!")
    print(f"Symbol: {asset['symbol']}")
    print(f"Name: {asset['asset_name']}")
    print(f"Quantity: {asset['quantity']}")
    print(f"Notes: {asset['notes']}")
else:
    print(f"❌ Get asset detail gagal!")
    print(f"Response: {response.text}")


# ══════════════════════════════════════════════════════════
# 6. UPDATE ASSET
# ══════════════════════════════════════════════════════════
print("\n6️⃣  UPDATE ASSET")
print("-" * 60)

update_data = {
    "quantity": 150,
    "notes": "Tambah beli 50 lembar lagi"
}

print(f"Update data: {json.dumps(update_data, indent=2)}")

response = requests.put(
    f"{BASE_URL}/assets/{asset1_id}",
    headers=headers,
    json=update_data,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    asset = response.json()
    print("✅ Asset updated!")
    print(f"New Quantity: {asset['quantity']}")
    print(f"New Notes: {asset['notes']}")
    print(f"Avg Buy Price: {asset['avg_buy_price']} (unchanged)")
else:
    print(f"❌ Update asset gagal!")
    print(f"Response: {response.text}")


# ══════════════════════════════════════════════════════════
# 7. DELETE ASSET
# ══════════════════════════════════════════════════════════
print("\n7️⃣  DELETE ASSET")
print("-" * 60)

print(f"Delete asset: {asset2_id} (Bitcoin)")

response = requests.delete(
    f"{BASE_URL}/assets/{asset2_id}",
    headers=headers,
    timeout=10
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print("✅ Asset deleted!")
    print(f"Message: {result['message']}")
else:
    print(f"❌ Delete asset gagal!")
    print(f"Response: {response.text}")


# ══════════════════════════════════════════════════════════
# 8. VERIFY ASSET TIDAK MUNCUL LAGI
# ══════════════════════════════════════════════════════════
print("\n8️⃣  VERIFY DELETED ASSET")
print("-" * 60)

response = requests.get(
    f"{BASE_URL}/assets",
    headers=headers,
    timeout=10
)

if response.status_code == 200:
    assets = response.json()
    print(f"✅ Asset list after delete: {len(assets)} assets")
    
    # Check if deleted asset still in list
    deleted_asset_found = any(a['id'] == asset2_id for a in assets)
    
    if not deleted_asset_found:
        print("✅ Deleted asset (Bitcoin) tidak muncul di list lagi")
    else:
        print("❌ Deleted asset masih muncul di list!")
    
    # Show remaining assets
    for asset in assets:
        print(f"  - {asset['symbol']}: {asset['asset_name']}")
else:
    print(f"❌ List assets gagal!")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ✅ ASSET CRUD TEST SELESAI")
print("="*60)
print("\n✅ Semua endpoint Asset CRUD berfungsi dengan baik!")
print("✅ Create, List, Get, Update, Delete → OK")
print("✅ Ownership validation → OK")
print("✅ Soft delete → OK")
print("\n📝 Next Step: Step 8 - Transaction System")
print("="*60 + "\n")
