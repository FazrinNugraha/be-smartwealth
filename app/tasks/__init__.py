"""
Background Tasks Package

Tasks:
- wealth_snapshot: Simpan snapshot net worth harian
- price_updater: Update harga aset otomatis
"""

from app.tasks.wealth_snapshot import wealth_snapshot_job
from app.tasks.price_updater import price_updater_job

__all__ = ["wealth_snapshot_job", "price_updater_job"]
