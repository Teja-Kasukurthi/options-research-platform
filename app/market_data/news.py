"""News scraper — Economic Times + MoneyControl headlines."""

from datetime import datetime

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)

ET_MARKETS_URL = "https://economictimes.indiatimes.com/markets/stocks/news"
MC_URL = "https://www.moneycontrol.com/news/business/markets/"


async def _fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers=headers)
        r.raise_for_status()
        return r.text


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
async def fetch_et_headlines(max_items: int = 20) -> list[dict]:
    try:
        html = await _fetch_html(ET_MARKETS_URL)
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for item in soup.select("div.eachStory")[:max_items]:
            a = item.find("a")
            if not a:
                continue
            time_el = item.find("time")
            articles.append({
                "source": "economic_times",
                "title": a.get_text(strip=True),
                "url": "https://economictimes.indiatimes.com" + (a.get("href") or ""),
                "published_at": time_el.get("data-time") if time_el else datetime.now().isoformat(),
            })
        return articles
    except Exception:
        logger.exception("et_scrape_error")
        return []


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
async def fetch_mc_headlines(max_items: int = 20) -> list[dict]:
    try:
        html = await _fetch_html(MC_URL)
        soup = BeautifulSoup(html, "lxml")
        articles = []
        for item in soup.select("li.clearfix")[:max_items]:
            a = item.find("a")
            if not a:
                continue
            articles.append({
                "source": "moneycontrol",
                "title": a.get_text(strip=True),
                "url": a.get("href", ""),
                "published_at": datetime.now().isoformat(),
            })
        return articles
    except Exception:
        logger.exception("mc_scrape_error")
        return []


async def fetch_all_headlines() -> list[dict]:
    et, mc = await asyncio.gather(fetch_et_headlines(), fetch_mc_headlines())
    return et + mc


import asyncio  # noqa: E402 — circular-free at module level
