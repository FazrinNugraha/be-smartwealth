"""
Currency utilities - Auto-detect currency based on asset type

Fungsi file ini:
- infer_currency(): Deteksi currency otomatis dari asset_type dan symbol
- get_currency_symbol(): Get simbol currency (Rp, $, €, dll)
"""

from typing import Literal


def infer_currency(
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
    symbol: str,
) -> str:
    """
    Auto-detect currency berdasarkan asset type
    
    Logic:
    - crypto: USD (harga global Bitcoin, Ethereum dalam USD)
    - stock_us: USD (saham Amerika)
    - stock_id: IDR (saham Indonesia di BEI)
    - gold: USD (gold futures dalam USD)
    - cash: symbol itu sendiri (IDR, USD, EUR)
    - mutual_fund: IDR (reksa dana Indonesia)
    - bond: IDR (obligasi Indonesia)
    - property: IDR (properti Indonesia)
    
    Args:
        asset_type: Jenis aset
        symbol: Symbol aset
    
    Returns:
        Currency code (USD, IDR, EUR, dll)
    
    Examples:
        >>> infer_currency("crypto", "bitcoin")
        "USD"
        
        >>> infer_currency("stock_id", "BBCA.JK")
        "IDR"
        
        >>> infer_currency("cash", "USD")
        "USD"
    """
    currency_map = {
        "crypto": "USD",
        "stock_us": "USD",
        "stock_id": "IDR",
        "gold": "IDR",       # Gold dikonversi ke IDR/gram
        "mutual_fund": "IDR",
        "bond": "IDR",
        "property": "IDR",
    }
    
    # Special case: cash menggunakan symbol sebagai currency
    if asset_type == "cash":
        return symbol.upper()
    
    return currency_map.get(asset_type, "IDR")


def get_currency_symbol(currency_code: str) -> str:
    """
    Get simbol currency untuk display
    
    Args:
        currency_code: Currency code (USD, IDR, EUR, dll)
    
    Returns:
        Currency symbol ($, Rp, €, dll)
    
    Examples:
        >>> get_currency_symbol("USD")
        "$"
        
        >>> get_currency_symbol("IDR")
        "Rp"
    """
    symbols = {
        "USD": "$",
        "IDR": "Rp",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
        "SGD": "S$",
        "MYR": "RM",
        "THB": "฿",
    }
    
    return symbols.get(currency_code.upper(), currency_code)
