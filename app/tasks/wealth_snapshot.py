"""
Wealth Snapshot Job - Simpan snapshot net worth harian

Fungsi:
- Jalan otomatis setiap hari jam 00:00 (midnight)
- Loop semua user yang punya aset aktif
- Hitung net worth user
- Simpan ke tabel wealth_history

Schedule: Cron (daily at 00:00)
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import User, UserAsset, WealthHistory
from app.services import dashboard_service


async def wealth_snapshot_job():
    """
    Background job untuk simpan snapshot net worth semua user harian secara efisien (Anti N+1).

    Flow:
    1. Tarik semua aset aktif dari semua user sekaligus.
    2. Kumpulkan kombinasi unik dari (symbol, asset_type) untuk meminimalisir API calls.
    3. Tarik harga untuk semua simbol unik dan USD/IDR rate secara paralel.
    4. Hitung total kekayaan (net worth) per user di memori.
    5. Simpan snapshot semua user ke database sekaligus.
    """
    print(f"[WEALTH SNAPSHOT] Starting job at {datetime.now(timezone.utc)}")

    async with async_session() as db:
        try:
            today = datetime.now(timezone.utc).date()

            # 1. Tarik semua aset aktif dari DB
            result = await db.execute(
                select(UserAsset).where(UserAsset.is_active == True)
            )
            all_assets = result.scalars().all()

            if not all_assets:
                print("[WEALTH SNAPSHOT] No active assets found. Job completed.")
                return

            print(f"[WEALTH SNAPSHOT] Found {len(all_assets)} active assets across all users.")

            # 2. Cari simbol aset yang unik
            # Format: set of tuples (symbol, asset_type)
            unique_assets = {(asset.symbol, asset.asset_type) for asset in all_assets}

            # 3. Tarik harga (Price) & Rate secara paralel (menggunakan dictionary)
            from app.services import price_service
            from app.services.dashboard_service import get_usd_idr_rate, FALLBACK_USD_IDR, to_idr
            from app.services.calculator import calculate_current_value

            prices_dict = {}

            # Helper untuk menarik harga individual dan menyimpannya ke dict
            async def fetch_and_store_price(symbol: str, asset_type: str):
                async with async_session() as price_db:
                    try:
                        price = await price_service.get_price(price_db, symbol, asset_type)
                        prices_dict[(symbol, asset_type)] = price
                    except Exception as e:
                        print(f"[WEALTH SNAPSHOT] Failed to fetch price for {symbol}: {e}")
                        prices_dict[(symbol, asset_type)] = None

            # Helper untuk menarik rate USD/IDR
            usd_idr_rate = FALLBACK_USD_IDR
            async def fetch_and_store_rate():
                nonlocal usd_idr_rate
                async with async_session() as price_db:
                    try:
                        usd_idr_rate = await get_usd_idr_rate(price_db)
                    except Exception as e:
                        print(f"[WEALTH SNAPSHOT] Failed to fetch USD/IDR rate: {e}")

            # Jalankan semua request harga + rate secara berbarengan (Concurrent)
            tasks = [fetch_and_store_price(sym, atype) for sym, atype in unique_assets]
            tasks.append(fetch_and_store_rate())
            await asyncio.gather(*tasks)

            print(f"[WEALTH SNAPSHOT] Fetched {len(prices_dict)} unique asset prices.")

            # 4. Kelompokkan aset berdasarkan user_id dan hitung total kekayaannya
            user_assets_map = {}
            for asset in all_assets:
                if asset.user_id not in user_assets_map:
                    user_assets_map[asset.user_id] = []
                user_assets_map[asset.user_id].append(asset)

            # Cek user mana yang sudah di-snapshot hari ini
            user_ids = list(user_assets_map.keys())
            existing_result = await db.execute(
                select(WealthHistory.user_id)
                .where(WealthHistory.user_id.in_(user_ids))
                .where(WealthHistory.snapshot_date == today)
            )
            already_snapshotted = set(existing_result.scalars().all())

            snapshots_to_insert = []

            for user_id, assets in user_assets_map.items():
                if user_id in already_snapshotted:
                    continue

                total_net_worth = Decimal("0")

                for asset in assets:
                    price = prices_dict.get((asset.symbol, asset.asset_type))
                    if not price:
                        continue
                    
                    currency = getattr(asset, "currency", None) or "IDR"
                    
                    # Hitung nilai aset berdasarkan quantity x price
                    current_value_native = calculate_current_value(asset.quantity, price)
                    # Konversi ke IDR
                    current_value_idr = to_idr(current_value_native, currency, usd_idr_rate)
                    
                    total_net_worth += current_value_idr

                if total_net_worth > 0:
                    snapshots_to_insert.append(
                        WealthHistory(
                            user_id=user_id,
                            total_value=total_net_worth,
                            snapshot_date=today,
                        )
                    )

            # 5. Simpan semua data snapshot sekaligus (Bulk Insert)
            if snapshots_to_insert:
                db.add_all(snapshots_to_insert)
                await db.commit()

            print(f"[WEALTH SNAPSHOT] Job completed. Saved {len(snapshots_to_insert)} snapshots.")

        except Exception as e:
            print(f"[WEALTH SNAPSHOT] Job failed with critical error: {e}")
            await db.rollback()


def run_wealth_snapshot_job():
    """
    Wrapper function untuk jalankan async job dari scheduler

    APScheduler butuh function synchronous, jadi kita wrap async function
    dengan asyncio.run()
    """
    asyncio.run(wealth_snapshot_job())


if __name__ == "__main__":
    # For manual testing
    print("Running wealth snapshot job manually...")
    run_wealth_snapshot_job()
