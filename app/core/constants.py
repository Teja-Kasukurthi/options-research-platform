from datetime import time

# NSE lot sizes (as of 2026)
LOT_SIZES: dict[str, int] = {
    "NIFTY": 75,
    "BANKNIFTY": 35,
    "FINNIFTY": 65,
    "MIDCPNIFTY": 75,
    "SENSEX": 10,
    "BANKEX": 15,
}

# Market hours IST
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)
PRE_OPEN_START = time(9, 0)

# F&O expiry
WEEKLY_EXPIRY_DAY = 3   # Thursday (weekday index)
MONTHLY_EXPIRY_DAY = 3  # Last Thursday

# Options chain depth (strikes either side of ATM)
CHAIN_DEPTH_STRIKES = 20

# Slippage model (basis points) by liquidity tier
SLIPPAGE_BPS = {
    "liquid": 2,       # Nifty/BankNifty front-week ATM
    "semi_liquid": 8,  # Next-week, 1-2 strikes OTM
    "illiquid": 25,    # Deep OTM, far expiry
}
