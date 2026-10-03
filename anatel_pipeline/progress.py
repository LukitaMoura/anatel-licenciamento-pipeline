"""Checkpoint por UF: permite retomar a execução de onde parou."""
import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)


class ProgressTracker:
    def __init__(self, path: str):
        self.path = path
        self.states = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f).get("completed_states", {})
        except (OSError, json.JSONDecodeError) as e:
            log.warning("Progresso ilegível, começando do zero: %s", e)
            return {}

    def is_done(self, uf: str) -> bool:
        return self.states.get(uf, {}).get("status") == "success"

    def record(self, uf: str, status: str, elapsed: float, rows: int = 0, error: str = "") -> None:
        entry = {
            "status": status,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if status == "success":
            entry["rows_processed"] = rows
        else:
            entry["error"] = error
        self.states[uf] = entry
        self._save()

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"completed_states": self.states}, f, indent=4, ensure_ascii=False)
