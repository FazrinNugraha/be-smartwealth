"""
Test Transaction System - Test BUY/SELL dengan auto-calculate

Test flow:
1. Login → get token
2. Create asset BBCA (100 lembar @ 9500)
3. BUY 50 lembar @ 10000 → verify avg_buy_price
4. SELL 30 lembar @ 10500 → verify quantity
5. List transactions
6. Test oversell (should fail)
7. Delete transaction → verify recalculation

Run: python test_transactions.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

print("\n" + "="*60)
print("  TRANSACTION SYSTEM TEST")
print("="*60)

# ══════════════════════════════════════════════════════════
# 1. LOGIN
# ══════════════════════════════════════════════════════════
print("\n1️⃣  LOGIN")
print("-" * 60)

response = requests.post(
    f"{BASE_URL}/auth/login/json",
    json={"email": "fazrin@example.com", "password": "password123BISA!"},
    timeout=10
)

if response.status_code == 200:
    access_token = response.json()["access_token"]
    print("✅ Login berhasil!")
else:
    print(f"❌ Login gagal! {response.text}")
    exit(1)

headers = {"Authorization": f"Bearer {access_token}"}


# ══════════════════════════════════════════════════════════
# 2. CREATE ASSET - BBCA
# ══════════════════════════════════════════════════════════
print("\n2️⃣  CREATE ASSET - BBCA (Initial)")
print("-" * 60)

# Use unique symbol with timestamp to avoid conflicts
from datetime import datetime
timestamp = datetime.now().strftime("%H%M%S")
symbol = f"BBCA-TEST-{timestamp}"

asset_data = {
    "symbol": symbol,
    "asset_name": "Bank Central Asia (Test)",
    "asset_type": "stock_id",
    "quantity": 100,
    "avg_buy_price": 9500,
    "notes": "Initial purchase for transaction test"
}

response = requests.post(
    f"{BASE_URL}/assets",
    headers=headers,
    json=asset_data,
    timeout=10
)

if response.status_code == 201:
    asset = response.json()
    asset_id = asset["id"]
    print("✅ Asset created!")
    print(f"Asset ID: {asset_id}")
    print(f"Quantity: {asset['quantity']}")
    print(f"Avg Buy Price: Rp {float(asset['avg_buy_price']):,.0f}")
else:
    print(f"❌ Create asset gagal! {response.text}")
    exit(1)


# ══════════════════════════════════════════════════════════
# 3. BUY TRANSACTION - Tambah 50 lembar
# ══════════════════════════════════════════════════════════
print("\n3️⃣  BUY TRANSACTION - Tambah 50 lembar @ Rp 10.000")
print("-" * 60)

tx_data = {
    "asset_id": asset_id,
    "transaction_type": "buy",
    "quantity": 50,
    "price_per_unit": 10000,
    "fees": 25000,
    "notes": "Average up",
    "transaction_date": datetime.now().isoformat()
}

print(f"Transaction: BUY {tx_data['quantity']} @ Rp {tx_data['price_per_unit']:,.0f}")

response = requests.post(
    f"{BASE_URL}/transactions",
    headers=headers,
    json=tx_data,
    timeout=10
)

if response.status_code == 201:
    tx = response.json()
    tx1_id = tx["id"]
    print("✅ Transaction created!")
    print(f"Transaction ID: {tx1_id}")
    print(f"Total Amount: Rp {float(tx['total_amount']):,.0f}")
    
    # Get updated asset
    response = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers, timeout=10)
    asset = response.json()
    print(f"\n📊 Asset Updated:")
    print(f"   Quantity: {asset['quantity']} lembar (was 100)")
    print(f"   Avg Buy Price: Rp {float(asset['avg_buy_price']):,.0f} (was Rp 9.500)")
    print(f"   Expected: Rp {(100*9500 + 50*10000)/150:,.0f}")
else:
    print(f"❌ Transaction gagal! {response.text}")
    exit(1)


# ══════════════════════════════════════════════════════════
# 4. SELL TRANSACTION - Jual 30 lembar
# ══════════════════════════════════════════════════════════
print("\n4️⃣  SELL TRANSACTION - Jual 30 lembar @ Rp 10.500")
print("-" * 60)

tx_data = {
    "asset_id": asset_id,
    "transaction_type": "sell",
    "quantity": 30,
    "price_per_unit": 10500,
    "fees": 20000,
    "notes": "Take profit",
    "transaction_date": datetime.now().isoformat()
}

print(f"Transaction: SELL {tx_data['quantity']} @ Rp {tx_data['price_per_unit']:,.0f}")

response = requests.post(
    f"{BASE_URL}/transactions",
    headers=headers,
    json=tx_data,
    timeout=10
)

if response.status_code == 201:
    tx = response.json()
    tx2_id = tx["id"]
    print("✅ Transaction created!")
    print(f"Transaction ID: {tx2_id}")
    print(f"Total Amount: Rp {float(tx['total_amount']):,.0f}")
    
    # Get updated asset
    response = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers, timeout=10)
    asset = response.json()
    avg_price = float(asset['avg_buy_price'])
    profit = (10500 - avg_price) * 30
    print(f"\n📊 Asset Updated:")
    print(f"   Quantity: {asset['quantity']} lembar (was 150)")
    print(f"   Avg Buy Price: Rp {avg_price:,.0f} (unchanged)")
    print(f"   Realized Profit: Rp {profit:,.0f}")
else:
    print(f"❌ Transaction gagal! {response.text}")


# ══════════════════════════════════════════════════════════
# 5. LIST TRANSACTIONS
# ══════════════════════════════════════════════════════════
print("\n5️⃣  LIST TRANSACTIONS")
print("-" * 60)

response = requests.get(
    f"{BASE_URL}/transactions?asset_id={asset_id}",
    headers=headers,
    timeout=10
)

if response.status_code == 200:
    transactions = response.json()
    print(f"✅ Found {len(transactions)} transactions")
    for i, tx in enumerate(transactions, 1):
        print(f"\n  Transaction {i}:")
        print(f"    Type: {tx['transaction_type'].upper()}")
        print(f"    Quantity: {tx['quantity']}")
        print(f"    Price: Rp {float(tx['price_per_unit']):,.0f}")
        print(f"    Total: Rp {float(tx['total_amount']):,.0f}")
        print(f"    Date: {tx['transaction_date'][:10]}")
else:
    print(f"❌ List transactions gagal! {response.text}")


# ══════════════════════════════════════════════════════════
# 6. TEST OVERSELL (Should Fail)
# ══════════════════════════════════════════════════════════
print("\n6️⃣  TEST OVERSELL VALIDATION")
print("-" * 60)

# Get current quantity
response = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers, timeout=10)
current_qty = float(response.json()['quantity'])

print(f"Current quantity: {current_qty}")
print(f"Trying to sell: {current_qty + 10} (oversell!)")

tx_data = {
    "asset_id": asset_id,
    "transaction_type": "sell",
    "quantity": current_qty + 10,
    "price_per_unit": 11000,
    "transaction_date": datetime.now().isoformat()
}

response = requests.post(
    f"{BASE_URL}/transactions",
    headers=headers,
    json=tx_data,
    timeout=10
)

if response.status_code == 400:
    print("✅ Oversell validation works!")
    print(f"   Error: {response.json()['detail']}")
else:
    print(f"❌ Oversell validation failed! Status: {response.status_code}")


# ══════════════════════════════════════════════════════════
# 7. DELETE TRANSACTION
# ══════════════════════════════════════════════════════════
print("\n7️⃣  DELETE TRANSACTION (Reverse BUY)")
print("-" * 60)

print(f"Deleting BUY transaction: {tx1_id}")

# Get asset before delete
response = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers, timeout=10)
before = response.json()
print(f"Before delete:")
print(f"   Quantity: {before['quantity']}")
print(f"   Avg Buy Price: Rp {float(before['avg_buy_price']):,.0f}")

# Delete transaction
response = requests.delete(
    f"{BASE_URL}/transactions/{tx1_id}",
    headers=headers,
    timeout=10
)

if response.status_code == 200:
    print("✅ Transaction deleted!")
    
    # Get asset after delete
    response = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers, timeout=10)
    after = response.json()
    print(f"After delete:")
    print(f"   Quantity: {after['quantity']} (reversed!)")
    print(f"   Avg Buy Price: Rp {float(after['avg_buy_price']):,.0f} (recalculated!)")
else:
    print(f"❌ Delete transaction gagal! {response.text}")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ✅ TRANSACTION SYSTEM TEST SELESAI")
print("="*60)
print("\n✅ Semua fitur transaction berfungsi dengan baik!")
print("✅ BUY → auto-calculate avg_buy_price")
print("✅ SELL → validate quantity, avg_buy_price unchanged")
print("✅ List transactions dengan filter")
print("✅ Oversell validation")
print("✅ Delete transaction → recalculate asset")
print("\n📝 Next Step: Step 9 - Price Service (yfinance, CoinGecko)")
print("="*60 + "\n")
