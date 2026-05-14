from datetime import datetime, timezone
from pathlib import Path
import json

from app.services.privacy import mask_sensitive_data


class AnalyticsLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.log_dir / "chat_events.jsonl"
        self.feedback_file = self.log_dir / "feedback.jsonl"

    def log_chat(self, payload: dict) -> None:
        self._append(self.events_file, payload)

    def log_feedback(self, payload: dict) -> None:
        self._append(self.feedback_file, payload)

    def _append(self, path: Path, payload: dict) -> None:
        sanitized = {
            key: mask_sensitive_data(value) if isinstance(value, str) else value
            for key, value in payload.items()
        }
        sanitized["created_at"] = datetime.now(timezone.utc).isoformat()
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(sanitized, ensure_ascii=False) + "\n")

