# SmartWealth Backend — Constants & Enums

ASSET_TYPES = {
    "stock_id": "Saham Indonesia",
    "stock_us": "Saham US/Global",
    "crypto": "Cryptocurrency",
    "gold": "Emas",
    "mutual_fund": "Reksa Dana",
    "bond": "Obligasi",
    "cash": "Dana Darurat / Kas",
    "property": "Properti",
}

RISK_PROFILES = {
    "conservative": "Konservatif",
    "moderate": "Moderat",
    "aggressive": "Agresif",
}

TRANSACTION_TYPES = ["buy", "sell"]

SUPPORTED_CURRENCIES = ["IDR", "USD"]

# Price source mapping by asset type
PRICE_SOURCES = {
    "stock_id": "yfinance",
    "stock_us": "yfinance",
    "crypto": "coingecko",
    "gold": "yfinance",
    "mutual_fund": "manual",
    "bond": "manual",
    "cash": "manual",
    "property": "manual",
}

# Cache TTL in seconds
PRICE_CACHE_TTL = 5 * 60          # 5 minutes
INSIGHT_CACHE_TTL = 6 * 60 * 60   # 6 hours
