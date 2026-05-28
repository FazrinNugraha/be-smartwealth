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
    Background job untuk simpan snapshot net worth semua user

    Flow:
    1. Get semua user yang punya aset aktif
    2. Loop setiap user:
       - Hitung net worth
       - Simpan ke wealth_history
    3. Log hasil (berapa user di-snapshot)

    Note:
        - Job ini jalan setiap hari jam 00:00
        - Jika user tidak punya aset, skip
        - Jika sudah ada snapshot hari ini, skip (prevent duplicate)
    """
    print(f"[WEALTH SNAPSHOT] Starting job at {datetime.now(timezone.utc)}")

    async with async_session() as db:
        try:
            # Get all users yang punya aset aktif
            result = await db.execute(
                select(User.id)
                .join(UserAsset, User.id == UserAsset.user_id)
                .where(UserAsset.is_active == True)
                .distinct()
            )
            user_ids = result.scalars().all()

            print(f"[WEALTH SNAPSHOT] Found {len(user_ids)} users with active assets")

            snapshot_count = 0
            today = datetime.now(timezone.utc).date()

            for user_id in user_ids:
                try:
                    # Check if snapshot already exists for today
                    existing = await db.execute(
                        select(WealthHistory)
                        .where(WealthHistory.user_id == user_id)
                        .where(WealthHistory.snapshot_date == today)
                    )

                    if existing.scalar_one_or_none():
                        print(
                            f"[WEALTH SNAPSHOT] Skip user {user_id} - already has snapshot for today"
                        )
                        continue

                    # Calculate net worth
                    net_worth_data = await dashboard_service.get_net_worth(
                        db, str(user_id)
                    )
                    total_value = Decimal(net_worth_data["total"])

                    # Skip if net worth is 0
                    if total_value == 0:
                        print(f"[WEALTH SNAPSHOT] Skip user {user_id} - net worth is 0")
                        continue

                    # Create snapshot
                    snapshot = WealthHistory(
                        user_id=user_id,
                        total_value=total_value,
                        snapshot_date=today,
                    )

                    db.add(snapshot)
                    await db.commit()

                    snapshot_count += 1
                    print(
                        f"[WEALTH SNAPSHOT] Saved snapshot for user {user_id}: Rp {total_value}"
                    )

                except Exception as e:
                    print(f"[WEALTH SNAPSHOT] Error processing user {user_id}: {e}")
                    await db.rollback()
                    continue

            print(f"[WEALTH SNAPSHOT] Job completed. Saved {snapshot_count} snapshots.")

        except Exception as e:
            print(f"[WEALTH SNAPSHOT] Job failed: {e}")
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
