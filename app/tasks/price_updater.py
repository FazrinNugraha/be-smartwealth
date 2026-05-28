"""
Price Updater Job - Update harga aset otomatis

Fungsi:
- Jalan otomatis setiap 5 menit
- Ambil semua unique symbols dari user_assets
- Fetch harga terbaru untuk setiap symbol
- Update cache di asset_prices

Schedule: Interval (every 5 minutes)
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import UserAsset
from app.services import price_service


async def price_updater_job():
    """
    Background job untuk update harga semua aset di cache

    Flow:
    1. Get semua unique symbols dari user_assets (yang aktif)
    2. Loop setiap symbol:
       - Fetch harga terbaru
       - Update cache di asset_prices
    3. Log hasil (berapa harga di-update)

    Note:
        - Job ini jalan setiap 5 menit
        - Hanya update aset yang ada di portfolio user
        - Jika fetch error, skip (cache tetap pakai data lama)
    """
    print(f"[PRICE UPDATER] Starting job at {datetime.now(timezone.utc)}")

    async with async_session() as db:
        try:
            # Get all unique symbols dari user assets yang aktif
            result = await db.execute(
                select(UserAsset.symbol, UserAsset.asset_type)
                .where(UserAsset.is_active == True)
                .distinct()
            )
            assets = result.all()

            print(f"[PRICE UPDATER] Found {len(assets)} unique assets to update")

            update_count = 0
            error_count = 0

            for symbol, asset_type in assets:
                try:
                    # Fetch price (will update cache automatically)
                    price = await price_service.get_price(db, symbol, asset_type)

                    if price:
                        update_count += 1
                        print(
                            f"[PRICE UPDATER] Updated {symbol} ({asset_type}): {price}"
                        )
                    else:
                        error_count += 1
                        print(
                            f"[PRICE UPDATER] Failed to fetch {symbol} ({asset_type})"
                        )

                except Exception as e:
                    error_count += 1
                    print(f"[PRICE UPDATER] Error updating {symbol}: {e}")
                    continue

            print(
                f"[PRICE UPDATER] Job completed. Updated: {update_count}, Errors: {error_count}"
            )

        except Exception as e:
            print(f"[PRICE UPDATER] Job failed: {e}")


def run_price_updater_job():
    """
    Wrapper function untuk jalankan async job dari scheduler

    APScheduler butuh function synchronous, jadi kita wrap async function
    dengan asyncio.run()
    """
    asyncio.run(price_updater_job())


if __name__ == "__main__":
    # For manual testing
    print("Running price updater job manually...")
    run_price_updater_job()
