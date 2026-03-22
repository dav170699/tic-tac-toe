"""
Signal Mapper — deterministic, no LLM.
Maps a SignalSet to a score per ETF category using signal_map.yaml.
"""
from collections import defaultdict
from pathlib import Path
from typing import Dict

import yaml

from src.analysis.summarizer import SignalSet
from src.utils.logger import logger


class SignalMapper:
    def __init__(self, signal_map_file: str = "config/signal_map.yaml"):
        path = Path(signal_map_file)
        if not path.exists():
            raise FileNotFoundError(f"Signal map not found: {signal_map_file}")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self.signal_map: Dict = raw.get("signals", {})

    def map(self, signal_set: SignalSet) -> Dict[str, float]:
        """Returns a dict {etf_category: cumulative_score}."""
        scores: Dict[str, float] = defaultdict(float)

        for signal in signal_set.signals:
            mappings = self.signal_map.get(signal.type, [])
            if not mappings:
                logger.debug(f"No mapping for signal type '{signal.type}'")
                continue
            for entry in mappings:
                category = entry.get("category", "")
                score = float(str(entry.get("score", 0)).replace("+", ""))
                scores[category] += score
                logger.debug(f"Signal '{signal.type}' → {category}: {score:+.0f}")

        logger.info(f"Signal mapper: scored {len(scores)} ETF categories")
        return dict(scores)
