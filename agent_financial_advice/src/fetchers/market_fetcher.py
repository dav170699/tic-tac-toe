"""
Market data fetcher using yfinance.
Retrieves index performance, VIX, EUR/USD and ETF prices.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from src.utils.logger import logger


INDICES = {
    "CAC40": "^FCHI",
    "STOXX50": "^STOXX50E",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "NIKKEI": "^N225",
    "MSCI_EM": "EEM",
}

VIX_TICKER = "^VIX"
EURUSD_TICKER = "EURUSD=X"


@dataclass
class IndexPerf:
    name: str
    ticker: str
    price: float
    change_1d: Optional[float] = None
    change_1w: Optional[float] = None
    change_1m: Optional[float] = None
    change_3m: Optional[float] = None


@dataclass
class ETFPrice:
    ticker: str
    price: float
    change_1w: Optional[float] = None
    change_1m: Optional[float] = None
    change_3m: Optional[float] = None


@dataclass
class MarketData:
    indices: Dict[str, IndexPerf] = field(default_factory=dict)
    vix: Optional[float] = None
    eur_usd: Optional[float] = None
    etf_prices: Dict[str, ETFPrice] = field(default_factory=dict)


def _pct_change(series: pd.Series, periods: int) -> Optional[float]:
    if len(series) < periods + 1:
        return None
    old = series.iloc[-(periods + 1)]
    new = series.iloc[-1]
    if old == 0:
        return None
    return round((new - old) / old * 100, 2)


class MarketDataFetcher:
    def fetch(self, etf_tickers: List[str]) -> MarketData:
        logger.info("Fetching market data via yfinance...")
        data = MarketData()

        # Fetch indices + VIX + EUR/USD
        all_tickers = list(INDICES.values()) + [VIX_TICKER, EURUSD_TICKER]
        try:
            hist = yf.download(all_tickers, period="3mo", auto_adjust=True, progress=False)
            closes = hist["Close"] if "Close" in hist.columns else hist

            for name, ticker in INDICES.items():
                if ticker in closes.columns:
                    s = closes[ticker].dropna()
                    if len(s) > 0:
                        data.indices[name] = IndexPerf(
                            name=name,
                            ticker=ticker,
                            price=round(float(s.iloc[-1]), 2),
                            change_1d=_pct_change(s, 1),
                            change_1w=_pct_change(s, 5),
                            change_1m=_pct_change(s, 21),
                            change_3m=_pct_change(s, 63),
                        )

            if VIX_TICKER in closes.columns:
                s = closes[VIX_TICKER].dropna()
                if len(s) > 0:
                    data.vix = round(float(s.iloc[-1]), 2)

            if EURUSD_TICKER in closes.columns:
                s = closes[EURUSD_TICKER].dropna()
                if len(s) > 0:
                    data.eur_usd = round(float(s.iloc[-1]), 4)

        except Exception as e:
            logger.warning(f"Failed to fetch index data: {e}")

        # Fetch ETF prices
        if etf_tickers:
            try:
                etf_hist = yf.download(etf_tickers, period="3mo", auto_adjust=True, progress=False)
                etf_closes = etf_hist["Close"] if "Close" in etf_hist.columns else etf_hist

                # Handle single ticker (yfinance returns Series, not DataFrame)
                if isinstance(etf_closes, pd.Series):
                    etf_closes = etf_closes.to_frame(name=etf_tickers[0])

                for ticker in etf_tickers:
                    if ticker in etf_closes.columns:
                        s = etf_closes[ticker].dropna()
                        if len(s) > 0:
                            data.etf_prices[ticker] = ETFPrice(
                                ticker=ticker,
                                price=round(float(s.iloc[-1]), 4),
                                change_1w=_pct_change(s, 5),
                                change_1m=_pct_change(s, 21),
                                change_3m=_pct_change(s, 63),
                            )
            except Exception as e:
                logger.warning(f"Failed to fetch ETF prices: {e}")

        logger.info(
            f"Market data fetched: {len(data.indices)} indices, "
            f"VIX={data.vix}, EUR/USD={data.eur_usd}, "
            f"{len(data.etf_prices)} ETFs"
        )
        return data
