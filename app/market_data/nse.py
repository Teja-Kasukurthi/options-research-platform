"""NSE India options chain + FII/DII data scraper."""

from datetime import date, datetime

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.market_data.normalizer import OptionsChain, OptionStrike

logger = structlog.get_logger(__name__)

NSE_BASE = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}

UNDERLYING_URL = {
    "NIFTY": f"{NSE_BASE}/api/option-chain-indices?symbol=NIFTY",
    "BANKNIFTY": f"{NSE_BASE}/api/option-chain-indices?symbol=BANKNIFTY",
    "FINNIFTY": f"{NSE_BASE}/api/option-chain-indices?symbol=FINNIFTY",
    "MIDCPNIFTY": f"{NSE_BASE}/api/option-chain-indices?symbol=MIDCPNIFTY",
}


class NSEScraper:
    def __init__(self) -> None:
        self._session_cookies: dict = {}

    async def _refresh_cookies(self, client: httpx.AsyncClient) -> None:
        r = await client.get(NSE_BASE, headers=NSE_HEADERS, timeout=10)
        self._session_cookies = dict(r.cookies)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def fetch_options_chain(self, underlying: str, expiry: date | None = None) -> OptionsChain | None:
        url = UNDERLYING_URL.get(underlying.upper())
        if not url:
            url = f"{NSE_BASE}/api/option-chain-equities?symbol={underlying.upper()}"

        async with httpx.AsyncClient(timeout=15) as client:
            await self._refresh_cookies(client)
            r = await client.get(url, headers=NSE_HEADERS, cookies=self._session_cookies)
            r.raise_for_status()
            data = r.json()

        return self._parse_chain(underlying, data, expiry)

    def _parse_chain(self, underlying: str, data: dict, target_expiry: date | None) -> OptionsChain | None:
        try:
            records = data["records"]
            spot = records["underlyingValue"]
            expiry_dates = records["expiryDates"]

            if target_expiry:
                expiry_str = target_expiry.strftime("%d-%b-%Y").upper()
            else:
                expiry_str = expiry_dates[0] if expiry_dates else None

            if not expiry_str:
                return None

            strikes: list[OptionStrike] = []
            for row in records.get("data", []):
                if row.get("expiryDate", "").upper() != expiry_str.upper():
                    continue
                strike = row["strikePrice"]
                ce = row.get("CE", {})
                pe = row.get("PE", {})
                strikes.append(OptionStrike(
                    strike=strike,
                    ce_ltp=ce.get("lastPrice"),
                    ce_bid=ce.get("bidprice"),
                    ce_ask=ce.get("askPrice"),
                    ce_oi=ce.get("openInterest"),
                    ce_volume=ce.get("totalTradedVolume"),
                    ce_iv=ce.get("impliedVolatility"),
                    pe_ltp=pe.get("lastPrice"),
                    pe_bid=pe.get("bidprice"),
                    pe_ask=pe.get("askPrice"),
                    pe_oi=pe.get("openInterest"),
                    pe_volume=pe.get("totalTradedVolume"),
                    pe_iv=pe.get("impliedVolatility"),
                ))

            # Parse expiry_str to date
            expiry_date = datetime.strptime(expiry_str, "%d-%b-%Y").date()

            return OptionsChain(
                underlying=underlying,
                expiry=expiry_date.isoformat(),
                spot_price=spot,
                timestamp=datetime.now(),
                strikes=sorted(strikes, key=lambda s: s.strike),
            )
        except Exception:
            logger.exception("nse_chain_parse_error", underlying=underlying)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def fetch_fii_dii(self, trade_date: date | None = None) -> dict | None:
        url = f"{NSE_BASE}/api/fiidiiTradeReact"
        async with httpx.AsyncClient(timeout=10) as client:
            await self._refresh_cookies(client)
            r = await client.get(url, headers=NSE_HEADERS, cookies=self._session_cookies)
            r.raise_for_status()
            rows = r.json()

        if not rows:
            return None

        row = rows[0]  # most recent
        return {
            "date": row.get("date"),
            "fii_net": row.get("fii_index_net"),
            "dii_net": row.get("dii_index_net"),
            "fii_buy": row.get("fii_index_buy"),
            "fii_sell": row.get("fii_index_sell"),
            "dii_buy": row.get("dii_index_buy"),
            "dii_sell": row.get("dii_index_sell"),
        }


_scraper: NSEScraper | None = None


def get_nse_scraper() -> NSEScraper:
    global _scraper
    if _scraper is None:
        _scraper = NSEScraper()
    return _scraper
