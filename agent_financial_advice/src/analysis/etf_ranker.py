"""
ETF Ranker — deterministic, no LLM.
Scores each ETF in the universe based on category scores from SignalMapper,
then enriches top candidates with performance data from MarketDataFetcher.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.fetchers.market_fetcher import MarketData
from src.utils.logger import logger


@dataclass
class ETFCandidate:
    isin: str
    ticker_yahoo: str
    name: str
    provider: str
    category: str
    geography: str
    ter: float
    themes: List[str]
    score: float
    price: Optional[float] = None
    change_1w: Optional[float] = None
    change_1m: Optional[float] = None
    change_3m: Optional[float] = None


class ETFRanker:
    def __init__(self, etf_universe_file: str = "data/etf_universe.yaml"):
        path = Path(etf_universe_file)
        if not path.exists():
            raise FileNotFoundError(f"ETF universe not found: {etf_universe_file}")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self.etfs = raw.get("etfs", [])
        logger.info(f"ETF universe loaded: {len(self.etfs)} ETFs")

    def rank(
        self,
        category_scores: Dict[str, float],
        market_data: MarketData,
        top_n: int = 5,
    ) -> List[ETFCandidate]:
        candidates = []

        for etf in self.etfs:
            if not etf.get("pea_eligible", False):
                continue

            category = etf.get("category", "")
            base_score = category_scores.get(category, 0.0)

            # Slight bonus for lower TER (cost efficiency)
            ter = float(etf.get("ter", 0.5))
            ter_bonus = max(0, (0.5 - ter) * 0.5)  # up to +0.25 for very low TER

            total_score = base_score + ter_bonus

            ticker = etf.get("ticker_yahoo", "")
            price_data = market_data.etf_prices.get(ticker)

            candidates.append(ETFCandidate(
                isin=etf.get("isin", ""),
                ticker_yahoo=ticker,
                name=etf.get("name", ""),
                provider=etf.get("provider", ""),
                category=category,
                geography=etf.get("geography", ""),
                ter=ter,
                themes=etf.get("themes", []),
                score=round(total_score, 3),
                price=price_data.price if price_data else None,
                change_1w=price_data.change_1w if price_data else None,
                change_1m=price_data.change_1m if price_data else None,
                change_3m=price_data.change_3m if price_data else None,
            ))

        # Sort by score descending, then by TER ascending for ties
        candidates.sort(key=lambda c: (-c.score, c.ter))

        top = candidates[:top_n]
        logger.info(f"ETF ranker: selected top {len(top)} candidates (scores: {[c.score for c in top]})")
        return top
