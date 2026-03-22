"""
News fetcher: NewsAPI.org + RSS feeds (Reuters, ECB, Les Echos, Le Monde).
Returns a deduplicated list of Article objects with URL, title, source, and body snippet.
"""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser
import requests

from src.utils.logger import logger


RSS_FEEDS = [
    ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Markets", "https://feeds.reuters.com/reuters/companyNews"),
    ("ECB", "https://www.ecb.europa.eu/rss/fap.html"),
    ("Les Echos Economie", "https://www.lesechos.fr/rss/rss_une.xml"),
    ("Le Monde Economie", "https://www.lemonde.fr/economie/rss_full.xml"),
    ("FT Markets", "https://www.ft.com/markets?format=rss"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
]

NEWSAPI_KEYWORDS = [
    "ETF", "ECB", "Federal Reserve", "inflation", "recession",
    "geopolitics", "eurozone", "interest rates", "stock market",
    "emerging markets", "China economy", "US economy", "energy crisis",
    "Ukraine", "Middle East", "BRICS", "dollar", "euro",
]


@dataclass
class Article:
    title: str
    url: str
    source: str
    published_at: str
    body_snippet: str


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _truncate(text: str, max_chars: int = 500) -> str:
    if not text:
        return ""
    text = text.strip()
    return text[:max_chars] + "..." if len(text) > max_chars else text


class NewsAggregator:
    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key

    def fetch(self, lookback_days: int = 7, max_articles: int = 50) -> List[Article]:
        seen_hashes = set()
        articles: List[Article] = []

        # 1. NewsAPI
        if self.newsapi_key:
            newsapi_articles = self._fetch_newsapi(lookback_days)
            for a in newsapi_articles:
                h = _url_hash(a.url)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    articles.append(a)

        # 2. RSS feeds
        rss_articles = self._fetch_rss()
        for a in rss_articles:
            h = _url_hash(a.url)
            if h not in seen_hashes:
                seen_hashes.add(h)
                articles.append(a)

        articles = articles[:max_articles]
        logger.info(f"News fetched: {len(articles)} unique articles")
        return articles

    def _fetch_newsapi(self, lookback_days: int) -> List[Article]:
        articles = []
        from_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        query = " OR ".join(f'"{kw}"' for kw in NEWSAPI_KEYWORDS[:10])  # API limit

        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "language": "en",
                    "sortBy": "relevancy",
                    "pageSize": 50,
                    "apiKey": self.newsapi_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                url = item.get("url", "")
                if not url or url == "https://removed.com":
                    continue
                articles.append(Article(
                    title=item.get("title", ""),
                    url=url,
                    source=item.get("source", {}).get("name", "NewsAPI"),
                    published_at=item.get("publishedAt", ""),
                    body_snippet=_truncate(item.get("description") or item.get("content") or ""),
                ))

            logger.info(f"NewsAPI: fetched {len(articles)} articles")
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed: {e}")

        return articles

    def _fetch_rss(self) -> List[Article]:
        articles = []
        for feed_name, feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]:  # max 10 per feed
                    url = entry.get("link", "")
                    if not url:
                        continue
                    summary = _truncate(
                        entry.get("summary") or entry.get("description") or ""
                    )
                    published = entry.get("published", entry.get("updated", ""))
                    articles.append(Article(
                        title=entry.get("title", ""),
                        url=url,
                        source=feed_name,
                        published_at=published,
                        body_snippet=summary,
                    ))
            except Exception as e:
                logger.warning(f"RSS feed failed ({feed_name}): {e}")

        logger.info(f"RSS feeds: fetched {len(articles)} articles")
        return articles
