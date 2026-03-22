import hashlib
import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional

from src.utils.logger import logger


class Cache:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def get(self, key: str, date_scoped: bool = True) -> Optional[Any]:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if date_scoped and data.get("date") != str(date.today()):
                return None
            return data.get("value")
        except Exception as e:
            logger.debug(f"Cache read error for key={key}: {e}")
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._key_path(key)
        try:
            payload = {"date": str(date.today()), "value": value, "saved_at": datetime.now().isoformat()}
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Cache write error for key={key}: {e}")
