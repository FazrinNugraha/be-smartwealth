"""
Calculator Service - Helper functions untuk perhitungan finansial

Fungsi file ini:
- calculate_roi: Hitung Return on Investment (%)
- calculate_unrealized_pnl: Hitung profit/loss yang belum direalisasi
- calculate_cagr: Hitung Compound Annual Growth Rate
- calculate_allocation: Hitung persentase alokasi per asset type

Semua fungsi return Decimal untuk presisi tinggi.
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict


def calculate_roi(
    current_value: Decimal,
    total_invested: Decimal,
) -> Decimal:
    """
    Hitung Return on Investment (ROI) dalam persentase

    Formula: ROI = ((Current Value - Total Invested) / Total Invested) × 100

    Args:
        current_value: Nilai aset saat ini (quantity × current_price)
        total_invested: Total uang yang diinvestasikan (quantity × avg_buy_price)

    Returns:
        ROI dalam persentase (contoh: 25.50 untuk 25.5%)

    Examples:
        >>> calculate_roi(Decimal("125000"), Decimal("100000"))
        Decimal("25.00")  # ROI = 25%

        >>> calculate_roi(Decimal("80000"), Decimal("100000"))
        Decimal("-20.00")  # ROI = -20% (rugi)
    """
    if total_invested == 0:
        return Decimal("0")

    roi = ((current_value - total_invested) / total_invested) * 100
    return roi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_unrealized_pnl(
    quantity: Decimal,
    avg_buy_price: Decimal,
    current_price: Decimal,
) -> Decimal:
    """
    Hitung unrealized profit/loss (P&L yang belum direalisasi)

    Formula: Unrealized P&L = (Current Price - Avg Buy Price) × Quantity

    Args:
        quantity: Jumlah aset yang dimiliki
        avg_buy_price: Harga beli rata-rata
        current_price: Harga pasar saat ini

    Returns:
        Profit/loss dalam nilai uang (positif = profit, negatif = loss)

    Examples:
        >>> calculate_unrealized_pnl(Decimal("100"), Decimal("8000"), Decimal("8500"))
        Decimal("50000.00")  # Profit Rp 50,000

        >>> calculate_unrealized_pnl(Decimal("100"), Decimal("8500"), Decimal("8000"))
        Decimal("-50000.00")  # Loss Rp 50,000
    """
    pnl = (current_price - avg_buy_price) * quantity
    return pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_cagr(
    current_value: Decimal,
    initial_value: Decimal,
    years: Decimal,
) -> Decimal:
    """
    Hitung Compound Annual Growth Rate (CAGR)

    Formula: CAGR = ((Current Value / Initial Value) ^ (1 / Years) - 1) × 100

    Args:
        current_value: Nilai aset saat ini
        initial_value: Nilai aset awal
        years: Jumlah tahun (bisa desimal, contoh: 1.5 tahun)

    Returns:
        CAGR dalam persentase per tahun

    Examples:
        >>> calculate_cagr(Decimal("150000"), Decimal("100000"), Decimal("2"))
        Decimal("22.47")  # CAGR = 22.47% per tahun

    Note:
        Jika years = 0 atau initial_value = 0, return 0
    """
    if years == 0 or initial_value == 0:
        return Decimal("0")

    # Convert to float for power calculation
    ratio = float(current_value / initial_value)
    exponent = float(1 / years)

    cagr = (pow(ratio, exponent) - 1) * 100
    return Decimal(str(cagr)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_allocation(
    asset_values: Dict[str, Decimal],
) -> Dict[str, Decimal]:
    """
    Hitung persentase alokasi per asset type

    Args:
        asset_values: Dict dengan key = asset_type, value = total value
        Contoh: {"crypto": 40000, "stock_id": 35000, "cash": 25000}

    Returns:
        Dict dengan key = asset_type, value = persentase
        Contoh: {"crypto": 40.00, "stock_id": 35.00, "cash": 25.00}

    Examples:
        >>> calculate_allocation({
        ...     "crypto": Decimal("40000"),
        ...     "stock_id": Decimal("35000"),
        ...     "cash": Decimal("25000")
        ... })
        {"crypto": Decimal("40.00"), "stock_id": Decimal("35.00"), "cash": Decimal("25.00")}
    """
    total = sum(asset_values.values())

    if total == 0:
        return {k: Decimal("0") for k in asset_values.keys()}

    allocation = {}
    for asset_type, value in asset_values.items():
        percentage = (value / total) * 100
        allocation[asset_type] = percentage.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return allocation


def calculate_years_held(
    purchase_date: datetime,
    current_date: datetime | None = None,
) -> Decimal:
    """
    Hitung berapa tahun aset sudah dipegang

    Args:
        purchase_date: Tanggal pembelian pertama
        current_date: Tanggal saat ini (default: now)

    Returns:
        Jumlah tahun dalam desimal (contoh: 1.5 untuk 1.5 tahun)

    Examples:
        >>> purchase = datetime(2024, 1, 1, tzinfo=timezone.utc)
        >>> current = datetime(2025, 7, 1, tzinfo=timezone.utc)
        >>> calculate_years_held(purchase, current)
        Decimal("1.50")  # 1.5 tahun
    """
    if current_date is None:
        current_date = datetime.now(timezone.utc)

    # Calculate days difference
    days = (current_date - purchase_date).days

    # Convert to years (365.25 to account for leap years)
    years = Decimal(str(days)) / Decimal("365.25")

    return years.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_total_invested(
    quantity: Decimal,
    avg_buy_price: Decimal,
) -> Decimal:
    """
    Hitung total uang yang diinvestasikan

    Formula: Total Invested = Quantity × Avg Buy Price

    Args:
        quantity: Jumlah aset
        avg_buy_price: Harga beli rata-rata

    Returns:
        Total invested dalam nilai uang

    Examples:
        >>> calculate_total_invested(Decimal("100"), Decimal("8500"))
        Decimal("850000.00")
    """
    total = quantity * avg_buy_price
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_current_value(
    quantity: Decimal,
    current_price: Decimal,
) -> Decimal:
    """
    Hitung nilai aset saat ini

    Formula: Current Value = Quantity × Current Price

    Args:
        quantity: Jumlah aset
        current_price: Harga pasar saat ini

    Returns:
        Current value dalam nilai uang

    Examples:
        >>> calculate_current_value(Decimal("100"), Decimal("9000"))
        Decimal("900000.00")
    """
    value = quantity * current_price
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
