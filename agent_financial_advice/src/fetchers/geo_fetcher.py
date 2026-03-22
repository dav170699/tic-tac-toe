"""
Geopolitical data fetcher using the GDELT Project API (free, no API key needed).
Returns top geopolitical events ranked by volume and tone.
"""
from dataclasses import dataclass
from typing import List
from urllib.parse import quote

import requests

from src.utils.logger import logger


GDELT_API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"

# Financial/geopolitical themes to monitor in GDELT
GDELT_THEMES = [
    "WAR", "ECON_INFLATION", "ECON_RECESSION", "ECON_REFORM",
    "ENV_GREEN", "UNGP_ENERGY_OIL", "PROTEST", "ELECTION",
    "SANCTION", "TRADE", "NUCLEAR", "MIGRATION",
]

# Countries of interest (FIPS codes)
COUNTRIES_OF_INTEREST = [
    "US", "CH", "RS", "UP", "GM", "FR", "IT", "UK",
    "JA", "CH", "IN", "BR", "SU", "IR", "IZ",
]


@dataclass
class GeoEvent:
    title: str
    url: str
    source: str
    date: str
    tone: float        # negative = negative sentiment
    themes: List[str]
    countries: List[str]


class GeopoliticalFetcher:
    def fetch(self, lookback_days: int = 7, max_events: int = 20) -> List[GeoEvent]:
        logger.info("Fetching geopolitical data from GDELT...")
        events: List[GeoEvent] = []

        # Query GDELT for articles matching financial/geopolitical themes
        query_terms = " OR ".join(GDELT_THEMES[:6])
        timespan = f"{lookback_days * 24}h"

        try:
            params = {
                "query": f"({query_terms}) sourcelang:english",
                "mode": "artlist",
                "maxrecords": max_events,
                "timespan": timespan,
                "format": "json",
                "sort": "tonedesc",  # most negative tone first (crisis events)
            }
            resp = requests.get(GDELT_API_BASE, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            for article in data.get("articles", []):
                url = article.get("url", "")
                if not url:
                    continue
                events.append(GeoEvent(
                    title=article.get("title", ""),
                    url=url,
                    source=article.get("domain", "GDELT"),
                    date=article.get("seendate", ""),
                    tone=float(article.get("tone", 0)),
                    themes=article.get("themes", "").split(";") if article.get("themes") else [],
                    countries=article.get("locations", "").split(";") if article.get("locations") else [],
                ))

            logger.info(f"GDELT: fetched {len(events)} geopolitical events")
        except Exception as e:
            logger.warning(f"GDELT fetch failed: {e}. Using empty geo data.")

        # Fallback: if GDELT fails, try a simpler query
        if not events:
            events = self._fetch_gdelt_simple(lookback_days, max_events)

        return events[:max_events]

    def _fetch_gdelt_simple(self, lookback_days: int, max_events: int) -> List[GeoEvent]:
        """Simplified GDELT query as fallback."""
        try:
            timespan = f"{min(lookback_days * 24, 168)}h"  # max 168h (7 days)
            params = {
                "query": "economy OR war OR inflation OR sanctions sourcelang:english",
                "mode": "artlist",
                "maxrecords": max_events,
                "timespan": timespan,
                "format": "json",
            }
            resp = requests.get(GDELT_API_BASE, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            events = []
            for article in data.get("articles", []):
                url = article.get("url", "")
                if url:
                    events.append(GeoEvent(
                        title=article.get("title", ""),
                        url=url,
                        source=article.get("domain", "GDELT"),
                        date=article.get("seendate", ""),
                        tone=float(article.get("tone", 0)),
                        themes=[],
                        countries=[],
                    ))
            return events
        except Exception as e:
            logger.warning(f"GDELT fallback also failed: {e}")
            return []
