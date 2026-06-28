"""
Price Service - Fetch real-time asset prices with caching

Fungsi file ini:
- Fetch harga saham dari yfinance (BBCA.JK, AAPL, dll)
- Fetch harga crypto dari CoinGecko API (bitcoin, ethereum, dll)
- Fetch harga emas dari yfinance (GC=F) → dikonversi ke IDR/gram
- Fetch USD/IDR exchange rate dari yfinance (IDR=X)
- Caching dengan TTL 5 menit di database (tabel asset_prices)
- Fallback ke cache lama jika API error

Flow:
1. Check cache di database → jika < 5 menit → return cache
2. Jika expired → fetch dari API → update cache → return
3. Jika API error → return cache terakhir (stale tapi lebih baik dari error)

Gold Flow (khusus):
1. Fetch GC=F (USD/troy oz) dari yfinance
2. Fetch IDR=X (USD/IDR rate) dari yfinance
3. Konversi: IDR/gram = (GC=F × IDR rate) ÷ 31.1035
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price import AssetPrice

# Cache TTL: 5 menit
CACHE_TTL_MINUTES = 5

# CoinGecko API base URL (free tier, no API key needed)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Troy ounce to gram conversion
TROY_OZ_TO_GRAM = Decimal("31.1035")


def _period_to_days(period: str) -> int:
    """Map dashboard periods to calendar days for historical APIs."""
    return {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "1y": 365,
        "all": 3650,
    }.get(period, 30)


def _period_to_start_date(period: str) -> str:
    """Return ISO start date string for a given dashboard period.
    
    Using explicit start dates (instead of yfinance period strings like '1mo')
    ensures ALL assets return data from the exact same calendar date,
    regardless of asset type, timezone, or market calendar differences.
    """
    from datetime import date
    today = date.today()
    days = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "1y": 365,
        "all": 3650,
    }.get(period, 30)
    return (today - timedelta(days=days)).isoformat()


async def fetch_stock_price(symbol: str) -> Decimal | None:
    """
    Fetch harga saham secara Async dari Yahoo Finance API v8
    tanpa menggunakan yfinance (menghindari thread pool blocking).
    """
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            
            if price and price > 0:
                return Decimal(str(price))
                
            return None
            
    except Exception as e:
        print(f"Error fetching stock price for {symbol} via Yahoo API: {e}")
        return None


async def fetch_stock_price_history(symbol: str, period: str) -> list[dict]:
    """
    Fetch history harga saham secara Async dari Yahoo Finance API v8.
    """
    from datetime import datetime, timedelta, timezone
    
    try:
        days = _period_to_days(period)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())
        
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&period1={period1}&period2={period2}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            result = data["chart"]["result"][0]
            
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {}).get("quote", [{}])[0]
            closes = indicators.get("close", [])
            
            points = []
            for ts, close in zip(timestamps, closes):
                if close is None or close <= 0:
                    continue
                    
                points.append({
                    "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                    "price": Decimal(str(close))
                })
                
            return points

    except Exception as e:
        print(f"Error fetching stock history for {symbol} via Yahoo API: {e}")
        return []


async def fetch_crypto_price(symbol: str) -> Decimal | None:
    """
    Fetch harga crypto dari CoinGecko API

    Args:
        symbol: Crypto ID (bitcoin, ethereum, binancecoin, dll)

    Returns:
        Harga terkini dalam USD atau None jika error

    Note:
        CoinGecko free tier: 10-30 calls/minute
        Endpoint: /simple/price?ids={symbol}&vs_currencies=usd
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": symbol.lower(),
                    "vs_currencies": "usd",
                },
            )
            response.raise_for_status()

            data = response.json()

            # Response format: {"bitcoin": {"usd": 50000}}
            if symbol.lower() in data and "usd" in data[symbol.lower()]:
                price = data[symbol.lower()]["usd"]
                return Decimal(str(price))

            return None

    except Exception as e:
        print(f"Error fetching crypto price for {symbol}: {e}")
        return None


async def fetch_crypto_price_history(symbol: str, period: str) -> list[dict]:
    """
    Fetch daily historical crypto prices from CoinGecko.

    CoinGecko returns multiple intraday points for short ranges, so this keeps
    the latest price per UTC date to make chart rendering simple.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{COINGECKO_API_URL}/coins/{symbol.lower()}/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": _period_to_days(period),
                },
            )
            response.raise_for_status()

            data = response.json()
            prices = data.get("prices", [])
            by_date = {}

            for ts_ms, price in prices:
                if price is None or price <= 0:
                    continue
                point_date = (
                    datetime.fromtimestamp(ts_ms / 1000, timezone.utc)
                    .date()
                    .isoformat()
                )
                by_date[point_date] = Decimal(str(price))

            return [
                {"date": point_date, "price": price}
                for point_date, price in sorted(by_date.items())
            ]

    except Exception as e:
        print(f"Error fetching crypto history for {symbol}: {e}")
        return []


async def get_price_from_cache(
    db: AsyncSession,
    symbol: str,
) -> AssetPrice | None:
    """
    Get harga dari cache database

    Args:
        db: Database session
        symbol: Asset symbol

    Returns:
        AssetPrice object atau None jika tidak ada cache
    """
    result = await db.execute(
        select(AssetPrice).where(AssetPrice.symbol == symbol.upper())
    )
    return result.scalar_one_or_none()


async def is_cache_valid(cache: AssetPrice | None) -> bool:
    """
    Check apakah cache masih valid (< 5 menit)

    Args:
        cache: AssetPrice object dari database

    Returns:
        True jika cache valid, False jika expired atau None
    """
    if not cache:
        return False

    now = datetime.now(timezone.utc)
    cache_age = now - cache.fetched_at

    return cache_age < timedelta(minutes=CACHE_TTL_MINUTES)


async def update_price_cache(
    db: AsyncSession,
    symbol: str,
    price: Decimal,
    source: str,
    asset_type: str,
) -> AssetPrice:
    """
    Update atau insert harga ke cache database

    Args:
        db: Database session
        symbol: Asset symbol
        price: Harga terkini
        source: Sumber data (yfinance, coingecko)
        asset_type: Jenis aset (stock_id, crypto, dll)

    Returns:
        AssetPrice object yang sudah disimpan
    """
    # Check if cache exists
    cache = await get_price_from_cache(db, symbol)

    if cache:
        # Update existing cache
        cache.price = price
        cache.source = source
        cache.asset_type = asset_type
        cache.fetched_at = datetime.now(timezone.utc)
    else:
        # Create new cache
        cache = AssetPrice(
            symbol=symbol.upper(),
            asset_type=asset_type,
            price=price,
            source=source,
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(cache)

    await db.commit()
    await db.refresh(cache)

    return cache


async def fetch_usd_idr_rate() -> Decimal | None:
    """
    Fetch kurs USD/IDR dari Yahoo Finance secara Async.
    """
    url = "https://query2.finance.yahoo.com/v8/finance/chart/IDR=X?interval=1d&range=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            meta = data["chart"]["result"][0]["meta"]
            rate = meta.get("regularMarketPrice")

            if rate and rate > 0:
                return Decimal(str(rate))

            return None

    except Exception as e:
        print(f"Error fetching USD/IDR rate via Yahoo API: {e}")
        return None


async def fetch_gold_price_idr_per_gram(db: AsyncSession) -> Decimal | None:
    """
    Fetch harga emas dalam IDR per gram

    Flow:
    1. Fetch GC=F (gold futures) dari yfinance → USD per troy ounce
    2. Fetch IDR=X (USD/IDR rate) dari yfinance
    3. Konversi: IDR/gram = (USD/troy oz × IDR rate) ÷ 31.1035

    Args:
        db: Database session (untuk cache USD/IDR rate)

    Returns:
        Harga emas dalam IDR per gram atau None jika error

    Example:
        GC=F = $2,350/troy oz
        IDR=X = 16,000
        Gold IDR/gram = (2,350 × 16,000) ÷ 31.1035 = Rp 1,208,600/gram
    """
    # Fetch gold price (USD/troy oz)
    gold_usd_per_oz = await fetch_stock_price("GC=F")
    if not gold_usd_per_oz:
        print("Failed to fetch gold price (GC=F)")
        return None

    # Fetch USD/IDR rate (try cache first)
    usd_idr_cache = await get_price_from_cache(db, "IDR=X")

    if await is_cache_valid(usd_idr_cache):
        usd_idr_rate = usd_idr_cache.price
    else:
        usd_idr_rate = await fetch_usd_idr_rate()
        if usd_idr_rate:
            await update_price_cache(db, "IDR=X", usd_idr_rate, "yfinance", "forex")

    if not usd_idr_rate:
        # Fallback ke rate stale jika ada
        if usd_idr_cache:
            usd_idr_rate = usd_idr_cache.price
            print("Using stale USD/IDR rate as fallback")
        else:
            print("Failed to fetch USD/IDR rate, no fallback available")
            return None

    # Konversi: IDR/gram = (USD/troy oz × IDR rate) ÷ 31.1035
    gold_idr_per_gram = (gold_usd_per_oz * usd_idr_rate) / TROY_OZ_TO_GRAM

    print(
        f"Gold: ${gold_usd_per_oz}/oz × {usd_idr_rate} IDR/USD ÷ {TROY_OZ_TO_GRAM} = Rp {gold_idr_per_gram:,.0f}/gram"
    )

    return gold_idr_per_gram


async def get_price(
    db: AsyncSession,
    symbol: str,
    asset_type: Literal[
        "stock_id",
        "stock_us",
        "crypto",
        "gold",
        "mutual_fund",
        "bond",
        "cash",
        "property",
    ],
) -> Decimal | None:
    """
    Get harga aset dengan caching

    Flow:
    1. Check cache → jika valid → return cache
    2. Jika expired → fetch dari API → update cache → return
    3. Jika API error → return cache lama (stale)

    Args:
        db: Database session
        symbol: Asset symbol
        asset_type: Jenis aset (stock_id, crypto, dll)

    Returns:
        Harga terkini atau None jika tidak bisa fetch

    Examples:
        >>> await get_price(db, "BBCA.JK", "stock_id")
        Decimal("8750")

        >>> await get_price(db, "bitcoin", "crypto")
        Decimal("50000")
    """
    # 1. Check cache
    cache = await get_price_from_cache(db, symbol)

    if await is_cache_valid(cache):
        # Cache valid, return immediately
        return cache.price

    # 2. Cache expired or not exists, fetch from API
    price = None
    source = None

    if asset_type in ["stock_id", "stock_us"]:
        # Fetch dari yfinance (return harga dalam currency asli)
        price = await fetch_stock_price(symbol)
        source = "yfinance"

    elif asset_type == "gold":
        # Gold: konversi GC=F (USD/troy oz) → IDR/gram
        price = await fetch_gold_price_idr_per_gram(db)
        source = "yfinance_converted"

    elif asset_type == "crypto":
        # Fetch dari CoinGecko
        price = await fetch_crypto_price(symbol)
        source = "coingecko"

    elif asset_type == "cash":
        # Cash selalu 1:1
        price = Decimal("1")
        source = "static"

    else:
        # mutual_fund, bond, property: belum support auto-fetch
        # Return cache lama jika ada
        if cache:
            return cache.price
        return None

    # 3. Update cache jika berhasil fetch
    if price:
        await update_price_cache(db, symbol, price, source, asset_type)
        return price

    # 4. API error, return cache lama jika ada (stale tapi lebih baik dari None)
    if cache:
        print(f"API error for {symbol}, returning stale cache")
        return cache.price

    return None


async def get_price_history(
    db: AsyncSession,
    symbol: str,
    asset_type: Literal[
        "stock_id",
        "stock_us",
        "crypto",
        "gold",
        "mutual_fund",
        "bond",
        "cash",
        "property",
    ],
    period: Literal["7d", "30d", "90d", "1y", "all"],
    usd_idr_rate: Decimal | None = None,
) -> list[dict]:
    """
    Get historical daily prices for interactive performance charts.

    Returns:
        List of {"date": "YYYY-MM-DD", "price": Decimal(...)} sorted ascending.

    Note:
        This is intentionally not cached yet. The first version keeps the API
        shape ready for the UI while the DB can later grow a real price history
        table without changing the frontend contract.
    """
    if asset_type in ["stock_id", "stock_us"]:
        return await fetch_stock_price_history(symbol, period)

    if asset_type == "crypto":
        return await fetch_crypto_price_history(symbol, period)

    if asset_type == "gold":
        rate = usd_idr_rate
        if rate is None:
            rate = await fetch_usd_idr_rate()
        if rate is None:
            cache = await get_price_from_cache(db, "IDR=X")
            rate = cache.price if cache else None
        if rate is None:
            return []

        gold_usd_points = await fetch_stock_price_history("GC=F", period)
        return [
            {
                "date": point["date"],
                "price": (point["price"] * rate) / TROY_OZ_TO_GRAM,
            }
            for point in gold_usd_points
        ]

    if asset_type == "cash":
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=_period_to_days(period))
        return [
            {"date": start.isoformat(), "price": Decimal("1")},
            {"date": today.isoformat(), "price": Decimal("1")},
        ]

    return []


async def search_crypto_symbols(query: str, limit: int = 10) -> list[dict]:
    """
    Search crypto symbols dari CoinGecko

    Args:
        query: Search query (bitcoin, eth, bnb, dll)
        limit: Max results

    Returns:
        List of crypto info: [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}, ...]

    Note:
        Endpoint: /search?query={query}
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{COINGECKO_API_URL}/search",
                params={"query": query},
            )
            response.raise_for_status()

            data = response.json()

            # Response format: {"coins": [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}, ...]}
            coins = data.get("coins", [])

            # Return top N results
            return [
                {
                    "id": coin["id"],
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                }
                for coin in coins[:limit]
            ]

    except Exception as e:
        print(f"Error searching crypto symbols: {e}")
        return []
