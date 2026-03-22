"""
Claude Call 1 — News Summarizer.
Takes raw articles + geo events and returns a structured SignalSet with:
- identified macro signals (type + geography + rationale)
- approved_sources: list of URLs actually used (anti-hallucination contract)
"""
import json
from dataclasses import dataclass, field
from typing import List, Optional

import anthropic

from src.fetchers.geo_fetcher import GeoEvent
from src.fetchers.news_fetcher import Article
from src.utils.logger import logger

VALID_SIGNAL_TYPES = [
    "equities_positive", "equities_negative", "risk_off", "risk_on",
    "bonds_positive", "inflation_high", "inflation_low",
    "geopolitical_tension", "europe_positive", "europe_negative",
    "asia_positive", "asia_negative", "usd_strong", "usd_weak",
    "energy_transition",
]

VALID_GEOGRAPHIES = ["US", "EU", "EM", "Japan", "China", "Global", "France", "Germany", "UK"]


@dataclass
class Signal:
    type: str
    geographies: List[str]
    rationale: str
    article_urls: List[str]


@dataclass
class SignalSet:
    signals: List[Signal] = field(default_factory=list)
    approved_sources: List[str] = field(default_factory=list)
    raw_summary: str = ""


def _build_prompt(articles: List[Article], geo_events: List[GeoEvent], language: str) -> str:
    lang_instruction = {
        "fr": "Réponds UNIQUEMENT en JSON valide. Les champs 'rationale' doivent être en français.",
        "es": "Responde ÚNICAMENTE en JSON válido. Los campos 'rationale' deben estar en español.",
        "en": "Reply ONLY with valid JSON. The 'rationale' fields must be in English.",
    }.get(language, "Reply ONLY with valid JSON.")

    articles_text = ""
    for i, a in enumerate(articles[:40]):  # cap at 40
        articles_text += (
            f"\n[{i+1}] SOURCE: {a.source} | DATE: {a.published_at}\n"
            f"TITLE: {a.title}\n"
            f"URL: {a.url}\n"
            f"SNIPPET: {a.body_snippet}\n"
        )

    geo_text = ""
    for i, g in enumerate(geo_events[:15]):
        geo_text += (
            f"\n[G{i+1}] SOURCE: {g.source} | TONE: {g.tone:.1f}\n"
            f"TITLE: {g.title}\n"
            f"URL: {g.url}\n"
        )

    valid_types_str = ", ".join(VALID_SIGNAL_TYPES)

    return f"""You are a financial analyst. Analyze the following news articles and geopolitical events to extract macro investment signals.

{lang_instruction}

VALID SIGNAL TYPES: {valid_types_str}
VALID GEOGRAPHIES: {", ".join(VALID_GEOGRAPHIES)}

---
NEWS ARTICLES:
{articles_text}

---
GEOPOLITICAL EVENTS:
{geo_text}

---
Return a JSON object with this exact structure:
{{
  "signals": [
    {{
      "type": "<one of the VALID SIGNAL TYPES>",
      "geographies": ["<one or more VALID GEOGRAPHIES>"],
      "rationale": "<1-2 sentence explanation>",
      "article_urls": ["<URL1>", "<URL2>"]
    }}
  ],
  "approved_sources": ["<all article URLs cited in any signal>"],
  "market_context": "<2-3 paragraph summary of the current macro environment>"
}}

Rules:
- Extract 5 to 10 signals maximum
- Only cite URLs that appear verbatim in the articles/events provided above
- Do NOT invent or guess URLs
- article_urls must be a subset of the URLs in the input
- approved_sources must be the union of all article_urls across all signals
"""


class NewsSummarizer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def summarize(
        self,
        articles: List[Article],
        geo_events: List[GeoEvent],
        language: str = "fr",
    ) -> SignalSet:
        logger.info(f"Claude Call 1: summarizing {len(articles)} articles + {len(geo_events)} geo events...")

        if not articles and not geo_events:
            logger.warning("No input data for summarizer, returning empty SignalSet")
            return SignalSet()

        prompt = _build_prompt(articles, geo_events, language)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system="You are a financial analyst. You always respond with valid JSON only, no markdown, no explanation outside the JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            data = json.loads(raw)
            signals = []
            for s in data.get("signals", []):
                sig_type = s.get("type", "")
                if sig_type not in VALID_SIGNAL_TYPES:
                    logger.warning(f"Unknown signal type '{sig_type}', skipping")
                    continue
                signals.append(Signal(
                    type=sig_type,
                    geographies=s.get("geographies", []),
                    rationale=s.get("rationale", ""),
                    article_urls=s.get("article_urls", []),
                ))

            approved = list(set(data.get("approved_sources", [])))
            market_context = data.get("market_context", "")

            logger.info(f"Summarizer: extracted {len(signals)} signals, {len(approved)} approved sources")
            return SignalSet(signals=signals, approved_sources=approved, raw_summary=market_context)

        except json.JSONDecodeError as e:
            logger.error(f"Summarizer: invalid JSON from Claude: {e}")
            return SignalSet()
        except Exception as e:
            logger.error(f"Summarizer failed: {e}")
            return SignalSet()
